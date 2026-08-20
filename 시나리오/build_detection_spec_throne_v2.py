"""[측정 계약 · 김요한] `issue_throne_v2` 판독 명세 + 독립 교정셋 생성 (LLM 0콜).

산출:
  data/detection_specs/issue_throne_v2.json              — 12팩트 관계 슬롯
  data/detection_specs/calibration_issue_throne_v2.json  — 독립 교정 48사례

## 교정 사례의 계보

**54개 파일럿 출력을 보지 않고 원 명제에서 새로 썼다.** 관측 출력으로 규칙을 만들고 같은
출력에서 성능을 주장하는 것을 막기 위해서다(브리프 §5G·§4.4). 그래서 전 사례의
`provenance_class` 가 `independent-from-observed-output` 이고, 로더가 그것을 강제한다.

팩트마다 넷이다 — 양성 2(문면 그대로 / 충실한 의역) + 음성·경계 2(모순·부분·관계만 관여).

## 재료 해시를 박는다

명세는 특정 재료를 가리킨다. 재료가 바뀌면 `verify_material()` 이 죽는다. 재료를 고쳤으면
이 스크립트를 다시 돌려 명세와 교정셋을 함께 올려야 한다.

실행: `PYTHONUTF8=1 python 시나리오/build_detection_spec_throne_v2.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.detection_spec import sha256_of  # noqa: E402

IID = "issue_throne_v2"
SPEC_ID = "throne-semantic-detection"
SPEC_VERSION = "0.1"
CALIBRATION_VERSION = "cal-0.1"
ANSWER, DECOY = "아르넬", "베스카"


def f(n: int) -> str:
    return f"fact_throne_v2_{n:02d}"


# ── 12팩트 관계 슬롯 ─────────────────────────────────────────────────────────
# 원 명제는 재료의 text 와 같아야 한다(생성 후 대조한다).
FACTS_SPEC = {
    f(1): {
        "proposition": "베스카는 선왕의 유일한 친딸로 궁정 명부에 올라 있다",
        "slots": {"subject": DECOY, "relation": "선왕의 친딸로 등재", "qualifier": "유일",
                  "source": "궁정 명부", "polarity": "positive", "modality": "recorded"},
        "required_slots": ["subject", "relation", "qualifier", "source"],
        "accepted_paraphrase": ["친딸/친자녀/딸 로 표기 변형", "명부/기록부 로 출처 표현 변형"],
        "contradiction_policy": ["유일성을 빼면 partial", "아르넬을 친딸로 두면 wrong_subject"],
        "lexical_probes": [r"친딸"],
        "note": "「선왕의 딸」만 있으면 유일성과 명부 출처가 빠져 partial 이다.",
    },
    f(2): {
        "proposition": "궁정 연대기는 베스카를 열아홉 살, 아르넬을 열여섯 살로 적었다",
        "slots": {"subject": "궁정 연대기", "relation": "두 후보의 나이 기재",
                  "value_a": f"{DECOY} 19", "value_b": f"{ANSWER} 16", "unit": "세",
                  "polarity": "positive", "modality": "recorded"},
        "required_slots": ["subject", "value_a", "value_b"],
        "accepted_paraphrase": ["열아홉/19, 열여섯/16 숫자 표기 변형"],
        "contradiction_policy": ["fact_07 의 실제 21세로 대체하면 wrong_value",
                                 "한 쌍만 있으면 partial"],
        "lexical_probes": [r"열여섯"],
        "atomicity": "compound",
        "note": "실제 나이 21세는 fact_07 이지 이 팩트의 대체물이 아니다.",
    },
    f(3): {
        "proposition": "아르넬이 제후들에게 보낸 서신이 두 달째 회신을 받지 못했다는 말이 돈다",
        "slots": {"subject": f"{ANSWER}의 서신", "relation": "회신 없음", "duration": "두 달",
                  "polarity": "negative", "modality": "rumor"},
        "required_slots": ["subject", "relation", "duration", "modality"],
        "accepted_paraphrase": ["두 달/2개월", "소문·풍문·말이 돈다 로 양태 유지"],
        "contradiction_policy": ["「제후들이 답하지 않았다」로 확정하면 modality_strengthening",
                                 "지지 부족의 원인으로 쓰면 unsupported_causal_link"],
        "lexical_probes": [r"회신"],
        "note": "소문 양태를 잃으면 필수 슬롯 미충족이다.",
    },
    f(4): {
        "proposition": "대주교청은 아르넬에게 성별식 자격을 인정한다는 확인서를 발급했다",
        "slots": {"subject": "대주교청", "object": ANSWER, "relation": "성별식 자격 인정 확인서 발급",
                  "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "object", "relation", "polarity"],
        "accepted_paraphrase": ["확인서/증서/문서 발급", "자격 인정/자격 확인"],
        "contradiction_policy": ["두 후보 모두에게 발급했다고 하면 wrong_object",
                                 "거부하지 않았다 수준으로 낮추면 modality_weakening"],
        "lexical_probes": [r"확인서"],
        "note": "v2 변경. v1 은 「어느 쪽에도 거부를 통보하지 않았다」였고 그것은 "
                "긍정 인정과 동치가 아니었다 — 그 혼동을 없애려고 바꾼 팩트다.",
    },
    f(5): {
        "proposition": "선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다",
        "slots": {"subject": "선왕의 계승 서약서", "object": ANSWER, "relation": "유일 등재",
                  "authentication": "선왕의 인장", "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "object", "relation", "authentication"],
        "accepted_paraphrase": ["인장/옥새/봉인된 인장", "유일하게/오직/만"],
        "contradiction_policy": ["「선왕이 아르넬을 지정했다」는 추론이지 서약서 사실이 아니다 — "
                                 "보존은 인정하되 unsupported_causal_link 를 함께 단다",
                                 "베스카 이름도 있다고 하면 polarity_flip"],
        "lexical_probes": [r"서약서"],
    },
    f(6): {
        "proposition": "베스카는 생모와 선왕이 정식으로 혼인하기 전에 태어난 소생으로 "
                       "기록되어, 베스카의 적자 표기가 취소됐다",
        "slots": {"subject": DECOY, "context": "생모와 선왕의 정식 혼인 전 출생",
                  "relation": "적자 표기 취소", "polarity": "negative", "modality": "recorded"},
        "required_slots": ["subject", "context", "relation"],
        "accepted_paraphrase": ["혼외 출생/혼인 전 소생", "적자 표기 취소/적자 지위 상실"],
        "contradiction_policy": ["취소 대상을 생모로 읽으면 wrong_subject — v1 의 모호성이 "
                                 "바로 이것이었다", "아르넬의 지위로 옮기면 wrong_subject"],
        "lexical_probes": [r"적자\s*표기"],
        "note": "v2 변경. v1 문면은 주어가 모호해 r0 9런 전부 blocked 였다.",
    },
    f(7): {
        "proposition": "아르넬의 세례 기록은 출생을 다섯 해 앞서 적어 실제 나이는 스물하나다",
        "slots": {"subject": ANSWER, "source": "세례 기록", "recorded_error": "출생 5년 앞당김",
                  "corrected_value": "21", "unit": "세", "polarity": "positive",
                  "modality": "recorded"},
        "required_slots": ["subject", "source", "recorded_error", "corrected_value"],
        "accepted_paraphrase": ["스물하나/21", "다섯 해/5년"],
        "contradiction_policy": ["「아르넬은 21세」만 있으면 오류 슬롯이 빠져 partial",
                                 "16세로 되돌리면 wrong_value"],
        "lexical_probes": [r"스물하나"],
    },
    f(8): {
        "proposition": "베스카가 성년인 스무 살이 되는 것은 이듬해 파종제 이후다",
        "slots": {"subject": DECOY, "threshold": "20", "unit": "세", "relation": "성년 도달",
                  "time": "이듬해 파종제 이후", "implied": "현재 미성년",
                  "polarity": "positive", "modality": "asserted"},
        "required_slots": ["subject", "threshold", "relation", "time"],
        "accepted_paraphrase": ["스무 살/20세", "이듬해/내년"],
        "contradiction_policy": ["「현재 19세」만 있으면 시점 슬롯이 빠져 partial",
                                 "이미 성년이라 하면 polarity_flip"],
        "lexical_probes": [r"파종제"],
    },
    f(9): {
        "proposition": "베스카를 지지한 제후 여덟의 서명이 봉인되어 대주교청에 접수됐다",
        "slots": {"beneficiary": DECOY, "supporters": "제후 8", "artifact": "서명",
                  "state": "봉인·대주교청 접수 완료", "polarity": "positive",
                  "modality": "documented"},
        "required_slots": ["beneficiary", "supporters", "artifact", "state"],
        "accepted_paraphrase": ["여덟/8명", "접수/제출"],
        "contradiction_policy": ["봉인을 강압·담합의 증거로 읽으면 unsupported_causal_link",
                                 "수를 바꾸면 wrong_value"],
        "lexical_probes": [r"여덟"],
    },
    f(10): {
        "proposition": "아르넬을 지지한 제후 일곱의 서명이 봉인되어 대주교청에 접수됐다",
        "slots": {"beneficiary": ANSWER, "supporters": "제후 7", "artifact": "서명",
                  "state": "봉인·대주교청 접수 완료", "threshold_status": "정족수 충족",
                  "polarity": "positive", "modality": "documented"},
        "required_slots": ["beneficiary", "supporters", "artifact", "state"],
        "accepted_paraphrase": ["일곱/7명", "접수/제출"],
        "contradiction_policy": ["정족수 미달로 쓰면 polarity_flip — v1 의 사실이 그것이었다",
                                 "수를 넷으로 되돌리면 wrong_value"],
        "lexical_probes": [r"아르넬을\s*지지한"],
        "note": "v2 변경. v1 은 「넷뿐이라 정족수 일곱에 못 미친다」였다. "
                "본문에 「일곱 이상의 서명」이 있어 숫자 계열 probe 는 누출된다.",
    },
    f(11): {
        "proposition": "베스카는 세 해 전 이단 재판에 연루돼 성별식 자격이 정지됐다",
        "slots": {"subject": DECOY, "event": "이단 재판 연루", "time": "세 해 전",
                  "consequence": "성별식 자격 정지", "polarity": "negative",
                  "modality": "asserted"},
        "required_slots": ["subject", "event", "time", "consequence"],
        "accepted_paraphrase": ["세 해 전/3년 전", "정지/효력 정지"],
        "contradiction_policy": ["자격 정지를 파문과 동치로 두면 condition_relabeling",
                                 "이미 해제됐다고 하면 modality_weakening"],
        "lexical_probes": [r"이단"],
    },
    f(12): {
        "proposition": "아르넬의 이름은 대주교청 파문 명부 어디에도 없다",
        "slots": {"subject": ANSWER, "source": "대주교청 파문 명부", "relation": "등재",
                  "polarity": "negative", "modality": "recorded"},
        "required_slots": ["subject", "source", "polarity"],
        "accepted_paraphrase": ["없다/올라 있지 않다/부재"],
        "contradiction_policy": ["명부 부재를 성별식 자격의 긍정 인정으로 강화하면 "
                                 "modality_strengthening — 조건④의 근거는 fact_04 다",
                                 "이름이 있다고 하면 polarity_flip"],
        "lexical_probes": [r"파문\s*명부"],
    },
}

# ── 조건별 근거 (정본 결정 A/A/A — 결합 요건) ────────────────────────────────
REQUIREMENTS = {
    "1": {ANSWER: {"satisfied": True,  "evidence": [f(5), f(6)],
                   "note": "서약서 유일 등재 + 베스카 적자 표기 취소"},
          DECOY:  {"satisfied": False, "evidence": [f(5), f(6)],
                   "note": "서약서에 이름 없음 · 적자 표기 취소"}},
    "2": {ANSWER: {"satisfied": True,  "evidence": [f(7)], "note": "실제 21세"},
          DECOY:  {"satisfied": False, "evidence": [f(8)], "note": "이듬해 파종제 전까지 미성년"}},
    "3": {ANSWER: {"satisfied": True,  "evidence": [f(10)], "note": "제후 7명 서명 접수"},
          DECOY:  {"satisfied": True,  "evidence": [f(9)],  "note": "제후 8명 서명 접수"}},
    "4": {ANSWER: {"satisfied": True,  "evidence": [f(4), f(12)],
                   "note": "자격 인정 확인서 + 파문 명부 부재"},
          DECOY:  {"satisfied": False, "evidence": [f(11)], "note": "성별식 자격 정지"}},
}

# ── 독립 교정 48사례 ─────────────────────────────────────────────────────────
# (fact 번호, 문장, 기대 상태, 기대 플래그, 관계 관여)
CAL = [
    (1, "궁정 명부에는 베스카가 선왕의 유일한 친딸로 올라 있다", "exact", [], True),
    (1, "명부 기록상 선왕의 친자녀는 베스카 하나뿐이다", "faithful", [], True),
    (1, "베스카는 선왕의 딸이다", "partial", ["source_dropped"], True),
    (1, "궁정 명부에는 아르넬이 선왕의 유일한 친아들로 올라 있다", "contradicted",
     ["wrong_subject"], True),

    (2, "궁정 연대기는 베스카 열아홉, 아르넬 열여섯으로 적고 있다", "exact", [], True),
    (2, "연대기 기록은 두 사람을 각각 19세와 16세로 남겼다", "faithful", [], True),
    (2, "연대기에 베스카는 열아홉으로 적혀 있다", "partial", [], True),
    (2, "연대기는 아르넬을 스물하나로 적었다", "contradicted", ["wrong_value"], True),

    (3, "아르넬의 서신이 두 달째 회신을 못 받았다는 말이 돈다", "exact", [], True),
    (3, "아르넬이 제후들에게 보낸 편지에 두 달 동안 답이 없다는 소문이 있다", "faithful", [], True),
    (3, "제후들은 아르넬의 서신에 두 달째 답하지 않았다", "contradicted",
     ["modality_strengthening"], True),
    (3, "제후들이 답하지 않았으므로 아르넬은 지지를 잃었다", "contradicted",
     ["modality_strengthening", "unsupported_causal_link"], True),

    (4, "대주교청은 아르넬에게 성별식 자격을 인정한다는 확인서를 발급했다", "exact", [], True),
    (4, "아르넬은 대주교청으로부터 성별식 자격 인정 문서를 받았다", "faithful", [], True),
    (4, "대주교청은 아르넬의 자격을 거부하지는 않았다", "contradicted",
     ["modality_weakening"], True),
    (4, "대주교청은 두 후보 모두에게 자격 인정 확인서를 발급했다", "contradicted",
     ["wrong_object"], True),

    (5, "선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다", "exact", [], True),
    (5, "인장이 찍힌 계승 서약서에 오른 이름은 아르넬뿐이다", "faithful", [], True),
    (5, "서약서에 아르넬의 이름이 있다", "partial", [], True),
    (5, "계승 서약서에는 베스카의 이름도 인장과 함께 올라 있다", "contradicted",
     ["polarity_flip"], True),

    (6, "베스카는 부모의 정식 혼인 전에 태어나 적자 표기가 취소됐다", "faithful", [], True),
    (6, "기록상 베스카는 생모와 선왕이 혼인하기 전에 난 소생이며 적자 표기가 지워졌다",
     "exact", [], True),
    (6, "베스카의 생모가 혼인 전 소생이라 생모의 적자 표기가 취소됐다", "contradicted",
     ["wrong_subject"], True),
    (6, "베스카의 적자 표기가 취소됐다", "partial", [], True),

    (7, "아르넬의 세례 기록이 출생을 다섯 해 앞서 적어 실제 나이는 스물하나다", "exact", [], True),
    (7, "세례부가 5년 이르게 기록돼 아르넬은 실제로 21세다", "faithful", [], True),
    (7, "아르넬은 스물한 살이다", "partial", [], True),
    (7, "아르넬의 세례 기록은 출생을 다섯 해 늦게 적었다", "contradicted", ["polarity_flip"], True),

    (8, "베스카가 스무 살 성년이 되는 것은 이듬해 파종제 이후다", "exact", [], True),
    (8, "베스카는 내년 파종제가 지나야 성년 20세에 이른다", "faithful", [], True),
    (8, "베스카는 아직 미성년이다", "partial", [], True),
    (8, "베스카는 이미 성년에 이르렀다", "contradicted", ["polarity_flip"], True),

    (9, "베스카를 지지한 제후 여덟의 서명이 봉인되어 대주교청에 접수됐다", "exact", [], True),
    (9, "제후 8명이 베스카 지지 서명을 봉인해 대주교청에 냈다", "faithful", [], True),
    (9, "베스카를 지지하는 제후들이 있다", "partial", ["source_dropped"], True),
    (9, "봉인된 것은 제후들이 강요당했다는 뜻이다", "absent",
     ["unsupported_causal_link"], True),

    (10, "아르넬을 지지한 제후 일곱의 서명이 봉인되어 대주교청에 접수됐다", "exact", [], True),
    (10, "제후 7명이 아르넬 지지 서명을 봉인해 대주교청에 제출했다", "faithful", [], True),
    (10, "아르넬을 지지한 제후는 넷뿐이라 정족수에 못 미친다", "contradicted",
     ["wrong_value", "polarity_flip"], True),
    (10, "아르넬도 제후들의 서명을 받았다", "partial", [], True),

    (11, "베스카는 세 해 전 이단 재판에 연루돼 성별식 자격이 정지됐다", "exact", [], True),
    (11, "3년 전 이단 재판에 얽혀 베스카의 성별식 자격이 효력을 잃었다", "faithful", [], True),
    (11, "베스카는 이단 재판으로 파문됐다", "contradicted", ["condition_relabeling"], True),
    (11, "베스카의 성별식 자격이 정지된 적이 있다", "partial", [], True),

    (12, "아르넬의 이름은 대주교청 파문 명부 어디에도 없다", "exact", [], True),
    (12, "파문 명부를 뒤져도 아르넬은 나오지 않는다", "faithful", [], True),
    (12, "파문 명부에 없으니 대주교청이 아르넬의 자격을 인정한 것이다", "absent",
     ["modality_strengthening"], True),
    (12, "아르넬의 이름이 파문 명부에 올라 있다", "contradicted", ["polarity_flip"], True),
]


def main() -> None:
    material = paths.facts(IID)
    if not material.exists():
        raise SystemExit(f"재료가 없다: {material} — build_issue_throne_v2.py 를 먼저 돌려라")
    texts = {x["fact_id"]: x["text"]
             for x in json.loads(material.read_text(encoding="utf-8"))["facts"]}

    # 명세의 원 명제가 재료 문면과 어긋나면 여기서 죽는다.
    bad = [k for k, v in FACTS_SPEC.items() if texts.get(k) != v["proposition"]]
    if bad:
        raise SystemExit(f"명세의 proposition 이 재료 text 와 다르다: {bad}")
    if set(FACTS_SPEC) != set(texts):
        raise SystemExit("명세 fact_id 집합이 재료와 다르다")

    spec = {
        "issue_id": IID, "spec_id": SPEC_ID, "spec_version": SPEC_VERSION,
        "material_sha256": sha256_of(material),
        "calibration_version": CALIBRATION_VERSION,
        "lexical_is_primary": False,
        "_note": ("시나리오가 소유하는 의미 판독 계약. lexical_probes 는 후보 span 탐색·"
                  "누출 검사용 보조지표이며 의미 보존 판정에 쓰지 않는다. "
                  "정본: THRONE_CANONICAL_DECISIONS.md (요한 승인 2026-08-20, A/A/A)."),
        "candidates": [ANSWER, DECOY],
        "requirements": REQUIREMENTS,
        "facts": FACTS_SPEC,
    }
    cal = {
        "issue_id": IID, "version": CALIBRATION_VERSION, "spec_version": SPEC_VERSION,
        "_note": ("파일럿 출력을 보지 않고 원 명제에서 새로 쓴 사례다. 관측 출력으로 규칙을 "
                  "만들고 같은 출력에서 성능을 주장하지 않기 위한 계보 분리다."),
        "cases": [
            {"case_id": f"cal_{n:02d}_{i}", "fact_id": f(n), "text": text,
             "expected_status": status, "expected_flags": flags,
             "expected_relation_engaged": rel,
             "provenance_class": "independent-from-observed-output"}
            for i, (n, text, status, flags, rel) in enumerate(CAL, 1)
        ],
    }

    out = paths.detection_spec(IID)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.calibration_set(IID).write_text(
        json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8")

    per_fact = {}
    for c in cal["cases"]:
        per_fact.setdefault(c["fact_id"], []).append(c["expected_status"])
    print(f"[생성] {out.name} · {paths.calibration_set(IID).name}")
    print(f"  팩트 {len(FACTS_SPEC)} · 교정 사례 {len(cal['cases'])} · 재료 해시 "
          f"{spec['material_sha256'][:12]}…")
    thin = [k for k, v in per_fact.items() if len(v) < 4]
    print(f"  팩트당 사례 4개: {'전부' if not thin else f'미달 {thin}'}")


if __name__ == "__main__":
    main()
