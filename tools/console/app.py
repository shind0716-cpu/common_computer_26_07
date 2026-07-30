"""[민옥] 실험 콘솔 v0 — 설정 폼 + 실행 + 수첩 매트릭스 + 개입 모드.

왜 요한 님 뷰어(tools/viewer)와 별도 앱인가: 뷰어는 **읽기 전용**이 설계 원칙이고
(§2 경계 원칙 — "어떤 산출물도 쓰지 않고, LLM 호출 0"), 이 콘솔은 실행과 개입을 한다.
쓰는 도구를 읽는 도구 안에 넣으면 그 원칙이 무너진다. 공유 파일 수정은 보드 합의가
필요하다는 규칙 5도 같은 곳을 가리킨다 — 그래서 파일을 건드리지 않고 옆에 세운다.

이 콘솔이 하는 일 4개:
  1. 설정 폼      — 설정 사전 8축을 눌러서 고르고, config yaml 을 만든다
  2. 실행         — 엔진을 **서브프로세스**로 띄우고 콘솔 출력을 실시간으로 보여준다
  3. 수첩 매트릭스 — 에이전트 × 라운드 격자로 수첩 원문을 읽는다(보유 관문의 직접 관측)
  4. 개입 모드     — 수첩을 고쳐 넣고 최종 폴링 1콜만 재실행한다(인과 개입)

왜 서브프로세스인가: 엔진은 LLM 호출을 하고 몇 분씩 돈다. 웹 요청 안에서 돌리면
브라우저가 타임아웃되고, 중간에 끊기면 무엇이 저장됐는지 알 수 없다. 서브프로세스로
띄우면 엔진의 기존 체크포인트(라운드별 flush)가 그대로 작동하고, 콘솔은 로그를 읽는
쪽에 서기만 하면 된다 — 실행 상태의 1급 기록은 여전히 data/debates 의 jsonl 이다.

개입 run 은 별도 run_id + condition 으로 나가고 note_update.origin="intervention" 이
붙는다(스키마 v0.3 §6). 집계에서 기본 제외되는 것은 그 필드 덕분이며, 이 콘솔은
"습관이 아니라 필드"라는 계약을 UI 로 집행한다.

실행(리포 루트에서):
  uvicorn tools.console.app:app --port 8021
  → http://127.0.0.1:8021
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from modules import debate_engine, llm, note_slot, paths

app = FastAPI(title="실험 콘솔 v0")
HERE = Path(__file__).resolve().parent

# 모델 목록의 "키 실재 여부"를 보려면 .env 가 이 프로세스에도 올라와 있어야 한다.
# (엔진은 서브프로세스라 각자 load_dotenv 하지만, 콘솔 UI 표시는 이 프로세스 몫)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
ROOT = paths.ROOT

# ─── 실행 상태 (프로세스 1개만 — 동시 실행은 비용 사고의 지름길) ─────────────
_proc: subprocess.Popen | None = None
_log: list[str] = []
_log_lock = threading.Lock()
_current: dict = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail_reader(p: subprocess.Popen) -> None:
    """서브프로세스 stdout 을 줄 단위로 빨아 _log 에 쌓는다."""
    for line in iter(p.stdout.readline, ""):
        with _log_lock:
            _log.append(line.rstrip("\n"))
    p.stdout.close()


# ─── 설정 사전 8축 — 폼의 단일 소스 ──────────────────────────────────────────
# 이 표가 곧 docs/proposals/EXPERIMENT_SETTINGS_v0.md §2 다. 값 목록을 여기 한 곳에
# 두고 폼·검증·config 생성이 모두 이것을 읽는다(사전과 UI 가 갈라지지 않게).
AXES = [
    {"key": "window", "label": "① 받는 말 — 범위", "type": "choice",
     "values": ["rolling", "cumulative"],
     "names": {"rolling": "직전만 (논문 세팅·재현용)",
               "cumulative": "전부 (회의록 전체 재독 = 온전 대화)"},
     "help": "남의 말이 몇 라운드 전까지 보이나."},
    {"key": "memory", "label": "② 받는 말 — 기억", "type": "choice",
     "values": ["none", "note"],
     "names": {"none": "수첩 없음", "note": "개인 수첩 (스스로 남길 것을 적는다)"},
     "help": "손실을 채널이 아니라 기억에 두는 축. 수첩을 켜면 배정 팩트는 라운드 0에만 나온다."},
    {"key": "note_budget", "label": "└ 수첩 예산(자)", "type": "number", "default": 500,
     "help": "memory=note 일 때만 의미. 250/1000 비교를 조건 이름 밖으로 밀지 않기 위해 별도 칸."},
    {"key": "note_call", "label": "└ 수첩 갱신 호출", "type": "choice",
     "values": ["utterance", "dedicated"],
     "names": {"utterance": "발화에 얹기 (+0콜, 파싱이 계약)",
               "dedicated": "별도 호출 (+에이전트수/라운드, 선별이 깨끗)"},
     "help": "두 방식을 한 run 안에 섞는 것은 계약상 금지. 라운드 0 첫 수첩은 항상 별도 호출."},
    {"key": "rounds", "label": "③ 라운드 수", "type": "number", "default": 3},
    {"key": "structure", "label": "④ 연결 모양", "type": "choice",
     "values": ["full", "line", "tree"],
     "names": {"full": "전원 (기본)", "line": "일렬 (릴레이 비교용)", "tree": "트리"}},
    {"key": "persona", "label": "⑥ 성격", "type": "choice",
     "values": ["default", "open", "stubborn"],
     "names": {"default": "기본", "open": "열린", "stubborn": "고집"},
     "help": "협력(무입장) 조건에서는 사용되지 않는다(우리 템플릿에 성격 슬롯 없음)."},
    {"key": "ledger_mode", "label": "⑧ 장부", "type": "choice",
     "values": ["off", "v0"],
     "names": {"off": "끔", "v0": "자동 재주입 (소실 팩트 전량 재제시)"},
     "help": "v0 는 라운드마다 판정기를 돈다 — 호출 수가 크게 늘어난다."},
    {"key": "final_poll", "label": "최종 폴링", "type": "choice",
     "values": ["yes", "no"], "names": {"yes": "돌린다 (벌거벗은 판단 1콜/인)",
                                        "no": "안 돌린다"},
     "help": "코어 5종의 채점 원자료. LLM judge 불사용이므로 이 응답이 곧 정답 여부."},
]

# ⑤ 입장·⑦ 정보 나누기는 배분표(assignment)가 결정한다 — 콘솔은 배분표를 고치지 않는다.
STATIC_NOTES = [
    "⑤ 입장: 배분표의 stance 가 결정한다(전원 none = 협력 조건). 콘솔은 배분표 무수정.",
    "⑦ 정보 나누기: assignment_gen 으로 미리 만든 배분표를 쓴다(split_pairs 요건 쌍 쪼개기).",
]


def _issues() -> list[str]:
    d = paths.DATA / "issues"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


def _runs() -> list[dict]:
    """data/debates 스캔 → run 목록(최신순). 수첩 유무를 함께 보고한다."""
    d = paths.DATA / "debates"
    out = []
    if not d.exists():
        return out
    for p in sorted(d.glob("debate_*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
        meta, n_notes, rid, iid = None, 0, None, None
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                ev = json.loads(line)
                rid = rid or ev.get("run_id")
                if ev.get("event") == "run_meta":
                    meta = ev
                    iid = ev.get("issue_id")
                elif ev.get("event") == "note_update":
                    n_notes += 1
        except Exception:
            continue
        if iid is None:
            # 구 로그(run_meta 없음): 파일명에서 복원 — debate_<issue>_<run>.jsonl
            stem = p.stem[len("debate_"):]
            if rid and stem.endswith("_" + rid):
                iid = stem[: -len(rid) - 1]
        st = (meta or {}).get("settings", {})
        out.append({
            "file": p.name, "run_id": rid, "issue_id": iid,
            "condition": (meta or {}).get("condition"),
            "window": st.get("window"), "memory": st.get("memory"),
            "rounds": st.get("rounds"), "agents": st.get("agents"),
            "ledger_mode": st.get("ledger_mode"),
            "note_call": st.get("note_call"), "note_budget": st.get("note_budget"),
            "n_notes": n_notes,
        })
    return out


def _read_events(issue_id: str, run_id: str) -> list[dict]:
    p = paths.debate(issue_id, run_id)
    if not p.exists():
        raise HTTPException(404, f"로그 없음: {p.name}")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# ─── API ─────────────────────────────────────────────────────────────────────
def _models() -> list[dict]:
    """고를 수 있는 모델 목록 + **키 실재 여부**.

    키가 없는 모델을 목록에서 숨기지 않고 `ready: false` 로 보여주는 이유: 숨기면
    "왜 GPT가 안 보이지"가 되고, 사람은 코드를 뒤져야 한다. 보이되 왜 못 쓰는지를
    같이 적는 편이 낫다(어느 환경변수가 비었는지까지)."""
    out = []
    for alias in ("claude-haiku", "claude-sonnet", "claude-opus",
                  "gpt-mini", "gemini-flash"):
        try:
            provider = llm.resolve_provider(alias)
        except KeyError:
            continue
        env = llm.PROVIDER_KEY_ENV[provider]
        key = os.environ.get(env, "")
        out.append({"alias": alias, "model_id": llm.resolve_model(alias),
                    "provider": provider, "key_env": env,
                    # 24자 미만은 자리표시자로 본다(preflight 와 같은 기준)
                    "ready": len(key) >= 24,
                    "reason": ("" if len(key) >= 24 else
                               (f"{env} 없음" if not key
                                else f"{env} 가 너무 짧음({len(key)}자 — 자리표시자)"))})
    return out


@app.get("/api/meta")
def api_meta():
    return {"axes": AXES, "static_notes": STATIC_NOTES,
            "issues": _issues(), "runs": _runs(),
            "models": _models(),
            "note_parse_ver": note_slot.NOTE_PARSE_VER}


class RunReq(BaseModel):
    issue_id: str
    run_id: str
    condition: str = ""
    window: str = "rolling"
    memory: str = "none"
    note_budget: int = 500
    note_call: str = "utterance"
    rounds: int = 3
    structure: str = "full"
    persona: str = "default"
    ledger_mode: str = "off"
    final_poll: bool = False
    seed: int = 42
    debate_model: str = "claude-haiku"
    debate_temperature: float = 1.0
    judge_n_votes: int = 3
    max_llm_calls: int | None = None


def _write_config(req: RunReq) -> Path:
    """폼 → config yaml. 콘솔이 만든 config 도 파일로 남긴다 — run_meta.config_ref
    가 이 파일의 sha256 을 찍기 때문에, 파일이 없으면 "조건을 아는 산출물"이 안 된다."""
    cfg = {
        "experiment": f"console_{req.run_id}",
        "condition": req.condition or None,
        "issue_id": req.issue_id, "run_id": req.run_id,
        "seed": req.seed, "rounds": req.rounds, "structure": req.structure,
        "window": req.window, "memory": req.memory,
        "note_budget": req.note_budget, "note_call": req.note_call,
        "final_poll": req.final_poll,
        "persona": req.persona,
        "debate_model": req.debate_model,
        "debate_temperature": req.debate_temperature,
        "judge_model": "claude-sonnet-4-6", "judge_temperature": 0,
        "judge_n_votes": req.judge_n_votes,
        "ledger_mode": req.ledger_mode,
    }
    if req.max_llm_calls:
        cfg["max_llm_calls"] = req.max_llm_calls
    d = ROOT / "configs" / "console"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{req.run_id}.yaml"
    p.write_text("# 콘솔 v0 생성 — 설정 사전 8축 좌표\n" +
                 yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                 encoding="utf-8")
    return p


@app.post("/api/estimate")
def api_estimate(req: RunReq):
    """호출 수 미리보기 — 돌리기 전에 비용을 본다. 엔진의 상한 계산과 같은 식."""
    try:
        assign = json.loads(paths.assignment(req.issue_id).read_text(encoding="utf-8"))
        facts = json.loads(paths.facts(req.issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(400, f"산출물 없음 — {e}")
    n = len(assign["agents"])
    stances = {a.get("stance") for a in assign["agents"]}
    calls = n * (req.rounds + 1)
    parts = [f"발화 {calls}"]
    if req.ledger_mode == "v0":
        j = req.rounds * len(facts["facts"]) * req.judge_n_votes
        calls += j
        parts.append(f"루프판정 {j}")
    if req.memory == "note":
        calls += n
        parts.append(f"라운드0 수첩 {n}")
        if req.note_call == "dedicated":
            dd = n * max(0, req.rounds - 1)
            calls += dd
            parts.append(f"수첩갱신 {dd}")
    if req.final_poll:
        calls += n
        parts.append(f"최종폴링 {n}")
    warn = []
    if req.memory == "note" and stances != {"none"}:
        warn.append("배분표 stance 가 전원 none 이 아니다 — 수첩은 협력 조건 전용이라 엔진이 즉사한다.")
    if req.window == "cumulative" and stances != {"none"}:
        warn.append("누적 창도 협력 조건 전용이다.")
    return {"agents": n, "total": calls, "breakdown": parts, "warnings": warn,
            "stances": sorted(s for s in stances if s)}


@app.post("/api/run")
def api_run(req: RunReq):
    global _proc, _log, _current
    if _proc is not None and _proc.poll() is None:
        raise HTTPException(409, "이미 실행 중 — 끝나거나 중단한 뒤에 다시.")
    out = paths.debate(req.issue_id, req.run_id)
    if out.exists():
        raise HTTPException(409, f"이미 있는 run: {out.name} — run_id 를 바꿔라 "
                                 "(append-only: 기존 기록을 덮어쓰지 않는다)")
    cfg_path = _write_config(req)
    cmd = [sys.executable, "-X", "utf8", "-m", "modules.debate_engine",
           "--issue", req.issue_id, "--run", req.run_id, "--config", str(cfg_path)]
    with _log_lock:
        _log = [f"$ {' '.join(cmd)}",
                f"[config] {cfg_path.relative_to(ROOT)}"]
    _current = {"issue_id": req.issue_id, "run_id": req.run_id,
                "config": str(cfg_path.relative_to(ROOT))}
    _proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", bufsize=1)
    threading.Thread(target=_tail_reader, args=(_proc,), daemon=True).start()
    return {"ok": True, "config": _current["config"], "out": out.name}


@app.get("/api/log")
def api_log(since: int = 0):
    with _log_lock:
        lines = _log[since:]
        total = len(_log)
    alive = _proc is not None and _proc.poll() is None
    code = None if (_proc is None or alive) else _proc.returncode
    return {"lines": lines, "next": total, "alive": alive, "returncode": code,
            "current": _current}


@app.post("/api/stop")
def api_stop():
    if _proc is None or _proc.poll() is not None:
        return {"ok": False, "msg": "실행 중이 아님"}
    _proc.terminate()
    # 체크포인트는 엔진이 라운드마다 flush 하므로 중단해도 그때까지는 남는다.
    return {"ok": True, "msg": "중단 요청 — 마지막 체크포인트까지는 저장됨"}


@app.get("/api/notes")
def api_notes(issue_id: str, run_id: str):
    """수첩 매트릭스 = 에이전트 × 라운드. 사건(note_update)에서 상태를 만든다
    (스키마 v0.3 §2: 사건이 1급, 상태는 뷰 — 그래서 여기서 계산하고 저장하지 않는다)."""
    events = _read_events(issue_id, run_id)
    meta = next((e for e in events if e["event"] == "run_meta"), {})
    st = meta.get("settings", {})
    agents, note_rounds, say_rounds = [], set(), set()
    cells, says = {}, {}
    for e in events:
        if e["event"] == "utterance":
            if e["agent_id"] not in agents:
                agents.append(e["agent_id"])
            says[(e["agent_id"], e["round"])] = e.get("response_text")
            say_rounds.add(e["round"])
        elif e["event"] == "note_update":
            cells[(e["agent_id"], e["round"])] = {
                "text": e["note_text"], "origin": e["origin"], "source": e["source"],
                "len": len(e["note_text"] or ""), "ts": e["ts"]}
            note_rounds.add(e["round"])
    polls = {e["agent_id"]: e.get("response_text")
             for e in events if e["event"] == "final_poll"}
    return {
        "settings": st, "condition": meta.get("condition"),
        "agents": sorted(agents),
        "note_rounds": sorted(note_rounds), "say_rounds": sorted(say_rounds),
        "cells": [{"agent_id": a, "round": r, **v} for (a, r), v in sorted(cells.items())],
        "says": [{"agent_id": a, "round": r, "text": t}
                 for (a, r), t in sorted(says.items())],
        "polls": polls,
    }


class InterveneReq(BaseModel):
    issue_id: str
    run_id: str            # 원본 run
    new_run_id: str        # 개입 run (별도 기록)
    notes: dict            # {agent_id: 고친 수첩 텍스트}
    debate_model: str = "claude-haiku"
    debate_temperature: float = 1.0


@app.post("/api/intervene")
def api_intervene(req: InterveneReq):
    """개입 창 — 수첩을 사람이 고쳐 넣고 **최종 폴링 1콜만** 재실행한다.

    설계 원칙 4(설정 사전 §2-2): "수첩에서 특정 팩트를 지우고 재실행하면 결론이
    바뀌나." 수첩이 조립 명세의 슬롯이기 때문에 가능한 인과 개입이다.

    계약 집행 3가지:
      · 새 run_id 로 나간다 — 원본 로그를 건드리지 않는다(append-only, 규칙 1)
      · note_update.origin="intervention" — 집계 기본 제외가 습관이 아니라 필드(§6)
      · condition 에 개입 표시 — 로그만 보고 구분 가능해야 한다(§6)
    """
    src = _read_events(req.issue_id, req.run_id)
    meta = next((e for e in src if e["event"] == "run_meta"), None)
    if meta is None:
        raise HTTPException(400, "원본 run 에 run_meta 없음 — 조건을 알 수 없는 로그로는 개입 불가")
    out = paths.debate(req.issue_id, req.new_run_id)
    if out.exists():
        raise HTTPException(409, f"이미 있는 run: {out.name}")

    issue = json.loads(paths.issue(req.issue_id).read_text(encoding="utf-8"))
    question = issue.get("question") or issue["title"]
    body = issue.get("body", "")

    # 원본의 마지막 수첩 판본을 시작점으로, 사람이 고친 것만 갈아 끼운다.
    last_note, last_round = {}, {}
    for e in src:
        if e["event"] == "note_update":
            last_note[e["agent_id"]] = e["note_text"]
            last_round[e["agent_id"]] = e["round"]
    if not last_note:
        raise HTTPException(400, "원본에 수첩이 없다 — 개입 창은 수첩 조건 전용")

    events = []

    def emit(event, **f):
        events.append({"event": event, "run_id": req.new_run_id, "ts": _now(), **f})

    st = dict(meta.get("settings", {}))
    st["intervention_of"] = req.run_id     # 어느 run 에서 갈라졌나
    emit("run_meta", issue_id=req.issue_id,
         condition=f"{meta.get('condition') or 'unknown'}+intervention",
         config_ref={"name": f"intervention_of_{req.run_id}", "sha256": None},
         settings=st)

    changed, results = [], {}
    for aid in sorted(last_note):
        note_text = last_note[aid]
        new_text = req.notes.get(aid, note_text)
        if new_text != note_text:
            changed.append(aid)
        # 개입 run 의 수첩도 note_update 로 기록한다 — 재조립 계약이 성립해야 하고,
        # origin 이 model 이 아니라는 것이 로그에 남아야 한다.
        emit("note_update", agent_id=aid, round=last_round[aid],
             note_text=new_text, origin="intervention", source="dedicated")
        f_inputs = debate_engine.assemble_coop_final(
            question, body, f"[당신의 수첩]\n{new_text or ''}\n")
        resp = llm.obtain_response(f_inputs, model=req.debate_model,
                                   temperature=req.debate_temperature)
        h = debate_engine.sha256(f_inputs)
        emit("prompt_assembly", round=last_round[aid] + 1, agent_id=aid,
             template="coop_final", prompt_ver=None, setting_key=None,
             slots={"note": {"agent_id": aid, "source_round": last_round[aid]},
                    "others": [], "previous": None, "assigned_fact_ids": [],
                    "inject": None},
             prompt_hash=h)
        emit("final_poll", agent_id=aid, round=last_round[aid] + 1,
             prompt_ver=None, prompt_hash=h,
             model=llm.resolve_model(req.debate_model),
             temperature=req.debate_temperature, response_text=resp)
        results[aid] = resp

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in events:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 원본 폴링과 나란히 돌려준다 — 바뀌었나가 이 창의 유일한 질문이다.
    before = {e["agent_id"]: e.get("response_text")
              for e in src if e["event"] == "final_poll"}
    return {"ok": True, "file": out.name, "changed_agents": changed,
            "before": before, "after": results}


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "index.html").read_text(encoding="utf-8")
