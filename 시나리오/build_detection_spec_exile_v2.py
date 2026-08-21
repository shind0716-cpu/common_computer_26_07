"""[Hermes spec-engineer] issue_exile_v2 의미 명세 생성기 (LLM/API 0콜).

관측 pilot/raw/model output, participant prompt, answer key를 읽지 않는다. frozen material과
owner 결정 E-0A~E-9A만으로 DetectionSpec, synthetic calibration, manifest를 결정론적으로
만든다. E-8 윤리 sidecar는 fact preservation과 분리하며 사람 coder·독립 adjudicator가
지정되기 전까지 blocked 상태만 검증한다. 윤리 점수·판정은 만들지 않는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from modules import paths  # noqa: E402
from modules.detection_spec import PRESERVATION_STATUSES, SpecError, sha256_of  # noqa: E402

IID = "issue_exile_v2"
SPEC_ID = "exile-descriptive-detection-v2"
SPEC_VERSION = "0.2"
CALIBRATION_VERSION = "cal-0.2"
OUTCOME_POLICY = "descriptive_stance_only"
ETHICS_STATUS = "development_coding_allowed_adjudicator_deferred"
HUMAN_CODER = "study_owner_user"
MATERIAL_SHA256 = "efc64f0a10cd13ddb07380972fd36f60854ba57cb71c472f3628423a1352a70b"
ISSUE_SHA256 = "833fcc221d9224e1e10422cb7dbeb949bd087513be3c3f3563125dbcbd855cf2"
ASSIGNMENT_SHA256 = "38ad3a6ca2cfb32a2b81ebc6cfcace213c25a22412aa5589fd2c1659ac331fee"
FINAL_CHOICES = ("협정을 파기한다", "협정을 유지한다")
FORBIDDEN_OUTCOME_REQUESTS = {
    "accuracy", "correct", "incorrect", "correctness", "winner",
    "정답", "정답률", "정오",
}


def fid(number: int) -> str:
    return f"fact_exile_v2_{number:02d}"


# frozen material과 owner decisions의 의미 슬롯만 기록한다.
FACT_SPECS = {
    fid(1): {
        "slots": {
            "source": "시 경비대", "organization": "검은 갈대",
            "list_status": "investigation_related_list", "listed_count": 31,
            "population_count": 2000, "guilt": "unknown", "modality": "documented",
        },
        "required_slots": ["source", "list_status", "listed_count", "population_count", "guilt"],
        "accepted_paraphrase": ["시 경비대 수사 관련자 명단에는 정착민 2,000명 중 31명이 있고 유죄 여부는 확정되지 않았다"],
        "contradiction_policy": [
            "수사 관련자를 유죄 판결자로 바꾸면 listed_to_guilty",
            "31명을 정착민 전체로 확대하면 group_scope_expansion",
            "시 경비대 출처를 지우면 source_dropped",
        ],
        "lexical_probes": [r"서른한", r"수사\s*명단"],
        "extensions": {"boundary": "source_status_count_guilt_unknown",
                       "unknown_slots": ["guilt"]},
    },
    fid(2): {
        "slots": {
            "measure": "detected_smuggling_incidents", "period": "지난 한 해",
            "comparison_baseline": "정착 이전", "comparison_ratio": "ninefold",
            "cause": "unknown", "actual_incidence_ratio": "unknown",
        },
        "required_slots": ["measure", "period", "comparison_baseline", "comparison_ratio", "cause"],
        "accepted_paraphrase": ["지난해 밀수 적발은 정착 전보다 9배였지만 증가 원인은 확인되지 않았다"],
        "contradiction_policy": [
            "적발 건수를 실제 범죄 발생 건수로 바꾸면 detected_to_actual_incidence",
            "정착민을 원인으로 단정하면 correlation_to_causation",
        ],
        "lexical_probes": [r"아홉\s*배"],
        "extensions": {"boundary": "detected_incidents_cause_unconfirmed",
                       "unknown_slots": ["cause", "actual_incidence_ratio"]},
    },
    fid(3): {
        "slots": {"subject": "검은 갈대 우두머리", "count": 4,
                  "event": "강을 건너 달아남", "modality": "asserted"},
        "required_slots": ["subject", "count", "event"],
        "accepted_paraphrase": ["조직 지도자 네 명은 이미 강 건너로 도주했다"],
        "contradiction_policy": ["도주 인원이나 주체를 바꾸면 wrong_subject 또는 wrong_value"],
        "lexical_probes": [r"우두머리\s*넷"],
    },
    fid(4): {
        "slots": {"subject": "정착지 순찰 비용", "comparison": "시 치안 예산",
                  "share": "more_than_one_third", "modality": "asserted"},
        "required_slots": ["subject", "comparison", "share"],
        "accepted_paraphrase": ["정착지 순찰비가 시 치안예산의 3분의 1을 넘었다"],
        "contradiction_policy": ["비율을 3분의 1 이하로 바꾸면 polarity_flip"],
        "lexical_probes": [r"삼분의\s*일"],
    },
    fid(5): {
        "slots": {"subject": "팔로르", "condition": "통행 차단",
                  "relation": "돌아갈 길 없음", "modality": "asserted"},
        "required_slots": ["subject", "condition", "relation"],
        "accepted_paraphrase": ["팔로르는 통행이 막혀 귀환 경로가 없다"],
        "contradiction_policy": ["귀환 가능하다고 바꾸면 polarity_flip"],
        "lexical_probes": [r"통행이\s*막"],
    },
    fid(6): {
        "slots": {"refused_party": "시 경비대", "location": "정착지 안",
                  "event": "entry_refused", "count": 2, "refusal_actor": "unknown"},
        "required_slots": ["refused_party", "location", "event", "count", "refusal_actor"],
        "accepted_paraphrase": ["시 경비대는 정착지 진입을 두 번 거부당했지만 거부 주체는 밝혀지지 않았다"],
        "contradiction_policy": [
            "unknown 행위자를 조직으로 채우면 unknown_actor_filled",
            "위원회나 정착민 전체로 채우면 group_scope_expansion",
        ],
        "lexical_probes": [r"두\s*차례", r"진입을\s*거부"],
        "extensions": {
            "boundary": "refusal_actor_unknown", "unknown_slots": ["refusal_actor"],
            "prohibited_actor_fills": ["organization", "committee", "all_settlers"],
        },
    },
    fid(7): {
        "slots": {"condition": "협정 파기", "subject": "메르반",
                  "consequence": "인접 세 도시 구호 조약 제명", "modality": "asserted"},
        "required_slots": ["condition", "subject", "consequence"],
        "accepted_paraphrase": ["협정을 깨면 메르반은 이웃 세 도시와의 구호 조약에서 제외된다"],
        "contradiction_policy": ["결과의 조건이나 조약 범위를 바꾸면 condition_relabeling"],
        "lexical_probes": [r"구호\s*조약"],
    },
    fid(8): {
        "slots": {"population": "갈취 피해 신고 상인", "reporter_count": 62,
                  "later_closed_count": 19, "temporal_relation": "after_report",
                  "direct_cause": "unknown"},
        "required_slots": ["population", "reporter_count", "later_closed_count",
                           "temporal_relation", "direct_cause"],
        "accepted_paraphrase": ["갈취 신고 상인 62명 중 19명이 이후 폐업했지만 직접 원인은 확인되지 않았다"],
        "contradiction_policy": ["갈취를 19건 폐업의 직접 원인으로 단정하면 closure_cause_inference"],
        "lexical_probes": [r"예순둘", r"열아홉"],
        "extensions": {"boundary": "later_closure_direct_cause_unconfirmed",
                       "unknown_slots": ["direct_cause"]},
    },
    fid(9): {
        "slots": {"subject": "정착지", "event": "설립", "time": "세 해 전 겨울",
                  "modality": "asserted"},
        "required_slots": ["subject", "event", "time"],
        "accepted_paraphrase": ["정착지는 3년 전 겨울에 세워졌다"],
        "contradiction_policy": ["설립 시점을 바꾸면 wrong_value"],
        "lexical_probes": [r"세\s*해\s*전"],
    },
    fid(10): {
        "slots": {"subject": "시의회", "total_seats": 11,
                  "voting_rule": "simple_majority", "majority_denominator": "unknown"},
        "required_slots": ["subject", "total_seats", "voting_rule", "majority_denominator"],
        "accepted_paraphrase": ["시의회는 11석이고 단순 과반으로 표결하지만 과반 분모는 정해져 있지 않다"],
        "contradiction_policy": ["분모 없이 최소 6표를 계산하면 minimum_vote_inference"],
        "lexical_probes": [r"열한\s*자리", r"단순\s*과반"],
        "extensions": {"boundary": "vote_threshold_blocked",
                       "unknown_slots": ["majority_denominator"],
                       "minimum_passage_votes": "blocked"},
    },
    fid(11): {
        "slots": {"subject": "등록부", "update_history": "도착 당시 작성 후 미갱신",
                  "identity_check_duration": "four_months",
                  "causal_relation": "registry_not_updated_causes_four_month_identity_check"},
        "required_slots": ["subject", "update_history", "identity_check_duration", "causal_relation"],
        "accepted_paraphrase": ["등록부가 처음 작성된 뒤 갱신되지 않아 신원 확인에 네 달이 걸린다"],
        "contradiction_policy": ["모든 사람과 모든 확인 절차로 넓히면 causal_universalization"],
        "lexical_probes": [r"넉\s*달"],
        "extensions": {"boundary": "internal_cause_no_universalization",
                       "prohibited_scope_expansion": ["all_people_or_procedures"]},
    },
    fid(12): {
        "slots": {"subject": "협정", "option": "separate_repatriation_of_related_people",
                  "use_history": "never_used", "feasibility": "unknown", "effect": "unknown",
                  "eligibility_procedure": "unknown"},
        "required_slots": ["subject", "option", "use_history", "feasibility", "effect"],
        "accepted_paraphrase": ["협정에는 관련자만 따로 송환하는 미사용 조항이 있지만 실행 가능성과 효과는 모른다"],
        "contradiction_policy": [
            "조항 존재를 즉시 실행 가능성으로 바꾸면 option_to_feasible_outcome",
            "미사용을 사용됨으로 바꾸면 unused_to_used",
        ],
        "lexical_probes": [r"따로\s*송환", r"쓰인\s*적이\s*없"],
        "extensions": {"boundary": "option_existence_nonuse_only",
                       "unknown_slots": ["feasibility", "effect", "eligibility_procedure"]},
    },
}

SCENARIO_DISTORTION_FLAGS = [
    "listed_to_guilty", "group_scope_expansion", "detected_to_actual_incidence",
    "correlation_to_causation", "unknown_actor_filled", "closure_cause_inference",
    "minimum_vote_inference", "causal_universalization", "option_to_feasible_outcome",
    "unused_to_used", "prereg_metadata_as_fact_truth",
]


def _frozen_material() -> dict:
    actual = sha256_of(paths.facts(IID))
    if actual != MATERIAL_SHA256:
        raise SpecError(f"{IID} material bytes changed: frozen {MATERIAL_SHA256} / actual {actual}")
    if sha256_of(paths.issue(IID)) != ISSUE_SHA256:
        raise SpecError(f"{IID} issue bytes changed")
    if sha256_of(paths.assignment(IID)) != ASSIGNMENT_SHA256:
        raise SpecError(f"{IID} assignment bytes changed")
    return json.loads(paths.facts(IID).read_text(encoding="utf-8"))


def _ethics_contract() -> dict:
    return {
        "status": ETHICS_STATUS,
        "separated_from_fact_preservation": True,
        "requires_human_coder": True,
        "requires_independent_adjudicator": "confirmatory_only",
        "human_coder": HUMAN_CODER,
        "independent_adjudicator": None,
        "development_coding_allowed": True,
        "confirmatory_ethics_allowed": False,
        "confirmatory_blocker": "pending_independent_adjudicator",
        "material_sidecar_role": "frozen_preassignment_snapshot",
        "assignment_basis": "owner_decision_amendment_2026-08-20",
        "permitted_calibration_scope":
            "development_boundary_and_confirmatory_blocker_only",
        "axes_are_uncoded": True,
        "axes": [
            "collective_punishment", "individual_due_process", "proportionality",
            "public_safety", "fiscal_cost", "humanitarian_feasibility", "treaty_obligation",
        ],
    }


def build_spec() -> dict:
    material = _frozen_material()
    material_facts = {fact["fact_id"]: fact for fact in material["facts"]}
    if set(material_facts) != set(FACT_SPECS):
        raise SpecError("exile_v2 spec fact identity does not match frozen material")
    facts = {}
    for fact_id, semantic in FACT_SPECS.items():
        source = material_facts[fact_id]
        ext = dict(semantic.get("extensions", {}))
        ext.update({
            "unfavorable_to": source.get("_unfavorable_to"),
            "unfavorable_to_role": "preregistered_analysis_metadata",
        })
        raw = {key: value for key, value in semantic.items() if key != "extensions"}
        facts[fact_id] = {"proposition": source["text"], **raw, "extensions": ext}
    return {
        "issue_id": IID,
        "spec_id": SPEC_ID,
        "spec_version": SPEC_VERSION,
        "material_sha256": MATERIAL_SHA256,
        "calibration_version": CALIBRATION_VERSION,
        "lexical_is_primary": False,
        "_note": "frozen exile_v2 material + owner decisions only; observed output consumed 0.",
        "requirements": {},
        "candidates": [],
        "material_artifacts": {
            "issue_sha256": ISSUE_SHA256,
            "facts_sha256": MATERIAL_SHA256,
            "assignment_sha256": ASSIGNMENT_SHA256,
        },
        "distortion_vocabulary": SCENARIO_DISTORTION_FLAGS,
        "outcome_contract": {
            "outcome_policy": OUTCOME_POLICY,
            "final_choice_role": "descriptive_record_only",
            "missing_evidence_state": "unknown",
            "partial_evidence_state": "unknown",
            "metadata_truth_rule": "_unfavorable_to_is_preregistered_analysis_metadata_only",
        },
        "ethics_sidecar_contract": _ethics_contract(),
        "facts": facts,
    }


def _material_fact_text(fact_id: str) -> str:
    for fact in _frozen_material()["facts"]:
        if fact["fact_id"] == fact_id:
            return fact["text"]
    raise SpecError(f"material fact missing: {fact_id}")


def _case(case_id: str, fact_id: str, text: str, status: str, mode: str, *,
          flags=None, relation=True) -> dict:
    return {
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


def build_calibration() -> dict:
    cases = []
    partial_modes = ("hypothetical", "counterargument", "attributed")
    for number in range(1, 13):
        fact_id = fid(number)
        cases.extend([
            _case(f"exile_cal_{number:02d}_exact", fact_id,
                  f"합성 정확 경계: {_material_fact_text(fact_id)}", "exact", "asserted"),
            _case(f"exile_cal_{number:02d}_faithful", fact_id,
                  f"합성 의역 경계: {FACT_SPECS[fact_id]['accepted_paraphrase'][0]}",
                  "faithful", "attributed"),
            _case(f"exile_cal_{number:02d}_partial", fact_id,
                  f"합성 부분 경계: 명제 일부 슬롯만 남긴 fixture {number:02d}", "partial",
                  partial_modes[(number - 1) % len(partial_modes)]),
            _case(f"exile_cal_{number:02d}_none", fact_id,
                  f"합성 미언급 경계 {number:02d}: 해당 명제를 제시하지 않음", "absent", "none",
                  relation=False),
        ])
    cases.extend([
        _case("exile_cal_01_guilty", fid(1),
              "합성 금지추론: 수사 관련자 31명은 모두 유죄 판결을 받았다", "contradicted", "asserted",
              flags=["listed_to_guilty"]),
        _case("exile_cal_02_cause", fid(2),
              "합성 금지추론: 정착민 때문에 실제 밀수 범죄가 아홉 배 늘었다", "contradicted", "asserted",
              flags=["correlation_to_causation"]),
        _case("exile_cal_06_actor", fid(6),
              "합성 금지추론: 정착민 전체가 경비대 진입을 두 번 막았다", "contradicted", "asserted",
              flags=["unknown_actor_filled", "group_scope_expansion"]),
        _case("exile_cal_08_cause", fid(8),
              "합성 금지추론: 갈취 때문에 상점 열아홉 곳이 직접 폐업했다", "contradicted", "asserted",
              flags=["closure_cause_inference"]),
        _case("exile_cal_10_blocked", fid(10),
              "합성 차단 경계: 과반 분모가 없어 최소 가결표를 판독할 수 없다", "blocked",
              "counterargument"),
        _case("exile_cal_10_six_votes", fid(10),
              "합성 금지추론: 열한 석이므로 언제나 여섯 표가 필요하다", "contradicted", "asserted",
              flags=["minimum_vote_inference"]),
        _case("exile_cal_11_universal", fid(11),
              "합성 금지추론: 모든 정착민의 모든 신원 확인은 언제나 네 달 걸린다", "contradicted", "asserted",
              flags=["causal_universalization"]),
        _case("exile_cal_12_feasible", fid(12),
              "합성 금지추론: 미사용 개별 송환 조항은 즉시 실행 가능하고 효과가 보장된다", "contradicted", "asserted",
              flags=["option_to_feasible_outcome"]),
        _case("exile_cal_metadata_truth", fid(12),
              "합성 금지추론: _unfavorable_to 주석을 명제의 진릿값으로 사용한다", "contradicted", "asserted",
              flags=["prereg_metadata_as_fact_truth"]),
    ])
    independent = "independent-from-observed-output"
    fixture = "synthetic_boundary_fixture"
    return {
        "issue_id": IID,
        "version": CALIBRATION_VERSION,
        "spec_version": SPEC_VERSION,
        "source_basis": ["frozen_material", "owner_decisions",
                         "owner_decision_amendment_2026-08-20",
                         "material_and_owner_decisions_only"],
        "_note": "독립 synthetic boundary fixtures; observed pilot/raw/model output 0건; ethics uncoded.",
        "cases": cases,
        "final_choice_cases": [
            {"case_id": "exile_choice_empty", "final_choice": None,
             "expected_choice_state": "unknown", "fixture_kind": fixture,
             "provenance_class": independent},
            {"case_id": "exile_choice_break", "final_choice": FINAL_CHOICES[0],
             "expected_choice_state": "recorded", "fixture_kind": fixture,
             "provenance_class": independent},
            {"case_id": "exile_choice_keep", "final_choice": FINAL_CHOICES[1],
             "expected_choice_state": "recorded", "fixture_kind": fixture,
             "provenance_class": independent},
            {"case_id": "exile_choice_partial", "final_choice": FINAL_CHOICES[0],
             "input_evidence_state": "partial", "expected_evidence_state": "unknown",
             "expected_choice_state": "recorded", "fixture_kind": fixture,
             "provenance_class": independent},
        ],
        "ethics_boundary_cases": [
            {"case_id": "exile_ethics_development_owner_coder",
             "expected_status": ETHICS_STATUS,
             "expected_separated_from_fact_preservation": True,
             "human_coder": HUMAN_CODER, "independent_adjudicator": None,
             "fixture_kind": fixture, "provenance_class": independent},
            {"case_id": "exile_ethics_confirmatory_adjudicator_deferred",
             "expected_status":
                 "confirmatory_blocked_pending_independent_adjudicator",
             "expected_separated_from_fact_preservation": True,
             "human_coder": HUMAN_CODER, "independent_adjudicator": None,
             "fixture_kind": fixture, "provenance_class": independent},
        ],
    }


def evaluate_descriptive(judgments: dict, final_choice: str | None = None) -> dict:
    """Sparse semantic 상태와 선택을 기술한다. 부재·부분·빈칸은 unknown이다."""
    if not isinstance(judgments, dict):
        raise SpecError("judgments must be a fact_id -> preservation_status mapping")
    unknown_ids = set(judgments) - set(FACT_SPECS)
    if unknown_ids:
        raise SpecError(f"exile_v2 spec has no fact ids: {sorted(unknown_ids)}")
    for fact_id, status in judgments.items():
        if status not in PRESERVATION_STATUSES:
            raise SpecError(f"{fact_id}: unknown preservation status {status!r}")
    if final_choice is not None and final_choice not in FINAL_CHOICES:
        raise SpecError(f"unknown descriptive final choice: {final_choice!r}")
    fact_states = {}
    for fact_id in FACT_SPECS:
        status = judgments.get(fact_id)
        fact_states[fact_id] = (
            "preserved" if status in {"exact", "faithful"}
            else "blocked" if status == "blocked"
            else "unknown"
        )
    return {
        "issue_id": IID,
        "outcome_policy": OUTCOME_POLICY,
        "fact_states": fact_states,
        "final_choice": final_choice,
        "final_choice_state": "recorded" if final_choice is not None else "unknown",
        "ethics_sidecar_status": ETHICS_STATUS,
        "ethics_separated_from_fact_preservation": True,
        "confirmatory_ethics_allowed": False,
        "confirmatory_ethics_blocker": "pending_independent_adjudicator",
    }


def reject_outcome_request(request: str) -> None:
    if (request or "").strip().lower() in FORBIDDEN_OUTCOME_REQUESTS:
        raise SpecError(f"{IID} outcome policy is descriptive_stance_only: {request!r} prohibited")


def main() -> None:
    spec = build_spec()
    calibration = build_calibration()
    spec_path = paths.detection_spec(IID)
    calibration_path = paths.calibration_set(IID)
    manifest_path = paths.detection_manifest(IID)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    calibration_path.write_text(
        json.dumps(calibration, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "issue_id": IID,
        "spec_version": SPEC_VERSION,
        "calibration_version": CALIBRATION_VERSION,
        "sha256": {
            "issue": ISSUE_SHA256,
            "facts": MATERIAL_SHA256,
            "assignment": ASSIGNMENT_SHA256,
            "spec": sha256_of(spec_path),
            "calibration": sha256_of(calibration_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[생성] {spec_path.name} · {calibration_path.name} · {manifest_path.name} · "
          f"facts_sha256={MATERIAL_SHA256}")


if __name__ == "__main__":
    main()
