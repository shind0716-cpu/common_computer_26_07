# -*- coding: utf-8 -*-
"""P3 전달 레이더 파일럿 — 별도 환경(OpenAI) 실행기. 탐색적/데모 지위.

지위: 브랜치 시제품·개인 키 집행(민옥 담화 전진 전례) — 팀 확정 judge(Sonnet·temp0·n3)가
아닌 **파일럿 판정기**(gpt-5.4-mini·temp0·n=1)를 쓴다. 정식 판정(H-T1·H-T2)은 미니 H2
실호출 몫이며, 이 산출물의 모든 수치는 "탐색적 — 정식 판정은 실호출분에서" 지위다.

무엇: 롤링 창 토론(자기·이웃 직전 발화만 — modules/debate_engine 정보 생태 재현)을
외부 모델로 돌려 v0.2 모양의 debate.jsonl / judgment.json 을 산출한다. 그러면
modules/transmission.py(레이더)가 무수정으로 소비한다. 팀 data/ 는 읽기만 하고,
산출물은 전부 experiments/transmission_pilot/data/ 아래(파이프라인 분리 — 민옥 관례).

안전장치: 호출 상한(--max-calls, 기본 300) · 단계별 체크포인트(완료 파일 스킵) ·
출력 절단 시 즉시 에러(민옥 D1 교훈) · judge 파싱실패 카운트(judge_health).

사용 (리포 루트에서):
  python experiments/transmission_pilot/run_pilot.py --phase probe   --issue carkey|esa
  python experiments/transmission_pilot/run_pilot.py --phase scan    --issue carkey|esa
  python experiments/transmission_pilot/run_pilot.py --phase debate  --issue carkey|esa
  python experiments/transmission_pilot/run_pilot.py --phase judge   --issue carkey|esa
  python experiments/transmission_pilot/run_pilot.py --phase analyze --issue carkey|esa
  (phase 는 독립 재실행 안전 — 완료 산출물이 있으면 스킵)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
FIX = HERE / "fixtures"
sys.path.insert(0, str(ROOT))  # modules.* import 용

RUN_ID = "tp1"                 # transmission pilot 1
ROUNDS = 4                     # 편차: 논문 상수 3 대비 +1 — 엄격 u>=1 관측창 확보 목적(README)
GEN_TEMP = 0.7                 # 민옥 N1 계승 (논문 1.2 는 별도 환경 통일 위해 미채택 — 편차 기록)
MAX_GEN_TOKENS = 1024          # 민옥 N2
MAX_JUDGE_TOKENS = 512
PROMPT_VER = "tp-v0.1"
JUDGE_PROMPT_VER = "tp-judge-v0.1"
PROBE_PROMPT_VER = "tp-prior-v0.1"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
GEN_MODEL = ENV.get("OPENAI_MODEL", "gpt-5.4-mini")
JUDGE_MODEL = ENV.get("JUDGE_MODEL", GEN_MODEL)

_client = None
N_CALLS = 0
MAX_CALLS = 300


def client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=ENV["OPENAI_API_KEY"])
    return _client


def chat(model: str, system: str, user: str, *, temperature: float | None,
         max_tokens: int, seed: int | None = None) -> str:
    """단일 호출 + 상한·절단 가드. 절단(finish_reason=length)은 즉시 에러 — D1 교훈."""
    global N_CALLS
    N_CALLS += 1
    if N_CALLS > MAX_CALLS:
        raise SystemExit(f"[ABORT] 호출 상한 초과 ({N_CALLS} > {MAX_CALLS})")
    kwargs = dict(model=model,
                  messages=[{"role": "system", "content": system},
                            {"role": "user", "content": user}],
                  max_completion_tokens=max_tokens)
    if temperature is not None:
        kwargs["temperature"] = temperature
    if seed is not None:
        kwargs["seed"] = seed  # best-effort (민옥 N3)
    resp = client().chat.completions.create(**kwargs)
    choice = resp.choices[0]
    if choice.finish_reason == "length":
        raise RuntimeError(f"출력 절단(finish_reason=length) — model={model}. D1 교훈: 폐기 대상")
    return choice.message.content or ""


# ---------------------------------------------------------------------------
# 재료 로드 (팀 data/ 는 읽기 전용, carkey 는 픽스처)
# ---------------------------------------------------------------------------
def materials(issue_key: str) -> dict:
    if issue_key == "esa":
        issue = json.loads((ROOT / "data/issues/issue_esa.json").read_text(encoding="utf-8"))
        facts = json.loads((ROOT / "data/facts/facts_issue_esa.json").read_text(encoding="utf-8"))
        assign = json.loads((ROOT / "data/assignments/assignment_issue_esa.json")
                            .read_text(encoding="utf-8"))
        # 파일럿 설정: ESA 는 question 필드가 없고 title 이 팩트 요지를 누출(레이더 영점 문제)
        # → 최소 질문으로 오버라이드(팀 파일 무수정 — 파일럿 로컬 설정, README 편차 기록).
        question = "룸메이트를 집주인에게 신고해야 할까요?"
    elif issue_key == "carkey":
        issue = json.loads((FIX / "issue_carkey.json").read_text(encoding="utf-8"))
        facts = json.loads((FIX / "facts_issue_carkey.json").read_text(encoding="utf-8"))
        assign = json.loads((FIX / "assignment_issue_carkey.json").read_text(encoding="utf-8"))
        question = issue["question"]
    else:
        raise KeyError(issue_key)
    return {"issue": issue, "facts": facts, "assignment": assign, "question": question,
            "issue_id": issue["issue_id"]}


def out_path(kind: str, issue_id: str) -> Path:
    DATA.mkdir(parents=True, exist_ok=True)
    names = {
        "debate": f"debate_{issue_id}_{RUN_ID}.jsonl",
        "judgment": f"judgment_{issue_id}_{RUN_ID}.json",
        "prior": f"prior_{issue_id}_{RUN_ID}.json",
        "scan": f"question_scan_{issue_id}_{RUN_ID}.json",
        "report": f"transmission_report_{issue_id}_{RUN_ID}.json",
    }
    return DATA / names[kind]


# ---------------------------------------------------------------------------
# phase: debate — 롤링 창 토론 (debate_engine 정보 생태 재현)
# ---------------------------------------------------------------------------
GEN_SYSTEM = ("당신은 토론 참가자입니다. 주어진 질문에 대해 자신의 입장(찬성=yes/반대=no)을 "
              "설득력 있게 주장하세요. 아는 사실이 있으면 최대한 유지하며 활용하세요. "
              "300자 이내의 한 단락으로 답하세요.")


def initial_prompt(question: str, fact_text: str, answer: str) -> str:
    return (f"질문: {question}\n\n당신이 알고 있는 사실:\n{fact_text}\n"
            f"당신의 입장: {answer}\n\n첫 발언을 하세요.")


def continue_prompt(question: str, previous: str, others: str) -> str:
    return (f"질문: {question}\n\n당신의 직전 발언:\n{previous}\n\n"
            f"다른 참가자들의 직전 발언:\n{others}\n\n"
            f"토론을 이어가세요. 당신의 입장을 유지하되 새 논점에 대응하세요.")


def phase_debate(issue_key: str) -> None:
    m = materials(issue_key)
    issue_id = m["issue_id"]
    dst = out_path("debate", issue_id)
    if dst.exists() and any('"event": "run_end"' in ln
                            for ln in dst.read_text(encoding="utf-8").splitlines()):
        print(f"[debate] {dst.name} 완료본 존재 — 스킵")
        return
    agents = m["assignment"]["agents"]
    fact_by_id = {f["fact_id"]: f["text"] for f in m["facts"]["facts"]}
    seed = int(m["assignment"].get("seed", 42))
    length = len(agents)
    events: list[dict] = []

    def emit(event: str, **fields):
        events.append({"event": event, "run_id": RUN_ID, "ts": now(), **fields})

    def flush():
        with dst.open("w", encoding="utf-8") as fh:
            for rec in events:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # round 0 — 할당 팩트는 여기 한 번만 (롤링 창 생태 재현의 핵심).
    current = []
    for i, ag in enumerate(agents):
        fact_text = "".join(f"- {fact_by_id[fid]}\n" for fid in ag["assigned_fact_ids"])
        answer = "yes" if ag["stance"] == "pro" else "no"
        inputs = initial_prompt(m["question"], fact_text, answer)
        resp = chat(GEN_MODEL, GEN_SYSTEM, inputs, temperature=GEN_TEMP,
                    max_tokens=MAX_GEN_TOKENS, seed=1000 * seed + i)
        current.append(resp)
        emit("utterance", ledger_mode="off", round=0, agent_id=ag["agent_id"],
             position=None, stance=ag["stance"], perspective=ag.get("perspective"),
             model=GEN_MODEL, temperature=GEN_TEMP, prompt_ver=PROMPT_VER,
             prompt_hash=sha256(inputs), response_text=resp)
        print(f"[debate] round 0 · {ag['agent_id']} ok")
    flush()

    # 좌석 셔플 + full edges (debate_engine 관례 재현).
    order_idx = list(range(length))
    random.Random(seed).shuffle(order_idx)
    seated = [agents[j] for j in order_idx]
    previous = [current[j] for j in order_idx]
    emit("seating", seed=seed, structure="full",
         order=[ag["agent_id"] for ag in seated])
    edges = [[j for j in range(length) if j != i] for i in range(length)]

    for r in range(1, ROUNDS + 1):
        nxt = []
        for i in range(length):
            others = "".join(f"참가자 {k + 1}: {previous[j]}\n"
                             for k, j in enumerate(edges[i]))
            inputs = continue_prompt(m["question"], previous[i] or "", others)
            resp = chat(GEN_MODEL, GEN_SYSTEM, inputs, temperature=GEN_TEMP,
                        max_tokens=MAX_GEN_TOKENS, seed=1000 * seed + 100 * r + i)
            nxt.append(resp)
            ag = seated[i]
            emit("utterance", ledger_mode="off", round=r, agent_id=ag["agent_id"],
                 position=i, stance=ag["stance"], perspective=ag.get("perspective"),
                 model=GEN_MODEL, temperature=GEN_TEMP, prompt_ver=PROMPT_VER,
                 prompt_hash=sha256(inputs), response_text=resp)
            print(f"[debate] round {r}/{ROUNDS} · {ag['agent_id']} ok")
        previous = nxt
        flush()  # 라운드 체크포인트

    emit("run_end", rounds_completed=ROUNDS, n_llm_calls=N_CALLS,
         n_fallbacks=0, status="complete")
    flush()
    print(f"[debate] 완료 → {dst.name} (발화 {length * (ROUNDS + 1)})")


# ---------------------------------------------------------------------------
# phase: judge — 팩트×stage 언급·귀속 판정 (파일럿 판정기 — 팀 확정 judge 아님)
# ---------------------------------------------------------------------------
JUDGE_SYSTEM = ("당신은 토론 기록 분석가입니다. 주어진 발언들에서 특정 사실이 언급되는지 "
                "판정합니다. 의역(paraphrase)도 언급으로 칩니다. 반드시 JSON 하나만 "
                "출력하세요.")


def judge_prompt(fact_text: str, utterances: list[tuple[str, str]]) -> str:
    utt = "".join(f"[{aid}] {text}\n\n" for aid, text in utterances)
    return (f"발언 기록:\n{utt}\n판정 대상 사실: \"{fact_text}\"\n\n"
            "위 사실(의역 포함)을 언급한 발언자가 있습니까?\n"
            '다음 JSON 형식으로만 답하세요: {"mentioned": true/false, '
            '"agents_mentioning": ["agent_..."]}')


def phase_judge(issue_key: str) -> None:
    m = materials(issue_key)
    issue_id = m["issue_id"]
    dst = out_path("judgment", issue_id)
    if dst.exists():
        print(f"[judge] {dst.name} 존재 — 스킵")
        return
    debate_lines = out_path("debate", issue_id).read_text(encoding="utf-8").splitlines()
    utts_by_round: dict[int, list[tuple[str, str]]] = {}
    for ln in debate_lines:
        if not ln.strip():
            continue
        ev = json.loads(ln)
        if ev.get("event") == "utterance":
            utts_by_round.setdefault(ev["round"], []).append(
                (ev["agent_id"], ev["response_text"]))
    facts = m["facts"]["facts"]
    n_parse_fail = 0
    stages = []
    for r in sorted(utts_by_round):
        frs = []
        for k, f in enumerate(facts):
            raw = chat(JUDGE_MODEL, JUDGE_SYSTEM,
                       judge_prompt(f["text"], utts_by_round[r]),
                       temperature=0, max_tokens=MAX_JUDGE_TOKENS,
                       seed=2000 + 100 * r + k)
            try:
                s = raw[raw.index("{"): raw.rindex("}") + 1]
                vote = json.loads(s)
                mentioned = bool(vote.get("mentioned"))
                ams = [a for a in vote.get("agents_mentioning", [])
                       if isinstance(a, str)]
            except Exception:
                n_parse_fail += 1
                mentioned, ams = False, []   # 무음 강등 대신 카운트 병기(judge_health)
            frs.append({"fact_id": f["fact_id"],
                        "status": "mentioned" if mentioned else "unmentioned",
                        "votes": [{"status": "mentioned" if mentioned else "unmentioned",
                                   "agents_mentioning": ams, "reason": "tp-single-vote"}],
                        "agents_mentioning": ams})
            print(f"[judge] stage {r}/{max(utts_by_round)} · 팩트 {k + 1}/{len(facts)} · "
                  f"파싱실패 누적 {n_parse_fail}")
        stages.append({"stage": r, "stage_type": "round", "facts": frs})
    judgment = {
        "schema_ver": "0.2", "created_by": "yohan_transmission_pilot",
        "created_at": now(), "issue_id": issue_id, "run_id": RUN_ID,
        "judge": {"model": JUDGE_MODEL, "temperature": 0, "n_votes": 1,
                  "aggregation": "single",
                  "prompt_ver": JUDGE_PROMPT_VER,
                  "note": "파일럿 판정기 — 팀 확정 judge(Sonnet·temp0·n3) 아님. 탐색적."},
        "stage_type": "round",
        "stages": stages,
        "summary": {"judge_health": {"n_calls": len(stages) * len(facts),
                                     "n_parse_fail": n_parse_fail}},
    }
    dst.write_text(json.dumps(judgment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[judge] 완료 → {dst.name} (parse_fail {n_parse_fail})")


# ---------------------------------------------------------------------------
# phase: probe — 프라이어 프로브 (민옥 확정 방식 v0: 기사 없이 팩트 지식 질의)
# ---------------------------------------------------------------------------
PROBE_SYSTEM = ("당신은 자신의 사전 지식을 정직하게 보고합니다. 지어내지 마세요. "
                "반드시 JSON 하나만 출력하세요.")


def phase_probe(issue_key: str) -> None:
    m = materials(issue_key)
    issue_id = m["issue_id"]
    dst = out_path("prior", issue_id)
    if dst.exists():
        print(f"[probe] {dst.name} 존재 — 스킵")
        return
    rows = []
    for k, f in enumerate(m["facts"]["facts"]):
        user = (f"다음 진술을 보세요:\n\"{f['text']}\"\n\n"
                "맥락 문서 없이, 당신의 사전 지식만으로 이 진술이 가리키는 구체 사건·"
                "인물·수치를 이미 알고 있습니까? 일반 상식으로 그럴듯한지가 아니라, "
                "이 특정 사실을 아는지를 답하세요.\n"
                'JSON: {"known": true/false, "reason": "한 문장"}')
        raw = chat(GEN_MODEL, PROBE_SYSTEM, user, temperature=0,
                   max_tokens=256, seed=3000 + k)
        try:
            s = raw[raw.index("{"): raw.rindex("}") + 1]
            known = bool(json.loads(s).get("known"))
        except Exception:
            known = False
        rows.append({"fact_id": f["fact_id"], "score": 1.0 if known else 0.0,
                     "raw": raw})
        print(f"[probe] {f['fact_id']}: known={known}")
    dst.write_text(json.dumps({
        "issue_id": issue_id, "run_id": RUN_ID, "probe_model": GEN_MODEL,
        "probe_prompt_ver": PROBE_PROMPT_VER, "probed_at": now(), "facts": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[probe] 완료 → {dst.name}")


# ---------------------------------------------------------------------------
# phase: scan — question 영점 조정 (v1.0 §3-2: question 문면에서 판독 가능한 팩트 제외)
# ---------------------------------------------------------------------------
def phase_scan(issue_key: str) -> None:
    m = materials(issue_key)
    issue_id = m["issue_id"]
    dst = out_path("scan", issue_id)
    if dst.exists():
        print(f"[scan] {dst.name} 존재 — 스킵")
        return
    exposed = []
    for k, f in enumerate(m["facts"]["facts"]):
        raw = chat(JUDGE_MODEL, JUDGE_SYSTEM,
                   judge_prompt(f["text"], [("question", m["question"])]),
                   temperature=0, max_tokens=MAX_JUDGE_TOKENS, seed=4000 + k)
        try:
            s = raw[raw.index("{"): raw.rindex("}") + 1]
            if bool(json.loads(s).get("mentioned")):
                exposed.append(f["fact_id"])
        except Exception:
            pass
    dst.write_text(json.dumps({
        "issue_id": issue_id, "question": m["question"],
        "question_exposed_ids": exposed, "scanned_at": now(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scan] 완료 → question_exposed={exposed}")


# ---------------------------------------------------------------------------
# phase: analyze — 레이더 소비 (modules.transmission 무수정)
# ---------------------------------------------------------------------------
def phase_analyze(issue_key: str) -> None:
    from modules import transmission as tr
    m = materials(issue_key)
    issue_id = m["issue_id"]
    judgment = json.loads(out_path("judgment", issue_id).read_text(encoding="utf-8"))
    events = [json.loads(ln) for ln
              in out_path("debate", issue_id).read_text(encoding="utf-8").splitlines()
              if ln.strip()]
    prior = json.loads(out_path("prior", issue_id).read_text(encoding="utf-8"))
    scan = json.loads(out_path("scan", issue_id).read_text(encoding="utf-8"))
    facts_by_id = {f["fact_id"]: dict(f) for f in m["facts"]["facts"]}
    for row in prior["facts"]:
        facts_by_id[row["fact_id"]].setdefault("prior", {})
        facts_by_id[row["fact_id"]]["prior"] = {"score": row["score"]}
    rep = tr.report(judgment, m["assignment"], events, facts_by_id,
                    question_exposed_ids=frozenset(scan["question_exposed_ids"]))
    rep["pilot_meta"] = {
        "status": "탐색적/데모 지위 — 정식 판정(H-T1·H-T2)은 미니 H2 실호출분에서",
        "scenario_credit": ("carkey: 안현수 7/27 둘째 이슈 후보 2 (후보 지위, 팀 검수 전)"
                            if issue_key == "carkey" else "ESA 팀 정본 픽스처"),
        "deviations": ["rounds=4(논문 3)", "GEN temp 0.7(민옥 N1)",
                       "파일럿 판정기 n=1(팀 확정 judge 아님)",
                       "ESA question 오버라이드(title 누출 회피)" if issue_key == "esa" else None],
    }
    dst = out_path("report", issue_id)
    dst.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    s = rep["system"]
    print(f"[analyze] {issue_id}: 쌍 {s['n_pairs_tracked']} · kinds={s['kinds']}")
    print(f"[analyze] TSR(엄격)={s['tsr_system']} 상한={s['tsr_system_upper']} "
          f"u0={s['n_acq_u0']} · low-prior TSR={rep['system_low_prior']['tsr_system']}")
    print(f"[analyze] question_exposed={scan['question_exposed_ids']}")
    print(f"[analyze] 완료 → {dst.name}")


def main() -> None:
    global MAX_CALLS
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["probe", "scan", "debate", "judge", "analyze"])
    ap.add_argument("--issue", required=True, choices=["esa", "carkey"])
    ap.add_argument("--max-calls", type=int, default=300)
    args = ap.parse_args()
    MAX_CALLS = args.max_calls
    {"probe": phase_probe, "scan": phase_scan, "debate": phase_debate,
     "judge": phase_judge, "analyze": phase_analyze}[args.phase](args.issue)
    print(f"[calls] 이번 실행 LLM 호출 {N_CALLS}회")


if __name__ == "__main__":
    main()
