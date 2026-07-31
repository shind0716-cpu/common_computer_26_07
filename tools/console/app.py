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
    # 값은 저자 discussion_setting.json 의 키와 **글자 단위로 같아야 한다.**
    # 종전 "open" 은 그 파일에 없는 키였고(실제 키: open-minded), 재현 트랙에서 고르면
    # debate_engine 의 settings[setting_key] 가 KeyError 로 즉사한다. 저자 저장소가
    # 없어서 재현 트랙 자체가 안 돌던 동안 가려져 있던 버그다(2026-07-30 실측).
    {"key": "persona", "label": "⑥ 성격", "type": "choice",
     "values": ["default", "open-minded", "stubborn"],
     "names": {"default": "기본", "open-minded": "열린", "stubborn": "고집"},
     "help": "재현 트랙(pro/con) 전용 — 협력 조건에는 우리 템플릿에 성격 슬롯이 없어 무시된다."},
    {"key": "ledger_mode", "label": "⑧ 장부", "type": "choice",
     "values": ["off", "v0"],
     "names": {"off": "끔", "v0": "자동 재주입 (소실 팩트 전량 재제시)"},
     "help": "v0 는 라운드마다 판정기를 돈다 — 호출 수가 크게 늘어난다."},
    # ⑨ 추론 모드 (2026-07-30 신설). 종전엔 공급자마다 사고량이 제각각인데 아무도
    # 지정하지 않았고 로그에도 없었다 — Gemini 만 minimal 하드코딩, Anthropic 은
    # 모델 기본값(Sonnet 5 는 adaptive thinking 기본 ON), OpenAI 도 모델 기본값.
    {"key": "reasoning", "label": "⑨ 추론(사고) 모드", "type": "choice",
     "values": ["default", "off", "on"],
     "names": {"default": "지정 안 함 (모델 기본값 — 종전 동작)",
               "off": "끔 (끌 수 있으면 끈다)",
               "on": "켬 (발화 전에 길게 생각)"},
     "help": "'지정 안 함'과 '끔'은 다른 상태다 — 앞은 모델 마음, 뒤는 우리가 정한 것. "
             "⚠ 공급자마다 추론 원문 접근성이 달라 on/off 비교는 같은 공급자 안에서만 유효. "
             "켜면 사고 토큰이 출력 예산을 먹어 본문이 잘릴 수 있어 상한을 함께 올린다(편차 D1)."},
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


def _issue_rows() -> list[dict]:
    """이슈 + 그 배분표의 트랙. 고르기 **전에** 무슨 조건인지 보이게 한다.

    협력(전원 none)이면 수첩·누적창이 가능하고, 재현(pro/con)이면 저자 저장소가
    필요하다 — 이 차이를 UI 가 미리 말하지 않으면 사람이 실행 버튼을 누른 뒤에
    RuntimeError 로 알게 된다(2026-07-30 실측)."""
    rows = []
    for iid in _issues():
        st = _stances_of(iid)
        rows.append({"issue_id": iid, "stances": sorted(s for s in st if s),
                     "coop": bool(st) and st == {"none"},
                     "has_assignment": bool(st)})
    return rows


# 정답 누설 필드 — 시나리오 열람에서 기본 가린다.
# 왜: issue_hire 의 facts 는 favors(어느 후보에게 유리한가)·requirement(어느 요건인가)
# 를 들고 있고, 이건 "정답이 무엇인가"를 사실상 적어둔 칸이다. 사람이 실험 전에
# 이걸 읽으면 조건 설정·프롬프트 손질이 정답 쪽으로 기울 수 있다(관측자 오염).
# 숨기는 게 아니라 **기본은 접고 눌러서 펴게** 한다 — 검수할 땐 봐야 하니까.
ANSWER_KEY_FIELDS = ("favors", "requirement", "side")


