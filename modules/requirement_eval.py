"""[측정 계약] 요건·결정 평가기 — 후보가 조건을 충족하는가 (LLM 0콜).

## 세 층을 섞지 않는다

    fact detector          명제가 보존됐는가          ← 이 모듈 밖(사람·독립 판정)
    requirement evaluator  후보가 조건 i 를 충족하는가  ← 여기
    decision evaluator     네 조건을 전부 충족한 후보    ← 여기

**fact detector 가 승자를 직접 만들지 않는다.** 그래서 이 모듈은 판정 상태를 인자로 받는다.
문자열 적중을 넣어 승자를 뽑는 경로가 생기면 안 되므로, 판정값이 닫힌 어휘가 아니면 죽는다.

## 모르면 모른다고 한다

근거 팩트가 `blocked`·`absent`·`contradicted`·`partial` 이면 그 조건은 `undetermined` 다.
`unsatisfied` 로 내리지 않는다 — 둘은 다르다. 「조건을 못 채웠다」와 「채웠는지 알 수 없다」를
같은 칸에 넣으면 판정 불가가 0점으로 위장된다(브리프 §5E).

조건 하나라도 undetermined 면 적격 여부는 `None` 이고 승자도 없다.

## 정본 의존

조건별 근거와 충족 여부는 **명세의 `requirements`** 에서 읽는다. 이 모듈은 계승법을 모른다.
`issue_throne_v2` 의 정본은 네 조건 결합 요건이며 아르넬 4/4 · 베스카 1/4 다
(THRONE_CANONICAL_DECISIONS.md, 요한 승인 2026-08-20 A/A/A).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.detection_spec import EVIDENTIAL_STATUSES, SpecError, validate_judgments

SATISFIED = "satisfied"
UNSATISFIED = "unsatisfied"
UNDETERMINED = "undetermined"


@dataclass
class CandidateResult:
    name: str
    requirements: dict = field(default_factory=dict)   # 조건번호 -> 상태
    evidence: dict = field(default_factory=dict)       # 조건번호 -> [fact_id]
    eligible: bool | None = None                       # None = 판정 불가


@dataclass
class DecisionResult:
    candidates: dict
    winner: str | None
    reason: str


def evaluate(spec, judgments: dict) -> DecisionResult:
    """판정 상태를 받아 조건 충족과 최종 적격을 계산한다.

    judgments: fact_id -> preservation_status (닫힌 어휘).
    명세의 전 팩트에 대해 값이 있어야 한다 — 빠지면 죽는다. 빈칸을 absent 로 채우면
    「말 안 했다」와 「판정 안 했다」가 섞인다.
    """
    if not spec.requirements:
        raise SpecError(f"{spec.issue_id}: 명세에 requirements 가 없다 — 결정 평가를 못 한다")

    _check_judgments(spec, judgments)

    results = {}
    for cand in spec.candidates:
        cr = CandidateResult(name=cand)
        for req_no, table in sorted(spec.requirements.items(), key=lambda kv: int(kv[0])):
            entry = table.get(cand)
            if entry is None:
                raise SpecError(f"{spec.issue_id}: 조건 {req_no} 에 후보 {cand} 항목이 없다")
            ev = list(entry["evidence"])
            unknown = [f for f in ev if f not in spec.facts]
            if unknown:
                raise SpecError(f"조건 {req_no}/{cand}: 명세에 없는 근거 fact_id {unknown}")
            cr.evidence[int(req_no)] = ev
            weak = [f for f in ev if judgments[f] not in EVIDENTIAL_STATUSES]
            if weak:
                cr.requirements[int(req_no)] = UNDETERMINED
            else:
                cr.requirements[int(req_no)] = SATISFIED if entry["satisfied"] else UNSATISFIED
        states = set(cr.requirements.values())
        if UNDETERMINED in states:
            cr.eligible = None
        else:
            cr.eligible = states == {SATISFIED}
        results[cand] = cr

    eligible = [c for c, r in results.items() if r.eligible is True]
    undet = [c for c, r in results.items() if r.eligible is None]
    if undet:
        winner, reason = None, (
            f"판정 불가 — 후보 {', '.join(undet)} 의 조건 일부가 undetermined 다. "
            f"근거 팩트가 보존되지 않아 적격을 계산할 수 없다.")
    elif len(eligible) == 1:
        winner, reason = eligible[0], f"{eligible[0]} 만 네 조건을 전부 충족한다"
    elif not eligible:
        winner, reason = None, "네 조건을 전부 충족한 후보가 없다"
    else:
        winner, reason = None, f"적격 후보가 둘 이상이다: {', '.join(eligible)}"
    return DecisionResult(candidates=results, winner=winner, reason=reason)


def _check_judgments(spec, judgments) -> None:
    """판정 사전 검증은 detection_spec 이 한 벌로 갖는다 — 사슬형 평가기와 같은 규칙을 쓴다."""
    validate_judgments(spec, judgments)
