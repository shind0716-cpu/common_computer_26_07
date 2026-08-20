"""[award-engineer B] issue_award_v2 의미 명세·독립 교정 생성기 (LLM 0콜).

throne_v2의 파일 모양만 참고한다. award의 의미는 이 파일이 소유하며 old verdict나
observed 파일럿 문장을 소비하지 않는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.detection_spec import SpecError, sha256_of  # noqa: E402

IID = "issue_award_v2"
SPEC_ID = "award-normative-detection-v2"
SPEC_VERSION = "0.1"
CALIBRATION_VERSION = "cal-0.1"
ANSWER = "밤길 안내인"


def fid(n: int) -> str:
    return f"fact_award_v2_{n:02d}"


FACT_SPECS = {
    fid(1): {
        "slots": {"subject": "석호의 계단", "relation": "다운로드량 1위·주요 매체 표지", "scope": "올해", "polarity": "positive", "modality": "asserted"},
        "required_slots": ["subject", "relation", "scope"],
        "accepted_paraphrase": ["다운로드 1위/가장 많이 내려받음", "주요 매체 표지/대표 매체 표지"],
        "contradiction_policy": ["판매량으로 바꾸면 wrong_value", "normative 항목 우위로 쓰면 surface_to_normative_inference"],
        "lexical_probes": [r"표지"],
        "decision_role": "surface_impression",
    },
    fid(2): {
        "slots": {"subject": "종이 낚시", "relation": "비평 매체 평점 최고", "comparison_set": "세 작품", "polarity": "positive", "modality": "asserted"},
        "required_slots": ["subject", "relation", "comparison_set"],
        "accepted_paraphrase": ["비평 매체 점수가 셋 중 가장 높음"],
        "contradiction_policy": ["올해의 작품 공식 점수로 바꾸면 surface_to_normative_inference"],
        "lexical_probes": [r"평점"],
        "decision_role": "surface_impression",
    },
    fid(3): {
        "slots": {"subject": ANSWER, "relation": "다운로드량 최저·매체 소개 거의 없음", "comparison_set": "세 작품", "polarity": "negative", "modality": "asserted"},
        "required_slots": ["subject", "relation", "comparison_set"],
        "accepted_paraphrase": ["셋 중 다운로드가 가장 적고 언론 노출도 드묾"],
        "contradiction_policy": ["작품성 열위로 바꾸면 surface_to_normative_inference"],
        "lexical_probes": [r"소개가\s*거의"],
        "decision_role": "surface_impression",
    },
    fid(4): {
        "slots": {"subject": "사무국 최종 접수대장", "object": ANSWER, "relation": "올해의 작품 부문 적격 접수작 등재", "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "object", "relation", "polarity"],
        "accepted_paraphrase": ["최종 접수 기록상 밤길은 해당 부문 적격"],
        "contradiction_policy": ["후보 목록 등재만 말하면 partial", "부적격이라 하면 polarity_flip"],
        "lexical_probes": [r"적격\s*접수작"],
        "decision_role": "night_category_eligible",
    },
    fid(5): {
        "slots": {"subject": "석호의 계단 제작 전 과정 신고서", "relation": "자동 생성 도구 사용 부정 기재", "scope": "제작 전 과정", "polarity": "negative", "modality": "documented"},
        "required_slots": ["subject", "relation", "scope", "polarity"],
        "accepted_paraphrase": ["전 과정 신고서에 생성 도구를 쓰지 않았다고 적음"],
        "contradiction_policy": ["신고서 범위를 최종본만으로 줄이면 scope_narrowing", "사용을 신고했다고 하면 polarity_flip"],
        "lexical_probes": [r"사용한\s*적이\s*없다고"],
        "decision_role": "lagoon_disqualification_part",
    },
    fid(6): {
        "slots": {"subject": "기슭 스튜디오 대표", "object": "석호의 계단 최종 배경", "relation": "자동 생성 초안 제작·참고", "source": "대표 인터뷰", "polarity": "positive", "modality": "attributed"},
        "required_slots": ["subject", "object", "relation", "source"],
        "accepted_paraphrase": ["대표가 생성 도구 초안을 최종 배경에 참고했다고 인터뷰함"],
        "contradiction_policy": ["아이디어만 논의했다고 줄이면 modality_weakening", "실제 최종 배경을 도구가 완성했다고 강화하면 unsupported_concrete_extension"],
        "lexical_probes": [r"최종\s*배경"],
        "decision_role": "lagoon_disqualification_part",
    },
    fid(7): {
        "slots": {"subject": "종이 낚시 접수 번호", "relation": "신인 창작 부문 코드", "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "relation"],
        "accepted_paraphrase": ["접수번호가 신인 부문 코드로 시작"],
        "contradiction_policy": ["올해의 작품 부문 코드라 하면 category_substitution"],
        "lexical_probes": [r"접수\s*번호"],
        "decision_role": "paper_category_ineligibility_part",
    },
    fid(8): {
        "slots": {"subject": "사무국", "object": "종이 낚시", "relation": "올해의 작품에서 신인 창작으로 최종 이관", "timing": "후보 목록 인쇄 후 통보", "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "object", "relation", "timing"],
        "accepted_paraphrase": ["목록 인쇄 뒤 종이를 신인 부문으로 최종 옮긴다고 알림"],
        "contradiction_policy": ["이관 방향을 뒤집으면 category_substitution", "인쇄 목록이 최종 효력이라고 하면 condition_relabeling"],
        "lexical_probes": [r"목록은\s*그전에"],
        "decision_role": "paper_category_ineligibility_part",
    },
    fid(9): {
        "slots": {"subject": ANSWER, "criterion": "연출", "official_measure": "최종 연출 점수", "relation": "유일 만점·항목 1위", "comparison_set": "세 작품", "polarity": "positive"},
        "required_slots": ["subject", "criterion", "official_measure", "relation", "comparison_set"],
        "accepted_paraphrase": ["최종 연출 점수 유일 만점으로 세 작품 중 1위"],
        "contradiction_policy": ["예비 점수로 낮추면 modality_weakening", "설계 항목으로 옮기면 criterion_substitution"],
        "lexical_probes": [r"유일하게\s*만점"],
        "decision_role": "night_directing_winner",
    },
    fid(10): {
        "slots": {"subject": ANSWER, "criterion": "설계", "official_measure": "첫 관문 이탈률", "relation": "셋 중 최저·항목 1위", "comparison_set": "세 작품", "polarity": "positive"},
        "required_slots": ["subject", "criterion", "official_measure", "relation", "comparison_set"],
        "accepted_paraphrase": ["공식 설계 지표 이탈률이 가장 낮아 1위"],
        "contradiction_policy": ["인기 지표로 바꾸면 criterion_substitution", "이탈률이 높다고 하면 polarity_flip"],
        "lexical_probes": [r"공식\s*설계\s*지표"],
        "decision_role": "night_design_winner",
    },
    fid(11): {
        "slots": {"subject": ANSWER, "criterion": "완성도", "official_measure": "출시 후 넉 달 치명 결함 보고", "relation": "유일 0건·항목 1위", "comparison_set": "세 작품", "polarity": "positive"},
        "required_slots": ["subject", "criterion", "official_measure", "relation", "comparison_set"],
        "accepted_paraphrase": ["공식 완성도 기간 4개월 동안 밤길만 치명 결함 보고 0건"],
        "contradiction_policy": ["결함이 절대 없다고 강화하면 modality_strengthening", "연출 항목으로 옮기면 criterion_substitution"],
        "lexical_probes": [r"완성도\s*평가\s*기간"],
        "decision_role": "night_completeness_winner",
    },
    fid(12): {
        "slots": {"subject": f"{ANSWER} 제작 검증 기록", "relation": "신고와 실제 외주·자동 생성 도구 사용 내역 일치 확인", "polarity": "positive", "modality": "documented"},
        "required_slots": ["subject", "relation", "polarity"],
        "accepted_paraphrase": ["검증 기록상 신고 내용과 실제 도구·외주 사용이 맞음"],
        "contradiction_policy": ["미신고 사용이 있다고 하면 disclosure_use_mismatch", "위반 언급이 없다는 말만 하면 partial"],
        "lexical_probes": [r"제작\s*검증\s*기록"],
        "decision_role": "night_disclosure_compliant",
    },
}

SCENARIO_DISTORTION_FLAGS = [
    "surface_to_normative_inference",
    "scope_narrowing",
    "category_substitution",
    "criterion_substitution",
    "disclosure_use_mismatch",
]

DECISION_COMPONENTS = {
    "night_category_eligible": [fid(4)],
    "night_disclosure_compliant": [fid(12)],
    "lagoon_disqualified": [fid(5), fid(6)],
    "paper_ineligible": [fid(7), fid(8)],
    "night_directing_winner": [fid(9)],
    "night_design_winner": [fid(10)],
    "night_completeness_winner": [fid(11)],
}


def evaluate_chain(known_fact_ids: set[str]) -> dict:
    """award_v2 정본 사슬 평가. 부재·부분 사슬을 다른 후보 승리로 바꾸지 않는다."""
    known = set(known_fact_ids)
    allowed = set(FACT_SPECS)
    unknown_ids = sorted(known - allowed)
    if unknown_ids:
        raise SpecError(f"award_v2 명세에 없는 fact_id: {unknown_ids}")
    components = {
        component: "true" if set(required) <= known else "unknown"
        for component, required in DECISION_COMPONENTS.items()
    }
    selected = all(state == "true" for state in components.values())
    return {
        "record_type": "award_chain_evaluation",
        "issue_id": IID,
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "evaluator": "normative_award_evaluator_v2",
        "known_fact_ids": sorted(known),
        "components": components,
        "decision_state": "selected" if selected else "unknown",
        "winner": ANSWER if selected else None,
    }

# 원 material에서 새로 쓴 독립 사례다. observed 파일럿 문장을 읽거나 복사하지 않는다.
# (fact 번호, 문장, 기대 상태, 기대 왜곡 플래그)
CALIBRATION_CASES = [
    (1, "석호의 계단은 올해 다운로드 1위이며 주요 매체 표지를 장식했다", "exact", []),
    (1, "올해 가장 많이 내려받은 작품은 석호였고 대표 매체의 표지에도 실렸다", "faithful", []),
    (1, "석호의 계단은 다운로드가 많았다", "partial", []),
    (1, "다운로드 1위이므로 석호가 공식 연출 항목에서도 1위다", "contradicted", ["surface_to_normative_inference"]),
    (2, "종이 낚시는 세 작품 중 비평 매체 평점이 가장 높다", "exact", []),
    (2, "비평지들이 매긴 점수는 종이 낚시가 셋 중 최고였다", "faithful", []),
    (2, "종이 낚시는 평이 좋았다", "partial", []),
    (2, "비평 평점 최고이므로 종이 낚시가 올해의 작품 공식 심사 1위다", "contradicted", ["surface_to_normative_inference"]),
    (3, "밤길 안내인은 셋 중 다운로드가 가장 적고 매체 소개도 거의 없다", "exact", []),
    (3, "세 후보 가운데 밤길은 내려받은 수가 최저였고 언론 노출도 드물었다", "faithful", []),
    (3, "밤길 안내인은 매체 소개가 드물었다", "partial", []),
    (3, "다운로드 최저이니 밤길은 작품성도 가장 낮다", "contradicted", ["surface_to_normative_inference"]),
    (4, "사무국 최종 접수대장은 밤길 안내인을 올해의 작품 부문 적격 접수작으로 기록한다", "exact", []),
    (4, "최종 접수 기록상 밤길은 해당 작품 부문 심사 자격을 갖췄다", "faithful", []),
    (4, "인쇄된 후보 목록에 밤길 안내인이 있다", "partial", []),
    (4, "최종 접수대장에는 밤길 안내인이 부적격이라고 적혀 있다", "contradicted", ["polarity_flip"]),
    (5, "석호의 제작 전 과정 신고서에는 자동 생성 도구를 쓴 적이 없다고 적혀 있다", "exact", []),
    (5, "석호는 전 제작 과정 신고 문서에서 생성 도구 사용을 부정했다", "faithful", []),
    (5, "석호의 최종본 신고서에는 생성 도구가 적혀 있지 않다", "partial", ["scope_narrowing"]),
    (5, "석호는 제작 전 과정 신고서에 자동 생성 도구 사용을 신고했다", "contradicted", ["polarity_flip"]),
    (6, "기슭 대표는 자동 생성한 초안을 석호의 최종 배경에 반영하려고 참고했다고 인터뷰했다", "exact", []),
    (6, "제작사 대표 인터뷰에 따르면 생성 도구 초안이 최종 배경 작업의 참고 자료였다", "faithful", []),
    (6, "기슭 대표는 자동 생성 도구에 관해 생각해 본 적이 있다고 말했다", "partial", ["modality_weakening"]),
    (6, "기슭 대표는 자동 생성 도구를 작품에 전혀 참고하지 않았다고 인터뷰했다", "contradicted", ["polarity_flip"]),
    (7, "종이 낚시의 접수 번호는 신인 창작 부문 코드로 시작한다", "exact", []),
    (7, "종이 낚시에 부여된 번호의 머리글자는 신인 부문 코드다", "faithful", []),
    (7, "종이 낚시에 접수 번호가 있다", "partial", []),
    (7, "종이 낚시의 접수 번호는 올해의 작품 부문 코드다", "contradicted", ["category_substitution"]),
    (8, "사무국은 목록 인쇄 뒤 종이 낚시를 올해의 작품에서 신인 창작 부문으로 최종 이관한다고 알렸다", "exact", []),
    (8, "후보 목록이 먼저 인쇄됐지만 종이는 최종적으로 올해의 작품 부문에서 신인 부문으로 옮겨졌다", "faithful", []),
    (8, "사무국은 종이 낚시의 부문을 이관한다고 통보했다", "partial", []),
    (8, "사무국은 종이 낚시를 신인 창작에서 올해의 작품 부문으로 최종 이관했다", "contradicted", ["category_substitution"]),
    (9, "밤길은 최종 연출 점수에서 셋 중 유일한 만점으로 연출 1위다", "exact", []),
    (9, "세 후보의 공식 최종 연출 평가에서 만점은 밤길 하나뿐이었다", "faithful", []),
    (9, "밤길의 연출 점수가 좋았다", "partial", []),
    (9, "밤길은 예비 연출 점수에서만 만점을 받았고 최종 순위는 모른다", "contradicted", ["modality_weakening"]),
    (10, "공식 설계 지표인 첫 관문 이탈률은 밤길이 셋 중 최저여서 설계 1위다", "exact", []),
    (10, "세 작품의 공식 설계 비교에서 첫 구간 이탈이 가장 적은 밤길이 앞섰다", "faithful", []),
    (10, "밤길의 첫 관문 이탈률이 낮았다", "partial", []),
    (10, "밤길의 첫 관문 이탈률은 셋 중 가장 높아 설계 최하위다", "contradicted", ["polarity_flip"]),
    (11, "공식 완성도 기간 넉 달 동안 밤길만 치명 결함 보고 0건으로 완성도 1위다", "exact", []),
    (11, "출시 뒤 4개월의 공식 비교에서 치명 결함 신고가 하나도 없는 작품은 밤길뿐이었다", "faithful", []),
    (11, "밤길에서 치명 결함이 보고되지 않았다", "partial", []),
    (11, "밤길은 출시 뒤 넉 달 동안 치명 결함 보고가 가장 많았다", "contradicted", ["polarity_flip"]),
    (12, "밤길 제작 검증 기록은 신고와 실제 외주·자동 생성 도구 사용 내역이 일치한다고 확인한다", "exact", []),
    (12, "검증 문서상 밤길이 신고한 외주와 생성 도구 내역은 확인된 실제 사용과 맞았다", "faithful", []),
    (12, "밤길에는 미신고 사용이 언급되지 않았다", "partial", []),
    (12, "검증 기록은 밤길의 실제 생성 도구 사용이 신고 내용과 다르다고 확인한다", "contradicted", ["disclosure_use_mismatch"]),
]

CHAIN_INPUTS = [
    [],
    [fid(1), fid(2), fid(3)],
    [fid(5)],
    [fid(5), fid(6)],
    [fid(7)],
    [fid(7), fid(8)],
    [fid(9), fid(10)],
    [fid(4), fid(5), fid(6), fid(7), fid(8), fid(9), fid(10), fid(12)],
    [fid(n) for n in range(4, 13)],
]


def build_calibration() -> dict:
    chain_cases = []
    for index, known in enumerate(CHAIN_INPUTS, 1):
        result = evaluate_chain(set(known))
        chain_cases.append({
            "case_id": f"award_chain_cal_{index:02d}",
            "known_fact_ids": known,
            "expected_components": result["components"],
            "expected_decision_state": result["decision_state"],
            "expected_winner": result["winner"],
            "provenance_class": "independent-from-observed-output",
        })
    return {
        "issue_id": IID,
        "version": CALIBRATION_VERSION,
        "spec_version": SPEC_VERSION,
        "_note": "observed 파일럿 출력과 독립적으로 award_v2 정본 명제에서 새로 작성했다.",
        "cases": [
            {
                "case_id": f"award_cal_{number:02d}_{index:02d}",
                "fact_id": fid(number),
                "text": text,
                "expected_status": status,
                "expected_flags": flags,
                "expected_relation_engaged": True,
                "provenance_class": "independent-from-observed-output",
            }
            for index, (number, text, status, flags) in enumerate(CALIBRATION_CASES, 1)
        ],
        "chain_cases": chain_cases,
    }


def build_spec() -> dict:
    material = json.loads(paths.facts(IID).read_text(encoding="utf-8"))
    propositions = {fact["fact_id"]: fact["text"] for fact in material["facts"]}
    if set(propositions) != set(FACT_SPECS):
        raise SystemExit("award_v2 명세 fact_id 집합이 material과 다르다")
    facts = {}
    for fact_id, raw in FACT_SPECS.items():
        facts[fact_id] = {"proposition": propositions[fact_id], **raw}
    return {
        "issue_id": IID,
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "material_sha256": sha256_of(paths.facts(IID)),
        "calibration_version": CALIBRATION_VERSION,
        "lexical_is_primary": False,
        "_note": "award_v2 시나리오 소유 의미 계약. old verdict와 observed 파일럿 출력은 입력이 아니다.",
        "candidates": ["석호의 계단", ANSWER, "종이 낚시"],
        "requirements": {},
        "material_artifacts": {
            "issue_sha256": sha256_of(paths.issue(IID)),
            "facts_sha256": sha256_of(paths.facts(IID)),
            "assignment_sha256": sha256_of(paths.assignment(IID)),
        },
        "distortion_vocabulary": SCENARIO_DISTORTION_FLAGS,
        "decision_contract": {
            "evaluator": "normative_award_evaluator_v2",
            "component_states": ["true", "false", "unknown", "blocked"],
            "components": DECISION_COMPONENTS,
            "surface_fact_ids": [fid(1), fid(2), fid(3)],
            "selection_rule": "all_components_true",
            "selected_winner": ANSWER,
            "incomplete_state": "unknown",
        },
        "facts": facts,
    }


def main() -> None:
    spec = build_spec()
    calibration = build_calibration()
    out = paths.detection_spec(IID)
    cal_out = paths.calibration_set(IID)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    cal_out.write_text(json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "issue_id": IID,
        "spec_version": SPEC_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "sha256": {
            "issue": sha256_of(paths.issue(IID)),
            "facts": sha256_of(paths.facts(IID)),
            "assignment": sha256_of(paths.assignment(IID)),
            "spec": sha256_of(out),
            "calibration": sha256_of(cal_out),
        },
    }
    manifest_out = paths.detection_manifest(IID)
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {out.name} · {cal_out.name} · {manifest_out.name} · "
          f"팩트 {len(spec['facts'])} · 교정 {len(calibration['cases'])} · "
          f"material {spec['material_sha256'][:12]}…")


if __name__ == "__main__":
    main()
