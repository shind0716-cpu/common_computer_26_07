"""[측정 계약] 사슬형 결정 평가기 — 명세의 decision_contract 를 읽어 계산한다 (LLM 0콜).

## 요건형과 무엇이 다른가

throne 은 후보마다 조건 넷을 논리곱으로 본다(`requirement_eval`). award 는 그 모양이
아니다 — 후보 셋 중 하나가 **부문 적격·신고 일치·경쟁작 결격·공식 세 항목 우위**라는
서로 다른 성분(component)을 모두 갖출 때만 뽑힌다. 조건 개수를 세는 게 아니라 사슬이
이어지는가를 본다.

두 모양을 한 함수에 욱여넣지 않고, 명세의 `decision_contract` 가 어느 쪽인지 선언하게 했다.

## 왜 모듈로 올렸는가

원래 `normative_award_evaluator_v2` 는 `시나리오/build_issue_award_v2.py` 안에 있었다.
빌드 스크립트는 생성 부작용이 있고 후보 지위이며, 분석 시점에 코드가 조용히 바뀌면 과거
결과의 재현이 깨진다. **분석기가 빌드를 import 하면 안 된다.** 그래서 로직은 여기로 옮기고
값(성분 정의·선택 규칙)은 명세 파일에서 읽는다.

## 입력을 바꿨다 — 이게 핵심이다

옮기기 전 서명은 `normative_award_evaluator_v2(known_fact_ids: set[str])` 였다. 「아는 팩트
집합」을 받으므로 **lexical 적중을 그대로 부어 넣어도 막히지 않는다.** throne 평가기는 그
경로를 막아 뒀는데 award 는 안 막혀 있었다.

여기서는 `judgments: fact_id -> preservation_status` 를 받고 `validate_judgments` 로 거른다.
불리언이나 미등록 문자열이면 죽는다.

## 부재를 반증으로 바꾸지 않는다

현재 award v2 재료에는 각 성분을 **반증하는** 팩트가 없다. 그러므로 필요한 팩트가 덜
모인 상태는 `false` 가 아니라 `unknown` 이다. 근거가 `blocked` 면 `blocked` 로 따로 남긴다 —
정본 모호로 못 재는 것과 아직 안 나온 것은 다르다.

표면 정보(다운로드 1위·평점 등)는 `surface_fact_ids` 로 선언되며 **어떤 성분에도 기여하지
않는다.** 명세가 그 약속을 어기면 로드 시점에 죽는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from modules.detection_spec import EVIDENTIAL_STATUSES, SpecError, validate_judgments

TRUE = "true"
FALSE = "false"
UNKNOWN = "unknown"
BLOCKED = "blocked"


@dataclass
class ChainResult:
    components: dict = field(default_factory=dict)      # 성분 이름 -> 상태
    evidence: dict = field(default_factory=dict)        # 성분 이름 -> [fact_id]
    decision_state: str = UNKNOWN
    winner: str | None = None
    reason: str = ""
    surface_fact_ids: list = field(default_factory=list)


def _contract(spec) -> dict:
    c = spec.decision_contract
    if not c:
        raise SpecError(f"{spec.issue_id}: 명세에 decision_contract 가 없다 — 사슬 평가 불가")
    for k in ("components", "selection_rule", "selected_winner", "incomplete_state"):
        if k not in c:
            raise SpecError(f"{spec.issue_id}: decision_contract 에 {k} 가 없다")
    if c["selection_rule"] != "all_components_true":
        raise SpecError(
            f"{spec.issue_id}: 모르는 selection_rule {c['selection_rule']!r} — "
            f"규칙을 추측해 승자를 만들지 않는다")
    if c["selected_winner"] not in spec.candidates:
        raise SpecError(
            f"{spec.issue_id}: selected_winner {c['selected_winner']!r} 가 후보 목록에 없다")

    surface = set(c.get("surface_fact_ids", []))
    used = {f for facts in c["components"].values() for f in facts}
    unknown = (used | surface) - set(spec.facts)
    if unknown:
        raise SpecError(f"{spec.issue_id}: 명세에 없는 fact_id 가 계약에 있다 {sorted(unknown)}")
    bleed = surface & used
    if bleed:
        raise SpecError(
            f"{spec.issue_id}: 표면 정보가 성분 근거로 쓰였다 {sorted(bleed)} — "
            f"인상과 규범 사슬을 섞지 않는다")
    if not c["components"]:
        raise SpecError(f"{spec.issue_id}: 성분이 하나도 없다")
    return c


def evaluate(spec, judgments: dict) -> ChainResult:
    """의미 판정으로 성분 상태와 최종 선택을 계산한다.

    judgments: fact_id -> preservation_status. 명세의 전 팩트에 값이 있어야 한다.
    """
    c = _contract(spec)
    validate_judgments(spec, judgments)

    res = ChainResult(surface_fact_ids=list(c.get("surface_fact_ids", [])))
    for name, facts in c["components"].items():
        res.evidence[name] = list(facts)
        if any(judgments[f] == BLOCKED for f in facts):
            res.components[name] = BLOCKED
        elif all(judgments[f] in EVIDENTIAL_STATUSES for f in facts):
            res.components[name] = TRUE
        else:
            # 반증 팩트가 없는 재료다 — 덜 모인 것을 false 로 내리지 않는다.
            res.components[name] = UNKNOWN

    states = set(res.components.values())
    if states == {TRUE}:
        res.decision_state = "selected"
        res.winner = c["selected_winner"]
        res.reason = f"성분 {len(res.components)}개가 모두 성립해 {res.winner} 가 선택된다"
    else:
        res.decision_state = c["incomplete_state"]
        res.winner = None
        weak = sorted(n for n, s in res.components.items() if s != TRUE)
        res.reason = (f"성분 {len(weak)}개가 미확정({', '.join(weak)}) — "
                      f"부재를 다른 후보의 우위로 바꾸지 않는다")
    return res
