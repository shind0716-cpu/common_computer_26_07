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
import re
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

from modules import debate_engine, llm, note_slot, paths, scenario_gate

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

# 콘솔이 만드는 config 의 저장처. 함수 안 하드코딩이 아니라 모듈 변수인 이유:
# 테스트가 임시 폴더로 갈아끼운다(SOLO_DIR·paths.DATA 전례). 종전엔 두 라우트가 각자
# ROOT/configs/console 을 조립해서, paths.DATA 만 갈아끼운 테스트의 픽스처 config
# (pilot_fixture.yaml 등)가 실제 리포에 남았다 — 2026-08-20 실측 잔재 2건 삭제.
CONFIG_DIR = ROOT / "configs" / "console"


def _cfg_ref(p: Path) -> str:
    """config 경로의 표시·응답용 문자열. 리포 안이면 상대경로(종전 동작), 테스트가
    CONFIG_DIR 를 리포 밖 임시 폴더로 갈아끼웠으면 절대경로 — relative_to 로 죽지 않는다."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)

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
    """확증 승인 또는 기계검증된 pilot 후보를 반환한다.

    파일 존재는 감사 대상 발견에만 쓰고, 실행 가능성은 각 gate 결과가 결정한다.
    """
    confirmatory = {r.issue_id for r in scenario_gate.registry_results() if r.allowed}
    pilot = {r.issue_id for r in scenario_gate.pilot_results() if r.allowed}
    return sorted(confirmatory | pilot)


def _issue_rows() -> list[dict]:
    """이슈 + 그 배분표의 트랙. 고르기 **전에** 무슨 조건인지 보이게 한다.

    협력(전원 none)이면 수첩·누적창이 가능하고, 재현(pro/con)이면 저자 저장소가
    필요하다 — 이 차이를 UI 가 미리 말하지 않으면 사람이 실행 버튼을 누른 뒤에
    RuntimeError 로 알게 된다(2026-07-30 실측)."""
    rows = []
    confirmatory = {r.issue_id: r for r in scenario_gate.registry_results() if r.allowed}
    pilot = {r.issue_id: r for r in scenario_gate.pilot_results() if r.allowed}
    for iid in sorted(set(confirmatory) | set(pilot)):
        result = confirmatory.get(iid) or pilot[iid]
        st = _stances_of(iid)
        rows.append({"issue_id": iid, "stances": sorted(s for s in st if s),
                     "coop": bool(st) and st == {"none"},
                     "has_assignment": bool(st),
                     "promotion_state": result.state,
                     "promotion_tier": ("confirmatory" if iid in confirmatory
                                        else "pilot_unvetted"),
                     "outcome_policy": result.outcome_policy,
                     "promotion_warnings": result.warnings})
    return rows


# 정답 누설 필드 — 시나리오 열람에서 기본 가린다.
# 왜: issue_hire 의 facts 는 favors(어느 후보에게 유리한가)·requirement(어느 요건인가)
# 를 들고 있고, 이건 "정답이 무엇인가"를 사실상 적어둔 칸이다. 사람이 실험 전에
# 이걸 읽으면 조건 설정·프롬프트 손질이 정답 쪽으로 기울 수 있다(관측자 오염).
# 숨기는 게 아니라 **기본은 접고 눌러서 펴게** 한다 — 검수할 땐 봐야 하니까.
ANSWER_KEY_FIELDS = ("favors", "requirement", "side")

# 2026-08-19 — 필드 하나를 더하는 땜질 대신 **밑줄로 시작하는 메타 필드 전부**를 가린다.
# 계기: 요한 측 재료의 팩트에 `_unfavorable_to`(어느 입장에 불리한가)가 있는데 위 목록에
# 없어 그대로 노출됐다. 이름을 하나씩 쫓아다니면 새 재료가 올 때마다 같은 구멍이 난다.
#
# 밑줄 필드가 설계 메모라는 근거(실측): `issue_camp.json` 의 `_note` 에
# "정답=무레온(요건 3/4 충족)" 이 적혀 있다 — 팩트 필드보다 이쪽이 더 직접적인 누설이었다.
# 그래서 팩트 필드뿐 아니라 **이슈 `_note`** 도 reveal 일 때만 내보낸다.
def _is_answer_key(field: str) -> bool:
    return field in ANSWER_KEY_FIELDS or field.startswith("_")


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

    hidden = sorted({k for f in facts for k in f if _is_answer_key(k)})
    if iss.get("_note") is not None and not reveal:
        hidden.append("issue._note")
    out_facts = []
    for f in facts:
        row = {k: v for k, v in f.items() if reveal or not _is_answer_key(k)}
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
        # 이슈 _note 는 설계 메모라 정답이 적혀 있다(camp: "정답=무레온") — reveal 일 때만.
        "note": (iss.get("_note") if reveal else None),
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


def _require_source_tier(issue_id: str, meta: dict | None, *, expected_calls: int,
                         max_calls: int | None, requested_metric: str | None = None):
    """후속 과금 경로가 원본 run의 tier를 상속하도록 실행 직전 재검증한다."""
    tier = (meta or {}).get("promotion_tier", "confirmatory")
    if tier == "pilot_unvetted":
        gate = scenario_gate.evaluate_pilot(
            issue_id, expected_calls=expected_calls, max_calls=max_calls,
            requested_metric=requested_metric)
    elif tier == "confirmatory":
        gate = scenario_gate.require(issue_id, requested_metric=requested_metric)
    else:
        raise HTTPException(400, f"원본 run의 promotion_tier를 알 수 없음: {tier!r}")
    if not gate.allowed:
        raise HTTPException(400, "scenario tier gate blocked — "
                            + "; ".join(gate.blocking_reasons))
    return gate


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
            "scenario_gate_rows": [r.to_dict() for r in scenario_gate.registry_results()],
            "pilot_gate_rows": [r.to_dict() for r in scenario_gate.pilot_results()],
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
    promotion_tier: str = "confirmatory"
    # descriptive_stance_only 에 accuracy를 요청하는 API 직접 호출을 기계적으로 막는다.
    outcome_metric: str | None = None


def _write_config(req: RunReq) -> Path:
    """폼 → config yaml. 콘솔이 만든 config 도 파일로 남긴다 — run_meta.config_ref
    가 이 파일의 sha256 을 찍기 때문에, 파일이 없으면 "조건을 아는 산출물"이 안 된다."""
    is_pilot = req.promotion_tier == "pilot_unvetted"
    condition = req.condition or None
    if is_pilot:
        condition = f"pilot/{req.condition or 'unspecified'}"
    cfg = {
        "experiment": f"console_{req.run_id}",
        "condition": condition,
        "promotion_tier": req.promotion_tier,
        "aggregate_eligible": not is_pilot,
        "report_eligible": not is_pilot,
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
    d = CONFIG_DIR
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
    # 목록을 통과했더라도 버튼을 누르는 사이 파일/manifest가 바뀔 수 있다. 실행 입구에서
    # 같은 gate를 독립 재검사하고, 실패하면 config 작성·Popen·LLM 호출 전에 끝낸다.
    if req.promotion_tier == "pilot_unvetted":
        estimate = api_estimate(req)
        if estimate.get("blocking"):
            raise HTTPException(400, "pilot preflight blocked — "
                                + "; ".join(estimate["blocking"]))
        promotion = scenario_gate.evaluate_pilot(
            req.issue_id,
            expected_calls=estimate["total"],
            max_calls=req.max_llm_calls,
            requested_metric=req.outcome_metric,
        )
    elif req.promotion_tier == "confirmatory":
        promotion = scenario_gate.require(req.issue_id, requested_metric=req.outcome_metric)
    else:
        raise HTTPException(400, f"unknown promotion_tier: {req.promotion_tier!r}")
    if not promotion.allowed:
        raise HTTPException(400, "scenario promotion gate blocked — "
                            + "; ".join(promotion.blocking_reasons))
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
                f"[config] {_cfg_ref(cfg_path)}"]
    _current = {"issue_id": req.issue_id, "run_id": req.run_id,
                "config": _cfg_ref(cfg_path)}
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
    max_llm_calls: int | None = None


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

    # 재료/tier/call budget을 API 키 조회나 provider 호출보다 먼저 검사한다.
    gate = _require_source_tier(
        req.issue_id, meta, expected_calls=len(last_note), max_calls=req.max_llm_calls)
    # 개입은 이 프로세스에서 llm.obtain_response를 직접 부르므로 여기서 key/temp를 검사한다.
    try:
        llm.preflight(req.debate_model, temperature=req.debate_temperature)
    except SystemExit as e:
        raise HTTPException(400, str(e))

    events = []

    def emit(event, **f):
        events.append({"event": event, "run_id": req.new_run_id, "ts": _now(), **f})

    st = dict(meta.get("settings", {}))
    st["intervention_of"] = req.run_id     # 어느 run 에서 갈라졌나
    source_tier = meta.get("promotion_tier") or "confirmatory"
    emit("run_meta", issue_id=req.issue_id,
         condition=f"{meta.get('condition') or 'unknown'}+intervention",
         promotion_tier=source_tier,
         aggregate_eligible=bool(meta.get("aggregate_eligible", source_tier != "pilot_unvetted")),
         report_eligible=bool(meta.get("report_eligible", source_tier != "pilot_unvetted")),
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
    max_llm_calls: int | None = None


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
    source_events = _read_events(req.issue_id, req.run_id)
    source_meta = next((e for e in source_events if e.get("event") == "run_meta"), None)
    cost = _judge_cost(req.issue_id, req.run_id, req.judge_n_votes)
    gate = _require_source_tier(
        req.issue_id, source_meta,
        expected_calls=0 if req.offline else cost["total"],
        max_calls=(req.max_llm_calls if not req.offline
                   else (req.max_llm_calls or scenario_gate.PILOT_CALL_LIMIT)),
    )
    source_tier = (source_meta or {}).get("promotion_tier", "confirmatory")
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
    d = CONFIG_DIR
    d.mkdir(parents=True, exist_ok=True)
    cfg_path = d / f"judge_{req.run_id}.yaml"
    cfg_path.write_text(
        "# 콘솔 v0 생성 — 채점 조건\n" + yaml.safe_dump(
            {"judge_model": req.judge_model, "judge_temperature": 0,
             "judge_n_votes": req.judge_n_votes,
             "promotion_tier": source_tier,
             "aggregate_eligible": source_tier != "pilot_unvetted",
             "report_eligible": source_tier != "pilot_unvetted",
             "max_llm_calls": (0 if req.offline else req.max_llm_calls)},
            allow_unicode=True, sort_keys=False), encoding="utf-8")

    cmd = [sys.executable, "-X", "utf8", "-m", "modules.judge",
           "--issue", req.issue_id, "--run", req.run_id, "--config", str(cfg_path)]
    if req.offline:
        cmd.append("--offline")
    with _log_lock:
        _log = [f"$ {' '.join(cmd)}", f"[config] {_cfg_ref(cfg_path)}",
                "[주의] 채점은 팩트×라운드×표 수만큼 호출한다 — 중단하면 처음부터다"
                "(judge 에는 체크포인트가 없다)."]
    _current = {"issue_id": req.issue_id, "run_id": req.run_id,
                "config": _cfg_ref(cfg_path), "kind": "judge"}
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


# ═══ 단독 실험 (experiments/memory_structure) — WORKORDER_SOLO_TAB 2026-08-18 ═══
# 이 아래는 전부 **추가**다 — 기존 debate 라우트·동작은 건드리지 않는다(워크오더 §2-1).
# 콘솔은 러너(run_solo.py)를 서브프로세스로 부르고 산출물을 **읽기만** 한다(§2-2).
# 러너 인터페이스가 부족하면 여기서 고치지 말고 보고한다.

# solo 산출물 경로 — 상수 한 곳(§2-4: paths.py 무수정, 콘솔 로컬 상수).
# 함수가 아니라 모듈 변수인 이유: 테스트가 임시 폴더로 갈아끼운다(paths.DATA 전례).
SOLO_DIR = ROOT / "experiments" / "memory_structure"

# run_solo.py --model 값 (llm.py 별칭). claude 두 종은 2026-08-24 추가 — Anthropic 키
# 도입 예정에 따라 미리 목록에 올린다. 키가 .env 에 없으면 ready:false 로 회색 표시되고
# 실행은 preflight 가 막는다(숨기지 않고 왜 못 쓰는지 보여주는 _models 원칙 그대로).
# claude-opus 는 비용 때문에 일부러 뺐다 — 필요하면 여기 한 줄.
SOLO_MODELS = ("gpt", "gemini-flash", "claude-haiku", "claude-sonnet")
SOLO_ARMS = {"A": "반복", "P": "전진(A′)", "B": "숙의"}
SOLO_MEMS = {"full": "전체", "note": "수첩", "prev": "직전만"}
SOLO_BUDGETS = (500, 250, 125, 60)               # 수첩 예산 스윕 후보 (500 = v1 기본)
SOLO_DEFAULT_BUDGET = 500                        # run_solo.DEFAULT_NOTE_BUDGET 미러
SOLO_DEFAULT_ISSUE = "issue_camp"                # run_solo.DEFAULT_ISSUE 미러
# 재료 이슈와 그 입장 목록 — run_solo.ISSUE_PROMPTS 미러(그쪽이 정본).
# 입장이 하나뿐이면 폼에서 입장 칸을 감춘다.
SOLO_ISSUES = {
    "issue_camp": ["fixed"],
    "issue_throne": ["fixed"],
    "issue_polar": ["후송", "대기"],
    "issue_exile": ["추방", "잔류"],
}
SOLO_STAGES = ("essay_r0", "essay_r1", "essay_r2", "essay_r3", "carrier")

# 실행 슬롯 락 (적대적 리뷰 ① 2026-08-19 · 치명). 409 검사와 _proc 대입 사이가
# 무방비면(FastAPI sync 라우트 = 스레드풀 동시 실행) 더블클릭 두 요청이 모두 관문을
# 통과해 실호출 러너 2개가 뜬다 — 같은 체크포인트에 교차 기록(오염)·이중 과금·첫
# 프로세스는 /api/stop 도 못 잡는 고아. solo 경로만 원자화한다(기존 debate 라우트
# 무수정 — §2-1). debate 쪽도 같은 구조의 창이 있으나 그건 보고 대상.
_run_lock = threading.Lock()

# model·run_id 는 경로에 결합되므로 경로 문자를 받지 않는다 (리뷰 ⑧ — '..'/'/' 로
# runs/ 밖 임의 .json 이 읽히는 상위 탈출 차단. 점(.)도 통째로 제외해 '..' 자체가 불가).
_SOLO_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")


def _solo_check_names(model: str, run_id: str) -> None:
    if not (_SOLO_NAME_RE.fullmatch(model) and _SOLO_NAME_RE.fullmatch(run_id)):
        raise HTTPException(400, "model·run_id 는 영숫자·밑줄·하이픈만 받는다 — "
                                 "경로 문자('/', '..', '\\')는 산출물 폴더 밖을 가리킬 수 있다.")


def _solo_runs_dir(dry: bool) -> Path:
    d = SOLO_DIR / "runs"
    return d / "_dry" if dry else d


def _solo_judgments_dir() -> Path:
    return SOLO_DIR / "judgments"


class SoloRunReq(BaseModel):
    model: str = "gpt"
    # 재료 이슈 (2026-08-19) — run_solo.py --issue 와 연결. 기본값이면 종전과 동일 동작.
    # 입장 대립형 재료(issue_polar·issue_exile)는 stance_key 가 있어야 러너가 받는다.
    issue: str = SOLO_DEFAULT_ISSUE
    stance_key: str | None = None
    arms: list[str] = ["A", "P", "B"]
    memories: list[str] = ["full", "note", "prev"]
    reps: list[int] = [1, 2, 3]
    note_budget: int = SOLO_DEFAULT_BUDGET
    facts_reverse: bool = False
    # --no-stance --final-poll 묶음 토글. 러너가 final_poll 단독을 즉사시키므로
    # (입장 고정 상태의 최종 판단은 설계상 무의미) 폼도 같은 제약을 한 칸으로 집행한다.
    ns_final_poll: bool = False
    dry: bool = False
    # "PROMPTS_v2·PREREG_v2 를 로컬 커밋했다"는 **사람의 확인**. UI 가 자동으로 켜면
    # 사전등록 관문이 장식이 된다 — 기본 False, 체크 시에만 --allow-v2 가 붙는다(§1·§2-3).
    prereg_confirmed: bool = False
    promotion_tier: str = "confirmatory"
    max_llm_calls: int | None = None


def _solo_v2_reasons(req: SoloRunReq) -> list[str]:
    """v2 사유 목록 — 비면 v1 기본 조건. 러너의 is_v2 판정(run_solo.main)과 같은 식."""
    reasons = []
    if req.note_budget != SOLO_DEFAULT_BUDGET:
        reasons.append(f"수첩 예산 {req.note_budget}")
    if req.facts_reverse:
        reasons.append("사실 역순")
    if req.ns_final_poll:
        reasons.append("입장 해제+최종 판단")
    return reasons


def _solo_suffix(req: SoloRunReq) -> str:
    """산출물 run_id 접미사 미리보기 — run_solo._variant_suffix 와 같은 규칙."""
    parts = []
    if req.note_budget != SOLO_DEFAULT_BUDGET:
        parts.append(f"b{req.note_budget}")
    if req.facts_reverse:
        parts.append("rev")
    if req.ns_final_poll:
        parts.append("ns")
    return ("_" + "_".join(parts)) if parts else ""


def _solo_run_base(req: SoloRunReq, dry: bool = False) -> Path:
    """이 요청의 산출물이 놓이는 폴더 — 러너 run_one 의 out_dir 규칙과 같다.
    camp 은 종전 경로, 그 외는 이슈 하위 폴더(run_id 에 이슈가 없어 안 나누면 파일명이 겹친다)."""
    d = _solo_runs_dir(dry) / req.model
    return d if req.issue == SOLO_DEFAULT_ISSUE else d / req.issue


def _solo_validate(req: SoloRunReq) -> None:
    if req.model not in SOLO_MODELS:
        raise HTTPException(400, f"모르는 모델: {req.model} (가능: {', '.join(SOLO_MODELS)})")
    # 이슈·입장 어휘 검사 — 러너도 즉사시키지만, 실행 버튼을 누른 뒤가 아니라 여기서 알린다.
    if req.issue not in SOLO_ISSUES:
        raise HTTPException(400, f"모르는 이슈: {req.issue} (가능: {', '.join(SOLO_ISSUES)})")
    stances = SOLO_ISSUES[req.issue]
    if len(stances) > 1 and req.stance_key not in stances:
        raise HTTPException(400, f"{req.issue} 는 입장을 골라야 합니다 (가능: {', '.join(stances)})")
    if len(stances) == 1 and req.stance_key not in (None, stances[0]):
        raise HTTPException(400, f"{req.issue} 는 입장이 하나뿐입니다 — stance_key 를 비워두세요")
    if not (req.arms and req.memories and req.reps):
        raise HTTPException(400, "진행/기억/반복을 하나 이상 고르세요.")
    bad = ([a for a in req.arms if a not in SOLO_ARMS]
           + [m for m in req.memories if m not in SOLO_MEMS])
    if bad:
        raise HTTPException(400, f"모르는 조건: {bad}")
    # 예산 어휘 검사 (리뷰 ⑨): UI 는 select 라 안전하지만 API 직접 호출의 오타(250→50,
    # 2500)가 사전등록에 없는 예산의 v2 산출물을 과금과 함께 만든다. 러너(수정 금지)는
    # 예산값을 검증하지 않으므로 콘솔이 유일한 방어선이다.
    if req.note_budget not in SOLO_BUDGETS:
        raise HTTPException(400, f"모르는 수첩 예산: {req.note_budget} "
                                 f"(가능: {'/'.join(map(str, SOLO_BUDGETS))} — 워크오더 §1)")


def _solo_planned_ids(req: SoloRunReq) -> list[str]:
    """이 요청이 만들 run_id 목록 — 러너의 run_id 조립식(run_one)과 같은 규칙."""
    sfx = _solo_suffix(req)
    return [f"{a}_{m}{sfx}_rep{n}"
            for a in req.arms for m in req.memories for n in req.reps]


@app.get("/api/solo/meta")
def api_solo_meta():
    """폼의 단일 소스 — 조건 어휘 + 모델 키 실재 여부(_models 와 같은 기준: 24자 미만
    은 자리표시자). 러너 파일 존재도 함께 — 없으면 실행 버튼이 눌리기 전에 안다.

    SOLO_ISSUES는 러너 어휘일 뿐 승인 목록이 아니다. 현재 registry 바이트에 대한 기계 게이트를
    다시 평가해 승인된 issue만 선택지로 내보내고, 차단 사유는 별도 행으로 보존한다."""
    models = []
    for key in SOLO_MODELS:
        try:
            provider = llm.resolve_provider(key)
        except KeyError:
            continue
        env = llm.PROVIDER_KEY_ENV[provider]
        val = os.environ.get(env, "")
        models.append({"key": key, "model_id": llm.resolve_model(key),
                       "provider": provider, "key_env": env,
                       "ready": len(val) >= 24,
                       "reason": ("" if len(val) >= 24 else
                                  (f"{env} 없음" if not val
                                   else f"{env} 가 너무 짧음({len(val)}자 — 자리표시자)"))})
    gate_results = [scenario_gate.evaluate(issue_id) for issue_id in SOLO_ISSUES]
    # 등급 분리(결정 패킷 G-0A·G-1A, 2026-08-20 owner 서명): 확증 승인이 없어도 파일럿
    # 기계검증을 통과한 재료는 선택지에 나온다. /api/solo/run 이 tier 별 게이트를 독립
    # 재검사하므로 이 목록은 후보 표시일 뿐 실행권한이 아니다(안전 수정 조항).
    pilot_gate_results = [
        scenario_gate.evaluate_pilot(issue_id, expected_calls=0,
                                     max_calls=scenario_gate.PILOT_CALL_LIMIT)
        for issue_id in SOLO_ISSUES]
    confirmatory_ok = {r.issue_id for r in gate_results if r.allowed}
    pilot_ok = {r.issue_id for r in pilot_gate_results if r.allowed}
    allowed_issue_ids = confirmatory_ok | pilot_ok
    visible_issues = {issue_id: stances for issue_id, stances in SOLO_ISSUES.items()
                      if issue_id in allowed_issue_ids}
    issue_tiers = {iid: ("confirmatory" if iid in confirmatory_ok else "pilot_unvetted")
                   for iid in allowed_issue_ids}
    visible_default = (SOLO_DEFAULT_ISSUE
                       if SOLO_DEFAULT_ISSUE in allowed_issue_ids else None)
    return {"models": models, "arms": SOLO_ARMS, "memories": SOLO_MEMS,
            "budgets": SOLO_BUDGETS, "default_budget": SOLO_DEFAULT_BUDGET,
            "issues": visible_issues, "default_issue": visible_default,
            "issue_tiers": issue_tiers,
            "scenario_gate_rows": [result.to_dict() for result in gate_results],
            "pilot_gate_rows": [result.to_dict() for result in pilot_gate_results],
            "pilot_call_limit": scenario_gate.PILOT_CALL_LIMIT,
            "runner_exists": (SOLO_DIR / "run_solo.py").exists()}


@app.post("/api/solo/estimate")
def api_solo_estimate(req: SoloRunReq):
    """실행 전 견적 — 워크오더 §1 산식: 런 수 × (full/prev 5콜, note 8콜)
    + final_poll 시 런당 1콜.

    리뷰 ⑤(2026-08-19): 산식만 보여주면 견적이 줄어드는 방향([skip])만 보이고, 실제
    과금이 견적을 **넘는** 유일한 경로 — 수첩 예산 초과 반려 재호출(note_r*_retry,
    note 런당 최대 +3콜) — 가 화면에 없었다. 상한(calls_max)을 함께 돌려준다.
    이미 결과가 있어 러너가 건너뛸 런(existing)도 세어 과대 방향까지 미리 보인다."""
    _solo_validate(req)
    n_runs = len(req.arms) * len(req.memories) * len(req.reps)
    per_mem = sum((8 if m == "note" else 5) for m in req.memories)
    calls = per_mem * len(req.arms) * len(req.reps)
    if req.ns_final_poll:
        calls += n_runs
    n_note_runs = (len(req.arms) * len(req.reps)
                   * sum(1 for m in req.memories if m == "note"))
    base = _solo_run_base(req)
    existing = [rid for rid in _solo_planned_ids(req)
                if (base / f"run_{rid}.json").exists()]
    reasons = _solo_v2_reasons(req)
    return {"runs": n_runs, "calls": calls,
            "calls_max": calls + 3 * n_note_runs,
            "note_retry_max": 3 * n_note_runs,
            "existing": existing,
            "is_v2": bool(reasons), "v2_reasons": reasons,
            "suffix": _solo_suffix(req)}


@app.post("/api/solo/run")
def api_solo_run(req: SoloRunReq):
    """run_solo.py 서브프로세스 실행 — 기존 _proc/_log 골격 재사용(동시 실행 1개 원칙).

    사전등록 관문(§2-3): v2 조건 실호출은 prereg_confirmed(사람 확인) 없이는 400 이고,
    확인된 경우에만 --allow-v2 를 붙인다. v1 조건엔 확인 여부와 무관하게 절대 안 붙는다.
    드라이런(0콜)은 러너와 같은 이유로 관문 밖 — 확인 없이 허용한다.

    전 구간이 _run_lock 안이다(리뷰 ①) — 검사·관문·Popen·_proc 대입이 원자여야
    동시 요청 2건이 러너 2개를 띄우는 사고(이중 과금·체크포인트 오염·고아)가 막힌다."""
    global _proc, _log, _current
    with _run_lock:
        if _proc is not None and _proc.poll() is None:
            raise HTTPException(409, "이미 실행 중 — 끝나거나 중단한 뒤에 다시.")
        _solo_validate(req)
        estimate = api_solo_estimate(req)
        if req.promotion_tier == "pilot_unvetted":
            gate = scenario_gate.evaluate_pilot(
                req.issue,
                expected_calls=0 if req.dry else estimate["calls_max"],
                max_calls=req.max_llm_calls,
            )
        elif req.promotion_tier == "confirmatory":
            gate = scenario_gate.require(req.issue)
        else:
            raise HTTPException(400, f"unknown promotion_tier: {req.promotion_tier!r}")
        if not gate.allowed:
            detail = "; ".join(gate.blocking_reasons) or "unknown blocking reason"
            raise HTTPException(400, f"scenario gate blocked {req.issue}: {detail}")
        reasons = _solo_v2_reasons(req)
        is_v2 = bool(reasons)
        if is_v2 and not req.dry and not req.prereg_confirmed:
            raise HTTPException(400,
                                "v2 조건 실호출 차단 — PROMPTS_v2·PREREG_v2 로컬 커밋 확인 체크가 "
                                f"필요하다 (v2 사유: {', '.join(reasons)}). 드라이런(0콜)은 확인 없이 가능.")
        if req.ns_final_poll and not req.dry:
            # 리뷰 ⑦ 완화: 러너의 _ns 접미사는 final_poll 을 인코딩하지 않는다(러너 소관 —
            # §2-2 보고 대상). CLI 로 --no-stance 단독 런을 이미 만들었다면 run_id 가 같아
            # 러너가 [skip] — "최종 판단" 실행이 조용히 무효가 되고 데이터는 끝내 안 모인다.
            # 그 조용한 무효를 여기서 시끄럽게 만든다.
            base = _solo_run_base(req)
            clash = []
            for rid in _solo_planned_ids(req):
                p = base / f"run_{rid}.json"
                if p.exists():
                    try:
                        doc = json.loads(p.read_text(encoding="utf-8"))
                        meta = (doc or {}).get("meta") or {}
                    except Exception:
                        meta = {}
                    if not meta.get("final_poll"):
                        clash.append(p.name)
            if clash:
                raise HTTPException(409,
                                    "기존 _ns 산출물이 final_poll 없이 존재 — run_id 가 같아 러너가 "
                                    f"[skip]하고 최종 판단은 수집되지 않는다: {', '.join(clash)}. "
                                    "파일을 옮기거나 rep 을 바꿔라(append-only — 덮어쓰지 않는다).")
        if not req.dry:
            # 키 관문만 여기서 — 온도·프롬프트·상한은 전부 러너 소관(러너도 preflight 를 한다.
            # 여기서 먼저 보면 스택트레이스가 아니라 400 문장으로 안다 — /api/run 전례).
            try:
                llm.preflight(req.model)
            except SystemExit as e:
                raise HTTPException(400, str(e))
            except KeyError as e:
                raise HTTPException(400, str(e))
        runner = SOLO_DIR / "run_solo.py"
        if not runner.exists():
            raise HTTPException(500, f"러너 없음: {runner}")
        # 워크오더 §1: sys.executable -X utf8 <경로> <인자들>. -u 는 파이프 버퍼링 해제 —
        # 없으면 자식 print 가 8KB 씩 뭉쳐 나와 로그가 실시간으로 안 흐른다.
        cmd = [sys.executable, "-X", "utf8", "-u", str(runner),
               "--model", req.model,
               "--issue", req.issue,
               "--arms", *req.arms,
               "--memories", *req.memories,
               "--reps", *[str(n) for n in req.reps]]
        if req.stance_key:
            cmd += ["--stance-key", req.stance_key]
        if req.note_budget != SOLO_DEFAULT_BUDGET:
            cmd += ["--note-budget", str(req.note_budget)]
        if req.facts_reverse:
            cmd.append("--facts-reverse")
        if req.ns_final_poll:
            cmd += ["--no-stance", "--final-poll"]
        if req.promotion_tier == "pilot_unvetted":
            # max_llm_calls는 요청/tranche 전체 상한이다. 러너의 역사적 --max-calls
            # (run 하나의 CallGate)와 단위를 섞지 않고 별도 인자로 전달한다.
            cmd += ["--promotion-tier", "pilot_unvetted",
                    "--max-llm-calls", str(req.max_llm_calls)]
        if req.dry:
            cmd.append("--dry")
        elif is_v2:
            cmd.append("--allow-v2")     # 사람 확인(prereg_confirmed)을 통과한 경우만 여기 도달
        with _log_lock:
            _log = [f"$ {' '.join(cmd)}"]
        _current = {"kind": "solo", "model": req.model, "dry": req.dry}
        _proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                 errors="replace", bufsize=1)
        threading.Thread(target=_tail_reader, args=(_proc,), daemon=True).start()
    return {"ok": True, "cmd": cmd, "dry": req.dry, "v2": is_v2}


def _solo_scan() -> list[dict]:
    """runs/<model>/ + runs/_dry/<model>/ 스캔 → 런 목록(최신순).

    v1 산출물엔 facts_order·stance·final_poll 메타가 없다(손잡이 자체가 없던 시절).
    부재를 기본값과 뭉치지 않는다 — None 으로 보내고 화면이 'v1'로 적는다(스키마 §4⁗
    의 "부재는 모름" 원칙). 결과 없이 체크포인트(.partial)만 있는 런은 중단/진행 중 —
    숨기면 "돌렸는데 어디 갔지"가 되므로 partial 표시로 드러낸다."""
    out = []
    jroot = _solo_judgments_dir()
    for dry in (False, True):
        base = _solo_runs_dir(dry)
        if not base.exists():
            continue
        for mdir in sorted(base.iterdir()):
            if not mdir.is_dir() or mdir.name.startswith("_"):
                continue
            done_ids = set()
            for p in sorted(mdir.glob("run_*.json")):
                rid_from_name = p.stem[len("run_"):]
                try:
                    doc = json.loads(p.read_text(encoding="utf-8"))
                    if not isinstance(doc, dict):
                        raise ValueError("결과가 JSON 객체가 아님")
                except Exception:
                    # 깨진 파일을 조용히 빼면(종전 동작) 잔존 .partial 이 "체크포인트만"
                    # 으로 위장되고, 러너는 깨진 .json 의 존재만 보고 [skip] 하므로
                    # "재실행하면 이어받는다" 안내가 거짓이 된다(리뷰 ④·⑩). 깨진 파일도
                    # 목록에 드러내고 done_ids 에 넣어 partial 위장을 차단한다.
                    done_ids.add(rid_from_name)
                    out.append({"model": mdir.name, "run_id": rid_from_name,
                                "file": p.name, "dry": dry, "broken": True,
                                "partial": False, "judged": False,
                                "mtime": p.stat().st_mtime})
                    continue
                rid = doc.get("run_id") or rid_from_name
                done_ids.add(rid)
                meta = doc.get("meta") or {}
                pv = doc.get("prompts_ver")
                out.append({
                    "model": mdir.name, "run_id": rid, "file": p.name, "dry": dry,
                    "arm": doc.get("arm"), "memory": doc.get("memory"),
                    "rep": doc.get("rep"),
                    "prompts_ver": pv,
                    "version": ("v1" if pv == "solo-v1" else ("v2" if pv else "?")),
                    "note_budget": meta.get("note_budget"),
                    "facts_order": meta.get("facts_order"),
                    "stance": meta.get("stance"),
                    "final_poll": meta.get("final_poll"),
                    "model_id": meta.get("model_id"),
                    "finished_at": meta.get("finished_at"),
                    "judged": (not dry) and (jroot / mdir.name / f"judge_{rid}.json").exists(),
                    "partial": False, "broken": False,
                    "mtime": p.stat().st_mtime,
                })
            for p in sorted(mdir.glob("run_*.partial.jsonl")):
                rid = p.name[len("run_"):-len(".partial.jsonl")]
                if rid in done_ids:
                    continue     # 완주(또는 깨진 완주) 런의 체크포인트 잔존물
                out.append({"model": mdir.name, "run_id": rid, "file": p.name,
                            "dry": dry, "partial": True, "broken": False,
                            "judged": False, "mtime": p.stat().st_mtime})
    out.sort(key=lambda r: r.get("mtime") or 0, reverse=True)
    return out


@app.get("/api/solo/runs")
def api_solo_runs():
    return {"runs": _solo_scan()}


@app.get("/api/solo/detail")
def api_solo_detail(model: str, run_id: str, dry: bool = False):
    """런 한 벌 원문 — 라운드별 발화·수첩(글자 수·여백)·회고·최종 판단.

    여백 = 예산 − 글자 수. 발견 ④(자리가 남는데 버린다)가 화면에서 바로 보이게
    수첩마다 병기한다(워크오더 §1 탭 2)."""
    _solo_check_names(model, run_id)
    p = _solo_runs_dir(dry) / model / f"run_{run_id}.json"
    if not p.exists():
        raise HTTPException(404, f"런 없음: {p.name}")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("결과가 JSON 객체가 아님")
    except (ValueError, OSError):
        raise HTTPException(422, f"깨진 결과 파일: {p.name} — 열 수 없다. "
                                 "파일을 치운 뒤 재실행해야 러너가 다시 돈다"
                                 "(깨진 파일이 있으면 러너는 [skip]한다).")
    meta = doc.get("meta") or {}
    budget = meta.get("note_budget") or SOLO_DEFAULT_BUDGET
    essays = [{"round": i, "text": t, "len": len(t or "")}
              for i, t in enumerate(doc.get("essays") or [])]
    notes = [{"round": i, "text": t, "len": len(t or ""),
              "margin": budget - len(t or "")}
             for i, t in enumerate(doc.get("notes") or [])]
    pv = doc.get("prompts_ver")
    return {"model": model, "run_id": run_id, "dry": dry,
            "prompts_ver": pv,
            "version": ("v1" if pv == "solo-v1" else ("v2" if pv else "?")),
            "arm": doc.get("arm"), "arm_name": doc.get("arm_name"),
            "memory": doc.get("memory"), "rep": doc.get("rep"),
            "meta": meta, "note_budget": budget,
            "essays": essays, "notes": notes,
            "recall": doc.get("recall"),
            # v1 산출물엔 final_poll 키 자체가 없다 — None 이면 화면이 칸을 생략한다.
            "final_poll": doc.get("final_poll"),
            "judged": (not dry) and
                      (_solo_judgments_dir() / model / f"judge_{run_id}.json").exists()}


def _solo_grid_cells(records: dict, stages: list[str]) -> dict:
    cells = {}
    for s in stages:
        for row in records.get(s) or []:
            votes = [v.get("status") for v in (row.get("votes") or [])]
            cells[(row["fact_id"], s)] = {
                "status": row.get("status"),
                # 표 분열 = 3표 불일치. judge 신뢰도의 직접 관측이라 격자에 병기한다.
                "split": len(set(votes)) > 1,
                "votes": votes,
            }
    return cells


def _solo_aggregate_eligible(model: str, run_id: str, judgment: dict) -> bool:
    """판정물과 source run 중 어느 한쪽이라도 파일럿이면 기본 집계에서 제외한다.

    구 v1 산출물은 라벨 자체가 없으므로 legacy eligible로 유지한다. 새 산출물의 라벨이
    한 파일에서 제거되거나 서로 충돌하면 다른 파일의 development-only 표식을 우선해
    fail-closed 한다.
    """
    docs = [judgment]
    issue_id = str(judgment.get("issue_id") or "")
    run_root = _solo_runs_dir(False) / model
    candidates = [run_root / f"run_{run_id}.json"]
    if issue_id and issue_id != SOLO_DEFAULT_ISSUE:
        candidates.append(run_root / issue_id / f"run_{run_id}.json")
    for source in candidates:
        if not source.exists():
            continue
        try:
            doc = json.loads(source.read_text(encoding="utf-8"))
            meta = (doc or {}).get("meta") or {}
            if not isinstance(meta, dict):
                return False
            docs.append(meta)
        except (ValueError, OSError, AttributeError):
            return False
        break

    tiers = {doc.get("promotion_tier") for doc in docs
             if doc.get("promotion_tier") is not None}
    if "pilot_unvetted" in tiers or len(tiers) > 1:
        return False
    for doc in docs:
        if "aggregate_eligible" in doc:
            value = doc["aggregate_eligible"]
            if not isinstance(value, bool) or value is False:
                return False
    return True


@app.get("/api/solo/grid")
def api_solo_grid(model: str, run_id: str):
    """생존 격자 — 사실 × 시점(essay_r0~r3·carrier). LLM 호출 0, judgments 재독만(§1 탭 3).

    같은 조건의 다른 반복(rep)이 채점돼 있으면 겹침 농도(셀 = 반복 중 mentioned 수)를
    함께 돌려준다 — 생존리포트 HTML 과 같은 읽기("셀 값 = 반복 3 중 생존 판정 수")."""
    _solo_check_names(model, run_id)
    jp = _solo_judgments_dir() / model / f"judge_{run_id}.json"
    if not jp.exists():
        raise HTTPException(404, f"채점 없음: {jp.name} — 채점 실행은 judge_solo.py CLI "
                                 "(콘솔 채점 UI 는 워크오더 §4 범위 밖)")
    try:
        doc = json.loads(jp.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("판정이 JSON 객체가 아님")
    except (ValueError, OSError):
        # judge_solo.py CLI 와 병행 사용이 계약된 패턴이라(위 404 문구가 그렇게 안내한다)
        # 쓰다 만 판정 파일을 만날 수 있다 — 500 대신 무엇이 왜 안 열리는지 말한다(리뷰 ⑩).
        raise HTTPException(422, f"깨진 판정 파일: {jp.name} — 채점이 진행 중이거나 중단됐다. "
                                 "완료 후 다시 열거나 파일을 치우고 재채점하라.")
    records = doc.get("records") or {}
    stages = ([s for s in SOLO_STAGES if s in records]
              + [s for s in records if s not in SOLO_STAGES])
    # 행 라벨 = 팩트 원문. 판정 파일이 자기 이슈를 안다(issue_id) — 콘솔이 추측하지 않는다.
    try:
        facts = json.loads(paths.facts(doc.get("issue_id", ""))
                           .read_text(encoding="utf-8"))["facts"]
        row_ids = [f["fact_id"] for f in facts]
        text_by_id = {f["fact_id"]: f["text"] for f in facts}
    except (FileNotFoundError, KeyError):
        row_ids, text_by_id = [], {}
    if not row_ids:      # 팩트 파일이 없으면 판정 기록의 등장 순서로라도 그린다
        for s in stages:
            for row in records.get(s) or []:
                if row["fact_id"] not in row_ids:
                    row_ids.append(row["fact_id"])
    cells = _solo_grid_cells(records, stages)
    rows = [{"fact_id": fid, "text": text_by_id.get(fid, ""),
             "cells": [cells.get((fid, s)) for s in stages]} for fid in row_ids]
    # 조건 겹침 — run_id 에서 _rep<k> 만 뗀 것이 조건 키(v2 접미사는 조건의 일부).
    cond = re.sub(r"_rep\d+$", "", run_id)
    sib = sorted(q.name[len("judge_"):-len(".json")]
                 for q in (_solo_judgments_dir() / model).glob(f"judge_{cond}_rep*.json"))
    agg = None
    if len(sib) > 1:
        counts: dict = {}
        usable, skipped, excluded_ineligible = [], [], []
        for sid in sib:
            try:
                jd = json.loads((_solo_judgments_dir() / model / f"judge_{sid}.json")
                                .read_text(encoding="utf-8"))
                if not isinstance(jd, dict):
                    raise ValueError("판정이 JSON 객체가 아님")
            except (ValueError, OSError):
                # 형제 하나가 쓰다 만 파일이어도 멀쩡한 격자는 그려야 한다(리뷰 ⑩).
                # 조용히 빼지 않고 skipped 로 화면에 드러낸다 — 농도 분모가 줄어든 이유.
                skipped.append(sid)
                continue
            if not _solo_aggregate_eligible(model, sid, jd):
                excluded_ineligible.append(sid)
                continue
            usable.append(sid)
            for s in stages:
                for row in (jd.get("records") or {}).get(s) or []:
                    if row.get("status") == "mentioned":
                        key = (row["fact_id"], s)
                        counts[key] = counts.get(key, 0) + 1
        if len(usable) > 1:
            agg = {"n_runs": len(usable), "run_ids": usable,
                   "skipped_run_ids": skipped, "condition": cond,
                   "excluded_ineligible_run_ids": excluded_ineligible,
                   "rows": [{"fact_id": fid, "text": text_by_id.get(fid, ""),
                             "cells": [counts.get((fid, s), 0) for s in stages]}
                            for fid in row_ids]}
    return {"model": model, "run_id": run_id, "issue_id": doc.get("issue_id"),
            "judge": doc.get("judge") or {}, "stages": stages, "rows": rows, "agg": agg}


# ═══ 압박 실험 (experiments/pressure_category) — 2026-08-24 추가 ═══
# 이 아래는 전부 **추가**다 — 기존 debate·solo 라우트·동작은 건드리지 않는다.
# 콘솔은 러너(run_pressure.py)를 서브프로세스로 부르고 산출물을 **읽기만** 한다.
# 사전등록 관문·프롬프트·체크포인트는 전부 러너 소관 (solo 와 같은 원칙).

PRESSURE_DIR = ROOT / "experiments" / "pressure_category"
PRESSURE_MODELS = SOLO_MODELS                       # llm.py 별칭 — solo 와 같은 후보
PRESSURE_SCRIPTS = {"C0": "압박 없음(대조)", "C1": "일치 압박", "C2": "반대 압박"}
PRESSURE_SCRIPT_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,24}")   # run_pressure.SCRIPT_ID_RE 미러
PRESSURE_CALLS_PER_RUN = 8                          # run_pressure.py 절차 미러 (4+3+1)
PRESSURE_RETRY_MAX = 3                              # 수첩 반려 재호출 상한 미러
PRESSURE_DEFAULT_MATERIALS = "issue_dorm"           # run_pressure.DEFAULT_MATERIALS_ID 미러


def _pressure_runs_dir(dry: bool) -> Path:
    d = PRESSURE_DIR / "runs"
    return d / "_dry" if dry else d


def _pressure_materials() -> dict[str, dict]:
    """재료 registry — issue_id → {파일·옵션·카테고리·가치 세트}. 발견 규칙은
    run_pressure.discover_materials 의 미러(그쪽이 정본): 기본 재료 + materials/*.json,
    템플릿 제외, 깨진 파일은 건너뛰되 broken 으로 드러낸다."""
    out: dict[str, dict] = {}
    cands = ([PRESSURE_DIR / "MATERIALS_v0.json"]
             + sorted((PRESSURE_DIR / "materials").glob("*.json")
                      if (PRESSURE_DIR / "materials").exists() else []))
    for p in cands:
        if not p.exists() or p.name == "MATERIALS_TEMPLATE.json":
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            iid = doc["issue_id"]
        except Exception:
            out[f"(깨짐) {p.name}"] = {"file": p.name, "broken": True}
            continue
        if iid in out:
            continue        # 충돌 — 러너가 즉사시키는 사안. 목록엔 먼저 온 것만.
        vs = doc.get("value_sets") or {}
        out[iid] = {
            "file": p.name, "broken": False,
            "options": doc.get("options") or [],
            "categories": doc.get("categories") or [],
            "vsets": {k: {"categories": (vs.get(k) or {}).get("categories") or [],
                          "aligned": (vs.get(k) or {}).get("aligned")}
                      for k in ("A", "B")},
        }
    return out


def _pressure_scripts() -> dict[str, dict]:
    """각본 registry — 내장 C0/C1/C2 + scripts/*.json (run_pressure.discover_scripts
    미러 — 그쪽이 정본). 등록 각본엔 라운드별 대사·r0 대사·방향을 함께 실어 화면이
    미리보기를 그릴 수 있게 한다."""
    out = {sid: {"label": lab, "target": None, "lines": None, "r0_line": None,
                 "custom": False}
           for sid, lab in PRESSURE_SCRIPTS.items()}
    sdir = PRESSURE_DIR / "scripts"
    if sdir.exists():
        for p in sorted(sdir.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                sid = d["script_id"]
            except Exception:
                continue
            if not PRESSURE_SCRIPT_ID_RE.fullmatch(sid or "") or sid in out:
                continue
            lines = d.get("lines")
            if isinstance(lines, str):
                lines = [lines]
            if not lines:
                continue
            out[sid] = {"label": d.get("label") or sid, "target": d.get("target", "none"),
                        "lines": lines, "r0_line": d.get("r0_line"),
                        "custom": True, "file": p.name}
    return out


class PressureRunReq(BaseModel):
    model: str = "gpt"
    # 재료(시나리오) — run_pressure.py --materials 와 연결. 팀원이 materials/ 에 넣은
    # 시나리오가 자동으로 목록에 뜬다. 기본값이면 종전과 동일 동작.
    materials: str = PRESSURE_DEFAULT_MATERIALS
    scripts: list[str] = ["C0", "C1", "C2"]
    vsets: list[str] = ["A", "B"]
    reps: list[int] = [1, 2, 3]
    dry: bool = False
    # "PREREG_v0.md 를 로컬 커밋했다"는 **사람의 확인** — solo 의 prereg_confirmed 와
    # 같은 원칙: UI 가 자동으로 켜면 사전등록 관문이 장식이 된다.
    prereg_confirmed: bool = False


def _pressure_validate(req: PressureRunReq) -> None:
    if req.model not in PRESSURE_MODELS:
        raise HTTPException(400, f"모르는 모델: {req.model} (가능: {', '.join(PRESSURE_MODELS)})")
    reg = _pressure_materials()
    if req.materials not in reg or reg[req.materials].get("broken"):
        ok = [k for k, v in reg.items() if not v.get("broken")]
        raise HTTPException(400, f"모르는 재료: {req.materials} (가능: {', '.join(ok)})")
    if not (req.scripts and req.vsets and req.reps):
        raise HTTPException(400, "각본/가치 세트/반복을 하나 이상 고르세요.")
    known_scripts = _pressure_scripts()
    bad = ([s for s in req.scripts if s not in known_scripts]
           + [v for v in req.vsets if v not in ("A", "B")])
    if bad:
        raise HTTPException(400, f"모르는 조건: {bad}")


def _pressure_run_base(req: PressureRunReq) -> Path:
    """이 요청의 산출물 폴더 — 러너 run_one 의 out_dir 규칙 미러
    (기본 재료는 종전 경로, 그 외는 issue_id 하위)."""
    d = _pressure_runs_dir(req.dry) / req.model
    return d if req.materials == PRESSURE_DEFAULT_MATERIALS else d / req.materials


def _pressure_planned_ids(req: PressureRunReq) -> list[str]:
    """이 요청이 만들 run_id 목록 — 러너의 조립식(run_one)과 같은 규칙."""
    return [f"{s}_{v}_rep{n}" for s in req.scripts for v in req.vsets for n in req.reps]


@app.get("/api/pressure/meta")
def api_pressure_meta():
    """폼의 단일 소스 — 조건 어휘 + 모델 키 실재 + 러너·재료·사전등록 파일 존재."""
    models = []
    for key in PRESSURE_MODELS:
        try:
            provider = llm.resolve_provider(key)
        except KeyError:
            continue
        env = llm.PROVIDER_KEY_ENV[provider]
        val = os.environ.get(env, "")
        models.append({"key": key, "model_id": llm.resolve_model(key),
                       "provider": provider, "key_env": env,
                       "ready": len(val) >= 24,
                       "reason": ("" if len(val) >= 24 else
                                  (f"{env} 없음" if not val
                                   else f"{env} 가 너무 짧음({len(val)}자 — 자리표시자)"))})
    return {"models": models, "scripts": _pressure_scripts(),
            "materials": _pressure_materials(),
            "default_materials": PRESSURE_DEFAULT_MATERIALS,
            "runner_exists": (PRESSURE_DIR / "run_pressure.py").exists(),
            "materials_exists": (PRESSURE_DIR / "MATERIALS_v0.json").exists(),
            "prereg_exists": (PRESSURE_DIR / "PREREG_v0.md").exists()}


@app.post("/api/pressure/estimate")
def api_pressure_estimate(req: PressureRunReq):
    """실행 전 견적 — 판당 8콜(글4·수첩3·최종1) + 수첩 반려 최대 +3콜.
    이미 결과가 있어 러너가 [skip] 할 런도 센다 (solo 견적과 같은 원칙)."""
    _pressure_validate(req)
    ids = _pressure_planned_ids(req)
    base = _pressure_run_base(req)
    existing = [rid for rid in ids if (base / f"run_{rid}.json").exists()]
    n = len(ids)
    return {"runs": n, "calls": PRESSURE_CALLS_PER_RUN * n,
            "calls_max": (PRESSURE_CALLS_PER_RUN + PRESSURE_RETRY_MAX) * n,
            "existing": existing}


@app.post("/api/pressure/run")
def api_pressure_run(req: PressureRunReq):
    """run_pressure.py 서브프로세스 실행 — 기존 _proc/_log 골격 재사용(동시 실행 1개).

    사전등록 관문: 실호출은 prereg_confirmed(사람 확인) 없이는 400, 확인된 경우에만
    --allow-live 를 붙인다. 드라이런(0콜)은 러너와 같은 이유로 관문 밖.
    전 구간이 _run_lock 안 — solo 와 같은 원자화(더블클릭 이중 실행 차단)."""
    global _proc, _log, _current
    with _run_lock:
        if _proc is not None and _proc.poll() is None:
            raise HTTPException(409, "이미 실행 중 — 끝나거나 중단한 뒤에 다시.")
        _pressure_validate(req)
        if not req.dry and not req.prereg_confirmed:
            raise HTTPException(400, "실호출 차단 — PREREG_v0.md 로컬 커밋 확인 체크가 "
                                     "필요하다. 드라이런(0콜)은 확인 없이 가능.")
        if not req.dry:
            try:
                llm.preflight(req.model)
            except SystemExit as e:
                raise HTTPException(400, str(e))
            except KeyError as e:
                raise HTTPException(400, str(e))
        runner = PRESSURE_DIR / "run_pressure.py"
        if not runner.exists():
            raise HTTPException(500, f"러너 없음: {runner}")
        cmd = [sys.executable, "-X", "utf8", "-u", str(runner),
               "--model", req.model,
               "--materials", req.materials,
               "--scripts", *req.scripts,
               "--vsets", *req.vsets,
               "--reps", *[str(n) for n in req.reps]]
        if req.dry:
            cmd.append("--dry")
        else:
            cmd.append("--allow-live")   # 사람 확인(prereg_confirmed)을 통과한 경우만 도달
        with _log_lock:
            _log = [f"$ {' '.join(cmd)}"]
        _current = {"kind": "pressure", "model": req.model, "dry": req.dry}
        _proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                 errors="replace", bufsize=1)
        threading.Thread(target=_tail_reader, args=(_proc,), daemon=True).start()
    return {"ok": True, "cmd": cmd, "dry": req.dry}


class PressureScriptReq(BaseModel):
    script_id: str
    label: str = ""
    target: str = "none"          # aligned | opposite | none
    r0_line: str | None = None    # 있으면 첫 라운드(사실 읽는 시점)부터 압박
    lines: list[str] = []         # 라운드 1~3 대사 (모자라면 러너가 마지막을 반복)


@app.post("/api/pressure/script")
def api_pressure_script(req: PressureScriptReq):
    """각본 등록 — scripts/<id>.json **새 파일 추가만**. 기존 각본(내장·등록분) 덮어쓰기는
    409: 문면을 고치면 과거 런과의 대응이 끊기므로, 바꾸고 싶으면 새 이름으로 등록한다
    (append-only — 색인 규칙과 같은 원리). 전례: 콘솔의 변종 이슈 파생·configs/console 생성."""
    sid = (req.script_id or "").strip()
    if not PRESSURE_SCRIPT_ID_RE.fullmatch(sid):
        raise HTTPException(400, "각본 id 는 영숫자·밑줄·하이픈 1~24자 (run_id·경로에 들어간다)")
    if req.target not in ("aligned", "opposite", "none"):
        raise HTTPException(400, "target 은 aligned(가치 정렬 쪽으로 민다) / opposite(반대쪽) "
                                 "/ none(방향 없음) 중 하나")
    lines = [x for x in (req.lines or []) if x and x.strip()]
    if not lines:
        raise HTTPException(400, "라운드 대사(lines)를 하나 이상 적으세요.")
    if req.target == "none":
        for ln in lines + ([req.r0_line] if req.r0_line else []):
            if "{TARGET}" in ln or "{OTHER}" in ln:
                raise HTTPException(400, "target 이 none 인데 대사에 {TARGET}/{OTHER} 자리가 "
                                         "있습니다 — 방향을 고르거나 자리를 지우세요.")
    if sid in _pressure_scripts():
        raise HTTPException(409, f"이미 있는 각본 id: {sid} — 기존 각본은 고치지 않습니다"
                                 "(과거 런과의 대응 보존). 새 이름으로 등록하세요.")
    sdir = PRESSURE_DIR / "scripts"
    sdir.mkdir(parents=True, exist_ok=True)
    dst = sdir / f"{sid}.json"
    if dst.exists():
        raise HTTPException(409, f"파일이 이미 있습니다: {dst.name}")
    doc = {"script_id": sid, "label": (req.label or sid).strip(),
           "target": req.target, "lines": lines}
    if req.r0_line and req.r0_line.strip():
        doc["r0_line"] = req.r0_line.strip()
    dst.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "script_id": sid, "file": dst.name}


@app.get("/api/pressure/runs")
def api_pressure_runs():
    """runs/<model>/ + runs/_dry/<model>/ 스캔 → 런 목록(최신순). _solo_scan 과 같은
    원칙: 깨진 파일·체크포인트만 있는 런도 숨기지 않고 드러낸다."""
    out = []
    for dry in (False, True):
        base = _pressure_runs_dir(dry)
        if not base.exists():
            continue
        for mdir in sorted(base.iterdir()):
            if not mdir.is_dir() or mdir.name.startswith("_"):
                continue
            done_keys = set()

            def _mat_of(p: Path) -> str:
                # 하위 폴더 이름 = 재료 issue_id (러너 out_dir 규칙 미러). 바로 아래 = 기본 재료.
                return p.parent.name if p.parent != mdir else PRESSURE_DEFAULT_MATERIALS

            # 기본 재료는 모델 폴더 바로 아래, 팀원 시나리오는 <issue_id>/ 하위 (러너 규칙 미러)
            for p in sorted(mdir.glob("run_*.json")) + sorted(mdir.glob("*/run_*.json")):
                rid_from_name = p.stem[len("run_"):]
                mat_id = _mat_of(p)
                try:
                    doc = json.loads(p.read_text(encoding="utf-8"))
                    if not isinstance(doc, dict):
                        raise ValueError("결과가 JSON 객체가 아님")
                except Exception:
                    done_keys.add((mat_id, rid_from_name))
                    out.append({"model": mdir.name, "run_id": rid_from_name,
                                "materials": mat_id, "issue_id": mat_id,
                                "file": p.name, "dry": dry, "broken": True,
                                "partial": False, "mtime": p.stat().st_mtime})
                    continue
                rid = doc.get("run_id") or rid_from_name
                done_keys.add((mat_id, rid))
                meta = doc.get("meta") or {}
                poll = (doc.get("final_poll") or "").strip()
                out.append({"model": mdir.name, "run_id": rid,
                            "materials": mat_id, "issue_id": doc.get("issue_id"),
                            "file": p.name,
                            "dry": dry, "script": doc.get("script"),
                            "script_label": doc.get("script_label"),
                            "value_set": doc.get("value_set"),
                            "aligned": doc.get("aligned"), "rep": doc.get("rep"),
                            "final_poll": poll[:60], "model_id": meta.get("model_id"),
                            "finished_at": meta.get("finished_at"),
                            "partial": False, "broken": False,
                            "mtime": p.stat().st_mtime})
            for p in (sorted(mdir.glob("run_*.partial.jsonl"))
                      + sorted(mdir.glob("*/run_*.partial.jsonl"))):
                rid = p.name[len("run_"):-len(".partial.jsonl")]
                mat_id = _mat_of(p)
                if (mat_id, rid) in done_keys:
                    continue
                out.append({"model": mdir.name, "run_id": rid,
                            "materials": mat_id, "issue_id": mat_id, "file": p.name,
                            "dry": dry, "partial": True, "broken": False,
                            "mtime": p.stat().st_mtime})
    out.sort(key=lambda r: r.get("mtime") or 0, reverse=True)
    return {"runs": out}


