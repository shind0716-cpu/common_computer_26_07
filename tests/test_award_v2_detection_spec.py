"""issue_award_v2 DetectionSpec·독립 calibration·결정 사슬 계약."""

import importlib
import itertools
import json
import unittest

from modules import content_hash, detection_spec as ds
from modules import paths

ISSUE = "issue_award_v2"


def fid(n: int) -> str:
    return f"fact_award_v2_{n:02d}"


class AwardV2SpecLoadingTests(unittest.TestCase):
    def test_spec_loads_exact_material_fact_identity_and_hash(self):
        spec = ds.load(ISSUE)
        material = json.loads(paths.facts(ISSUE).read_text(encoding="utf-8"))

        self.assertEqual(spec.issue_id, ISSUE)
        self.assertEqual(set(spec.facts), {fid(n) for n in range(1, 13)})
        self.assertEqual(set(spec.facts), {fact["fact_id"] for fact in material["facts"]})
        spec.verify_material()

    def test_surface_facts_are_excluded_from_normative_decision_contract(self):
        spec = ds.load(ISSUE)
        surface = {fact_id for fact_id, fact in spec.facts.items()
                   if fact.decision_role == "surface_impression"}
        self.assertEqual(surface, {fid(1), fid(2), fid(3)})
        self.assertEqual(set(spec.decision_contract["surface_fact_ids"]), surface)
        component_facts = {
            fact_id
            for required in spec.decision_contract["components"].values()
            for fact_id in required
        }
        self.assertFalse(surface & component_facts)
        self.assertEqual(component_facts, {fid(n) for n in range(4, 13)})

    def test_scenario_owned_distortion_flag_is_accepted_only_for_award_spec(self):
        spec = ds.load(ISSUE)
        record = {
            "issue_id": ISSUE,
            "spec_version": spec.spec_version,
            "fact_id": fid(1),
            "preservation_status": "contradicted",
            "mention_mode": "asserted",
            "relation_engaged": True,
            "distortion_flags": ["surface_to_normative_inference"],
            "judge_kind": "human",
            "provenance_class": "development/test",
            "reason": "인기를 공식 심사 우위로 바꿨다",
        }
        ds.validate_record(spec, record)


class AwardV2CalibrationTests(unittest.TestCase):
    def test_every_fact_has_independent_positive_and_negative_cases(self):
        spec = ds.load(ISSUE)
        calibration = ds.load_calibration(ISSUE)
        by_fact = {}
        for case in calibration.cases:
            ds.validate_calibration_case(spec, case)
            by_fact.setdefault(case["fact_id"], set()).add(case["expected_status"])
            self.assertEqual(
                case["provenance_class"], "independent-from-observed-output")

        self.assertEqual(set(by_fact), set(spec.facts))
        for fact_id, statuses in by_fact.items():
            self.assertTrue(statuses & {"exact", "faithful"}, f"{fact_id}: 양성 없음")
            self.assertTrue(statuses & {"partial", "absent", "contradicted"},
                            f"{fact_id}: 음성·경계 없음")

    def test_chain_calibration_contains_partial_and_full_independent_cases(self):
        calibration = ds.load_calibration(ISSUE)
        self.assertGreaterEqual(len(calibration.chain_cases), 8)
        self.assertTrue(all(case["provenance_class"] ==
                            "independent-from-observed-output"
                            for case in calibration.chain_cases))
        self.assertTrue(any(case["expected_winner"] is None
                            for case in calibration.chain_cases))
        self.assertTrue(any(case["expected_winner"] == "밤길 안내인"
                            for case in calibration.chain_cases))


class AwardV2DecisionChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = importlib.import_module("시나리오.build_detection_spec_award_v2")
        cls.required = sorted({fid(n) for n in range(4, 13)})

    def test_every_proper_subset_is_unknown_and_has_no_winner(self):
        for size in range(len(self.required)):
            for subset in itertools.combinations(self.required, size):
                with self.subTest(size=size, subset=subset):
                    record = self.builder.evaluate_chain(set(subset))
                    self.assertEqual(record["decision_state"], "unknown")
                    self.assertIsNone(record["winner"])
                    self.assertIn("unknown", set(record["components"].values()))

    def test_surface_facts_do_not_complete_the_chain(self):
        record = self.builder.evaluate_chain({fid(1), fid(2), fid(3)})
        self.assertEqual(record["decision_state"], "unknown")
        self.assertIsNone(record["winner"])

    def test_only_full_normative_chain_selects_night_guide(self):
        record = self.builder.evaluate_chain(set(self.required))
        self.assertEqual(record["record_type"], "award_chain_evaluation")
        self.assertEqual(record["issue_id"], ISSUE)
        self.assertEqual(record["spec_version"], "0.1")
        self.assertTrue(all(value == "true" for value in record["components"].values()))
        self.assertEqual(record["decision_state"], "selected")
        self.assertEqual(record["winner"], "밤길 안내인")

    def test_unknown_fact_id_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            self.builder.evaluate_chain({"fact_award_v2_99"})


class AwardV2HashManifestTests(unittest.TestCase):
    def test_manifest_hashes_material_spec_and_calibration_bytes(self):
        manifest_path = paths.detection_manifest(ISSUE)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_paths = {
            "issue": paths.issue(ISSUE),
            "facts": paths.facts(ISSUE),
            "assignment": paths.assignment(ISSUE),
            "spec": paths.detection_spec(ISSUE),
            "calibration": paths.calibration_set(ISSUE),
        }
        self.assertEqual(set(manifest["sha256"]), set(expected_paths))
        for key, path in expected_paths.items():
            with self.subTest(artifact=key):
                actual = content_hash.sha256_file(path)
                self.assertEqual(manifest["sha256"][key], actual)
        self.assertEqual(manifest["spec_version"], ds.load(ISSUE).spec_version)
        self.assertEqual(manifest["calibration_version"], ds.load(ISSUE).calibration_version)


if __name__ == "__main__":
    unittest.main()
