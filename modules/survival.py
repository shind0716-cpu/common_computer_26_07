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
# 팩트 기준 시계 (fact-clock) — 도입 시점 정렬 생존분석 (전역 시계의 보완)
#   설계·해석 기준 사전 고정: docs/analysis/FACTCLOCK_PREREG.md
#   기존 P2 함수·시그니처는 불변. 아래는 순수 추가분(API 0 · 파일 안 씀).
#   위 conditional_attrition 은 전역 stage 축을 모든 팩트가 공유하지만, 여기서는 각 팩트의
#   '도입(첫 SURVIVING) stage'를 age 0 으로 정렬해 도입 후 경과 나이별 hazard 를 잰다.
#   채점(judgment) 재사용 → 추가 채점 비용 0. 잣대·입력 계약은 P2 와 동일(SURVIVING·fact_id·status).
# ---------------------------------------------------------------------------
def _as_judgment_list(judgments: dict | list) -> list[dict]:
    """단일 judgment dict 또는 그 리스트를 리스트로 정규화(플루럴 시그니처 지원)."""
    if isinstance(judgments, dict):
        return [judgments]
    return list(judgments)


def _surv_flags(
    judgment: dict,
    facts_by_id: dict[str, dict] | None,
    *,
    critical_only: bool,
) -> tuple[dict[str, list[bool]], list[str]]:
    """judgment 를 도입 정렬용 팩트별 생존 불리언 열로 변환.

    반환 (introduced, never):
      introduced: fact_id -> surv_flags[0..M] (age 0 = 첫 SURVIVING, surv_flags[0]=True).
      never:      한 번도 SURVIVING 이 아니었던 fact_id 목록(미도입 — 모집단 제외).
    stage 는 정렬된 위치 인덱스로만 쓴다(절대값 무관). _sorted_stages·_status_map 재사용.
    """
    stages = _sorted_stages(judgment)
    maps = [_status_map(st) for st in stages]
    all_ids: list[str] = []
    seen: set[str] = set()
    for m in maps:
        for fid in m:
            if fid not in seen:
                seen.add(fid)
                all_ids.append(fid)

    introduced: dict[str, list[bool]] = {}
    never: list[str] = []
    for fid in all_ids:
        if critical_only and not _is_critical(fid, facts_by_id):
            continue
        flags_global = [m.get(fid) in SURVIVING for m in maps]
        intro = next((i for i, b in enumerate(flags_global) if b), None)
        if intro is None:
            never.append(fid)
            continue
        introduced[fid] = flags_global[intro:]  # age 0..M
    return introduced, never


def _fact_event(surv_flags: list[bool], w: int) -> tuple[str, int, str]:
    """도입 정렬된 생존 열 → 단일 사건 ('death'|'censored', age, reason). 순수.

    FACTCLOCK_PREREG.md §2 의사코드. surv_flags[0]=True(도입) 전제.
    reason:
      fatal_run        — 연속 비생존 런 길이 >= w+1 → 사망(age = 런 시작).
      terminal_silence — 런 < w+1 이 관측 경계에서 끝남 → 검열(직전 생존 age). **관측창 부족**
                         으로 재등장 확인 불가라 검열된 것이지 재등장 확인이 아니다(사후 명시,
                         FACTCLOCK_PREREG.md §7). w=1 사망 감소를 churn 으로만 읽지 않기 위함.
      survived_to_end  — 관측 끝까지 생존(중간 브릿지 재등장 포함) → 검열(age M).
    """
    M = len(surv_flags) - 1
    t = 1
    while t <= M:
        if not surv_flags[t]:
            run = 0
            while t + run <= M and not surv_flags[t + run]:
                run += 1
            if run >= w + 1:
                return "death", t, "fatal_run"
            if t + run - 1 == M:      # 런이 관측 경계에서 끝남 → 미확정 침묵
                return "censored", t - 1, "terminal_silence"
            t = t + run               # 브릿지(관용, w>=1): 재등장 지점부터 계속
        else:
            t += 1
    return "censored", M, "survived_to_end"


