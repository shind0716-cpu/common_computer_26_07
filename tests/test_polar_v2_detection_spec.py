"""issue_polar_v2 DetectionSpec·독립 calibration·manifest 계약."""

import ast
import importlib
import json
import unittest
from pathlib import Path

from modules import content_hash, detection_spec as ds
from modules import paths

ISSUE = "issue_polar_v2"
FORBIDDEN_RESULT_KEYS = {"winner", "accuracy", "correct", "incorrect", "answer_key"}


def fid(number: int) -> str:
    return f"fact_polar_v2_{number:02d}"


def raw_spec() -> dict:
    return json.loads(paths.detection_spec(ISSUE).read_text(encoding="utf-8"))


class PolarV2PackageSmokeTests(unittest.TestCase):
    def test_package_loads_exact_current_material_identity_and_hash(self):
        importlib.import_module("시나리오.build_detection_spec_polar_v2")
        spec = ds.load(ISSUE)
        material = json.loads(paths.facts(ISSUE).read_text(encoding="utf-8"))

        self.assertEqual(spec.issue_id, ISSUE)
        self.assertEqual(set(spec.facts), {fid(n) for n in range(1, 13)})
        self.assertEqual(set(spec.facts), {fact["fact_id"] for fact in material["facts"]})
        self.assertEqual(spec.material_sha256,
                         content_hash.sha256_file(paths.facts(ISSUE)))
        spec.verify_material()


class PolarV2SemanticBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = ds.load(ISSUE)
        cls.raw = raw_spec()

    def test_outcome_contract_is_descriptive_and_has_no_answer_semantics(self):
        contract = self.raw["outcome_contract"]
        self.assertEqual(contract["outcome_policy"], "descriptive_stance_only")
        self.assertEqual(contract["final_choice_role"], "descriptive_record_only")
        self.assertEqual(contract["missing_evidence_state"], "unknown")
        self.assertEqual(FORBIDDEN_RESULT_KEYS & set(contract), set())
        self.assertEqual(self.spec.candidates, [])
        self.assertEqual(self.spec.requirements, {})

    def test_fact03_is_route_alternate_not_hospital_round_trip_or_impossibility(self):
        fact = self.raw["facts"][fid(3)]
        ext = fact["extensions"]
        self.assertEqual(fact["slots"]["site_role"], "evacuation_route_alternate_landing_site")
        self.assertEqual(fact["slots"]["travel_time"], "one_way_six_hours")
        self.assertEqual(fact["slots"]["refueling_stop"], "none")
        self.assertIn("route_to_hospital_time", ext["unknown_slots"])
        self.assertIn("round_trip_time", ext["unknown_slots"])
        self.assertIn("flight_feasibility", ext["unknown_slots"])
        self.assertTrue(any("route_or_destination_conflation" in rule
                            for rule in fact["contradiction_policy"]))

    def test_fact05_is_historical_case_only(self):
        fact = self.raw["facts"][fid(5)]
        ext = fact["extensions"]
        self.assertEqual(ext["boundary"], "historical_case_only")
        self.assertEqual(fact["slots"]["event_scope"], "one_historical_turnback_case")
        self.assertEqual(
            set(ext["unknown_slots"]),
            {"present_failure_probability", "present_failure_inevitability", "universal_failure"})

    def test_fact11_accessibility_unknown_and_11_12_orientation_blocked(self):
        f11 = self.raw["facts"][fid(11)]
        self.assertEqual(f11["extensions"]["boundary"], "accessibility_unknown")
        self.assertEqual(f11["slots"]["accessibility"], "unknown")
        self.assertEqual(f11["extensions"]["orientation_policy"], "orientation_blocked")
        self.assertEqual(self.raw["facts"][fid(12)]["extensions"]["orientation_policy"],
                         "orientation_blocked")

    def test_unfavorable_to_is_prereg_metadata_not_truth_or_favors(self):
        for fact_id, fact in self.raw["facts"].items():
            with self.subTest(fact_id=fact_id):
                self.assertEqual(fact["extensions"]["unfavorable_to_role"],
                                 "preregistered_analysis_metadata")
                self.assertNotIn("favors", fact)
                self.assertNotIn("truth", fact)

    def test_polar_owned_distortion_flags_are_local_to_polar_spec(self):
        record = {
            "issue_id": ISSUE,
            "spec_version": self.spec.spec_version,
            "fact_id": fid(3),
            "preservation_status": "contradicted",
            "mention_mode": "asserted",
            "relation_engaged": True,
            "distortion_flags": ["route_or_destination_conflation"],
            "judge_kind": "human",
            "provenance_class": "development/test",
            "reason": "대체 착륙장을 병원 목적지로 바꿈",
        }
        ds.validate_record(self.spec, record)
        with self.assertRaises(ds.SpecError):
            ds.validate_record(ds.load("issue_throne_v2"), {
                **record,
                "issue_id": "issue_throne_v2",
                "spec_version": ds.load("issue_throne_v2").spec_version,
                "fact_id": "fact_throne_v2_01",
            })