def _scenario(issue_id: str, *, reveal: bool = False) -> dict:
    """시나리오 한 벌(원문 + 팩트 + 배분)을 열람용으로 조립한다. 읽기 전용.

    실험을 돌리기 전에 "이 시나리오가 무엇을 묻고, 누가 무엇을 아는가"를 사람이
    확인할 수 있어야 한다. 종전엔 이걸 보려면 data/ 아래 json 3개를 직접 열어야
    했다(민옥 요청 7/30).

    reveal=False(기본)면 정답 누설 필드를 뺀 뒤 돌려준다 — ANSWER_KEY_FIELDS 주석 참조."""
    try:
        iss = json.loads(paths.issue(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(404, f"이슈 원문 없음: {issue_id}")
    try:
        facts = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))["facts"]
    except FileNotFoundError:
        facts = []
    try:
        asg = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError:
        asg = {"agents": []}

    hidden = [k for k in ANSWER_KEY_FIELDS if any(k in f for f in facts)]
    out_facts = []
    for f in facts:
        row = {k: v for k, v in f.items() if reveal or k not in ANSWER_KEY_FIELDS}
        out_facts.append(row)

    # 배분 요약: 누가 몇 개를 쥐고, 공유/미공유가 어떻게 갈리나.
    by_fact = {f["fact_id"]: f for f in facts}
    agents = []
    for a in asg.get("agents", []):
        ids = list(a.get("assigned_fact_ids", []))
        agents.append({
            "agent_id": a.get("agent_id"), "stance": a.get("stance"),
            "perspective": a.get("perspective"), "n_facts": len(ids),
            "assigned_fact_ids": ids,
            "n_unshared": sum(1 for i in ids
                              if by_fact.get(i, {}).get("share") == "unshared"),
        })
    # 고아 팩트 = 아무에게도 안 간 것. 있으면 배분이 잘못된 것이므로 드러낸다.
    assigned = {i for a in asg.get("agents", []) for i in a.get("assigned_fact_ids", [])}
    orphans = [f["fact_id"] for f in facts if f["fact_id"] not in assigned]

    st = {a.get("stance") for a in asg.get("agents", [])}
    return {
        "issue_id": issue_id,
        "title": iss.get("title"), "question": iss.get("question"),
        "body": iss.get("body"), "options": iss.get("options"),
        "source": iss.get("source"),
        "usage_approved": (iss.get("source_meta") or {}).get("usage_approved"),
        "note": iss.get("_note"),
        "n_facts": len(facts),
        "n_critical": sum(1 for f in facts if f.get("critical")),
        "share_counts": {v: sum(1 for f in facts if f.get("share") == v)
                         for v in ("shared", "unshared")
                         if any(f.get("share") == v for f in facts)},
        "facts": out_facts,
        "agents": agents, "orphan_fact_ids": orphans,
        "overlap_k": asg.get("overlap_k"), "assignment_mode": asg.get("created_by"),
        "coop": bool(st) and st == {"none"},
        "stances": sorted(s for s in st if s),
        "hidden_fields": hidden, "revealed": reveal,
    }


@app.get("/api/scenario")
def api_scenario(issue_id: str, reveal: bool = False):
    return _scenario(issue_id, reveal=reveal)


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
def _author_repo_present() -> bool:
    """저자 저장소(DelibTrace) 클론이 있나 — 재현 트랙(pro/con) 실행의 선행 조건.

    authors_prompts.author_dir() 를 그대로 쓴다(경로 규칙을 두 곳에 두면 갈라진다).
    존재 확인만 하고 읽지 않는다 — 읽으면 없을 때 예외가 나서 목록 조회가 죽는다."""
    from modules import authors_prompts
    try:
        return authors_prompts.author_dir().exists()
    except Exception:
        return False


def _author_dir_hint() -> str:
    from modules import authors_prompts
    try:
        d = authors_prompts.DEFAULT_DIR
    except Exception:
        return "DelibTrace 클론 필요"
    return (f"git clone https://github.com/whr000001/DelibTrace.git \"{d}\" "
            f"(또는 환경변수 DELIBTRACE_DIR 지정)")


