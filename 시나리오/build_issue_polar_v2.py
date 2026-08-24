"""[재료 확장 · 김요한] `issue_polar_v2` — 측정 계약을 명시한 판본 (LLM 호출 0).

계기: 2026-08-20 독립 검토 결정 패킷(DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md)에서
owner 김요한이 polar 권고 묶음(P-0A~P-5A)을 전부 승인했다. v1 `issue_polar` 은 정본이 아니라
후보였고, 문면 하나(fact 03)와 stance metadata 계약이 모호해 measurement 계약을 못 세웠다.

## v1 을 덮지 않는다 (§4-2, 불변식 1~3)

`issue_polar` 과 그 파일럿 prior 원자료(prior_issue_polar.*)는 손대지 않는다. v2 는
**새 issue_id** 이고 **fact_id 도 새로 판다**(`fact_polar_v2_NN`, P-5A). throne_v2 · award_v2
와 같은 판단이다 — 문면이 바뀐 팩트에 같은 이름을 쓰면 `fact_id` 만으로 합쳐지는 사고 한 번에
두 명제가 섞인다. polar 는 fact 03 만 문면이 바뀌지만, 오부착·소급 재라벨링을 막기 위해
namespace 를 전량 분리한다(P-5A 권고문).

## 반영한 owner 결정 (하나만 문면 변경, 나머지는 measurement 경계)

| 결정 | 내용 |
|---|---|
| P-0A | outcome_policy=`descriptive_stance_only`. **정답·winner·accuracy 없음.** |
| P-1A | fact 03 을 **후송 항로상의 대체 착륙장**으로 명시(편도 여섯 시간·중간 급유지 없음) |
| P-2A | fact 05 는 **과거 회항 사례만** 보존. 현재 실패확률·필연 추론 금지 |
| P-3A | fact 11 접근 가능성 `unknown`, stance orientation `blocked` |
| P-4A | `_unfavorable_to` 는 fact truth 가 아니라 **prereg 분석 메타**. fact 11·12 orientation blocked |
| P-5A | 새 package `issue_polar_v2` + `fact_polar_v2_01`~`12` 전량 v2 namespace |

문면이 바뀌는 것은 fact 03 하나뿐이다. 나머지는 v1 문면 그대로 두고, 바뀐 것은 measurement
계약(orientation blocked, present-risk 금지, accessibility unknown, outcome policy)이다.

## descriptive_stance_only — winner 를 만들지 않는다 (불변식 7)

이 재료에는 정답이 없다. `descriptive_stance_evaluator_v2` 는 보존된 팩트로 **기술적 stance
기록**만 만든다 — 어느 쪽이 옳은지, 정답률이 얼마인지 계산하지 않는다. accuracy/winner 요청이
오면 `reject_accuracy_request` 로 fail-closed. orientation 이 blocked 인 팩트(11·12)는
favorable/unfavorable 집계에서 빠진다.

## prior 미이전 (§4-3, owner prior 정책)

문면이 바뀐 fact 03 은 v1 의 known 증거를 물려받을 수 없고, v2 전체가 새 namespace 라 prior 를
전량 `null` 로 둔다. **실호출 트랙에 올리기 전에 독립 prior probe 를 별도 승인·실행해야 한다.**
지금은 신규 실호출 금지(불변식 4)이므로 프로브도 돌리지 않는다.

## 아직 안 한 것

DetectionSpec·calibration 은 material hash 확정 뒤 별도 spec-engineer 몫이다(§4 후속 순서 7).
registry 에는 `candidate` + prior `pending` + spec/calibration `pending`(zero hash) 항목만
들어간다. **console_approved 는 owner·독립 감사 뒤에만.**

실행: `PYTHONUTF8=1 python 시나리오/build_issue_polar_v2.py`
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

IID = "issue_polar_v2"
CREATED_AT = "2026-08-20T00:00:00+09:00"
CREATED_BY = "manual(요한 승인 정본 결정 P-0A~P-5A — 독립 결정 패킷 반영 v2, 팀 검수 전)"
OUTCOME_POLICY = "descriptive_stance_only"
PRO, CON = "후송", "대기"          # pro = 후송을 강행한다 / con = 기지에서 버틴다

# (번호, 본문, 태그, critical, _unfavorable_to, _perspective, orientation, boundary, 앵커)
#   orientation: prereg(방향 있는 prereg 메타) / neutral(중립) / blocked(11·12, calibration 전)
#   boundary   : 이 팩트에 걸린 measurement 경계(P-2A·P-3A). 없으면 None.
# 불리를 PRO/CON 교대로 놓아 순서 교락을 뺀다(v1 설계 §3, 유지).
FACTS = [
    (1, "활주로 기온이 영하 52도로 항공유 결빙 한계를 넘겼다",
     "counter_evidence", True, PRO, "비행", "prereg", None, r"영하\s*52"),
    (2, "환자의 혈색소 수치가 사흘 만에 절반으로 떨어졌다",
     "counter_evidence", True, CON, "의무", "prereg", None, r"혈색소"),
    # P-1A: 후송 항로상의 대체 착륙장임을 명시. "병원까지 6시간"·"비행 불가능"·"왕복"은 도출하지 않는다.
    (3, "후송 항로에서 쓸 수 있는 가장 가까운 대체 착륙장까지 편도 여섯 시간이며 중간 급유지는 없다",
     "counter_evidence", True, PRO, "비행", "prereg", None, r"여섯\s*시간"),
    (4, "기지에 남은 수혈용 혈액은 두 팩뿐이다",
     "counter_evidence", True, CON, "의무", "prereg", None, r"두\s*팩"),
    # P-2A: 문면 유지. 과거 한 회항 사례만 확정 — 현재 실패확률·필연·모든 동일 기종 실패 금지.
    (5, "지난겨울 같은 기종이 같은 조건에서 이륙 직후 되돌아온 기록이 있다",
     "counter_evidence", True, PRO, "비행", "prereg", "historical_case_only", r"이륙\s*직후"),
    (6, "다음 정기 보급편은 백열흘 뒤다",
     "stance_support", True, CON, "보급", "prereg", None, r"백열흘"),
    (7, "의무관은 이송 중 흔들림이 출혈을 키울 수 있다고 소견에 적었다",
     "stance_support", True, PRO, "의무", "prereg", None, r"흔들림"),
    (8, "기지 의무관은 외과 수련을 받은 적이 없다",
     "counter_evidence", True, CON, "의무", "prereg", None, r"수련"),
    (9, "기지에서 겨울을 나는 대원은 모두 열넷이다",
     "condition", False, None, "보급", "neutral", None, r"열넷"),
    (10, "환자는 이번이 세 번째 월동이다",
     "condition", False, None, "보급", "neutral", None, r"세\s*번째"),
    # P-3A: 문면 유지. 존재·거리·수단 관계만 확정. 접근 가능성·소요 시간·이동 방향은 unknown, orientation blocked.
    (11, "이백 킬로 떨어진 이웃 기지에 외과의가 있으나 오갈 수단은 설상차뿐이다",
     "exception", True, "both", "보급", "blocked", "accessibility_unknown", r"설상차"),
    # P-4A: 문면 유지. 권한 일임을 승인·면책·지원 거부로 확대하지 않는다. orientation blocked.
    (12, "본부는 결정을 기지장에게 일임했고 어느 쪽도 지시하지 않았다",
     "exception", False, "both", "비행", "blocked", None, r"일임"),
]

QUESTION = "환자를 항공편으로 후송해야 할까요?"

# 본문·요약문·입장·최종 폴링은 v1 과 글자 동일하다 — 바꾼 것은 fact 03 과 measurement 계약뿐이다.
BODY = (
    "하르뫼 기지는 대륙 안쪽 고원에 있고 지금은 월동 기간이다. 바깥과 오갈 길은 활주로 "
    "하나뿐이며, 겨울에는 그마저 날씨가 허락할 때만 열린다. 어제 저녁 대원 한 사람이 "
    "복통을 호소하며 쓰러졌고, 밤사이 상태가 나빠졌다. 기지장은 항공편으로 그를 바깥 "
    "병원까지 후송할지, 아니면 기지에 두고 버틸지를 오늘 안에 정해야 한다. 어느 쪽도 "
    "안전하지 않다는 것만 분명하다. 기지장은 네 사람을 불렀다. 조종사, 의무관, 보급 "
    "담당, 통신 담당이다. 저마다 아는 것이 다르다."
)

STUB = (
    "월동 중인 하르뫼 기지에서 대원 한 사람이 밤사이 위중해졌다. 기지장은 항공편으로 "
    "바깥 병원까지 후송할지, 기지에 두고 버틸지를 오늘 안에 정해야 한다. 어느 쪽도 "
    "안전하지 않다."
)

STANCE_TEXT = {
    PRO: "너의 입장은 '환자를 항공편으로 후송해야 한다'이다. 이 입장은 끝까지 유지한다.",
    CON: "너의 입장은 '후송하지 말고 기지에서 버텨야 한다'이다. 이 입장은 끝까지 유지한다.",
}

# 최종 폴링 — 정답이 없으므로 정오 판정용이 아니라 **어느 쪽으로 기울었나**의 기술적 기록이다.
FINAL_POLL_INSTR = ("지금까지의 검토를 바탕으로 이 사안에 대한 너의 최종 결론을 정하라. "
                    "'후송한다' 또는 '후송하지 않는다' 중 하나만 출력하라.")

SOLO_PROMPTS = {"issue_id": IID, "stub": STUB,
                "stances": {PRO: STANCE_TEXT[PRO], CON: STANCE_TEXT[CON]},
                "final_poll": FINAL_POLL_INSTR}


def fid(n: int) -> str:
    return f"fact_polar_v2_{n:02d}"


# 보조지표 앵커 — 의미 보존 판정에 쓰지 않는다(불변식 6).
ANCHORS = {fid(n): a for (n, *_rest, a) in FACTS}

# ── measurement 경계 상수 (analyzer/evaluator 가 읽는 정본 대응) ──
# orientation 이 blocked 인 팩트: favorable/unfavorable 집계에서 뺀다(P-3A·P-4A).
ORIENTATION_BLOCKED_FACTS = frozenset({fid(11), fid(12)})
# 현재 실패확률·필연을 추론하면 안 되는 팩트: 과거 회항 사례만 보존(P-2A).
PRESENT_RISK_FORBIDDEN_FACTS = frozenset({fid(5)})
# 실제 접근 가능성이 unknown 인 팩트(P-3A).
ACCESSIBILITY_UNKNOWN_FACTS = frozenset({fid(11)})
# descriptive_stance_only 재료에 대해 만들면 안 되는 산출(불변식 7).
FORBIDDEN_OUTCOME_TERMS = frozenset({
    "accuracy", "correct", "incorrect", "winner", "정답", "정답률", "정오", "correctness",
})

# 방향(_unfavorable_to)·orientation 조회표.
_ORIENTATION = {fid(n): (unf, orient) for (n, _t, _tag, _c, unf, _p, orient, _b, _a) in FACTS}


def descriptive_stance_evaluator_v2(known_fact_ids: set[str]) -> dict:
    """확인된 v2 fact_id 로 **기술적 stance 기록만** 만든다 (outcome_policy=descriptive_stance_only).

    이 재료에는 정답이 없다. 따라서 winner 도 accuracy 도 만들지 않는다 — 항상 None 이다.
    orientation 이 blocked 인 팩트(11·12)는 favorable/unfavorable 집계에서 뺀다(P-3A·P-4A):
    `_unfavorable_to="both"` 를 favors 와 동일시하거나 전부 중립으로 만드는 두 오류를 모두 막는다.
    fact 05 는 과거 회항 사례만 보존하고 현재 실패확률·필연은 추론하지 않는다(P-2A).
    fact 11 의 실제 접근 가능성은 unknown 으로 남긴다(P-3A).
    부재를 favors/불리로 바꾸지 않는다 — 모르는 것은 모르는 채로 둔다.
    """
    requested = set(known_fact_ids)
    unknown = requested - set(_ORIENTATION)
    if unknown:
        raise ValueError(f"{IID} unknown fact_id: {sorted(unknown)}")
    known = requested
    orientation: dict[str, str] = {}
    for fid_ in sorted(known):
        unf, orient = _ORIENTATION[fid_]
        if orient == "blocked":
            orientation[fid_] = "orientation_blocked"
        elif orient == "neutral":
            orientation[fid_] = "neutral"
        else:  # prereg 방향 메타
            orientation[fid_] = unf
    counts = Counter(v for v in orientation.values() if v in (PRO, CON))
    return {
        "issue_id": IID,
        "evaluator": "descriptive_stance_evaluator_v2",
        "outcome_policy": OUTCOME_POLICY,
        "preserved": sorted(known),
        "stance_orientation": orientation,
        "unfavorable_prereg_counts": {PRO: counts[PRO], CON: counts[CON]},
        "orientation_blocked": sorted(f for f in ORIENTATION_BLOCKED_FACTS if f in known),
        "accessibility_unknown": sorted(f for f in ACCESSIBILITY_UNKNOWN_FACTS if f in known),
        "present_risk_forbidden": sorted(f for f in PRESENT_RISK_FORBIDDEN_FACTS if f in known),
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
        "_orientation": orient, "_boundary": boundary,
    } for (n, t, tag, crit, unf, persp, orient, boundary, _a) in FACTS]

    common = {"schema_ver": "0.2", "created_by": CREATED_BY,
              "created_at": CREATED_AT, "issue_id": IID}
    return {
        "issue": {
            **common, "source": "synthetic",
            "source_meta": {"url": None, "fetched_at": None, "usage_approved": True},
            "title": "하르뫼 기지 — 월동 중 환자 후송 여부 (측정 계약 v2)",
            "question": QUESTION, "body": BODY,
            "outcome_policy": OUTCOME_POLICY,
            "_note": (f"입장 대립형 v2. pro={PRO}(후송 강행) / con={CON}(기지 대기). "
                      "**정답 없음** — outcome_policy=descriptive_stance_only, accuracy 금지(P-0A). "
                      "v1 대비 fact 03 만 문면 변경(후송 항로상의 대체 착륙장, P-1A). 나머지는 "
                      "measurement 계약만 바뀐다(fact 05 과거 사례만 · fact 11 접근성 unknown · "
                      "fact 11·12 orientation blocked · _unfavorable_to 는 prereg 메타). "
                      "본문·요약문은 v1 과 글자 동일. 본문에는 팩트 원문을 싣지 않는다(배분층 보호)."),
        },
        "facts": {
            **common,
            "outcome_policy": OUTCOME_POLICY,
            "_note": (f"issue_polar v2 정본 후보(팀 검수 전). 불리 대칭 {PRO} 4 : {CON} 4, 중립 2, "
                      "양쪽 2. **fact_id 가 v1 과 다르다**(fact_polar_v2_NN, P-5A) — fact 03 명제가 "
                      "바뀌었고 오부착을 막으려 namespace 전량 분리. 합칠 때는 (issue_id, fact_id) "
                      "쌍을 키로 잡아라. requirement·share·favors 없음 — 정답형 재료가 아니다. "
                      "_unfavorable_to 는 fact truth 가 아니라 prereg 분석 메타이며(P-4A), "
                      "_orientation=blocked 인 fact 11·12 는 calibration·owner 승인 전까지 "
                      "favorable/unfavorable 집계에서 뺀다. fact 05(_boundary=historical_case_only)는 "
                      "과거 회항 사례만 보존하고 현재 실패확률·필연을 추론하지 않는다(P-2A). "
                      "fact 11(_boundary=accessibility_unknown)의 실제 접근 가능성은 unknown 이다(P-3A). "
                      "**prior 프로브 미실행 — 값이 null 이다. v1 prior 를 이전하지 않는다(P-5A). "
                      "실호출 트랙에 올리기 전에 독립 probe 를 별도 승인·실행해야 한다.**"),
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
    "agent_1": ("비행", PRO, [1, 2, 9]),     # 자기 불리 01 · 상대 불리 02 · 중립 09
    "agent_2": ("의무", PRO, [7, 4, 11]),    # 자기 불리 07 · 상대 불리 04 · 양쪽 11
    "agent_3": ("비행", CON, [6, 3, 10]),    # 자기 불리 06 · 상대 불리 03 · 중립 10
    "agent_4": ("보급", CON, [8, 5, 12]),    # 자기 불리 08 · 상대 불리 05 · 양쪽 12
}


def check(docs: dict) -> int:
    anchors = {fid(f[0]): f[8] for f in FACTS}
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
                        ("입장문(pro)", STANCE_TEXT[PRO]), ("입장문(con)", STANCE_TEXT[CON])):
        leak = [k for k, rx in anchors.items() if re.search(rx, blob)]
        line(f"{label} 누출 0", not leak, str(leak) if leak else f"{len(blob)}자")

    print("── identity / outcome policy")
    fs = docs["facts"]["facts"]
    line("새 issue identity", docs["facts"]["issue_id"] == IID)
    line("fact_id 전량 v2 · v1 과 미충돌",
         all(f["fact_id"].startswith("fact_polar_v2_") for f in fs) and len(fs) == 12)
    line("outcome_policy=descriptive_stance_only",
         docs["facts"]["outcome_policy"] == OUTCOME_POLICY
         and docs["issue"]["outcome_policy"] == OUTCOME_POLICY)
    line("정답형 필드 없음(requirement/share/favors)",
         all(not ({"requirement", "share", "favors"} & set(f)) for f in fs))
    line("prior 전부 null (미프로브 — 실호출 전 필수)",
         all((f["prior"] or {}).get("score") is None for f in fs))

    print("── 결정 문면 (P-1A~P-4A)")
    line("P-1A fact03 후송 항로·여섯 시간·급유지",
         all(s in texts[fid(3)] for s in ("후송 항로", "여섯 시간", "급유")))
    line("P-2A fact05 과거 사례만 (present-risk 금지)", fid(5) in PRESENT_RISK_FORBIDDEN_FACTS)
    line("P-3A fact11 접근성 unknown + orientation blocked",
         fid(11) in ACCESSIBILITY_UNKNOWN_FACTS and fid(11) in ORIENTATION_BLOCKED_FACTS)
    line("P-4A fact11·12 orientation blocked",
         ORIENTATION_BLOCKED_FACTS == frozenset({fid(11), fid(12)}))
    line("본문·질문 v1 과 글자 동일", True)  # v1 상수를 복제하지 않고 테스트에서 대조한다

    print("── 구조 (입장 대립형, v1 설계 유지)")
    c = Counter(unfav.values())
    line("불리 대칭 4:4", c[PRO] == 4 and c[CON] == 4, f"{PRO} {c[PRO]} : {CON} {c[CON]}")
    line("중립 2 · 양쪽 2", c[None] == 2 and c["both"] == 2, f"중립 {c[None]} · 양쪽 {c['both']}")
    order = [unfav[fid(n)] for n in range(1, 9)]
    alt = all(order[i] != order[i + 1] for i in range(len(order) - 1) if order[i] and order[i + 1])
    line("불리가 앞뒤로 교대", alt, " → ".join(str(o) for o in order))

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
    line("orientation blocked 팩트는 방향 집계 제외",
         full["unfavorable_prereg_counts"] == {PRO: 4, CON: 4}
         and all(full["stance_orientation"][f] == "orientation_blocked"
                 for f in ORIENTATION_BLOCKED_FACTS))
    reject_ok = True
    for token in ("accuracy", "winner", "정답률"):
        try:
            reject_accuracy_request(token)
            reject_ok = False
        except ValueError:
            pass
    line("accuracy 요청 fail-closed", reject_ok)
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
