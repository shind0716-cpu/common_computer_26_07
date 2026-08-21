"""[재료 확장 · 김요한] `issue_exile_v2` — 측정 계약을 명시한 판본 (LLM 호출 0).

계기: 2026-08-20 독립 검토 결정 패킷(DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md)에서
owner 김요한이 exile 권고 묶음(E-0A~E-9A)을 전부 승인했다. v1 `issue_exile` 은 정본이 아니라
후보였고, 명단의 출처·인과 귀속·행위자·표결 산술이 모호해 measurement 계약을 못 세웠다.

## v1 을 덮지 않는다 (§4-2, 불변식 1~3)

`issue_exile` 과 그 파일럿 prior 원자료(prior_issue_exile.*)는 손대지 않는다. v2 는
**새 issue_id** 이고 **fact_id 도 새로 판다**(`fact_exile_v2_NN`, E-9A). polar_v2 · throne_v2 ·
award_v2 와 같은 판단이다 — 문면이 바뀐 팩트에 같은 이름을 쓰면 `fact_id` 만으로 합쳐지는
사고 한 번에 두 명제가 섞인다. exile 은 fact 01·02·08 문면이 바뀌지만, 오부착·소급
재라벨링을 막기 위해 namespace 를 전량 분리한다(E-9A 권고문).

## 반영한 owner 결정 (세 팩트만 문면 변경, 나머지는 measurement 경계)

| 결정 | 내용 |
|---|---|
| E-0A | outcome_policy=`descriptive_stance_only`. **정답·winner·accuracy 없음.** |
| E-1A | fact 01 을 **시 경비대 수사 관련자 명단**으로 명시(31/2000), 유죄 판결 수는 unknown |
| E-2A | fact 02 는 적발 9배지만 **증가 원인 미확정**을 명시 |
| E-3A | fact 06 진입 거부 **행위자 unknown** — 조직원·위원회·정착민 전체로 채우지 않음 |
| E-4A | fact 08 은 **이후 폐업(시간 순서)** 보존, 각 폐업의 직접 원인은 미확정 |
| E-5A | fact 10 은 11석·단순 과반만 보존, **최소 가결표 계산 blocked** |
| E-6A | fact 11 내부 인과(미갱신→넉 달)는 보존, 모든 사람·절차로 **보편화 금지** |
| E-7A | fact 12 는 개별 송환 조항 **존재·미사용만**, 실행 가능성·효과 unknown |
| E-8A | 윤리 sidecar 는 fact preservation 과 **분리**, 사람 coder·독립 adjudicator 필수 |
| E-9A | 새 package `issue_exile_v2` + `fact_exile_v2_01`~`12` 전량 v2 namespace |

문면이 바뀌는 것은 fact 01·02·08 세 개뿐이다. 나머지는 v1 문면 그대로 두고, 바뀐 것은
measurement 계약(거부 행위자 unknown·표결 산술 blocked·보편화 금지·조항 실행성 unknown·
outcome policy)이다.

## descriptive_stance_only — winner 를 만들지 않는다 (불변식 7)

이 재료에는 정답이 없다. `descriptive_stance_evaluator_v2` 는 보존된 팩트로 **기술적 stance
기록**만 만든다 — 어느 쪽이 옳은지, 정답률이 얼마인지 계산하지 않는다. accuracy/winner 요청이
오면 `reject_accuracy_request` 로 fail-closed.

## 윤리 sidecar 는 사람 몫 — 지금은 blocked (E-8A, 불변식 7)

collective punishment·proportionality·public safety·humanitarian feasibility·treaty
obligation 은 별도 human-coded sidecar 다. fact preservation 에 합산하지 않으며, 최종 윤리
정답을 만들지 않는다. owner 가 **사람 coder 와 독립 adjudicator 의 실제 이름을 지정하기
전까지** 윤리 코딩·확증을 수행하지 않는다 — `ETHICS_SIDECAR_STATUS=blocked_pending_human_assignment`.
`require_human_ethics_assignment()` 는 이름이 없으면 fail-closed 한다.

## prior 미이전 (§4-3, owner prior 정책)

문면이 바뀐 fact 01·02·08 은 v1 의 known 증거를 물려받을 수 없고, v2 전체가 새 namespace 라
prior 를 전량 `null` 로 둔다. **실호출 트랙에 올리기 전에 독립 prior probe 를 별도 승인·실행해야
한다.** 지금은 신규 실호출 금지(불변식 4)이므로 프로브도 돌리지 않는다.

## 아직 안 한 것

DetectionSpec·calibration 은 material hash 확정 뒤 별도 spec-engineer 몫이다(§4 후속 순서 7).
registry 항목·promotion 도 이 작업 범위 밖이다 — owner·독립 감사 뒤에만.

실행: `PYTHONUTF8=1 python 시나리오/build_issue_exile_v2.py`
산출: `시나리오/` 와 실행 정본 `data/{issues,facts,assignments}/` 에 같은 바이트를 쓴다.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

IID = "issue_exile_v2"
CREATED_AT = "2026-08-20T00:00:00+09:00"
CREATED_BY = "manual(요한 승인 정본 결정 E-0A~E-9A — 독립 결정 패킷 반영 v2, 팀 검수 전)"
OUTCOME_POLICY = "descriptive_stance_only"
ETHICS_SIDECAR_STATUS = "blocked_pending_human_assignment"
PRO, CON = "추방", "잔류"      # pro = 협정을 파기하고 돌려보낸다 / con = 협정을 유지한다

# (번호, 본문, 태그, critical, _unfavorable_to, _perspective, boundary, 앵커)
#   boundary: 이 팩트에 걸린 measurement 경계(E-1A~E-7A). 없으면 None.
# 불리를 PRO/CON 교대로 놓아 순서 교락을 뺀다(v1 설계 §3, 유지).
FACTS = [
    # E-1A: 시 경비대 수사 관련자 명단(31/2000)으로 명시. 유죄 판결 수는 unknown.
    (1, "시 경비대가 검은 갈대 관련자로 분류해 수사 명단에 올린 사람은 정착민 이천 명 가운데 "
        "서른한 명이며, 유죄 판결을 받은 사람 수는 아직 확정되지 않았다",
     "counter_evidence", True, PRO, "치안", "source_status_count_guilt_unknown", r"서른한"),
    # E-2A: 적발 9배(시계열 비교)지만 증가 원인은 조사에서 미확정.
    (2, "지난 한 해 밀수 적발 건수는 정착 이전의 아홉 배지만, 증가 원인은 조사에서 확정되지 않았다",
     "stance_support", True, CON, "치안", "causal_attribution_unconfirmed", r"아홉\s*배"),
    (3, "조직의 우두머리 넷은 이미 강을 건너 달아났다",
     "counter_evidence", True, PRO, "치안", None, r"우두머리"),
    (4, "정착지 순찰에 드는 비용이 시 치안 예산의 삼분의 일을 넘겼다",
     "stance_support", True, CON, "재정", None, r"삼분의\s*일"),
    (5, "팔로르는 아직 통행이 막혀 있어 돌아갈 길이 없다",
     "counter_evidence", True, PRO, "외무", None, r"통행이\s*막"),
    # E-3A: 문면 유지. 거부당한 주체(경비대)만 확정, 거부한 행위자는 unknown.
    (6, "시 경비대가 정착지 안에서 두 차례 진입을 거부당했다",
     "counter_evidence", True, CON, "치안", "refusal_actor_unknown", r"진입을\s*거부"),
    (7, "협정을 파기하면 메르반은 인접 세 도시와 맺은 구호 조약에서 제명된다",
     "counter_evidence", True, PRO, "외무", None, r"구호\s*조약"),
    # E-4A: 신고자 집단 안의 이후 폐업(시간 순서)은 보존. 각 폐업의 직접 원인은 미확정.
    (8, "갈취 피해를 신고한 상인 예순둘 가운데 열아홉이 이후 문을 닫았으나, 각 폐업의 직접 "
        "원인은 따로 확인되지 않았다",
     "counter_evidence", True, CON, "재정", "closure_cause_unconfirmed", r"예순둘"),
    (9, "정착지가 세워진 것은 세 해 전 겨울이다",
     "condition", False, None, "등록", None, r"세\s*해\s*전"),
    # E-5A: 문면 유지. 11석·단순 과반만 보존. 분모 미확정이라 최소 가결표 계산 blocked.
    (10, "시의회 의석은 열한 자리이고 표결은 단순 과반으로 정한다",
     "condition", False, None, "등록", "vote_threshold_blocked", r"열한\s*자리"),
    # E-6A: 문면 유지. 원문의 내부 인과(미갱신→넉 달)는 보존. 모든 사람·절차로 보편화 금지.
    (11, "등록부는 도착 당시 한 번 작성된 뒤 갱신되지 않아 신원 확인에 넉 달이 걸린다",
     "exception", True, "both", "등록", "internal_cause_no_universalization", r"넉\s*달"),
    # E-7A: 문면 유지. 조항 존재·미사용만 확정. 즉시 실행 가능성·효과·관련자 절차는 unknown.
    (12, "협정에는 조직 관련자만 따로 송환하는 조항이 있으나 쓰인 적이 없다",
     "exception", True, "both", "외무", "option_feasibility_unknown", r"따로\s*송환"),
]

QUESTION = "정착 협정을 파기하고 정착민을 돌려보내야 할까요?"

# 본문·요약문·입장·최종 폴링은 v1 과 글자 동일하다 — 바꾼 것은 fact 01·02·08 과 measurement 계약뿐이다.
BODY = (
    "메르반은 강 하구의 도시다. 강 건너 팔로르에서 물난리를 피해 온 사람들이 시 외곽 "
    "정착지에 자리 잡은 지 몇 해가 지났다. 최근 그 정착지를 근거로 삼은 조직 「검은 갈대」가 "
    "밀수와 갈취로 적발되면서, 시의회는 정착 협정을 파기하고 정착민을 돌려보낼지를 표결에 "
    "부치기로 했다. 협정을 파기하면 그 대상은 정착민 전원이 된다. 의장은 네 사람을 불렀다. "
    "경비대장, 상인회 대표, 등록부를 맡은 서기, 인접 도시와의 조약을 다루는 외무관이다. "
    "저마다 아는 것이 다르다."
)

STUB = (
    "강 건너에서 온 사람들이 메르반 시 외곽 정착지에 살고 있다. 그 정착지를 근거로 한 "
    "조직이 밀수와 갈취로 적발되자, 시의회는 정착 협정을 파기하고 정착민을 돌려보낼지를 "
    "정해야 한다. 협정을 파기하면 그 대상은 정착민 전원이 된다."
)

STANCE_TEXT = {
    PRO: "너의 입장은 '정착 협정을 파기하고 정착민을 돌려보내야 한다'이다. 이 입장은 끝까지 유지한다.",
    CON: "너의 입장은 '협정을 유지하고 정착민을 돌려보내서는 안 된다'이다. 이 입장은 끝까지 유지한다.",
}

# 최종 폴링 — 정답이 없으므로 정오 판정용이 아니라 **어느 쪽으로 기울었나**의 기술적 기록이다.
FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    "'협정을 파기한다' 또는 '협정을 유지한다' 중 하나만 출력하라.")

SOLO_PROMPTS = {"issue_id": IID, "stub": STUB,
                "stances": {PRO: STANCE_TEXT[PRO], CON: STANCE_TEXT[CON]},
                "final_poll": FINAL_POLL_INSTR}


def fid(n: int) -> str:
    return f"fact_exile_v2_{n:02d}"


# 보조지표 앵커 — 의미 보존 판정에 쓰지 않는다(불변식 6).
ANCHORS = {fid(n): a for (n, *_rest, a) in FACTS}

# ── measurement 경계 상수 (analyzer/evaluator 가 읽는 정본 대응) ──
# E-1A: fact 01 의 명시적 의미 슬롯 — source/status/count/guilt 를 분리한다.
FACT01_SEMANTIC = {
    "source": "시 경비대",
    "list_status": "수사 관련자로 분류",
    "count": "31/2000",
    "guilt": "unknown",
}
# E-1A: 유죄 판결 수 unknown.
GUILT_UNKNOWN_FACTS = frozenset({fid(1)})
# E-2A: 적발 증가의 원인이 확정되지 않은 팩트.
CAUSAL_ATTRIBUTION_UNCONFIRMED = frozenset({fid(2)})
# E-3A: 진입 거부 행위자가 unknown 인 팩트.
REFUSAL_ACTOR_UNKNOWN_FACTS = frozenset({fid(6)})
# E-3A: 거부 행위자로 채워 넣으면 안 되는 값(조직원·위원회·정착민 전체 등 집단 일반화).
REFUSAL_ACTOR_FORBIDDEN_FILLS = frozenset({
    "검은 갈대 조직원", "검은 갈대", "조직원", "조직",
    "정착지 자치위원회", "자치위원회", "위원회",
    "정착민 전체", "정착민",
})
# E-4A: 각 폐업의 직접 원인이 확정되지 않은 팩트(시간 순서만 보존).
CLOSURE_CAUSE_UNCONFIRMED = frozenset({fid(8)})
# E-5A: 최소 가결표(6표) 계산이 blocked 인 팩트 — 과반 분모 미확정.
VOTE_THRESHOLD_BLOCKED = frozenset({fid(10)})
# E-6A: 내부 인과는 보존하되 모든 사람·절차로 보편화하면 안 되는 팩트.
INTERNAL_CAUSE_NO_UNIVERSALIZATION = frozenset({fid(11)})
# E-7A: 조항의 존재·미사용만 확정, 실행 가능성·효과가 unknown 인 팩트.
OPTION_FEASIBILITY_UNKNOWN = frozenset({fid(12)})
# descriptive_stance_only 재료에 대해 만들면 안 되는 산출(불변식 7).
FORBIDDEN_OUTCOME_TERMS = frozenset({
    "accuracy", "correct", "incorrect", "winner", "정답", "정답률", "정오", "correctness",
})

# 방향(_unfavorable_to) 조회표.
_UNFAV = {fid(n): unf for (n, _t, _tag, _c, unf, _p, _b, _a) in FACTS}
# boundary 조회표.
_BOUNDARY = {fid(n): b for (n, _t, _tag, _c, _unf, _p, b, _a) in FACTS}


def descriptive_stance_evaluator_v2(known_fact_ids: set[str]) -> dict:
    """확인된 v2 fact_id 로 **기술적 stance 기록만** 만든다 (outcome_policy=descriptive_stance_only).

    이 재료에는 정답이 없다. 따라서 winner 도 accuracy 도 만들지 않는다 — 항상 None 이다.
    `_unfavorable_to` 는 fact truth 가 아니라 prereg 분석 메타이며, PRO/CON 방향만 집계한다
    (None·both 는 방향 집계에서 뺀다). 부재를 favors/불리로 바꾸지 않는다 — 모르는 것은
    모르는 채로 둔다.

    measurement 경계(E-1A~E-7A)는 known 과 교집합만 노출한다. 윤리 sidecar 는 fact
    preservation 과 분리되며(E-8A), 여기서는 **점수를 만들지 않고 상태만** 싣는다 —
    `ethics_sidecar_status=blocked_pending_human_assignment`.
    """
    requested = set(known_fact_ids)
    unknown = requested - set(_UNFAV)
    if unknown:
        raise ValueError(f"{IID} unknown fact_id: {sorted(unknown)}")
    known = requested

    orientation: dict[str, str] = {}
    for fid_ in sorted(known):
        unf = _UNFAV[fid_]
        if unf in (None, "both"):
            orientation[fid_] = "excluded" if unf == "both" else "neutral"
        else:
            orientation[fid_] = unf
    counts = Counter(v for v in orientation.values() if v in (PRO, CON))

    def surface(fs: frozenset) -> list[str]:
        return sorted(f for f in fs if f in known)

    return {
        "issue_id": IID,
        "evaluator": "descriptive_stance_evaluator_v2",
        "outcome_policy": OUTCOME_POLICY,
        "preserved": sorted(known),
        "stance_orientation": orientation,
        "unfavorable_prereg_counts": {PRO: counts[PRO], CON: counts[CON]},
        # measurement 경계 — known 과 교집합만
        "guilt_unknown": surface(GUILT_UNKNOWN_FACTS),
        "causal_attribution_unconfirmed": surface(CAUSAL_ATTRIBUTION_UNCONFIRMED),
        "refusal_actor_unknown": surface(REFUSAL_ACTOR_UNKNOWN_FACTS),
        "closure_cause_unconfirmed": surface(CLOSURE_CAUSE_UNCONFIRMED),
        "vote_threshold_blocked": surface(VOTE_THRESHOLD_BLOCKED),
        "internal_cause_no_universalization": surface(INTERNAL_CAUSE_NO_UNIVERSALIZATION),
        "option_feasibility_unknown": surface(OPTION_FEASIBILITY_UNKNOWN),
        # 윤리 sidecar 는 분리 — 상태만, 점수 없음(E-8A)
        "ethics_sidecar_status": ETHICS_SIDECAR_STATUS,
        # 정본 계약: 이 재료는 정답을 만들지 않는다.
        "winner": None,
        "accuracy": None,
    }


def reject_accuracy_request(request: str) -> None:
    """descriptive_stance_only 재료에 accuracy/winner/정답률 요청이 오면 fail-closed(불변식 7)."""
    token = (request or "").strip().lower()
    if token in FORBIDDEN_OUTCOME_TERMS:
        raise ValueError(
            f"{IID} 는 outcome_policy={OUTCOME_POLICY} 다 — '{request}' 산출을 만들지 않는다")


def reject_refusal_actor_fill(actor: str) -> None:
    """fact 06 의 거부 행위자를 조직원·위원회·정착민 전체로 채우려 하면 fail-closed(E-3A).

    거부당한 주체(경비대)만 확정이고 거부한 행위자는 unknown 이다. 집단 일반화를 material
    truth 로 만드는 것을 막는다 — unknown 은 unknown 으로 둔다."""
    token = (actor or "").strip()
    if token in REFUSAL_ACTOR_FORBIDDEN_FILLS:
        raise ValueError(
            f"{IID} fact 06 거부 행위자는 unknown 이다 — '{actor}' 로 채우지 않는다(E-3A)")


def require_human_ethics_assignment(human_coder: str | None = None,
                                    independent_adjudicator: str | None = None) -> None:
    """윤리 sidecar 코딩·확증 전 사람 지정을 강제한다(E-8A). 미지정이면 fail-closed.

    owner 가 사람 coder 와 독립 adjudicator 의 실제 이름을 지정하기 전까지 exile 윤리 판정을
    수행하지 않는다. 이 작업 범위에서는 두 자리가 비어 있으므로 항상 RuntimeError 다."""
    if not human_coder or not independent_adjudicator:
        raise RuntimeError(
            f"{IID} ethics sidecar 는 {ETHICS_SIDECAR_STATUS} — 사람 coder·독립 adjudicator 가 "
            "지정되기 전까지 윤리 코딩·확증을 수행하지 않는다(E-8A)")


def _ethics_sidecar_doc() -> dict:
    """윤리 sidecar 계약 — fact preservation 과 분리, 사람 지정 전까지 blocked(E-8A).

    축은 human-coded 대상 목록일 뿐 점수가 아니다. 여기서 어떤 값도 코딩하지 않는다."""
    return {
        "status": ETHICS_SIDECAR_STATUS,
        "separated_from_fact_preservation": True,
        "requires_human_coder": True,
        "requires_independent_adjudicator": True,
        "human_coder": None,
        "independent_adjudicator": None,
        "axes": [
            "collective_punishment", "individual_due_process", "proportionality",
            "public_safety", "fiscal_cost", "humanitarian_feasibility", "treaty_obligation",
        ],
        "_note": ("collective/individual responsibility·proportionality·public safety·"
                  "fiscal cost·humanitarian feasibility·treaty obligation 은 별도 human-coded "
                  "sidecar 다. fact preservation 에 합산하지 않으며 최종 윤리 정답을 만들지 "
                  "않는다. owner 가 사람 coder 와 독립 adjudicator 의 실제 이름을 지정하기 "
                  "전까지 코딩·확증을 수행하지 않는다(E-8A)."),
    }


def _guard_prior(path: Path) -> None:
    """이미 prior 가 채워진 facts 파일을 덮어쓰지 않는다 (v1 스크립트 계승).
    프로브는 실호출이다. 앵커 한 줄 고치려고 재빌드했다가 실호출 결과가 조용히 지워지면 안 된다."""
    if not path.exists():
        return
    try:
        cur = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    if any((f.get("prior") or {}).get("score") is not None for f in cur.get("facts", [])):
        raise SystemExit(
            f"[build] {path.name} 에 prior 프로브 결과가 있다 — 덮어쓰면 실호출 결과가 사라진다.")


def build_docs() -> dict:
    facts = [{
        "fact_id": fid(n), "text": t, "tags": [tag], "critical": crit,
        "prior": {"score": None, "probe_model": None,
                  "probe_prompt_ver": None, "probed_at": None},
        "_unfavorable_to": unf, "_perspective": persp,
        "_boundary": boundary,
    } for (n, t, tag, crit, unf, persp, boundary, _a) in FACTS]
    # E-1A: fact 01 에만 명시적 의미 슬롯을 붙인다(source/status/count/guilt).
    for f in facts:
        if f["fact_id"] == fid(1):
            f["_semantic"] = dict(FACT01_SEMANTIC)

    common = {"schema_ver": "0.2", "created_by": CREATED_BY,
              "created_at": CREATED_AT, "issue_id": IID}
    ethics = _ethics_sidecar_doc()
    return {
        "issue": {
            **common, "source": "synthetic",
            "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
            "title": "메르반 시의회 — 정착 협정 파기 표결 (측정 계약 v2)",
            "question": QUESTION, "body": BODY,
            "outcome_policy": OUTCOME_POLICY,
            "ethics_sidecar": ethics,
            "_note": (f"입장 대립형 v2(윤리 대 실리). pro={PRO}(협정 파기) / con={CON}(협정 유지). "
                      "**정답 없음** — outcome_policy=descriptive_stance_only, accuracy 금지(E-0A). "
                      "v1 대비 fact 01·02·08 만 문면 변경(E-1A 수사 명단·유죄 unknown · E-2A 원인 "
                      "미확정 · E-4A 이후 폐업·직접 원인 미확정). 나머지는 measurement 계약만 "
                      "바뀐다(fact 06 거부 행위자 unknown · fact 10 표결 산술 blocked · fact 11 "
                      "인과 보편화 금지 · fact 12 조항 실행성 unknown). 도시·지역·조직 이름과 수치는 "
                      "전부 허구이며 실재하는 나라·민족·분쟁을 가리키지 않는다. 딜레마의 실체는 "
                      "'저들이 위험한가'가 아니라 '일부의 행위로 전체를 벌할 것인가'이며, fact 01 이 "
                      "그 비율(2000 중 31)을 명시한다. 윤리 sidecar 는 fact preservation 과 분리하고 "
                      "사람 coder·독립 adjudicator 미지정이라 blocked 다(E-8A). 본문·요약문은 v1 과 "
                      "글자 동일. 본문에는 팩트 원문을 싣지 않는다(배분층 보호)."),
        },
        "facts": {
            **common,
            "outcome_policy": OUTCOME_POLICY,
            "ethics_sidecar": ethics,
            "_note": (f"issue_exile v2 정본 후보(팀 검수 전). 불리 대칭 {PRO} 4 : {CON} 4, 중립 2, "
                      "양쪽 2, 교대 배치. **fact_id 가 v1 과 다르다**(fact_exile_v2_NN, E-9A) — fact "
                      "01·02·08 명제가 바뀌었고 오부착을 막으려 namespace 전량 분리. 합칠 때는 "
                      "(issue_id, fact_id) 쌍을 키로 잡아라. requirement·share·favors 없음 — 정답형 "
                      "재료가 아니다. _unfavorable_to 는 fact truth 가 아니라 prereg 분석 메타다. "
                      "fact 01(_semantic·_boundary=source_status_count_guilt_unknown)은 시 경비대 "
                      "수사 관련자 명단(31/2000)이고 유죄 판결 수는 unknown 이다(E-1A). fact 02 는 "
                      "적발 9배지만 원인 미확정(E-2A). fact 06 거부 행위자 unknown — 조직원·위원회· "
                      "정착민 전체로 채우지 않는다(E-3A). fact 08 은 이후 폐업만 보존하고 직접 원인은 "
                      "미확정(E-4A). fact 10 은 11석·단순 과반만 보존, 6표 계산 blocked(E-5A). fact 11 "
                      "내부 인과는 보존하되 보편화 금지(E-6A). fact 12 는 조항 존재·미사용만, 실행성 "
                      "unknown(E-7A). 윤리 sidecar 는 fact preservation 과 분리·사람 지정 전까지 "
                      "blocked(E-8A). **prior 프로브 미실행 — 값이 null 이다. v1 prior 를 이전하지 "
                      "않는다(E-9A). 실호출 트랙에 올리기 전에 독립 probe 를 별도 승인·실행해야 한다.**"),
            "extractor": {"name": "manual", "ver": "1"},
            "facts": facts,
        },
        "assignment": {
            **common, "seed": 42, "overlap_k": 1,
            "_note": ("4에이전트(관점 × 입장), 에이전트당 3팩트, 밀도 1.0(전 팩트 고립). "
                      "제약: 모든 에이전트가 자기 입장 불리 1 + 상대 입장 불리 1 을 대칭으로 "
                      "보유한다. 아무도 12팩트 전량을 혼자 갖지 않는다(취합 없이는 전체 그림이 "
                      "안 잡힌다). descriptive 재료라 정답 사슬은 없지만 v1 의 대칭 배분을 유지한다. "
                      "⚠ stance 가 none 이 아니라 현행 콘솔은 재현 트랙으로 판정할 수 있다 — "
                      "토론 실행 경로는 게이트와 합의 후 연다."),
            "agents": [{"agent_id": a, "perspective": p, "stance": s,
                        "assigned_fact_ids": [fid(n) for n in ns]}
                       for a, (p, s, ns) in ASSIGN.items()],
        },
    }


# 토론용 배분 — 에이전트마다 [자기 불리 1 + 상대 불리 1 + 중립·양쪽 1]. 전 팩트 고립(v1 설계 유지).
ASSIGN = {
    "agent_1": ("치안", PRO, [1, 2, 9]),     # 자기 불리 01 · 상대 불리 02 · 중립 09
    "agent_2": ("재정", PRO, [5, 8, 11]),    # 자기 불리 05 · 상대 불리 08 · 양쪽 11
    "agent_3": ("등록", CON, [4, 3, 10]),    # 자기 불리 04 · 상대 불리 03 · 중립 10
    "agent_4": ("외무", CON, [6, 7, 12]),    # 자기 불리 06 · 상대 불리 07 · 양쪽 12
}


def check(docs: dict) -> int:
    anchors = {fid(f[0]): f[7] for f in FACTS}
    texts = {fid(f[0]): f[1] for f in FACTS}
    unfav = {fid(f[0]): f[4] for f in FACTS}
    bad = 0

    def line(name: str, ok: bool, detail: str = "") -> None:
        nonlocal bad
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {name}{('  ' + detail) if detail else ''}")

    print("── 앵커 (보조지표, 의미 판정 아님)")
    miss = [k for k, rx in anchors.items() if not re.search(rx, texts[k])]
    line("자기 팩트 적중", not miss, f"미적중 {miss}" if miss else "12/12")
    cross = {k: [j for j, t in texts.items() if j != k and re.search(rx, t)]
             for k, rx in anchors.items()}
    cross = {k: v for k, v in cross.items() if v}
    line("교차 오검출 0", not cross, str(cross) if cross else "")
    for label, blob in (("본문", BODY), ("요약문", STUB),
                        ("입장문(추방)", STANCE_TEXT[PRO]), ("입장문(잔류)", STANCE_TEXT[CON])):
        leak = [k for k, rx in anchors.items() if re.search(rx, blob)]
        line(f"{label} 누출 0", not leak, str(leak) if leak else f"{len(blob)}자")

    print("── identity / outcome policy")
    fs = docs["facts"]["facts"]
    line("새 issue identity", docs["facts"]["issue_id"] == IID)
    line("fact_id 전량 v2 · v1 과 미충돌",
         all(f["fact_id"].startswith("fact_exile_v2_") for f in fs) and len(fs) == 12)
    line("outcome_policy=descriptive_stance_only",
         docs["facts"]["outcome_policy"] == OUTCOME_POLICY
         and docs["issue"]["outcome_policy"] == OUTCOME_POLICY)
    line("정답형 필드 없음(requirement/share/favors)",
         all(not ({"requirement", "share", "favors"} & set(f)) for f in fs))
    line("prior 전부 null (미프로브 — 실호출 전 필수)",
         all((f["prior"] or {}).get("score") is None for f in fs))

    print("── 결정 문면 (E-1A~E-7A)")
    line("E-1A fact01 수사 명단·31/2000·유죄 unknown",
         all(s in texts[fid(1)] for s in ("시 경비대", "수사", "서른한", "이천", "유죄"))
         and fid(1) in GUILT_UNKNOWN_FACTS
         and FACT01_SEMANTIC["source"] == "시 경비대" and FACT01_SEMANTIC["count"] == "31/2000")
    line("E-2A fact02 적발 9배·원인 미확정",
         "아홉 배" in texts[fid(2)] and "원인" in texts[fid(2)]
         and fid(2) in CAUSAL_ATTRIBUTION_UNCONFIRMED)
    line("E-3A fact06 거부 행위자 unknown (미충전)",
         fid(6) in REFUSAL_ACTOR_UNKNOWN_FACTS
         and not any(x in texts[fid(6)] for x in ("조직원", "자치위원회", "정착민 전체")))
    line("E-4A fact08 이후 폐업·직접 원인 미확정",
         all(s in texts[fid(8)] for s in ("예순둘", "이후", "직접 원인"))
         and fid(8) in CLOSURE_CAUSE_UNCONFIRMED)
    line("E-5A fact10 11석·단순 과반·표결 산술 blocked",
         "열한 자리" in texts[fid(10)] and "단순 과반" in texts[fid(10)]
         and fid(10) in VOTE_THRESHOLD_BLOCKED)
    line("E-6A fact11 내부 인과 보존·보편화 금지",
         all(s in texts[fid(11)] for s in ("갱신되지 않아", "넉 달"))
         and fid(11) in INTERNAL_CAUSE_NO_UNIVERSALIZATION)
    line("E-7A fact12 조항 존재·미사용만·실행성 unknown",
         all(s in texts[fid(12)] for s in ("따로 송환", "쓰인 적이 없다"))
         and fid(12) in OPTION_FEASIBILITY_UNKNOWN)

    print("── 윤리 sidecar (E-8A — 분리·사람 지정 전 blocked)")
    for label, doc in (("issue", docs["issue"]), ("facts", docs["facts"])):
        sc = doc["ethics_sidecar"]
        line(f"{label} sidecar blocked·분리",
             sc["status"] == ETHICS_SIDECAR_STATUS and sc["separated_from_fact_preservation"]
             and sc["human_coder"] is None and sc["independent_adjudicator"] is None)
    ethics_blocked = True
    try:
        require_human_ethics_assignment()
        ethics_blocked = False
    except RuntimeError:
        pass
    line("사람 미지정 시 윤리 코딩 fail-closed", ethics_blocked)

    print("── 구조 (입장 대립형, v1 설계 유지)")
    c = Counter(unfav.values())
    line("불리 대칭 4:4", c[PRO] == 4 and c[CON] == 4, f"{PRO} {c[PRO]} : {CON} {c[CON]}")
    line("중립 2 · 양쪽 2", c[None] == 2 and c["both"] == 2, f"중립 {c[None]} · 양쪽 {c['both']}")
    order = [unfav[fid(n)] for n in range(1, 9)]
    alt = all(order[i] != order[i + 1] for i in range(len(order) - 1))
    line("불리가 앞뒤로 교대", alt, " → ".join(str(o) for o in order))
    line("비율 명시 팩트가 추방 쪽 불리", unfav[fid(1)] == PRO and "서른한" in texts[fid(1)])
    line("제3경로(개별 송환) 존재", unfav[fid(12)] == "both")

    print("── 배분 (자기 불리 1 + 상대 불리 1, 전 팩트 고립)")
    own = Counter(i for a in docs["assignment"]["agents"] for i in a["assigned_fact_ids"])
    all_ids = set(texts)
    for a in docs["assignment"]["agents"]:
        ids = a["assigned_fact_ids"]
        mine = [i[-2:] for i in ids if unfav[i] == a["stance"]]
        theirs = [i[-2:] for i in ids if unfav[i] not in (a["stance"], None, "both")]
        line(f"{a['agent_id']} ({a['stance']})", len(mine) >= 1 and len(theirs) >= 1,
             f"자기불리 {mine} · 상대불리 {theirs}")
    line("전 팩트 고립(밀도 1.0)", set(own.values()) == {1} and len(own) == 12,
         f"보유자 분포 {dict(sorted(Counter(own.values()).items()))} · 배분 {len(own)}개")
    line("혼자 전체 사슬 보유 0명",
         not any(all_ids <= set(a["assigned_fact_ids"]) for a in docs["assignment"]["agents"]))

    print("── evaluator (descriptive — winner/accuracy 없음)")
    empty = descriptive_stance_evaluator_v2(set())
    full = descriptive_stance_evaluator_v2(all_ids)
    line("빈 known → winner/accuracy None", empty["winner"] is None and empty["accuracy"] is None)
    line("전체 known → winner/accuracy None", full["winner"] is None and full["accuracy"] is None)
    line("방향 집계 4:4 (None·both 제외)",
         full["unfavorable_prereg_counts"] == {PRO: 4, CON: 4})
    line("윤리 sidecar 상태만 노출(점수 없음)",
         full["ethics_sidecar_status"] == ETHICS_SIDECAR_STATUS
         and not ({"collective_punishment", "proportionality", "ethics_score"} & set(full)))
    reject_ok = True
    for token in ("accuracy", "winner", "정답률"):
        try:
            reject_accuracy_request(token)
            reject_ok = False
        except ValueError:
            pass
    line("accuracy 요청 fail-closed", reject_ok)
    actor_ok = True
    for actor in ("검은 갈대 조직원", "정착지 자치위원회", "정착민 전체"):
        try:
            reject_refusal_actor_fill(actor)
            actor_ok = False
        except ValueError:
            pass
    line("거부 행위자 충전 fail-closed", actor_ok)
    return bad


def _serialized_outputs() -> dict[Path, str]:
    docs = build_docs()
    return {
        HERE / f"{IID}.json": json.dumps(docs["issue"], ensure_ascii=False, indent=2),
        HERE / f"facts_{IID}.json": json.dumps(docs["facts"], ensure_ascii=False, indent=2),
        HERE / f"assignment_{IID}.json": json.dumps(docs["assignment"], ensure_ascii=False, indent=2),
        ROOT / "data" / "issues" / f"{IID}.json": json.dumps(docs["issue"], ensure_ascii=False, indent=2),
        ROOT / "data" / "facts" / f"facts_{IID}.json": json.dumps(docs["facts"], ensure_ascii=False, indent=2),
        ROOT / "data" / "assignments" / f"assignment_{IID}.json": json.dumps(docs["assignment"], ensure_ascii=False, indent=2),
    }


def main() -> None:
    payloads = _serialized_outputs()
    for path in payloads:
        if path.name.startswith("facts_"):
            _guard_prior(path)
    for path, text in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("[생성] " + ", ".join(str(p.relative_to(ROOT)) for p in payloads) + "\n")
    bad = check(build_docs())
    print(f"\n{'전부 통과' if not bad else f'실패 {bad}건'}")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
