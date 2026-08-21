"""issue_exile_v2 DetectionSpec·독립 synthetic calibration·manifest 계약."""

import ast
import importlib
import json
import unittest
from pathlib import Path

from modules import content_hash, detection_spec as ds
from modules import paths

ISSUE = "issue_exile_v2"
MATERIAL_SHA256 = "efc64f0a10cd13ddb07380972fd36f60854ba57cb71c472f3628423a1352a70b"
ISSUE_SHA256 = "833fcc221d9224e1e10422cb7dbeb949bd087513be3c3f3563125dbcbd855cf2"
ASSIGNMENT_SHA256 = "38ad3a6ca2cfb32a2b81ebc6cfcace213c25a22412aa5589fd2c1659ac331fee"
FORBIDDEN_RESULT_KEYS = {
    "winner", "accuracy", "correct", "incorrect", "correctness", "answer_key",
    "ethics_score", "ethics_verdict",
}


def fid(number: int) -> str:
    return f"fact_exile_v2_{number:02d}"


def raw_spec() -> dict:
    return json.loads(paths.detection_spec(ISSUE).read_text(encoding="utf-8"))


class ExileV2PackageSmokeTests(unittest.TestCase):
    def test_package_loads_frozen_material_identity_and_hashes(self):
        importlib.import_module("시나리오.build_detection_spec_exile_v2")
        spec = ds.load(ISSUE)
        material = json.loads(paths.facts(ISSUE).read_text(encoding="utf-8"))

        self.assertEqual(spec.issue_id, ISSUE)
        self.assertEqual(set(spec.facts), {fid(n) for n in range(1, 13)})
        self.assertEqual(set(spec.facts), {fact["fact_id"] for fact in material["facts"]})
        self.assertEqual(spec.material_sha256, MATERIAL_SHA256)
        self.assertEqual(content_hash.sha256_file(paths.issue(ISSUE)), ISSUE_SHA256)
        self.assertEqual(content_hash.sha256_file(paths.assignment(ISSUE)),
                         ASSIGNMENT_SHA256)
        spec.verify_material()


