#!/usr/bin/env python
"""U자 곡선 재해석 원커맨드 러너 — 실측 FAR 곡선 vs 조건부 지표 2종을 나란히.

판별 프로토콜: docs/analysis/UCURVE_PREREG.md (데이터 확인 전 사전 고정).
이 스크립트는 modules/survival.py 의 **공개 인터페이스만** 호출한다(지표 로직 재구현 금지,
LLM 호출 없음 — 순수 계산). survival.report() 가 산출하는:
  · far_by_stage  : 실측 FAR 곡선(참고지표, judge.far 위임)
  · transitions   : 전이 hazard conditional_attrition (주지표 1)
  · post_intro_final_loss : 누적 소실률 (주지표 2)
을 그대로 받아 stdout 표 + json 파일로 낸다.

사용:
  python -m scripts.run_ucurve_reanalysis data/judgments/judgment_issue_esa_dryrun.json
  python scripts/run_ucurve_reanalysis.py <judgment.json> [<judgment2.json> ...] [--out out.json] [--critical-only]

facts 파일(critical 라벨용)은 judgment 의 issue_id 로 자동 탐색한다. 없으면 system 지표만
내고 critical 지표는 생략한다(경고만, 에러 아님). 파일이 아직 없는 Mystery Case 는 경로만
주어지면 동작하며, 없을 때는 리포 기존 픽스처로 스모크할 수 있다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 리포 루트를 import 경로에 추가(scripts/ 에서 modules 패키지를 찾도록).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules import survival  # noqa: E402  (경로 주입 후 import)
from modules import paths     # noqa: E402


def _load_judgment(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _try_load_facts_by_id(judgment: dict, judgment_path: Path) -> tuple[dict, str | None]:
    """judgment 의 issue_id 로 facts 파일을 찾아 {fact_id: fact} 반환.

    반환 (facts_by_id, warn). facts 파일이 없으면 ({}, 경고문). critical 지표는 이때 생략.
    survival.far_by_stage/report 는 critical_only=False 면 facts_by_id 를 실제로 읽지 않으므로
    빈 dict 로도 system 지표가 정상 산출된다.
    """
    issue_id = judgment.get("issue_id")
    if not issue_id:
        return {}, f"judgment 에 issue_id 없음({judgment_path.name}) — critical 지표 생략"
    facts_path = paths.facts(issue_id)
    if not facts_path.exists():
        return {}, f"facts 파일 없음({facts_path}) — critical 지표 생략, system 지표만 산출"
    doc = json.loads(facts_path.read_text(encoding="utf-8"))
    return {f["fact_id"]: f for f in doc["facts"]}, None


def analyze_one(judgment_path: Path, *, critical_only: bool, fact_clock: bool = False) -> dict:
    """judgment 하나에 대해 survival.report() 를 호출하고 결과 dict 를 조립(순수).

    fact_clock=True 면 도입 시점 정렬 생존분석(survival.fact_clock_report, w=0·w=1)을 덧붙인다.
    기본(False)이면 기존 P2 출력만 — 기본 동작 불변.
    """
    judgment = _load_judgment(judgment_path)
    facts_by_id, warn = _try_load_facts_by_id(judgment, judgment_path)

    scope = "critical" if critical_only else "system"
    if critical_only and not facts_by_id:
        # critical 요청인데 facts 없음 → 조용히 system 으로 강등(경고 남김).
        warn = (warn or "") + " | --critical-only 요청이나 facts 부재로 system 으로 강등"
        critical_only = False
        scope = "system"

    rep = survival.report(judgment, facts_by_id, critical_only=critical_only)

    stage_values = [s.get("stage") for s in sorted(
        judgment.get("stages", []), key=lambda s: (s.get("stage") is None, s.get("stage")))]

    out = {
        "judgment_path": str(judgment_path),
        "issue_id": judgment.get("issue_id"),
        "run_id": judgment.get("run_id"),
        "stage_type": judgment.get("stage_type"),
        "scope": scope,
        "n_stages": len(judgment.get("stages", [])),
        "stage_values": stage_values,
        "far_by_stage": rep["far_by_stage"],                 # 실측 FAR(참고)
        "transitions": rep["transitions"],                    # 전이 hazard(주지표1)
        "post_intro_final_loss": rep["post_intro_final_loss"],# 누적(주지표2)
        "warning": warn,
    }
    if fact_clock:
        out["fact_clock"] = survival.fact_clock_report(judgment, facts_by_id=facts_by_id,
                                                       critical_only=critical_only)
    return out


def _print_report(r: dict) -> None:
    """실측 FAR 곡선과 조건부 지표 2종을 나란히 stdout 에 출력."""
    print("=" * 66)
    print(f"[ucurve] {r['judgment_path']}")
    print(f"         issue={r['issue_id']} run={r['run_id']} "
          f"stage_type={r['stage_type']} scope={r['scope']}")
    print(f"         stage {r['n_stages']}개: {r['stage_values']}")
    if r.get("warning"):
        print(f"  (!) {r['warning']}")

    print("\n  [참고] 실측 FAR 곡선 (도입 타이밍 오염 포함):")
    for f in r["far_by_stage"]:
        print(f"    stage {f['stage']}: FAR={f['far']}")

    print("\n  [주지표1] 전이 hazard (조건부 소실률 — 도입 전 팩트 배제):")
    if not r["transitions"]:
        print("    (전이 없음 — stage 0/1개)")
    for i, t in enumerate(r["transitions"]):
        label = "T_early" if i == 0 else ("T_late" if i == len(r["transitions"]) - 1 else f"T{i}")
        print(f"    {label} stage {t['from_stage']}→{t['to_stage']}: "
              f"hazard={t['cond_attrition']} "
              f"(모수 {t['surviving_denom']} · 소실 {t['lost']}) "
              f"내역 {t['lost_by_status']}")

    p = r["post_intro_final_loss"]
    print("\n  [주지표2] 누적 (도입 후 최종생존):")
    print(f"    rate={p['rate']} (모수 {p['denom']} · 소실 {p['lost']})")

    # U자 진단 힌트(정성): 실측 FAR 우측 팔 vs 마지막 전이 hazard.
    fars = [f["far"] for f in r["far_by_stage"] if f["far"] is not None]
    if len(fars) >= 3:
        right_arm_rise = fars[-1] - min(fars)
        last_haz = r["transitions"][-1]["cond_attrition"] if r["transitions"] else None
        print(f"\n  [진단 힌트] 실측 FAR 우측 상승폭≈{round(right_arm_rise, 4)} · "
              f"T_late hazard={last_haz} "
              f"→ 판별은 UCURVE_PREREG.md 표에 대조(이 스크립트는 판정하지 않음)")

    if r.get("fact_clock"):
        _print_fact_clock(r["fact_clock"])
    print()


def _print_fact_clock(fc_report: dict) -> None:
    """도입 시점 정렬 생존분석(fact-clock) — w=0·w=1 생명표를 나란히 stdout 에."""
    print("\n  [fact-clock] 도입 시점 정렬 생존분석 (기준: FACTCLOCK_PREREG.md)")
    for w in sorted(fc_report["by_w"]):
        fc = fc_report["by_w"][w]
        pop = fc["population"]
        print(f"    · w={w}  도입 {pop['n_introduced']}개 · 미도입 {pop['n_never_introduced']}개 "
              f"· 사망 {fc['n_deaths_total']} · 검열 {fc['n_censored_total']}")
        for row in fc["life_table"]:
            if row["age"] == 0:
                continue  # age0 은 도입 기준(사망 없음)
            print(f"        age {row['age']}: hazard={row['hazard']} "
                  f"(at-risk {row['at_risk']} · 사망 {row['deaths']} · 검열 {row['censored']})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="U자 곡선 재해석 러너 — 실측 FAR vs 조건부 지표(survival.report 위임)")
    ap.add_argument("judgments", nargs="+", type=Path, help="judgment JSON 경로(1개 이상)")
    ap.add_argument("--out", type=Path, default=None,
                    help="결과 json 저장 경로(생략 시 각 입력 옆 <stem>.ucurve.json)")
    ap.add_argument("--critical-only", action="store_true",
                    help="critical 팩트만 집계(facts 파일 필요)")
    ap.add_argument("--fact-clock", action="store_true",
                    help="도입 시점 정렬 생존분석(fact-clock, w=0·w=1)을 추가 출력")
    args = ap.parse_args(argv)

    results = []
    for jp in args.judgments:
        if not jp.exists():
            print(f"[ucurve] (!) 파일 없음 — 건너뜀: {jp}", file=sys.stderr)
            continue
        r = analyze_one(jp, critical_only=args.critical_only, fact_clock=args.fact_clock)
        _print_report(r)
        results.append(r)

    if not results:
        print("[ucurve] 분석된 judgment 없음.", file=sys.stderr)
        return 1

    payload = {"protocol": "docs/analysis/UCURVE_PREREG.md", "results": results}
    if args.out:
        out_path = args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ucurve] 결과 저장: {out_path}")
    else:
        for r in results:
            jp = Path(r["judgment_path"])
            op = jp.with_suffix(".ucurve.json")
            op.write_text(json.dumps({"protocol": payload["protocol"], "results": [r]},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[ucurve] 결과 저장: {op}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