class PolarV2IndependentCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = ds.load(ISSUE)
        cls.cal = ds.load_calibration(ISSUE)
        cls.raw_cal = json.loads(paths.calibration_set(ISSUE).read_text(encoding="utf-8"))

    def test_every_fact_has_positive_negative_and_mention_mode_boundaries(self):
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
            self.assertTrue(statuses & {"exact", "faithful"}, f"{fact_id}: 양성 없음")
            self.assertTrue(statuses & {"partial", "absent", "contradicted", "blocked"},
                            f"{fact_id}: 음성·경계 없음")
        self.assertEqual(modes,
                         {"asserted", "attributed", "hypothetical", "counterargument", "none"})

    def test_calibration_covers_blocked_unknown_and_prohibited_inference_boundaries(self):
        cases = self.cal.cases
        self.assertTrue(any(c["expected_status"] == "blocked" for c in cases))
        self.assertTrue(any(c.get("expected_orientation") == "orientation_blocked"
                            for c in cases if c["fact_id"] in {fid(11), fid(12)}))
        flags = {flag for case in cases for flag in case.get("expected_flags", [])}
        self.assertIn("route_or_destination_conflation", flags)
        self.assertIn("historical_case_to_present_probability", flags)
        self.assertIn("accessibility_inference", flags)
        self.assertIn("prereg_metadata_as_fact_truth", flags)

    def test_calibration_has_no_observed_run_or_model_output_provenance(self):
        forbidden_fields = {
            "run_id", "source_run_id", "model_output", "raw_output", "pilot_id",
            "observed_text", "response_id", "prompt", "answer_key",
        }
        self.assertFalse(forbidden_fields & set(self.raw_cal))
        for case in self.cal.cases:
            self.assertFalse(forbidden_fields & set(case))
        self.assertIn("material_and_owner_decisions_only", self.raw_cal["source_basis"])

    def test_final_choice_calibration_is_descriptive_not_accuracy(self):
        cases = self.raw_cal["final_choice_cases"]
        self.assertGreaterEqual(len(cases), 4)
        self.assertTrue(any(case["final_choice"] is None and
                            case["expected_choice_state"] == "unknown" for case in cases))
        self.assertTrue(any(case["final_choice"] == "후송한다" and
                            case["expected_choice_state"] == "recorded" for case in cases))
        self.assertTrue(any(case["final_choice"] == "후송하지 않는다" and
                            case["expected_choice_state"] == "recorded" for case in cases))
        for case in cases:
            self.assertFalse(FORBIDDEN_RESULT_KEYS & set(case))
            self.assertEqual(case["provenance_class"],
                             "independent-from-observed-output")

    def test_builder_does_not_read_observed_debate_judgment_or_raw_paths(self):
        builder = importlib.import_module("시나리오.build_detection_spec_polar_v2")
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


class PolarV2DescriptiveEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = importlib.import_module("시나리오.build_detection_spec_polar_v2")

    def assert_no_answer_semantics(self, result):
        self.assertFalse(FORBIDDEN_RESULT_KEYS & set(result))
        self.assertNotIn("selected_side", result)

    def test_empty_input_remains_unknown(self):
        result = self.builder.evaluate_descriptive({}, final_choice=None)
        self.assertEqual(set(result["fact_states"].values()), {"unknown"})
        self.assertEqual(result["final_choice_state"], "unknown")
        self.assertIsNone(result["final_choice"])
        self.assert_no_answer_semantics(result)

    def test_partial_and_unmentioned_do_not_become_false_or_other_side(self):
        result = self.builder.evaluate_descriptive({fid(1): "partial", fid(2): "absent"})
        self.assertEqual(result["fact_states"][fid(1)], "unknown")
        self.assertEqual(result["fact_states"][fid(2)], "unknown")
        self.assertNotIn("false", result["fact_states"].values())
        self.assert_no_answer_semantics(result)

    def test_final_choice_is_only_recorded(self):
        for choice in ("후송한다", "후송하지 않는다"):
            with self.subTest(choice=choice):
                result = self.builder.evaluate_descriptive({}, final_choice=choice)
                self.assertEqual(result["final_choice"], choice)
                self.assertEqual(result["final_choice_state"], "recorded")
                self.assert_no_answer_semantics(result)

    def test_orientation_blocked_is_not_taken_from_unfavorable_metadata(self):
        result = self.builder.evaluate_descriptive(
            {fid(11): "faithful", fid(12): "exact"})
        self.assertEqual(result["orientation_states"][fid(11)], "orientation_blocked")
        self.assertEqual(result["orientation_states"][fid(12)], "orientation_blocked")
        self.assertEqual(result["stance_counts"], {"후송": 0, "대기": 0})

    def test_unknown_fact_status_choice_and_accuracy_request_fail_closed(self):
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({fid(99): "faithful"})
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({fid(1): "false"})
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_descriptive({}, final_choice="후송이 정답")
        for request in ("accuracy", "winner", "정답률"):
            with self.subTest(request=request):
                with self.assertRaises(ds.SpecError):
                    self.builder.reject_outcome_request(request)


class PolarV2ManifestTests(unittest.TestCase):
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
        self.assertEqual(manifest["spec_version"], ds.load(ISSUE).spec_version)
        self.assertEqual(manifest["calibration_version"], ds.load(ISSUE).calibration_version)


if __name__ == "__main__":
    unittest.main()