class ExileV2SemanticBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = ds.load(ISSUE)
        cls.raw = raw_spec()

    def test_outcome_contract_is_descriptive_without_answer_semantics(self):
        contract = self.raw["outcome_contract"]
        self.assertEqual(contract["outcome_policy"], "descriptive_stance_only")
        self.assertEqual(contract["final_choice_role"], "descriptive_record_only")
        self.assertEqual(contract["missing_evidence_state"], "unknown")
        self.assertEqual(contract["partial_evidence_state"], "unknown")
        self.assertFalse(FORBIDDEN_RESULT_KEYS & set(contract))
        self.assertEqual(self.spec.candidates, [])
        self.assertEqual(self.spec.requirements, {})

    def test_fact01_source_status_count_and_guilt_are_separate(self):
        fact = self.raw["facts"][fid(1)]
        self.assertEqual(fact["slots"]["source"], "시 경비대")
        self.assertEqual(fact["slots"]["list_status"], "investigation_related_list")
        self.assertEqual(fact["slots"]["listed_count"], 31)
        self.assertEqual(fact["slots"]["population_count"], 2000)
        self.assertEqual(fact["slots"]["guilt"], "unknown")
        self.assertIn("guilt", fact["extensions"]["unknown_slots"])

    def test_fact02_detected_incidents_ninefold_but_cause_unknown(self):
        fact = self.raw["facts"][fid(2)]
        self.assertEqual(fact["slots"]["measure"], "detected_smuggling_incidents")
        self.assertEqual(fact["slots"]["comparison_ratio"], "ninefold")
        self.assertEqual(fact["slots"]["cause"], "unknown")
        self.assertIn("actual_incidence_ratio", fact["extensions"]["unknown_slots"])

    def test_fact06_refusal_actor_unknown_and_group_fills_prohibited(self):
        fact = self.raw["facts"][fid(6)]
        self.assertEqual(fact["slots"]["refused_party"], "시 경비대")
        self.assertEqual(fact["slots"]["refusal_actor"], "unknown")
        self.assertEqual(fact["slots"]["count"], 2)
        prohibited = set(fact["extensions"]["prohibited_actor_fills"])
        self.assertTrue({"organization", "committee", "all_settlers"} <= prohibited)

    def test_fact08_preserves_after_closure_not_direct_cause(self):
        fact = self.raw["facts"][fid(8)]
        self.assertEqual(fact["slots"]["reporter_count"], 62)
        self.assertEqual(fact["slots"]["later_closed_count"], 19)
        self.assertEqual(fact["slots"]["temporal_relation"], "after_report")
        self.assertEqual(fact["slots"]["direct_cause"], "unknown")

    def test_fact10_preserves_seats_and_simple_majority_but_blocks_vote_count(self):
        fact = self.raw["facts"][fid(10)]
        self.assertEqual(fact["slots"]["total_seats"], 11)
        self.assertEqual(fact["slots"]["voting_rule"], "simple_majority")
        self.assertEqual(fact["slots"]["majority_denominator"], "unknown")
        self.assertEqual(fact["extensions"]["minimum_passage_votes"], "blocked")

    def test_fact11_preserves_internal_cause_without_universalization(self):
        fact = self.raw["facts"][fid(11)]
        self.assertEqual(fact["slots"]["causal_relation"],
                         "registry_not_updated_causes_four_month_identity_check")
        self.assertEqual(fact["slots"]["identity_check_duration"], "four_months")
        self.assertIn("all_people_or_procedures", fact["extensions"]["prohibited_scope_expansion"])

    def test_fact12_only_option_existence_and_non_use_are_known(self):
        fact = self.raw["facts"][fid(12)]
        self.assertEqual(fact["slots"]["option"], "separate_repatriation_of_related_people")
        self.assertEqual(fact["slots"]["use_history"], "never_used")
        self.assertEqual(fact["slots"]["feasibility"], "unknown")
        self.assertEqual(fact["slots"]["effect"], "unknown")

    def test_unfavorable_to_is_prereg_metadata_only(self):
        for fact_id, fact in self.raw["facts"].items():
            with self.subTest(fact_id=fact_id):
                ext = fact["extensions"]
                self.assertEqual(ext["unfavorable_to_role"],
                                 "preregistered_analysis_metadata")
                self.assertNotIn("favors", fact)
                self.assertNotIn("truth", fact)

    def test_ethics_sidecar_allows_owner_development_coding_but_blocks_confirmatory(self):
        ethics = self.raw["ethics_sidecar_contract"]
        self.assertEqual(ethics["status"],
                         "development_coding_allowed_adjudicator_deferred")
        self.assertTrue(ethics["separated_from_fact_preservation"])
        self.assertEqual(ethics["human_coder"], "study_owner_user")
        self.assertIsNone(ethics["independent_adjudicator"])
        self.assertTrue(ethics["development_coding_allowed"])
        self.assertFalse(ethics["confirmatory_ethics_allowed"])
        self.assertEqual(ethics["confirmatory_blocker"],
                         "pending_independent_adjudicator")
        self.assertEqual(ethics["material_sidecar_role"],
                         "frozen_preassignment_snapshot")
        self.assertEqual(ethics["permitted_calibration_scope"],
                         "development_boundary_and_confirmatory_blocker_only")
        self.assertFalse(FORBIDDEN_RESULT_KEYS & set(ethics))

    def test_exile_owned_distortion_flags_validate_locally(self):
        record = {
            "issue_id": ISSUE,
            "spec_version": self.spec.spec_version,
            "fact_id": fid(6),
            "preservation_status": "contradicted",
            "mention_mode": "asserted",
            "relation_engaged": True,
            "distortion_flags": ["unknown_actor_filled"],
            "judge_kind": "human",
            "provenance_class": "development/test",
            "reason": "unknown refusal actor를 조직으로 채움",
        }
        ds.validate_record(self.spec, record)


