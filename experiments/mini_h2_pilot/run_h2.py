# -*- coding: utf-8 -*-
"""미니 H2 파일럿 — 별도 환경(OpenAI) 실행기. 탐색적/데모 지위.

지위: 팀 예산이 OpenAI 키라 본 파이프라인(Anthropic 전용 llm.py)을 못 태운다.
민옥 담화 전진·요한 tp1 전례를 따라 파일럿 지위로 집행하고, 정식 H1/H2 판정은
Anthropic 예산 확보 후 실호출 몫이다. 모든 수치는 "탐색적 — 정식 판정은 실호출분에서".

tp1과 다른 점 (정본 계승 극대화):
- 토론 루프를 재구현하지 않는다 — **modules.debate_engine.run()을 utterance_fn/
  judge_vote_fn 주입 슬롯으로 그대로 재사용**한다(테스트 98종이 검증한 결합부 그대로).
  ledger v0의 (A)주입→(B)발화→(C)즉시판정 루프·호출상한·체크포인트 전부 정본이다.
- judge 잣대 문구도 정본 재사용 — judge.JUDGE_SYSTEM·_user_prompt·_parse_vote를
  그대로 쓰고 수송(transport)만 OpenAI로 바꾼다. 판정기 편차 = 모델뿐.
- 저자 프롬프트 원문(authors_prompts → DelibTrace-main) 그대로. temp 1.2 논문 상수
  그대로(OpenAI 0~2 허용 — Anthropic 선결 ①에 해당 없음).

편차 기록 (README에도 명시):
  D-p1 debate_model=gpt-5.4-mini (팀 정본 claude-haiku — 예산 사유)
  D-p2 judge=gpt-5.4-mini·temp0·n=3 다수결 (확정 사양과 모델만 다름, n=3·다수결 유지)
  D-p3 issue_esa에 question 필드 로컬 주입 (title이 팩트 요지 누출 — tp1 편차 계승,
       팀 data/ 무수정: 파일럿 사본에만 주입)

산출물: experiments/mini_h2_pilot/data/ (팀 data/와 분리 — 민옥 관례).
paths.DATA를 이 폴더로 재지정해 엔진·judge 순수 함수가 무수정으로 동작한다.

안전장치: 엔진 내장 상한·라운드 체크포인트 + 전역 호출 상한(--max-calls) +
출력 절단 즉시 에러(민옥 D1 교훈) + judge stage별 체크포인트(부분 재개).

사용 (리포 루트에서):
  python experiments/mini_h2_pilot/run_h2.py --phase debate  --arm off [--dry]
  python experiments/mini_h2_pilot/run_h2.py --phase debate  --arm v0  [--dry]
  python experiments/mini_h2_pilot/run_h2.py --phase judge   --arm off [--dry]
  python experiments/mini_h2_pilot/run_h2.py --phase judge   --arm v0  [--dry]
  python experiments/mini_h2_pilot/run_h2.py --phase analyze
  python experiments/mini_h2_pilot/run_h2.py --phase all [--dry]   # 위 5개 순차
  (--dry = API 0원 리허설: 가짜 발화 + 문자열 대조 판정으로 전 구간 완주 검증)
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PILOT_DATA = HERE / "data"
sys.path.insert(0, str(ROOT))

from modules import debate_engine, ledger, paths  # noqa: E402
from modules import judge as judge_mod  # noqa: E402

ISSUE_ID = "issue_esa"
RUN_IDS = {"off": "h2p_off", "v0": "h2p_v0"}
CFGS = {"off": HERE / "configs" / "h2p_off.yaml", "v0": HERE / "configs" / "h2p_v0.yaml"}
QUESTION_OVERRIDE = "룸메이트를 집주인에게 신고해야 할까요?"  # D-p3 (tp1 계승)
MAX_GEN_TOKENS = 2048   # llm.MAX_TOKENS와 동일
MAX_JUDGE_TOKENS = 512  # judge._online_vote와 동일

N_CALLS = 0
MAX_CALLS = 600  # off 32 + v0 140 + 사후 judge 144x2 = 460 예상, 여유 포함
_client = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


ENV = load_env()
GEN_MODEL = ENV.get("OPENAI_MODEL", "gpt-5.4-mini")


def client():
    global _client
    if _client is None:
        from openai import OpenAI
        if "OPENAI_API_KEY" not in ENV:
            raise SystemExit("[h2p] .env에 OPENAI_API_KEY 없음")
        _client = OpenAI(api_key=ENV["OPENAI_API_KEY"])
    return _client


def chat(system: str | None, user: str, *, temperature: float | None,
         max_tokens: int) -> str:
    """단일 호출 + 전역 상한·절단 가드(민옥 D1: 절단은 즉시 에러, 폐기 대상)."""
    global N_CALLS
    N_CALLS += 1
    if N_CALLS > MAX_CALLS:
        raise SystemExit(f"[ABORT] 전역 호출 상한 초과 ({N_CALLS} > {MAX_CALLS})")
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": user}]
    kwargs = dict(model=GEN_MODEL, messages=messages, max_completion_tokens=max_tokens)
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = client().chat.completions.create(**kwargs)
    choice = resp.choices[0]
    if choice.finish_reason == "length":
        raise RuntimeError(f"출력 절단(finish_reason=length) — D1 교훈: 폐기 대상")
    return choice.message.content or ""


# ---------------------------------------------------------------------------
# paths 재지정 + 픽스처 사본 (팀 data/ 읽기 전용, 산출물은 파일럿 폴더로)
# ---------------------------------------------------------------------------
def setup_pilot_data() -> None:
    paths.DATA = PILOT_DATA
    for sub in ("issues", "facts", "assignments", "debates", "judgments"):
        (PILOT_DATA / sub).mkdir(parents=True, exist_ok=True)
    team = ROOT / "data"
    pairs = [
        (team / "issues" / f"{ISSUE_ID}.json", PILOT_DATA / "issues" / f"{ISSUE_ID}.json"),
        (team / "facts" / f"facts_{ISSUE_ID}.json",
         PILOT_DATA / "facts" / f"facts_{ISSUE_ID}.json"),
        (team / "assignments" / f"assignment_{ISSUE_ID}.json",
         PILOT_DATA / "assignments" / f"assignment_{ISSUE_ID}.json"),
    ]
    for src, dst in pairs:
        if not dst.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    # D-p3: question 주입 (파일럿 사본에만 — 팀 파일 무수정)
    issue_p = PILOT_DATA / "issues" / f"{ISSUE_ID}.json"
    doc = json.loads(issue_p.read_text(encoding="utf-8"))
    if doc.get("question") != QUESTION_OVERRIDE:
        doc["question"] = QUESTION_OVERRIDE
        issue_p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 주입 함수 — 실호출판 / 리허설(dry)판
# ---------------------------------------------------------------------------
def make_utterance_fn(dry: bool, facts_list: list[dict]):
    if not dry:
        # 엔진이 조립한 저자 프롬프트 원문을 그대로 user 메시지로 (llm.obtain_response와
        # 동일 계약: system 없음). temperature는 config의 1.2가 엔진에서 넘어온다.
        def fn(inputs, model=None, temperature=None):
            return chat(None, inputs, temperature=temperature, max_tokens=MAX_GEN_TOKENS)
        return fn

    # dry: 결정론적 가짜 발화 — 호출 순번 n에 따라 팩트 하나를 원문 인용해
    # (n % len) 판정 스텁(_offline_vote, 문자열 대조)이 라운드마다 다른 생존
    # 패턴을 보게 한다 → 주입·재발화 집계 경로가 실제로 굴러가는지 검증용.
    counter = {"n": 0}

    def fake(inputs, model=None, temperature=None):
        n = counter["n"]
        counter["n"] += 1
        quoted = facts_list[n % len(facts_list)]["text"]
        return f"(리허설 발화 {n}) 제 생각은 이렇습니다. {quoted}"
    return fake


def make_vote_fn(dry: bool):
    if dry:
        return judge_mod._offline_vote  # 문자열 대조 스텁 (정본)

    def vote(fact, stage_utterances):
        # 잣대 문구 = judge.py 정본 그대로. 수송만 OpenAI (D-p2).
        raw = chat(judge_mod.JUDGE_SYSTEM,
                   judge_mod._user_prompt(fact, stage_utterances),
                   temperature=0, max_tokens=MAX_JUDGE_TOKENS)
        return judge_mod._parse_vote(raw, stage_utterances)
    return vote


# ---------------------------------------------------------------------------
# phase: debate — 정본 엔진 재사용 (결합부 무수정)
# ---------------------------------------------------------------------------
def phase_debate(arm: str, dry: bool) -> None:
    run_id = RUN_IDS[arm]
    dst = paths.debate(ISSUE_ID, run_id)
    if dst.exists():
        print(f"[debate:{arm}] {dst.name} 존재 — 스킵 (재실행하려면 파일 삭제)")
        return
    facts_list = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]
    debate_engine.run(
        ISSUE_ID, run_id, CFGS[arm],
        utterance_fn=make_utterance_fn(dry, facts_list),
        judge_vote_fn=make_vote_fn(dry),  # off 팔에선 엔진이 사용 안 함
    )
    print(f"[debate:{arm}] 완료 → {dst.name}")


# ---------------------------------------------------------------------------
# phase: judge — 사후 판정 (양 팔 같은 잣대, n=3 다수결·stage별 체크포인트)
# ---------------------------------------------------------------------------
def phase_judge(arm: str, dry: bool) -> None:
    run_id = RUN_IDS[arm]
    dst = paths.judgment(ISSUE_ID, run_id)
    if dst.exists():
        print(f"[judge:{arm}] {dst.name} 존재 — 스킵")
        return
    part_p = PILOT_DATA / "judgments" / f"partial_{ISSUE_ID}_{run_id}.json"
    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]
    facts_by_id = {f["fact_id"]: f for f in facts}
    stages_utt = judge_mod.group_by_stage(
        judge_mod.load_utterances(paths.debate(ISSUE_ID, run_id)))
    n_votes = 3
    vote_fn = make_vote_fn(dry)

    done: dict = json.loads(part_p.read_text(encoding="utf-8")) if part_p.exists() else {}
    stages_out = []
    for stage, utts in stages_utt.items():
        key = str(stage)
        if key in done:
            stages_out.append(done[key])
            print(f"[judge:{arm}] stage {stage} 체크포인트 재사용")
            continue
        recs = judge_mod.judge_stage(utts, facts, vote_fn=vote_fn, n_votes=n_votes)
        rec = {"stage": stage, "facts": recs}
        stages_out.append(rec)
        done[key] = rec
        part_p.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
        print(f"[judge:{arm}] stage {stage} 판정 완료 (팩트 {len(facts)} x {n_votes}표)")

    far_by_stage = [{"stage": s["stage"],
                     "far_system": judge_mod.far(s["facts"], facts_by_id),
                     "far_critical": judge_mod.far(s["facts"], facts_by_id,
                                                   critical_only=True)}
                    for s in stages_out]
    n_parse = sum(1 for s in stages_out for f in s["facts"]
                  for v in f["votes"] if judge_mod._is_parse_fail(v))
    judgment = {
        "schema_ver": judge_mod.SCHEMA_VER, "created_by": "mini_h2_pilot",
        "created_at": now(), "issue_id": ISSUE_ID, "run_id": run_id,
        "judge": {"model": ("dry-offline-stub" if dry else GEN_MODEL), "temperature": 0,
                  "n_votes": n_votes, "aggregation": "majority",
                  "prompt_ver": judge_mod.JUDGE_PROMPT_VER,
                  "note": "파일럿 판정기(D-p2) — 확정 사양(Sonnet)과 모델만 다름. 탐색적."},
        "stage_type": "round", "stages": stages_out, "recall_probe": [],
        "summary": {"far_by_stage": far_by_stage,
                    "far_system": far_by_stage[-1]["far_system"] if far_by_stage else None,
                    "far_agent_mean": None,
                    "far_critical": far_by_stage[-1]["far_critical"] if far_by_stage else None,
                    "judge_health": {"n_calls": len(stages_out) * len(facts) * n_votes,
                                     "n_parse_fail": n_parse}},
    }
    dst.write_text(json.dumps(judgment, ensure_ascii=False, indent=2), encoding="utf-8")
    part_p.unlink(missing_ok=True)
    print(f"[judge:{arm}] 완료 → {dst.name} (parse_fail {n_parse})")


# ---------------------------------------------------------------------------
# phase: analyze — QUESTIONS.md Q0~Q5 자동 집계
# ---------------------------------------------------------------------------
def _stage_status(judgment: dict) -> dict[int, dict[str, str]]:
    """stage -> {fact_id -> status}"""
    return {s["stage"]: {f["fact_id"]: f["status"] for f in s["facts"]}
            for s in judgment["stages"]}


def phase_analyze() -> None:
    out = {"created_at": now(), "issue_id": ISSUE_ID,
           "status": "탐색적/파일럿 — 정식 H1/H2 판정은 Anthropic 실호출분에서",
           "prereg": "experiments/mini_h2_pilot/QUESTIONS.md (커밋 = 등록)"}
    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]
    facts_by_id = {f["fact_id"]: f for f in facts}
    J, S, inj = {}, {}, {}
    for arm, run_id in RUN_IDS.items():
        J[arm] = json.loads(paths.judgment(ISSUE_ID, run_id).read_text(encoding="utf-8"))
        S[arm] = _stage_status(J[arm])
        events = [json.loads(ln) for ln in paths.debate(ISSUE_ID, run_id)
                  .read_text(encoding="utf-8").splitlines() if ln.strip()]
        inj[arm] = {e["round"]: e["injected_fact_ids"]
                    for e in events if e.get("event") == "ledger_inject"}

    surviving = judge_mod.SURVIVING
    # Q0 — FAR off vs v0
    out["q0_far_by_stage"] = {arm: J[arm]["summary"]["far_by_stage"] for arm in RUN_IDS}

    # Q1 재발화율 / Q2 재소실률 / Q3 블록 궤적 (v0 팔)
    q1, q2, q3 = [], [], []
    st = S["v0"]
    max_stage = max(st) if st else 0
    for r, ids in sorted(inj["v0"].items()):
        revived = [fid for fid in ids if st.get(r, {}).get(fid) in surviving]
        q1.append({"round": r, "injected": len(ids), "revived": len(revived),
                   "rate": round(len(revived) / len(ids), 4) if ids else None})
        if r + 1 <= max_stage:
            dead_again = [fid for fid in revived
                          if st.get(r + 1, {}).get(fid) not in surviving]
            q2.append({"round": r, "revived_at_r": len(revived),
                       "dead_at_r1": len(dead_again),
                       "rate": round(len(dead_again) / len(revived), 4) if revived else None})
        block = ledger.build_injection_block(ids, facts_by_id)
        q3.append({"round": r, "n_facts": len(ids), "n_chars": len(block)})
    out["q1_reuptake"], out["q2_relapse"], out["q3_block_growth"] = q1, q2, q3

    # Q4 경로 분해 예습 — 신규 언급(r-1 미언급 → r 언급)을 당회 inject 여부로 이분
    def new_mentions(status_map, inject_map):
        rows = []
        for r in sorted(status_map):
            if r == 0:
                continue
            prev, cur = status_map.get(r - 1, {}), status_map[r]
            injected = set(inject_map.get(r, []))
            for fid, stt in cur.items():
                if stt in surviving and prev.get(fid) not in surviving:
                    rows.append({"round": r, "fact_id": fid,
                                 "via": "ledger_linked" if fid in injected else "organic"})
        return rows
    v0_new = new_mentions(S["v0"], inj["v0"])
    off_new = new_mentions(S["off"], {})
    out["q4_pathways"] = {
        "v0": {"ledger_linked": sum(1 for x in v0_new if x["via"] == "ledger_linked"),
               "organic": sum(1 for x in v0_new if x["via"] == "organic"),
               "detail": v0_new},
        "off_arm_organic": len(off_new),
    }

    # Q5 판정기 건강 — 만장일치율·parse_fail
    q5 = {}
    for arm in RUN_IDS:
        cells = unanimous = 0
        for s in J[arm]["stages"]:
            for f in s["facts"]:
                cells += 1
                if len({v["status"] for v in f["votes"]}) == 1:
                    unanimous += 1
        q5[arm] = {"cells": cells,
                   "unanimous_rate": round(unanimous / cells, 4) if cells else None,
                   "judge_health": J[arm]["summary"]["judge_health"]}
    out["q5_judge_agreement"] = q5

    dst = PILOT_DATA / "h2_report.json"
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[analyze] Q0 far(마지막 stage): "
          f"off={J['off']['summary']['far_system']} v0={J['v0']['summary']['far_system']}")
    print(f"[analyze] Q1 재발화율: {[x['rate'] for x in q1]}  "
          f"Q2 재소실률: {[x['rate'] for x in q2]}")
    print(f"[analyze] Q4 신규 언급 v0: ledger={out['q4_pathways']['v0']['ledger_linked']} "
          f"organic={out['q4_pathways']['v0']['organic']} / off={len(off_new)}")
    print(f"[analyze] 완료 → {dst.name}")


def main() -> None:
    global MAX_CALLS
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["debate", "judge", "analyze", "all"])
    ap.add_argument("--arm", choices=["off", "v0"], help="debate/judge 필수")
    ap.add_argument("--dry", action="store_true", help="API 0원 리허설")
    ap.add_argument("--max-calls", type=int, default=600)
    args = ap.parse_args()
    MAX_CALLS = args.max_calls

    setup_pilot_data()
    if args.phase == "all":
        for arm in ("off", "v0"):
            phase_debate(arm, args.dry)
            phase_judge(arm, args.dry)
        phase_analyze()
    elif args.phase == "analyze":
        phase_analyze()
    else:
        if not args.arm:
            raise SystemExit("--arm off|v0 필요")
        {"debate": phase_debate, "judge": phase_judge}[args.phase](args.arm, args.dry)
    print(f"[calls] 이번 실행 외부 LLM 호출 {N_CALLS}회")


if __name__ == "__main__":
    main()
