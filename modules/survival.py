"""[조건부 소실률] 관찰 트랙 순환 함정 보정 지표 (주지표 P2).

배경: FAR(judge.far)은 status ∉ SURVIVING 을 소실로 센다. 그런데
SURVIVING={mentioned, accepted} 이므로 '아직 등장 전(unmentioned)' 팩트까지 소실로
집계된다. 팩트가 사후(post-hoc) claim 이라, 초반엔 미등장 팩트가 소실로 잡혀 FAR 이
부풀고 중반 도입→후반 이탈로 U자 곡선(0.42→0.17→0.25)이 관측됐다 — 순환 함정.

이 모듈은 '이미 등장(생존)한 팩트가 다음 단계에서 사라지는 비율'만 재어 도입 시점과
소실을 분리한다. SCHEMA·judge 를 바꾸지 않고 잣대(judge.SURVIVING)를 그대로 재사용하며,
참고용으로 전체 FAR(judge.far)을 병기한다. 순수 함수만 제공(API 호출 0, 파일 안 씀).

판정 잣대의 단일 소스: '소실' 정의는 judge.SURVIVING 을 그대로 쓴다(ledger 와 동일 계약).
judgment 구조 의존 최소화: stages[].facts[].{fact_id, status} 두 필드만 읽는다.

두 관점:
  1) 전이 hazard  conditional_attrition — 각 k→k+1 에서 'k 생존자 중 k+1 에 이탈' 비율.
  2) 누적 최종생존 post_intro_final_loss — '한번이라도 도입된 팩트가 끝까지 살아남았나'.
경계(결정 2): k+1(또는 마지막 stage)에서 SURVIVING 으로 재확인된 것만 생존 유지.
             레코드 자체가 없으면 소실로 집계(judge 의 보수적 관례와 일치).

사용(단독):
  python -m modules.survival --issue issue_esa --run dryrun [--critical-only]
    → 전이별 조건부 소실률 + 누적 지표 + 참고 FAR 을 콘솔에 출력(파일 안 씀, 점검용).
"""
from __future__ import annotations

import argparse
import json

from . import paths, ledger
from .judge import SURVIVING, far


# ---------------------------------------------------------------------------
# 핵심 순수 함수 (모두 API 호출 0 · 파일 쓰기 없음)
# ---------------------------------------------------------------------------
def _sorted_stages(judgment: dict) -> list[dict]:
    """stage 값 오름차순으로 정렬한 stage 레코드 목록."""
    return sorted(judgment.get("stages", []), key=lambda s: s.get("stage"))


def _status_map(stage_record: dict) -> dict[str, str]:
    """stage 레코드에서 {fact_id: status}. fact_id·status 두 필드만 읽는다."""
    return {f["fact_id"]: f.get("status") for f in stage_record.get("facts", [])}


def _is_critical(fid: str, facts_by_id: dict[str, dict] | None) -> bool:
    return bool((facts_by_id or {}).get(fid, {}).get("critical"))


def conditional_attrition(
    judgment: dict,
    facts_by_id: dict[str, dict] | None = None,
    *,
    critical_only: bool = False,
) -> list[dict]:
    """stage 전이별(k→k+1) 조건부 소실률(hazard).

    모수 = stage k 에서 status ∈ SURVIVING 인 팩트. 소실 = 그 중 stage k+1 에서
    status ∉ SURVIVING(레코드 부재 포함 — 결정 2). '아직 등장 전(unmentioned)'은
    모수에서 자동 배제되어 순환 함정을 해소한다.

    각 전이 원소:
      from_stage, to_stage, surviving_denom, lost, cond_attrition(모수 0이면 None),
      lost_fact_ids(감사), lost_by_status(감사: unmentioned/refuted/ignored/absent 분해).
    stage 가 0/1개면 전이가 없어 [] 를 반환한다.
    critical_only=True 면 facts_by_id 로 critical 팩트만 모수에 넣는다.
    """
    stages = _sorted_stages(judgment)
    rows: list[dict] = []
    for a, b in zip(stages, stages[1:]):
        map_k = _status_map(a)
        map_k1 = _status_map(b)
        denom_ids = [
            fid for fid, s in map_k.items()
            if s in SURVIVING and (not critical_only or _is_critical(fid, facts_by_id))
        ]
        lost_ids = [fid for fid in denom_ids if map_k1.get(fid) not in SURVIVING]

        # 감사용 소실 내역 분해: k+1 레코드 부재는 'absent', 그 외는 status 값별로.
        by_status = {"unmentioned": 0, "refuted": 0, "ignored": 0, "absent": 0}
        for fid in lost_ids:
            key = "absent" if fid not in map_k1 else map_k1.get(fid)
            by_status[key] = by_status.get(key, 0) + 1

        rate = round(len(lost_ids) / len(denom_ids), 4) if denom_ids else None
        rows.append({
            "from_stage": a.get("stage"),
            "to_stage": b.get("stage"),
            "surviving_denom": len(denom_ids),
            "lost": len(lost_ids),
            "cond_attrition": rate,
            "lost_fact_ids": lost_ids,
            "lost_by_status": by_status,
        })
    return rows