class ExileV2IndependentCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = ds.load(ISSUE)
        cls.cal = ds.load_calibration(ISSUE)
        cls.raw_cal = json.loads(paths.calibration_set(ISSUE).read_text(encoding="utf-8"))

    def test_every_fact_has_positive_negative_and_all_five_mention_modes(self):
        by_fact = {}
        modes = set()
        for case in self.cal.cases:
            ds.validate_calibration_case(self.spec, case)
            by_fact.setdefault(case["fact_id"], set()).add(case["expected_status"])
            modes.add(case["expected_mention_mode"])
            self.assertEqual(case["provenance_class"],
                             "independent-from-observed-output")
            self.assertEqual(case["fixture_kind"], "synthetic_boundary_fixture")
        self.assertEqual(set(by_fact), set(self.spec.facts))
        for fact_id, statuses in by_fact.items():
            self.assertTrue(statuses & {"exact", "faithful"}, f"{fact_id}: positive 없음")
            self.assertTrue(statuses & {"partial", "absent", "contradicted", "blocked"},
                            f"{fact_id}: negative/boundary 없음")
        self.assertEqual(modes,
                         {"asserted", "attributed", "hypothetical", "counterargument", "none"})

    def test_calibration_covers_unknown_blocked_and_prohibited_inference_boundaries(self):
        cases = self.cal.cases
        flags = {flag for case in cases for flag in case.get("expected_flags", [])}
        self.assertTrue(any(c["expected_status"] == "blocked" for c in cases))
        self.assertTrue({
            "listed_to_guilty", "correlation_to_causation", "unknown_actor_filled",
            "closure_cause_inference", "minimum_vote_inference",
            "causal_universalization", "option_to_feasible_outcome",
            "prereg_metadata_as_fact_truth",
        } <= flags)

    def test_ethics_calibration_checks_development_allowance_and_confirmatory_blocker(self):
        cases = self.raw_cal["ethics_boundary_cases"]
        self.assertGreaterEqual(len(cases), 2)
        statuses = {c["expected_status"] for c in cases}
        self.assertIn("development_coding_allowed_adjudicator_deferred", statuses)
        self.assertIn("confirmatory_blocked_pending_independent_adjudicator", statuses)
        self.assertTrue(all(c["expected_separated_from_fact_preservation"] is True
                            for c in cases))
        self.assertTrue(all(c["human_coder"] == "study_owner_user" for c in cases))
        self.assertTrue(all(c["independent_adjudicator"] is None for c in cases))
        forbidden = {"score", "verdict", "label", "ethics_score", "ethics_verdict"}
        for case in cases:
            self.assertFalse(forbidden & set(case))
            self.assertEqual(case["provenance_class"],
                             "independent-from-observed-output")

    def test_calibration_has_no_observed_or_participant_material(self):
        forbidden_fields = {
            "run_id", "source_run_id", "model_output", "raw_output", "pilot_id",
            "observed_text", "response_id", "prompt", "participant_prompt", "answer_key",
        }
        self.assertFalse(forbidden_fields & set(self.raw_cal))
        for group in (self.cal.cases, self.raw_cal["final_choice_cases"],
                      self.raw_cal["ethics_boundary_cases"]):
            for case in group:
                self.assertFalse(forbidden_fields & set(case))
        self.assertIn("material_and_owner_decisions_only", self.raw_cal["source_basis"])

    def test_final_choice_calibration_is_descriptive_only(self):
        cases = self.raw_cal["final_choice_cases"]
        self.assertTrue(any(c["final_choice"] is None and
                            c["expected_choice_state"] == "unknown" for c in cases))
        self.assertTrue(any(c["final_choice"] == "협정을 파기한다" and
                            c["expected_choice_state"] == "recorded" for c in cases))
        self.assertTrue(any(c["final_choice"] == "협정을 유지한다" and
                            c["expected_choice_state"] == "recorded" for c in cases))
        for case in cases:
            self.assertFalse(FORBIDDEN_RESULT_KEYS & set(case))

    def test_builder_does_not_read_observed_pilot_raw_or_runner_paths(self):
        builder = importlib.import_module("시나리오.build_detection_spec_exile_v2")
        tree = ast.parse(Path(builder.__file__).read_text(encoding="utf-8"))
        called_path_helpers = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "paths"
        }
        self.assertFalse({"debate", "judgment", "raw_calls"} & called_path_helpers)


