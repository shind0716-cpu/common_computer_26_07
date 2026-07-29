# -*- coding: utf-8 -*-
"""[요한 · 계기 점검] H3·H4 — 추가 LLM 호출 0, 기존 산출물 재분석.

지위: 탐색적/계기 점검. 판별표 밖, 가설 검정 아님. 단일 run·단일 판정기(파일럿 n=1)이며
일반화하지 않는다. 사전 예측은 실행 전 대화에 기록됨(H3: v0 근접도 > off / H4: 누출이
high-prior 팩트에 몰림) — 둘 다 결과는 아래.

H3 (차분 방어선 검증): 판정기가 "언급"으로 센 발화가 팩트 원문에 얼마나 가까운지를
팔(off/v0)별로 잰다. 장부 팔이 계통적으로 더 원문에 가까우면, 팔 간 차분에서 판정 오차가
상쇄된다는 방어선이 깨진다. 근접도 = 팩트 텍스트의 문자 3-gram 중 발화에 나타난 비율
(containment; 축자 인용=1.0). 어휘 계산이라 결정론적 — 판정기 재호출 없음.

H4 (prior 구성과 누출): 접근 없는 발화(resurgence)와 prior_suspect가 모델이 이미 아는
팩트(프라이어 프로브 known=True)에 몰리는지 본다. 몰리면 "닫힌 세계"가 방어막으로 작동한
것이고, 안 몰리면 누출 경로가 사전지식이 아니라는 뜻.

주의: H4는 access_report의 resurgence **좌표**만 쓰고, 재검토 대상으로 표기된 집계 수치
(사망·부활 건수)는 인용하지 않는다(7/29 정정 조항).

사용: python experiments/instrument_check/run_checks.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent.parent
H2 = ROOT / "experiments/mini_h2_pilot/data"
TP = ROOT / "experiments/transmission_pilot/data"
OUT = Path(__file__).resolve().parent / "results.json"


def ngrams(text: str, n: int = 3) -> set:
    t = re.sub(r"[^0-9A-Za-z가-힣]", "", text or "")
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def containment(fact: str, utterance: str) -> float | None:
    """팩트 3-gram 중 발화에 나타난 비율. 축자 인용이면 1.0에 가깝다."""
    F, U = ngrams(fact), ngrams(utterance)
    return len(F & U) / len(F) if F else None


def load_arm(arm: str) -> tuple[dict, dict, dict]:
    events = [json.loads(l) for l
              in (H2 / f"debates/debate_issue_esa_h2p_{arm}.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    utt = {(e["round"], e["agent_id"]): e.get("response_text", "")
           for e in events if e.get("event") == "utterance"}
    inj: dict = {}
    for e in events:
        if e.get("event") == "ledger_inject":
            inj.setdefault(e.get("round"), set()).update(e.get("injected_fact_ids", []))
    judgment = json.loads((H2 / f"judgments/judgment_issue_esa_h2p_{arm}.json")
                          .read_text(encoding="utf-8"))
    return utt, inj, judgment


def h3() -> dict:
    facts = json.loads((H2 / "facts/facts_issue_esa.json").read_text(encoding="utf-8"))
    ftext = {f["fact_id"]: f["text"] for f in facts["facts"]}
    out = {}
    for arm in ("off", "v0"):
        utt, inj, judgment = load_arm(arm)
        detected, undetected, rows = [], [], []
        for st in judgment["stages"]:
            s = st["stage"]
            for f in st.get("facts", []):
                fid = f["fact_id"]
                F = ngrams(ftext.get(fid, ""))
                if not F:
                    continue
                ams = set(f.get("agents_mentioning") or [])
                for (r, a), u in utt.items():
                    if r != s:
                        continue
                    c = len(F & ngrams(u)) / len(F)
                    if a in ams:
                        detected.append(c)
                        was_inj = any(fid in inj.get(rr, set()) for rr in inj if rr <= s)
                        rows.append({"stage": s, "fact_id": fid, "agent_id": a,
                                     "proximity": round(c, 4), "injected_before": was_inj})
                    else:
                        undetected.append(c)
        detected.sort()
        undetected.sort()
        p10 = detected[len(detected) // 10]
        by_stage = {}
        for s in sorted({r["stage"] for r in rows}):
            sub = [r["proximity"] for r in rows if r["stage"] == s]
            by_stage[s] = {"n": len(sub), "mean": round(mean(sub), 4),
                           "median": round(median(sub), 4)}
        arm_out = {
            "n_mentions": len(rows),
            "inject_rounds": sorted(inj),
            "proximity_mean": round(mean(r["proximity"] for r in rows), 4),
            "by_stage": by_stage,
            "detected": {"n": len(detected), "min": round(detected[0], 4),
                         "p10": round(p10, 4),
                         "median": round(detected[len(detected) // 2], 4)},
            "undetected": {"n": len(undetected),
                           "median": round(undetected[len(undetected) // 2], 4),
                           "p90": round(undetected[int(len(undetected) * 0.9)], 4),
                           "max": round(undetected[-1], 4)},
            "overlap_above_detected_p10": sum(1 for c in undetected if c >= p10),
        }
        if arm == "v0":
            for flag in (True, False):
                sub = [r["proximity"] for r in rows if r["injected_before"] == flag]
                if sub:
                    arm_out[f"injected_{flag}"] = {"n": len(sub),
                                                   "mean": round(mean(sub), 4)}
        out[arm] = arm_out
    return out


def h4() -> dict:
    out = {}
    for issue in ("issue_esa", "issue_carkey"):
        prior = json.loads((TP / f"prior_{issue}_tp1.json").read_text(encoding="utf-8"))
        known = {r["fact_id"]: r["score"] > 0 for r in prior["facts"]}
        acc = json.loads((TP / f"access_report_{issue}_tp1.json").read_text(encoding="utf-8"))
        tr = json.loads((TP / f"transmission_report_{issue}_tp1.json").read_text(encoding="utf-8"))
        ps = {r["fact_id"]: r["n_prior_suspect"] for r in tr["fact_metrics"]}
        events = []
        for rec in acc["records"]:
            fid = rec["fact_id"]
            rounds = [t["round"] for t in rec["timeline"] if t["resurgent_speakers"]]
            if rounds or ps.get(fid, 0):
                events.append({"fact_id": fid, "known": known.get(fid),
                               "resurgent_rounds": rounds,
                               "prior_suspect": ps.get(fid, 0)})
        out[issue] = {
            "n_facts": len(known),
            "n_known_true": sum(known.values()),
            "events": events,
            "resurgent_facts_known_true": sum(1 for e in events
                                              if e["resurgent_rounds"] and e["known"]),
            "resurgent_facts_known_false": sum(1 for e in events
                                               if e["resurgent_rounds"] and not e["known"]),
            "prior_suspect_total": sum(ps.values()),
        }
    return out


def main() -> None:
    results = {
        "status": "탐색적 계기 점검 — 판별표 밖·추가 LLM 0·단일 run·파일럿 판정기(n=1)",
        "predictions_before_run": {
            "H3": "v0 팔의 원문 근접도가 off 팔보다 높다",
            "H4": "resurgence·prior_suspect가 known=True 팩트에 몰린다",
        },
        "H3_arm_dependent_judge_error": h3(),
        "H4_prior_composition_leak": h4(),
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n[saved] {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