def fact_clock(
    judgments: dict | list,
    w: int = 0,
    *,
    facts_by_id: dict[str, dict] | None = None,
    critical_only: bool = False,
) -> dict:
    """도입 시점 정렬 생존분석(허용폭 w) — age 별 생명표.

    judgments: 단일 judgment dict 또는 리스트(여러 run 을 age 별로 pool).
    각 (judgment, fact) 를 도입 정렬해 _fact_event 로 사건 산출 후 age 별 합산.
    우측 검열(설계 원칙 1): at_risk(t) = event_age >= t 인 팩트 수 → 관측창 < t 인 팩트는
    분모에서 자동 제외. 미도입 팩트는 모집단에서 빼고 카운트만 보고.
    반환: {w, population, max_age, life_table[], survival[](KM), n_deaths_total, n_censored_total}.
    순수 계산 — API 0 · 파일 안 씀.
    """
    js = _as_judgment_list(judgments)
    deaths_at: dict[int, int] = {}
    censored_at: dict[int, int] = {}
    censored_reason: dict[str, int] = {"survived_to_end": 0, "terminal_silence": 0}
    event_ages: list[int] = []
    n_introduced = 0
    never_list: list[dict] = []
    max_m = 0

    for j in js:
        introduced, never = _surv_flags(j, facts_by_id, critical_only=critical_only)
        run_id = j.get("run_id")
        for fid in never:
            never_list.append({"run_id": run_id, "fact_id": fid})
        for fid, flags in introduced.items():
            n_introduced += 1
            max_m = max(max_m, len(flags) - 1)
            kind, age, reason = _fact_event(flags, w)
            event_ages.append(age)
            if kind == "death":
                deaths_at[age] = deaths_at.get(age, 0) + 1
            else:
                censored_at[age] = censored_at.get(age, 0) + 1
                censored_reason[reason] = censored_reason.get(reason, 0) + 1

    life_table: list[dict] = []
    survival: list[dict] = []
    surv_prob = 1.0
    for t in range(0, max_m + 1):
        at_risk = sum(1 for e in event_ages if e >= t)
        d = deaths_at.get(t, 0)
        c = censored_at.get(t, 0)
        if t == 0:
            haz = 0.0 if at_risk else None       # 도입 정의상 age 0 사망 없음
        else:
            haz = round(d / at_risk, 4) if at_risk else None
            if haz is not None:
                surv_prob *= (1 - haz)
        life_table.append({"age": t, "at_risk": at_risk, "deaths": d,
                           "censored": c, "hazard": haz})
        survival.append({"age": t, "S": round(surv_prob, 4)})

    return {
        "w": w,
        "population": {
            "n_introduced": n_introduced,
            "n_never_introduced": len(never_list),
            "never_introduced": never_list,
        },
        "max_age": max_m,
        "life_table": life_table,
        "survival": survival,
        "n_deaths_total": sum(deaths_at.values()),
        "n_censored_total": sum(censored_at.values()),
        # 검열 사유 분해: survived_to_end(진짜 생존) vs terminal_silence(관측창 부족).
        "censored_breakdown": censored_reason,
    }


def w_divergence(
    judgments: dict | list,
    *,
    facts_by_id: dict[str, dict] | None = None,
    critical_only: bool = False,
    w_low: int = 0,
    w_high: int = 1,
) -> dict:
    """w_low 에서 사망한 팩트가 w_high 에서 어떻게 갈리는지 분해(FACTCLOCK_PREREG.md §7).

    "w=1 에서 사망이 사라졌다"를 churn 으로만 읽으면 위험하다 — 종말부 침묵(관측창 부족)이
    섞여 있기 때문. w_low(기본 0) 사망 팩트를 w_high(기본 1) 판정으로 재분류:
      death_robust            — w_high 에서도 사망(관용폭 무관, 실재 손실).
      churn_reappearance      — w_high 에서 생존(survived_to_end) = 실제 재등장으로 사망 취소.
      artifact_terminal_silence — w_high 에서 종말부 침묵 검열 = **관측창 부족 아티팩트**(재등장
                                  확인 기회가 없어서 검열, churn 아님).
    반환 {w_low, w_high, counts, detail[]}. 순수 계산.
    """
    js = _as_judgment_list(judgments)
    counts = {"death_robust": 0, "churn_reappearance": 0, "artifact_terminal_silence": 0}
    detail: list[dict] = []
    for j in js:
        introduced, _ = _surv_flags(j, facts_by_id, critical_only=critical_only)
        for fid, flags in introduced.items():
            k0, _a0, _r0 = _fact_event(flags, w_low)
            if k0 != "death":
                continue
            k1, _a1, r1 = _fact_event(flags, w_high)
            if k1 == "death":
                cls = "death_robust"
            elif r1 == "terminal_silence":
                cls = "artifact_terminal_silence"
            else:
                cls = "churn_reappearance"
            counts[cls] += 1
            detail.append({"run_id": j.get("run_id"), "fact_id": fid, "class": cls})
    return {"w_low": w_low, "w_high": w_high, "counts": counts, "detail": detail}


def _judgment_sha256(judgment: dict) -> str:
    """감사 필드용 — judgment 의 canonical json 해시(기존 P2 러너 감사 방식 계승)."""
    import hashlib  # 지연 import(상단 import 블록 무수정)

    blob = json.dumps(judgment, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def fact_clock_report(
    judgments: dict | list,
    *,
    facts_by_id: dict[str, dict] | None = None,
    critical_only: bool = False,
    ws: tuple[int, ...] = (0, 1),
) -> dict:
    """w=0·w=1 병렬 fact-clock + 감사 필드. 두 값을 항상 나란히(설계 원칙 2)."""
    js = _as_judgment_list(judgments)
    inputs = [{
        "issue_id": j.get("issue_id"),
        "run_id": j.get("run_id"),
        "sha256": _judgment_sha256(j),
        "n_stages": len(j.get("stages", [])),
        "stage_values": [s.get("stage") for s in _sorted_stages(j)],
    } for j in js]
    report = {
        "protocol": "docs/analysis/FACTCLOCK_PREREG.md",
        "surviving_set": sorted(SURVIVING),
        "audit": {"n_judgments": len(js), "inputs": inputs},
        "by_w": {w: fact_clock(js, w, facts_by_id=facts_by_id, critical_only=critical_only)
                 for w in ws},
    }
    # w=0·w=1 을 모두 산출하면 사망 감소의 기전(churn vs 관측창 부족)을 분해해 병기.
    if 0 in ws and 1 in ws:
        report["w_divergence"] = w_divergence(
            js, facts_by_id=facts_by_id, critical_only=critical_only, w_low=0, w_high=1)
    return report


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