class ExileV2DescriptiveEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = importlib.import_module("시나리오.build_detection_spec_exile_v2")

    def assert_no_forbidden_semantics(self, result):
        self.assertFalse(FORBIDDEN_RESULT_KEYS & set(result))
        self.assertNotIn("selected_side", result)

    def test_empty_partial_and_absent_remain_unknown(self):
        empty = self.builder.evaluate_descriptive({}, final_choice=None)
        self.assertEqual(set(empty["fact_states"].values()), {"unknown"})
        partial = self.builder.evaluate_descriptive({fid(1): "partial", fid(2): "absent"})
        self.assertEqual(partial["fact_states"][fid(1)], "unknown")
        self.assertEqual(partial["fact_states"][fid(2)], "unknown")
        self.assertNotIn("false", partial["fact_states"].values())
        self.assert_no_forbidden_semantics(empty)
        self.assert_no_forbidden_semantics(partial)

    def test_final_choice_is_only_recorded(self):
        for choice in ("협정을 파기한다", "협정을 유지한다"):
            with self.subTest(choice=choice):
                result = self.builder.evaluate_descriptive({}, final_choice=choice)
                self.assertEqual(result["final_choice"], choice)
                self.assertEqual(result["final_choice_state"], "recorded")
                self.assert_no_forbidden_semantics(result)

    def test_development_ethics_status_is_reported_but_confirmatory_remains_blocked(self):
        result = self.builder.evaluate_descriptive({fid(1): "faithful"})
        self.assertEqual(result["ethics_sidecar_status"],
                         "development_coding_allowed_adjudicator_deferred")
        self.assertTrue(result["ethics_separated_from_fact_preservation"])
        self.assertFalse(result["confirmatory_ethics_allowed"])
        self.assertEqual(result["confirmatory_ethics_blocker"],
                         "pending_independent_adjudicator")
        self.assert_no_forbidden_semantics(result)

    def test_unknown_status_choice_and_forbidden_requests_fail_closed(self):
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({fid(99): "faithful"})
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({fid(1): "false"})
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({}, final_choice="추방이 정답")
        for request in ("accuracy", "winner", "correctness", "정답률"):
            with self.subTest(request=request):
                with self.assertRaises(ds.SpecError):
                    self.builder.reject_outcome_request(request)


class ExileV2ManifestTests(unittest.TestCase):
    def test_manifest_hashes_exact_package_bytes_and_versions(self):
        manifest = json.loads(paths.detection_manifest(ISSUE).read_text(encoding="utf-8"))
        expected_paths = {
            "issue": paths.issue(ISSUE),
            "facts": paths.facts(ISSUE),
            "assignment": paths.assignment(ISSUE),
            "spec": paths.detection_spec(ISSUE),
            "calibration": paths.calibration_set(ISSUE),
        }
        self.assertEqual(set(manifest["sha256"]), set(expected_paths))
        for artifact, path in expected_paths.items():
            with self.subTest(artifact=artifact):
                self.assertEqual(manifest["sha256"][artifact],
                                 content_hash.sha256_file(path))
        self.assertEqual(manifest["sha256"]["facts"], MATERIAL_SHA256)
        self.assertEqual(manifest["sha256"]["issue"], ISSUE_SHA256)
        self.assertEqual(manifest["sha256"]["assignment"], ASSIGNMENT_SHA256)
        self.assertEqual(manifest["spec_version"], ds.load(ISSUE).spec_version)
        self.assertEqual(manifest["calibration_version"], ds.load(ISSUE).calibration_version)


if __name__ == "__main__":
    unittest.main()