def post_intro_final_loss(
    judgment: dict,
    facts_by_id: dict[str, dict] | None = None,
    *,
    critical_only: bool = False,
) -> dict:
    """누적 지표 — 도입된 팩트가 마지막 stage 까지 살아남는가.

    모수 = 마지막 stage '이전' 어느 stage 에서든 한 번이라도 status ∈ SURVIVING 이었던
    팩트. 소실 = 그 모수 중 마지막 stage 에서 status ∉ SURVIVING(레코드 부재 포함 — 결정 2).
    반환 {denom, lost, rate(모수 0이면 None)}. stage 0/1개면 '이전 stage' 없어 denom=0.
    critical_only=True 면 critical 팩트만 모수에 넣는다.
    """
    stages = _sorted_stages(judgment)
    if len(stages) < 2:
        return {"denom": 0, "lost": 0, "rate": None}

    *prior, last = stages
    introduced: set[str] = set()
    for st in prior:
        for fid, status in _status_map(st).items():
            if status in SURVIVING and (not critical_only or _is_critical(fid, facts_by_id)):
                introduced.add(fid)

    last_map = _status_map(last)
    lost = sum(1 for fid in introduced if last_map.get(fid) not in SURVIVING)
    denom = len(introduced)
    rate = round(lost / denom, 4) if denom else None
    return {"denom": denom, "lost": lost, "rate": rate}


def far_by_stage(
    judgment: dict,
    facts_by_id: dict[str, dict],
    *,
    critical_only: bool = False,
) -> list[dict]:
    """참고용 전체 FAR 병기. 각 stage 에 judge.far 를 그대로 위임(재구현 금지)."""
    return [
        {"stage": st.get("stage"),
         "far": far(st.get("facts", []), facts_by_id, critical_only=critical_only)}
        for st in _sorted_stages(judgment)
    ]


def report(
    judgment: dict,
    facts_by_id: dict[str, dict],
    *,
    critical_only: bool = False,
) -> dict:
    """주지표(조건부·누적) + 참고지표(FAR)를 한 구조로."""
    return {
        "transitions": conditional_attrition(judgment, facts_by_id, critical_only=critical_only),
        "post_intro_final_loss": post_intro_final_loss(judgment, facts_by_id, critical_only=critical_only),
        "far_by_stage": far_by_stage(judgment, facts_by_id, critical_only=critical_only),
    }


# ---------------------------------------------------------------------------
# CLI (점검용 — 파일을 쓰지 않는다)
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="조건부 소실률(P2) — 전이 hazard·누적·참고 FAR 점검")
    ap.add_argument("--issue", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--critical-only", action="store_true", help="critical 팩트만 집계")
    args = ap.parse_args()

    judgment = ledger.load_judgment(args.issue, args.run)
    facts_by_id = ledger.load_facts_by_id(args.issue)
    rep = report(judgment, facts_by_id, critical_only=args.critical_only)

    scope = "critical" if args.critical_only else "system"
    print(f"[survival] issue={args.issue} run={args.run} scope={scope}")
    print("[survival] 전이별 조건부 소실률(hazard):")
    for t in rep["transitions"]:
        print(f"  stage {t['from_stage']}→{t['to_stage']}: "
              f"모수 {t['surviving_denom']} · 소실 {t['lost']} · "
              f"조건부={t['cond_attrition']} · 내역 {t['lost_by_status']}")
    p = rep["post_intro_final_loss"]
    print(f"[survival] 누적(도입 후 최종생존): 모수 {p['denom']} · 소실 {p['lost']} · rate={p['rate']}")
    print("[survival] 참고용 전체 FAR(단계별):")
    for f in rep["far_by_stage"]:
        print(f"  stage {f['stage']}: far={f['far']}")


if __name__ == "__main__":
    main()
