"""[민옥 트랙] 교차 채점 — PREREG_v1 §5 (중대 8): 제2 판정기로 표본 런을 재채점, κ 보고.

주 판정기 gpt-mini의 자기계열 교락(피험자 GPT와 동일 모델) 완화 장치.
제2 판정기 = gemini-flash (temp 0 · n=3 다수결 · votes 보존 — 사양 동일, 모델만 교체).
표본: 모델별 1런 (2모델 축소 D-0 반영 → 계 2런). 선정은 사전 임의 고정 — 주 조건(②)의
전진 팔 rep1. 콜: 2런 × 6텍스트 × 12팩트 × 3표 = 432콜.

실행: PYTHONUTF8=1 python experiments/memory_structure/judge_cross.py
산출: judgments_cross/<모델>/judge_<run>.json + κ(전체 일치율·Cohen's kappa) 콘솔 출력
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules import judge as J  # noqa: E402
from modules import llm  # noqa: E402

ISSUE_ID = "issue_camp"
CROSS_MODEL = "gemini-flash"          # 제2 판정기
N_VOTES = 3
SAMPLES = [("gpt", "P_note_rep1"), ("gemini-flash", "P_note_rep1")]  # 사전 고정 표본
HERE = Path(__file__).resolve().parent
SURV = J.SURVIVING


def targets_of(run: dict):
    t = [(f"essay_r{i}", e) for i, e in enumerate(run["essays"])]
    if run["memory"] == "note":
        t.append(("carrier", run["notes"][-1]))
    elif run["memory"] == "prev":
        t.append(("carrier", run["essays"][-1]))
    return t


def main() -> None:
    facts = json.loads(paths.facts(ISSUE_ID).read_text(encoding="utf-8"))["facts"]
    llm.preflight(CROSS_MODEL, temperature=J.JUDGE_TEMPERATURE)
    vote_fn = lambda f, u: J._llm_vote(CROSS_MODEL, f, u)  # noqa: E731

    agree = disagree = 0
    a_pos = b_pos = both_pos = 0
    n_cells = 0
    for run_model, run_id in SAMPLES:
        run = json.loads((HERE / "runs" / run_model / f"run_{run_id}.json").read_text(encoding="utf-8"))
        primary = json.loads((HERE / "judgments" / run_model / f"judge_{run_id}.json").read_text(encoding="utf-8"))
        out_dir = HERE / "judgments_cross" / run_model
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = out_dir / f"judge_{run_id}.json"
        if dst.exists():
            cross = json.loads(dst.read_text(encoding="utf-8"))
            print(f"[skip] {run_model}/{run_id} — 기존 교차 판정 사용")
        else:
            records = {}
            for tag, text in targets_of(run):
                utt = [{"agent_id": "solo", "response_text": text}]
                records[tag] = [J.judge_fact(utt, f, vote_fn=vote_fn, n_votes=N_VOTES) for f in facts]
                print(f"  {run_model}/{run_id}/{tag} 완료")
            cross = {"schema": "solo_judgment_cross_v1", "run_id": run_id, "run_model": run_model,
                     "judge": {"model": CROSS_MODEL, "model_id": llm.resolve_model(CROSS_MODEL),
                               "temperature": J.JUDGE_TEMPERATURE, "n_votes": N_VOTES,
                               "prompt_ver": J.JUDGE_PROMPT_VER + "+merged_system",
                               "judged_at": datetime.now(timezone.utc).isoformat()},
                     "records": records}
            dst.write_text(json.dumps(cross, ensure_ascii=False, indent=2), encoding="utf-8")
        # κ 집계 (텍스트×팩트 셀 단위 이진 일치)
        for tag in cross["records"]:
            p = {r["fact_id"]: r["status"] in SURV for r in primary["records"][tag]}
            c = {r["fact_id"]: r["status"] in SURV for r in cross["records"][tag]}
            for f in p:
                n_cells += 1
                a_pos += p[f]; b_pos += c[f]; both_pos += p[f] and c[f]
                if p[f] == c[f]: agree += 1
                else: disagree += 1
    po = agree / n_cells
    pa, pb = a_pos / n_cells, b_pos / n_cells
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    print(f"\n[교차 채점] 셀 {n_cells} · 일치 {agree} ({100*po:.1f}%) · Cohen's κ = {kappa:.3f}")
    print(f"  (기준: κ ≥ 0.60 판정 가능 · ≥ 0.80 양호 — 7/27 팀 합의 하한)")
    print(f"  주 판정기 생존률 {100*pa:.1f}% vs 교차 판정기 {100*pb:.1f}%"
          f" — 격차가 크면 판정기 비대칭(자기계열) 신호")


if __name__ == "__main__":
    main()