@app.get("/api/pressure/detail")
def api_pressure_detail(model: str, run_id: str, dry: bool = False,
                        materials: str = PRESSURE_DEFAULT_MATERIALS):
    """런 한 벌 원문 — 라운드별 글·수첩(글자 수·여백)·각본 대사·최종 선택."""
    _solo_check_names(model, run_id)     # 같은 경로 문자 방어(영숫자·밑줄·하이픈만)
    if not _SOLO_NAME_RE.fullmatch(materials):
        raise HTTPException(400, "materials 는 영숫자·밑줄·하이픈만 받는다")
    base = _pressure_runs_dir(dry) / model
    if materials != PRESSURE_DEFAULT_MATERIALS:
        base = base / materials
    p = base / f"run_{run_id}.json"
    if not p.exists():
        raise HTTPException(404, f"런 없음: {p.name}")
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("결과가 JSON 객체가 아님")
    except (ValueError, OSError):
        raise HTTPException(422, f"깨진 결과 파일: {p.name} — 파일을 치운 뒤 재실행해야 "
                                 "러너가 다시 돈다(깨진 파일이 있으면 러너는 [skip]한다).")
    meta = doc.get("meta") or {}
    budget = meta.get("note_budget") or 500
    essays = [{"round": i, "text": t, "len": len(t or "")}
              for i, t in enumerate(doc.get("essays") or [])]
    notes = [{"round": i, "text": t, "len": len(t or ""),
              "margin": budget - len(t or "")}
             for i, t in enumerate(doc.get("notes") or [])]
    return {"model": model, "run_id": run_id, "dry": dry,
            "script": doc.get("script"), "script_label": doc.get("script_label"),
            "script_line": doc.get("script_line"),
            # 등록 각본판 필드 — 구판 산출물엔 없다(None 이면 화면이 단일 대사로 그린다)
            "script_lines": doc.get("script_lines"),
            "script_r0_line": doc.get("script_r0_line"),
            "script_source": doc.get("script_source"),
            "value_set": doc.get("value_set"),
            "value_categories": doc.get("value_categories"),
            "aligned": doc.get("aligned"), "rep": doc.get("rep"),
            "meta": meta, "note_budget": budget,
            "essays": essays, "notes": notes,
            "final_poll": doc.get("final_poll")}
