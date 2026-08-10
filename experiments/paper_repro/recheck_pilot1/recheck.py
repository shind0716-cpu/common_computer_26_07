# -*- coding: utf-8 -*-
"""pilot1 재집계 — PREREG.md 의 사전 고정 규칙 실행 (LLM 호출 0, 원자료 무수정).

산출: 이 폴더의 recheck_result.json (+ 재산출 judgment/stance 사본).
data/ 는 읽기 전용 — 원본 산출물을 덮어쓰지 않는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACK = HERE.parent
ROOT = TRACK.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TRACK))

import bridge  # noqa: E402
from experiments.judge_axis.axis_probe import parse_matched  # noqa: E402 — 파서 재사용(읽기만)

DATA = TRACK / "data"
ISSUE = "issue_ethics_0476"
RUN = "pilot1"


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    facts_doc = json.loads((DATA / "facts" / f"facts_{ISSUE}.json").read_text(encoding="utf-8"))
    assignment = json.loads((DATA / "assignments" / f"assignment_{ISSUE}.json").read_text(
        encoding="utf-8"))
    n_facts = len(facts_doc["facts"])

    # 1) 저자 축 원장 재파싱 대조 (R3)
    rows = load_jsonl(DATA / "raw_calls" / f"axis_author_{RUN}.jsonl")
    reparse_mismatch = []
    reparsed_rows = []
    for r in rows:
        idx, status = parse_matched(r["raw_response"], n_facts)
        if idx != r.get("matched_fact_ids") or (status == "parse_fail") != (
                r.get("matched_fact_ids") is None):
            reparse_mismatch.append({"round": r["round"], "agent_id": r["agent_id"],
                                     "stored": r.get("matched_fact_ids"), "reparsed": idx,
                                     "reparse_status": status})
        reparsed_rows.append({**r, "matched_fact_ids": idx})

    # 2) 수정된 bridge 로 judgment 재산출 → 원본 대조 (R1/R2)
    jd_new = bridge.author_rows_to_judgment(
        reparsed_rows, facts_doc, issue_id=ISSUE, run_id=f"{RUN}_author_recheck",
        prompt_ver="delibtrace@afce3595")
    jd_old = json.loads((DATA / "judgments" / f"judgment_{ISSUE}_{RUN}_author.json").read_text(
        encoding="utf-8"))
    far_new = [{"stage": e["stage"], "far_system": e["far_system"],
                "far_critical": e["far_critical"]} for e in jd_new["summary"]["far_by_stage"]]
    far_old = [{"stage": e["stage"], "far_system": e["far_system"],
                "far_critical": e["far_critical"]} for e in jd_old["summary"]["far_by_stage"]]
    status_diff = []
    old_stages = {s["stage"]: {f["fact_id"]: f["status"] for f in s["facts"]}
                  for s in jd_old["stages"]}
    for s in jd_new["stages"]:
        for f in s["facts"]:
            old = old_stages.get(s["stage"], {}).get(f["fact_id"])
            if old != f["status"]:
                status_diff.append({"stage": s["stage"], "fact_id": f["fact_id"],
                                    "old": old, "new": f["status"]})

    # 3) stance 재산출 → 원본 대조
    srows = load_jsonl(DATA / "raw_calls" / f"stance_{RUN}.jsonl")
    sd_new = bridge.stance_rows_to_summary(srows, assignment, issue_id=ISSUE, run_id=f"{RUN}_recheck")
    sd_old = json.loads((DATA / f"stance_summary_{ISSUE}_{RUN}.json").read_text(encoding="utf-8"))
    stance_new = sd_new["summary"]["match_rate_by_round"]
    stance_old = sd_old["summary"]["match_rate_by_round"]

    result = {
        "prereg": "PREREG.md (실행 전 커밋)",
        "n_rows_author": len(rows),
        "n_rows_stance": len(srows),
        "r3_reparse_mismatch": reparse_mismatch,
        "far_by_stage_original": far_old,
        "far_by_stage_recheck": far_new,
        "far_identical": far_new == far_old,
        "status_diff": status_diff,
        "stance_original": stance_old,
        "stance_recheck": stance_new,
        "stance_identical": stance_new == stance_old,
        "verdict": None,  # 아래에서 채움
    }
    if result["far_identical"] and result["stance_identical"] and not reparse_mismatch:
        result["verdict"] = "R1 — 전건 일치: 0.92 는 리뷰 결함의 오염이 아님(검산 완료)"
    elif reparse_mismatch:
        result["verdict"] = "R3 — 재파싱 불일치: 행 원문 판독(G5) 선행 필요"
    else:
        result["verdict"] = "R2 — 불일치: 원본 정정 대상 표기·원인 판독 선행"

    (HERE / "judgment_recheck.json").write_text(
        json.dumps(jd_new, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "stance_recheck.json").write_text(
        json.dumps(sd_new, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "recheck_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("far_by_stage_original", "far_by_stage_recheck")},
                     ensure_ascii=False, indent=2))
    print("far 원본:", far_old)
    print("far 재산출:", far_new)


if __name__ == "__main__":
    main()
