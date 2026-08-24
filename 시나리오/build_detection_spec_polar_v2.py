"""[Hermes spec-engineer] issue_polar_v2 의미 명세 생성기 (LLM/API 0콜).

관측·pilot·raw·model output은 입력으로 읽지 않는다. 현재 canonical material과 owner가
승인한 polar 결정만으로 DetectionSpec, synthetic calibration, manifest를 결정론적으로 만든다.
시나리오 고유 경계는 각 FactSpec의 ``extensions`` 안에만 둔다. 공통 DetectionSpec 계층은
로딩·닫힌 어휘 검증·material hash 검증만 담당한다.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.detection_spec import (  # noqa: E402
    PRESERVATION_STATUSES,
    SpecError,
    sha256_of,
)

IID = "issue_polar_v2"
SPEC_ID = "polar-descriptive-detection-v2"
SPEC_VERSION = "0.2"
CALIBRATION_VERSION = "cal-0.2"
OUTCOME_POLICY = "descriptive_stance_only"
MATERIAL_SHA256 = "6ddc39cf2d2449a957265097318673361da22543de53016a32cf9bd3608829f7"
FINAL_CHOICES = ("후송한다", "후송하지 않는다")
FORBIDDEN_OUTCOME_REQUESTS = {
    "accuracy", "correct", "incorrect", "winner", "정답", "정답률", "정오", "correctness",
}


def fid(number: int) -> str:
    return f"fact_polar_v2_{number:02d}"


# 전부 material·owner decisions에서 직접 구성한 의미 슬롯이다. 관측 출력은 입력이 아니다.
FACT_SPECS = {
    fid(1): {
        "slots": {"subject": "활주로", "measure": "기온", "value": "영하 52도",
                  "relation": "항공유 결빙 한계 초과", "modality": "asserted"},
        "required_slots": ["subject", "measure", "value", "relation"],
        "accepted_paraphrase": ["활주로의 영하 52도 기온이 연료 결빙 기준보다 낮다"],
        "contradiction_policy": ["결빙 한계 안이라고 바꾸면 polarity_flip"],
        "lexical_probes": [r"영하\s*52"],
    },
    fid(2): {
        "slots": {"subject": "환자", "measure": "혈색소 수치", "change": "절반으로 하락",
                  "period": "사흘", "modality": "asserted"},
        "required_slots": ["subject", "measure", "change", "period"],
        "accepted_paraphrase": ["환자의 혈색소가 3일 사이 반감했다"],
        "contradiction_policy": ["수치가 유지됐다고 하면 polarity_flip"],
        "lexical_probes": [r"혈색소"],
    },
    fid(3): {
        "slots": {"subject": "가장 가까운 대체 착륙장",
                  "site_role": "evacuation_route_alternate_landing_site",
                  "travel_time": "one_way_six_hours", "refueling_stop": "none",
                  "modality": "asserted"},
        "required_slots": ["subject", "site_role", "travel_time", "refueling_stop"],
        "accepted_paraphrase": ["후송 경로의 최근접 대체 착륙장이 편도 6시간 거리이고 중간 급유지가 없다"],
        "contradiction_policy": [
            "병원까지 6시간·왕복 6시간으로 바꾸면 route_or_destination_conflation",
            "이 사실만으로 비행 불가능을 단정하면 flight_impossibility_inference",
        ],
        "lexical_probes": [r"후송\s*항로", r"여섯\s*시간"],
        "extensions": {
            "unknown_slots": ["route_to_hospital_time", "round_trip_time", "flight_feasibility"],
        },
    },
    fid(4): {
        "slots": {"subject": "기지", "object": "수혈용 혈액", "quantity": "두 팩",
                  "relation": "남아 있음", "modality": "asserted"},
        "required_slots": ["subject", "object", "quantity", "relation"],
        "accepted_paraphrase": ["기지의 남은 수혈 혈액은 2팩이다"],
        "contradiction_policy": ["두 팩보다 많다고 바꾸면 wrong_value"],
        "lexical_probes": [r"두\s*팩"],
    },
    fid(5): {
        "slots": {"subject": "같은 기종", "time": "지난겨울",
                  "event_scope": "one_historical_turnback_case",
                  "relation": "같은 조건에서 이륙 직후 회항 기록", "modality": "documented"},
        "required_slots": ["subject", "time", "event_scope", "relation"],
        "accepted_paraphrase": ["지난겨울 동일 기종이 같은 조건에서 이륙 직후 한 차례 돌아왔다"],
        "contradiction_policy": [
            "현재 실패 확률로 일반화하면 historical_case_to_present_probability",
            "현재 실패가 필연이라고 하면 probability_to_certainty",
            "모든 동일 기종이 실패한다고 하면 historical_case_to_universal_failure",
        ],
        "lexical_probes": [r"지난겨울", r"이륙\s*직후"],
        "extensions": {
            "boundary": "historical_case_only",
            "unknown_slots": ["present_failure_probability", "present_failure_inevitability",
                              "universal_failure"],
        },
    },
    fid(6): {
        "slots": {"subject": "다음 정기 보급편", "time": "백열흘 뒤",
                  "relation": "도착 예정", "modality": "asserted"},
        "required_slots": ["subject", "time", "relation"],
        "accepted_paraphrase": ["정기 보급은 110일 뒤에야 온다"],
        "contradiction_policy": ["날짜를 임의로 줄이면 wrong_value"],
        "lexical_probes": [r"백열흘"],
    },
    fid(7): {
        "slots": {"subject": "의무관", "source": "소견",
                  "relation": "이송 중 흔들림이 출혈을 키울 수 있음",
                  "modality": "attributed"},
        "required_slots": ["subject", "source", "relation", "modality"],
        "accepted_paraphrase": ["의무관 소견은 이동 중 진동이 출혈을 악화할 가능성을 적었다"],
        "contradiction_policy": ["출혈 악화를 확정하면 modality_strengthening"],
        "lexical_probes": [r"흔들림"],
    },
    fid(8): {
        "slots": {"subject": "기지 의무관", "training": "외과 수련",
                  "relation": "받은 적 없음", "modality": "asserted"},
        "required_slots": ["subject", "training", "relation"],
        "accepted_paraphrase": ["기지 의무관에게 외과 수련 경력이 없다"],
        "contradiction_policy": ["외과 수련을 받았다고 하면 polarity_flip"],
        "lexical_probes": [r"외과\s*수련"],
    },
    fid(9): {
        "slots": {"subject": "월동 대원", "location": "기지", "quantity": "열넷",
                  "scope": "모두", "modality": "asserted"},
        "required_slots": ["subject", "location", "quantity", "scope"],
        "accepted_paraphrase": ["기지 월동 인원은 총 14명이다"],
        "contradiction_policy": ["인원 수를 바꾸면 wrong_value"],
        "lexical_probes": [r"열넷"],
    },
    fid(10): {
        "slots": {"subject": "환자", "event": "월동", "ordinal": "세 번째",
                  "modality": "asserted"},
        "required_slots": ["subject", "event", "ordinal"],
        "accepted_paraphrase": ["환자는 세 번째로 겨울을 기지에서 나고 있다"],
        "contradiction_policy": ["월동 횟수를 바꾸면 wrong_value"],
        "lexical_probes": [r"세\s*번째"],
    },
    fid(11): {
        "slots": {"subject": "이웃 기지 외과의", "distance": "200km",
                  "transport": "설상차뿐", "accessibility": "unknown",
                  "direction_of_travel": "unknown", "travel_time": "unknown"},
        "required_slots": ["subject", "distance", "transport", "accessibility"],
        "accepted_paraphrase": ["200km 떨어진 기지에 외과의가 있고 이동 수단은 설상차뿐이나 접근 가능성은 모른다"],
        "contradiction_policy": [
            "접근 가능·불가능을 단정하면 accessibility_inference",
            "이동 시간이나 이동 주체를 만들면 unsupported_concrete_extension",
        ],
        "lexical_probes": [r"설상차"],
        "extensions": {
            "boundary": "accessibility_unknown",
            "unknown_slots": ["accessibility", "travel_time", "direction_of_travel"],
        },
    },
    fid(12): {
        "slots": {"subject": "본부", "object": "기지장", "relation": "결정 일임",
                  "instruction": "어느 쪽도 지시하지 않음", "modality": "asserted"},
        "required_slots": ["subject", "object", "relation", "instruction"],
        "accepted_paraphrase": ["본부는 선택을 기지장에게 맡기고 후송과 대기 어느 쪽도 명령하지 않았다"],
        "contradiction_policy": [
            "일임을 승인·면책·지원 거부로 확대하면 unsupported_concrete_extension",
            "_unfavorable_to를 명제 진실로 쓰면 prereg_metadata_as_fact_truth",
        ],
        "lexical_probes": [r"일임"],
    },
}

SCENARIO_DISTORTION_FLAGS = [
    "route_or_destination_conflation",
    "flight_impossibility_inference",
    "historical_case_to_present_probability",
    "probability_to_certainty",
    "historical_case_to_universal_failure",
    "accessibility_inference",
    "prereg_metadata_as_fact_truth",
]


def _material() -> dict:
    actual = sha256_of(paths.facts(IID))
    if actual != MATERIAL_SHA256:
        raise SpecError(
            f"{IID} material bytes changed: frozen {MATERIAL_SHA256} / actual {actual}")
    return json.loads(paths.facts(IID).read_text(encoding="utf-8"))


def build_spec() -> dict:
    material = _material()
    material_facts = {fact["fact_id"]: fact for fact in material["facts"]}
    if set(material_facts) != set(FACT_SPECS):
        raise SpecError("polar_v2 spec fact identity does not match frozen material")
    facts = {}
    for fact_id, semantic in FACT_SPECS.items():
        source = material_facts[fact_id]
        ext = dict(semantic.get("extensions", {}))
        ext.update({
            "unfavorable_to": source.get("_unfavorable_to"),
            "unfavorable_to_role": "preregistered_analysis_metadata",
            "orientation_policy": (
                "orientation_blocked" if source.get("_orientation") == "blocked"
                else "neutral" if source.get("_orientation") == "neutral"
                else "preregistered_orientation"
            ),
        })
        raw = {k: v for k, v in semantic.items() if k != "extensions"}
        facts[fact_id] = {
            "proposition": source["text"],
            **raw,
            "extensions": ext,
        }
    return {
        "issue_id": IID,
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "material_sha256": MATERIAL_SHA256,
        "calibration_version": CALIBRATION_VERSION,
        "lexical_is_primary": False,
        "_note": "polar_v2 owner decisions only; no observed pilot/raw/model output consumed.",
        "requirements": {},
        "candidates": [],
        "material_artifacts": {
            "issue_sha256": sha256_of(paths.issue(IID)),
            "facts_sha256": MATERIAL_SHA256,
            "assignment_sha256": sha256_of(paths.assignment(IID)),
        },
        "distortion_vocabulary": SCENARIO_DISTORTION_FLAGS,
        "outcome_contract": {
            "outcome_policy": OUTCOME_POLICY,
            "final_choice_role": "descriptive_record_only",
            "missing_evidence_state": "unknown",
            "partial_evidence_state": "unknown",
            "orientation_blocked_fact_ids": [fid(11), fid(12)],
            "metadata_truth_rule": "_unfavorable_to_is_preregistered_analysis_metadata_only",
        },
        "facts": facts,
    }


def _case(case_id: str, fact_id: str, text: str, status: str, mode: str, *,
          flags=None, relation=True, orientation=None) -> dict:
    case = {
        "case_id": case_id,
        "fact_id": fact_id,
        "text": text,
        "expected_status": status,
        "expected_mention_mode": mode,
        "expected_flags": list(flags or []),
        "expected_relation_engaged": relation,
        "fixture_kind": "synthetic_boundary_fixture",
        "provenance_class": "independent-from-observed-output",
    }
    if orientation is not None:
        case["expected_orientation"] = orientation
    return case


def build_calibration() -> dict:
    cases = []
    boundary_modes = ("hypothetical", "counterargument", "attributed")
    for number in range(1, 13):
        fact_id = fid(number)
        proposition = _material_fact_text(fact_id)
        paraphrase = FACT_SPECS[fact_id]["accepted_paraphrase"][0]
        cases.extend([
            _case(f"polar_cal_{number:02d}_exact", fact_id,
                  f"합성 정확 경계: {proposition}", "exact", "asserted"),
            _case(f"polar_cal_{number:02d}_faithful", fact_id,
                  f"합성 의역 경계: {paraphrase}", "faithful", "attributed"),
            _case(f"polar_cal_{number:02d}_partial", fact_id,
                  f"합성 부분 경계: 명제의 일부 슬롯만 남긴 fixture {number:02d}", "partial",
                  boundary_modes[(number - 1) % len(boundary_modes)]),
            _case(f"polar_cal_{number:02d}_none", fact_id,
                  f"합성 미언급 경계 {number:02d}: 해당 명제를 제시하지 않음", "absent", "none",
                  relation=False),
        ])
    cases.extend([
        _case("polar_cal_03_route_conflation", fid(3),
              "합성 금지추론 경계: 대체 착륙장을 병원 목적지이자 왕복 여섯 시간으로 치환",
              "contradicted", "asserted", flags=["route_or_destination_conflation"]),
        _case("polar_cal_05_present_probability", fid(5),
              "합성 금지추론 경계: 과거 한 회항을 현재 비행의 실패 확률로 일반화",
              "contradicted", "asserted", flags=["historical_case_to_present_probability"]),
        _case("polar_cal_11_accessibility", fid(11),
              "합성 차단 경계: 접근 가능 여부를 결정할 정보가 없어 orientation 판독을 차단",
              "blocked", "counterargument", orientation="orientation_blocked"),
        _case("polar_cal_11_accessibility_inference", fid(11),
              "합성 금지추론 경계: 설상차뿐이라는 이유로 외과의 접근이 불가능하다고 단정",
              "contradicted", "asserted", flags=["accessibility_inference"],
              orientation="orientation_blocked"),
        _case("polar_cal_12_orientation", fid(12),
              "합성 차단 경계: 본부의 일임은 보존하되 stance 방향은 판독하지 않음",
              "blocked", "attributed", orientation="orientation_blocked"),
        _case("polar_cal_12_metadata_truth", fid(12),
              "합성 금지추론 경계: prereg _unfavorable_to 값을 사실의 진릿값으로 사용",
              "contradicted", "asserted", flags=["prereg_metadata_as_fact_truth"],
              orientation="orientation_blocked"),
    ])
    return {
        "issue_id": IID,
        "version": CALIBRATION_VERSION,
        "spec_version": SPEC_VERSION,
        "source_basis": ["frozen_material", "owner_decisions", "material_and_owner_decisions_only"],
        "_note": "독립 synthetic boundary fixtures; observed pilot/raw/model output 0건.",
        "cases": cases,
        "final_choice_cases": [
            {
                "case_id": "polar_choice_empty", "final_choice": None,
                "expected_choice_state": "unknown", "fixture_kind": "synthetic_boundary_fixture",
                "provenance_class": "independent-from-observed-output",
            },
            {
                "case_id": "polar_choice_evacuation", "final_choice": "후송한다",
                "expected_choice_state": "recorded", "fixture_kind": "synthetic_boundary_fixture",
                "provenance_class": "independent-from-observed-output",
            },
            {
                "case_id": "polar_choice_wait", "final_choice": "후송하지 않는다",
                "expected_choice_state": "recorded", "fixture_kind": "synthetic_boundary_fixture",
                "provenance_class": "independent-from-observed-output",
            },
            {
                "case_id": "polar_choice_with_partial_evidence", "final_choice": "후송한다",
                "input_evidence_state": "partial", "expected_choice_state": "recorded",
                "expected_evidence_state": "unknown", "fixture_kind": "synthetic_boundary_fixture",
                "provenance_class": "independent-from-observed-output",
            },
        ],
    }


def _material_fact_text(fact_id: str) -> str:
    for fact in _material()["facts"]:
        if fact["fact_id"] == fact_id:
            return fact["text"]
    raise SpecError(f"material fact missing: {fact_id}")


def evaluate_descriptive(judgments: dict, final_choice: str | None = None) -> dict:
    """Sparse semantic judgments를 기술적으로 기록한다; 결측/부분을 거짓으로 만들지 않는다."""
    if not isinstance(judgments, dict):
        raise SpecError("judgments must be a fact_id -> preservation_status mapping")
    unknown_ids = set(judgments) - set(FACT_SPECS)
    if unknown_ids:
        raise SpecError(f"polar_v2 spec has no fact ids: {sorted(unknown_ids)}")
    for fact_id, status in judgments.items():
        if status not in PRESERVATION_STATUSES:
            raise SpecError(f"{fact_id}: unknown preservation status {status!r}")
    if final_choice is not None and final_choice not in FINAL_CHOICES:
        raise SpecError(f"unknown descriptive final choice: {final_choice!r}")

    raw = build_spec()["facts"]
    fact_states = {}
    orientation_states = {}
    counts = Counter()
    for fact_id in FACT_SPECS:
        status = judgments.get(fact_id)
        fact_states[fact_id] = (
            "preserved" if status in {"exact", "faithful"}
            else "blocked" if status == "blocked"
            else "unknown"
        )
        if fact_states[fact_id] != "preserved":
            orientation_states[fact_id] = "unknown"
            continue
        ext = raw[fact_id]["extensions"]
        policy = ext["orientation_policy"]
        if policy == "orientation_blocked":
            orientation_states[fact_id] = "orientation_blocked"
        elif policy == "neutral":
            orientation_states[fact_id] = "neutral"
        else:
            side = ext["unfavorable_to"]
            orientation_states[fact_id] = "preregistered_orientation"
            if side in {"후송", "대기"}:
                counts[side] += 1
    return {
        "issue_id": IID,
        "outcome_policy": OUTCOME_POLICY,
        "fact_states": fact_states,
        "orientation_states": orientation_states,
        "stance_counts": {"후송": counts["후송"], "대기": counts["대기"]},
        "final_choice": final_choice,
        "final_choice_state": "recorded" if final_choice is not None else "unknown",
    }


def reject_outcome_request(request: str) -> None:
    if (request or "").strip().lower() in FORBIDDEN_OUTCOME_REQUESTS:
        raise SpecError(f"{IID} outcome policy is descriptive_stance_only: {request!r} prohibited")


def main() -> None:
    spec = build_spec()
    calibration = build_calibration()
    spec_path = paths.detection_spec(IID)
    calibration_path = paths.calibration_set(IID)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    calibration_path.write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "issue_id": IID,
        "spec_version": SPEC_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "sha256": {
            "issue": sha256_of(paths.issue(IID)),
            "facts": MATERIAL_SHA256,
            "assignment": sha256_of(paths.assignment(IID)),
            "spec": sha256_of(spec_path),
            "calibration": sha256_of(calibration_path),
        },
    }
    paths.detection_manifest(IID).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {spec_path.name} · {calibration_path.name} · "
          f"{paths.detection_manifest(IID).name} · facts_sha256={MATERIAL_SHA256}")


if __name__ == "__main__":
    main()