def _stances_of(issue_id: str) -> set:
    try:
        doc = json.loads(paths.assignment(issue_id).read_text(encoding="utf-8"))
    except Exception:
        return set()
    return {a.get("stance") for a in doc.get("agents", [])}


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
            "issues": _issues(), "issue_rows": _issue_rows(), "runs": _runs(),
            "models": _models(),
            "author_repo": _author_repo_present(),
            "author_hint": _author_dir_hint(),
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
    reasoning: str = "default"
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
        "reasoning": req.reasoning,          # ⑨ 추론 모드
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
    # ── 경고 계산 ────────────────────────────────────────────────────────────
    # 이 이슈가 협력 조건인가(전원 none)를 먼저 정한다 — 그 값이 아래 판정 전부의
    # 전제다. 협력이 아니면 저자 템플릿(discussion_*) 경로로 가고, 그건 저자 저장소
    # 클론을 요구한다.
    coop = stances == {"none"}
    warn, blocking = [], []
    # 온도 관문 (2026-07-30 · 민옥). 범위 밖 온도는 400 이고, 400 은 재시도해도 400 이라
    # 5회 뒤 공백 폴백으로 넘어간다 — 빈 발화 로그가 종료코드 0 으로 완주한다.
    # 엔진의 preflight 도 같은 검사를 하지만, 여기서 먼저 보여주면 버튼을 누르기 전에 안다.
    try:
        llm.check_temperature(req.debate_model, req.debate_temperature)
        llm.check_reasoning(req.debate_model, req.reasoning)
    except SystemExit as e:
        blocking.append(str(e).replace("\n", " "))
    except KeyError as e:
        blocking.append(f"공급자를 알 수 없는 모델 — {e}")
    if req.reasoning == "on":
        warn.append("추론을 켜면 사고 토큰이 출력 예산을 먹어 본문이 잘릴 수 있습니다 "
                    "(편차 D1 — 7/27에 제미나이 팔 전체를 폐기하게 만든 사고). "
                    "상한을 함께 올리고 절단은 예외로 잡지만, 결과 원문을 눈으로 확인하세요.")
    if req.memory == "note" and not coop:
        blocking.append("수첩(memory=note)은 협력 조건 전용 — 저자 템플릿엔 수첩 슬롯이 없어 엔진이 즉사한다.")
    if req.window == "cumulative" and not coop:
        blocking.append("누적 창(window=cumulative)도 협력 조건 전용이다.")
    if not coop:
        # 재현 트랙(pro/con)은 저자 프롬프트를 원본 저장소에서 직접 읽는다
        # (라이선스 보류 — 우리 리포에 복사하지 않는다). 클론이 없으면 실행 도중
        # RuntimeError 로 죽는데, 그때는 이미 사람이 실행 버튼을 누른 뒤다.
        # 그래서 누르기 전에 여기서 알린다(2026-07-30 실측 — issue_esa 로 즉사).
        if not _author_repo_present():
            blocking.append(
                f"이 배분표는 stance={sorted(stances)} (재현 트랙)이라 저자 저장소가 필요하다. "
                f"없으면 실행 즉시 RuntimeError. → {_author_dir_hint()}")
        else:
            warn.append("재현 트랙(pro/con) 조건이다 — 저자 템플릿을 쓰므로 수첩·누적창을 켤 수 없다.")
    return {"agents": n, "total": calls, "breakdown": parts,
            "warnings": warn, "blocking": blocking, "coop": coop,
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

    # 실행 전 차단 — 경고만으로는 부족하다. 사람이 경고를 지나쳐 누를 수 있고,
    # 그러면 엔진이 도중에 죽으며 사람은 스택트레이스를 읽어야 한다.
    # (2026-07-30 실측: issue_esa 를 골라 실행 → authors_prompts RuntimeError)
    try:
        llm.check_temperature(req.debate_model, req.debate_temperature)
        llm.check_reasoning(req.debate_model, req.reasoning)
    except SystemExit as e:
        raise HTTPException(400, str(e))
    stances = _stances_of(req.issue_id)
    if stances and stances != {"none"}:
        if req.memory == "note":
            raise HTTPException(400, "수첩(memory=note)은 협력 조건 전용 — 이 배분표는 "
                                     f"stance={sorted(stances)} 다. 저자 템플릿엔 수첩 슬롯이 없다.")
        if req.window != "rolling":
            raise HTTPException(400, f"window={req.window} 는 협력 조건 전용 — 이 배분표는 "
                                     f"stance={sorted(stances)}(재현 트랙)다.")
        if not _author_repo_present():
            raise HTTPException(400,
                                f"재현 트랙(stance={sorted(stances)})은 저자 저장소가 필요하다. "
                                f"{_author_dir_hint()}")

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
    # 키·온도 관문 (2026-07-30 · 민옥). /api/run 은 엔진 서브프로세스가 preflight 를
    # 부르지만, 개입은 **이 프로세스에서** llm.obtain_response 를 직접 부른다. 그건 어떤
    # 실패도 5회 백오프 뒤 공백으로 폴백하므로, 키가 자리표시자면 "개입 후 판단"이 빈
    # 문자열로 저장되고 화면에는 원본과 다르게 — 즉 "결론이 바뀌었다"로 — 보인다.
    # 인과 개입은 이 창의 존재 이유이므로, 가짜 차이가 나오는 경로를 열어둘 수 없다.
    try:
        llm.preflight(req.debate_model, temperature=req.debate_temperature)
    except SystemExit as e:
        raise HTTPException(400, str(e))
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


# ─── 변종 이슈 파생 (에이전트 수) ────────────────────────────────────────────
# 왜 폼 드롭다운 하나로 안 되는가: 엔진은 에이전트 수를 **배분표에서** 읽는다(config 가
# 아니다). 그래서 "에이전트 수를 바꾼다 = 배분표를 새로 만든다"이고, 같은 issue_id 아래
# 배분표를 갈아치우면 그 이슈로 돌린 과거 run 들이 "어떤 배분이었는지"를 새 파일에
# 잘못 맞춰보게 된다. 그래서 **변종 이슈를 파생**시킨다 — 원문·팩트를 새 id 로 복사하고
# 배분표만 새로 만든다. 과거 run 은 원본 id 아래 그대로 남는다(append-only, 규약 1).
class VariantReq(BaseModel):
    issue_id: str                    # 원본
    suffix: str                      # 새 id 의 꼬리. 예: a6 → issue_hire_a6
    n_agents: int = 4
    seed: int = 42
    mode: str = "split_pairs"        # split_pairs | k_overlap
    overlap_k: int = 1
    stance: str = "none"


@app.post("/api/variant")
def api_variant(req: VariantReq):
    from modules import assignment_gen, validate as validate_mod

    suffix = "".join(c for c in req.suffix if c.isalnum() or c in "-_")
    if not suffix:
        raise HTTPException(400, "꼬리표가 비었다 — 영숫자·하이픈·밑줄만 쓸 수 있다.")
    new_id = f"{req.issue_id}_{suffix}"
    targets = [paths.issue(new_id), paths.facts(new_id), paths.assignment(new_id)]
    exists = [p.name for p in targets if p.exists()]
    if exists:
        raise HTTPException(409, f"이미 있음: {', '.join(exists)} — 덮어쓰지 않는다"
                                 "(append-only). 꼬리표를 바꿔라.")

    try:
        issue_doc = json.loads(paths.issue(req.issue_id).read_text(encoding="utf-8"))
        facts_doc = json.loads(paths.facts(req.issue_id).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise HTTPException(400, f"원본 산출물 없음 — {e}")

    # issue_id 는 세 파일에서 모두 새 id 를 가리켜야 한다. 하나라도 원본 id 가 남으면
    # 엔진이 원본 팩트를 찾아가 배분과 팩트가 어긋난다.
    issue_doc["issue_id"] = new_id
    facts_doc["issue_id"] = new_id
    issue_doc["_note"] = (f"{req.issue_id} 의 변종 (에이전트 {req.n_agents}명 배분). "
                          f"원문·팩트는 원본과 같고 배분표만 다르다. 콘솔 생성.")
    try:
        if req.mode == "split_pairs":
            asg = assignment_gen.generate_split_pairs(
                facts_doc, n_agents=req.n_agents, seed=req.seed,
                overlap_k=req.overlap_k, stance=req.stance)
        else:
            asg = assignment_gen.generate_k_overlap(
                facts_doc, n_agents=req.n_agents, seed=req.seed, overlap_k=req.overlap_k)
    except (ValueError, AssertionError) as e:
        # 생성기가 자기 규칙(같은 요건 2개 금지 등)을 못 지키면 시끄럽게 죽는다.
        raise HTTPException(400, f"배분 생성 실패 — {e}")
    asg["issue_id"] = new_id

    for p, doc in zip(targets, (issue_doc, facts_doc, asg)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # 규칙 3: 산출물을 만들면 자가 검사한다. validate 는 CLI 라 실패 시 SystemExit 이므로
    # 여기서 잡아 400 으로 바꾼다 — 검사에 걸린 파일을 남겨두면 다음 사람이 그걸 쓴다.
    # validate 는 CLI 라 실패 이유를 stdout 에 찍고 SystemExit(1) 로 죽는다. 종료 코드만
    # 보여주면 "— 1" 이 되어 사람이 아무것도 못 하므로, 찍은 문장을 잡아서 돌려준다.
    import contextlib
    import io

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            for p in targets:
                validate_mod.validate(p)
    except SystemExit:
        for p in targets:
            p.unlink(missing_ok=True)
        reason = next((l for l in buf.getvalue().splitlines() if l.startswith("[FAIL]")),
                      buf.getvalue().strip() or "이유 미상")
        raise HTTPException(400, f"생성물이 스키마 검사에 걸려 되돌렸다 — {reason}")

    return {"ok": True, "issue_id": new_id, "n_agents": req.n_agents,
            "files": [p.name for p in targets],
            "unshared_per_agent": [a["assigned_fact_ids"] and sum(
                1 for i in a["assigned_fact_ids"]
                if next((f for f in facts_doc["facts"] if f["fact_id"] == i), {})
                .get("share") == "unshared") for a in asg["agents"]]}


# ─── 채점(FAR) ───────────────────────────────────────────────────────────────
# judge 는 이미 far()·far_by_stage() 를 갖고 있었지만 콘솔이 채점 단계를 안 붙여서,
# 실험을 돌려도 팩트 생존 수치가 나오지 않았다(7/30 실측: 협력 트랙 run 4개 전부
# judgment 없음). 비용이 크므로 자동이 아니라 **버튼 + 예상 콜 수**로 붙인다.
class JudgeReq(BaseModel):
    issue_id: str
    run_id: str
    judge_model: str = "gpt-mini"
    judge_n_votes: int = 3
    offline: bool = False


def _judge_cost(issue_id: str, run_id: str, n_votes: int) -> dict:
    facts = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))["facts"]
    events = _read_events(issue_id, run_id)
    stages = sorted({e["round"] for e in events if e["event"] == "utterance"})
    return {"facts": len(facts), "stages": len(stages), "n_votes": n_votes,
            "total": len(facts) * len(stages) * n_votes}


@app.get("/api/judge/status")
def api_judge_status(issue_id: str, run_id: str, judge_model: str = "gpt-mini",
                     judge_n_votes: int = 3):
    """채점됐나 + 채점하면 몇 콜인가 + 지금 그 모델로 채점이 가능한가."""
    jp = paths.judgment(issue_id, run_id)
    cost = _judge_cost(issue_id, run_id, judge_n_votes)
    ready, reason = True, ""
    try:
        llm.preflight(judge_model, temperature=0)
    except SystemExit as e:
        ready, reason = False, str(e).splitlines()[0]
    except KeyError as e:
        ready, reason = False, str(e)
    return {"judged": jp.exists(), "file": jp.name, "cost": cost,
            "judge_ready": ready, "judge_reason": reason,
            "spec_note": "팀 확정 판정 사양은 Sonnet·temp0·n=3 이다. 다른 공급자로 채점하면 "
                         "judgment 의 prompt_ver 에 +merged_system 이 붙어 잣대가 달랐음이 "
                         "산출물에 남는다(사후 보고 대상)."}


@app.post("/api/judge/run")
def api_judge_run(req: JudgeReq):
    """채점을 서브프로세스로 띄운다. 실행 슬롯은 토론과 공유 — 동시 실행은 비용 사고다."""
    global _proc, _log, _current
    if _proc is not None and _proc.poll() is None:
        raise HTTPException(409, "이미 실행 중 — 끝나거나 중단한 뒤에 다시.")
    if paths.judgment(req.issue_id, req.run_id).exists():
        raise HTTPException(409, f"이미 채점됨: {paths.judgment(req.issue_id, req.run_id).name} "
                                 "— 재채점은 기존 판정을 덮어쓰므로 파일을 먼저 옮겨라"
                                 "(append-only).")
    if not req.offline:
        try:
            llm.preflight(req.judge_model, temperature=0)
        except SystemExit as e:
            raise HTTPException(400, str(e))

    # 판정 조건도 파일로 남긴다 — run config 와 같은 이유(산출물이 자기 잣대를 알아야 한다).
    d = ROOT / "configs" / "console"
    d.mkdir(parents=True, exist_ok=True)
    cfg_path = d / f"judge_{req.run_id}.yaml"
    cfg_path.write_text(
        "# 콘솔 v0 생성 — 채점 조건\n" + yaml.safe_dump(
            {"judge_model": req.judge_model, "judge_temperature": 0,
             "judge_n_votes": req.judge_n_votes},
            allow_unicode=True, sort_keys=False), encoding="utf-8")

    cmd = [sys.executable, "-X", "utf8", "-m", "modules.judge",
           "--issue", req.issue_id, "--run", req.run_id, "--config", str(cfg_path)]
    if req.offline:
        cmd.append("--offline")
    with _log_lock:
        _log = [f"$ {' '.join(cmd)}", f"[config] {cfg_path.relative_to(ROOT)}",
                "[주의] 채점은 팩트×라운드×표 수만큼 호출한다 — 중단하면 처음부터다"
                "(judge 에는 체크포인트가 없다)."]
    _current = {"issue_id": req.issue_id, "run_id": req.run_id,
                "config": str(cfg_path.relative_to(ROOT)), "kind": "judge"}
    _proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", bufsize=1)
    threading.Thread(target=_tail_reader, args=(_proc,), daemon=True).start()
    return {"ok": True, "config": _current["config"]}


@app.get("/api/far")
def api_far(issue_id: str, run_id: str, critical_only: bool = False):
    """판정 파일 → FAR + 조건부 소실률. 계산은 survival.report 에 위임한다(재구현 금지)."""
    from modules import survival

    jp = paths.judgment(issue_id, run_id)
    if not jp.exists():
        raise HTTPException(404, f"채점 안 됨: {jp.name} — 먼저 채점을 돌려라")
    judgment = json.loads(jp.read_text(encoding="utf-8"))
    facts = json.loads(paths.facts(issue_id).read_text(encoding="utf-8"))["facts"]
    facts_by_id = {f["fact_id"]: f for f in facts}
    rep = survival.report(judgment, facts_by_id, critical_only=critical_only)
    return {
        "judge": judgment.get("judge", {}),
        "summary": judgment.get("summary", {}),
        "report": rep,
        "critical_only": critical_only,
        # FAR 수식은 아직 잠정이다(judge.py 머리말 — 노션 확정 대기). 화면이 이걸 감추면
        # 사람이 확정된 수치로 읽는다.
        "far_note": "FAR 수식 방향은 미확정(잠정 정의: status ∉ {mentioned, accepted} = 소실). "
                    "초반 미등장 팩트가 소실로 잡혀 부풀 수 있어 조건부 소실률을 함께 본다.",
    }


@app.get("/", response_class=HTMLResponse)
def index():
    # 캐시 금지 (2026-07-30 · 민옥). 이 화면은 개발 중에 계속 고쳐지는데, 브라우저가
    # 옛 index.html 을 들고 있으면 **고친 기능이 통째로 없는 화면**을 보게 된다 — 서버는
    # 멀쩡한데 사람은 "안 된다"고 판단하게 되는 자리다(실측: FAR 패널을 못 찾음).
    # 서버 자체는 재시작해야 반영된다(uvicorn 은 --reload 없이 모듈을 다시 안 읽는다).
    return HTMLResponse(
        (HERE / "index.html").read_text(encoding="utf-8"),
        headers={"Cache-Control": "no-store, must-revalidate"})
