"""DetectionSpec 로더·검증기 계약 테스트.

브리프 CLAUDE_IMPLEMENTATION_BRIEF_throne_detection_v0.md §5C·§6 을 그대로 옮긴 것이다.
핵심은 **fail-closed** — 모르는 것을 0점이나 absent 로 조용히 바꾸지 않는다.
"""

import copy
import json
import unittest
from pathlib import Path

from modules import detection_spec as ds
from modules import paths

ISSUE = "issue_throne_v2"


def base_record(**over):
    r = {
        "issue_id": ISSUE,
        "spec_id": "throne-semantic-detection",
        "spec_version": "0.1",
        "fact_id": "fact_throne_v2_10",
        "run_id": "A_full_rep1",
        "text_role": "essay_r0",
        "lexical_hit": False,
        "lexical_spans": [],
        "preservation_status": "faithful",
        "mention_mode": "asserted",
        "relation_engaged": True,
        "distortion_flags": [],
        "evidence": "아르넬을 지지한 제후 일곱의 서명이 접수됐다",
        "reason": "주체·수치·상태 보존",
        "judge_kind": "human",
        "provenance_class": "observed/development-only",
    }
    r.update(over)
    return r


class SpecLoadingTests(unittest.TestCase):
    def test_loads_throne_v2_spec_with_twelve_facts(self):
        spec = ds.load(ISSUE)
        self.assertEqual(spec.issue_id, ISSUE)
        self.assertEqual(len(spec.facts), 12)

    def test_every_fact_declares_required_slots(self):
        spec = ds.load(ISSUE)
        for fact_id, fs in spec.facts.items():
            self.assertTrue(fs.required_slots, f"{fact_id}: required_slots 비었음")

    def test_required_slots_are_all_declared_in_slots(self):
        """필수라고 적어 놓고 슬롯에 없으면 판정자가 무엇을 볼지 모른다."""
        spec = ds.load(ISSUE)
        for fact_id, fs in spec.facts.items():
            missing = [s for s in fs.required_slots if s not in fs.slots]
            self.assertEqual(missing, [], f"{fact_id}: required 인데 slots 에 없음 {missing}")

    def test_every_fact_names_the_entity_it_is_about(self):
        """엔티티 슬롯 이름은 역할에 따라 다르다 — 제후 서명 팩트는 subject 가 아니라
        beneficiary 다(누구를 위한 서명인가). 이름을 강제하지 말고 존재를 강제한다."""
        entity_slots = {"subject", "beneficiary"}
        spec = ds.load(ISSUE)
        for fact_id, fs in spec.facts.items():
            self.assertTrue(entity_slots & set(fs.slots),
                            f"{fact_id}: 대상 엔티티 슬롯 없음 ({sorted(fs.slots)})")

    def test_unknown_issue_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.load("issue_does_not_exist")

    def test_material_hash_match_passes(self):
        ds.load(ISSUE).verify_material()

    def test_material_hash_mismatch_fails_closed(self):
        spec = ds.load(ISSUE)
        spec.material_sha256 = "0" * 64
        with self.assertRaises(ds.SpecError):
            spec.verify_material()

    def test_spec_fact_ids_match_material_fact_ids(self):
        spec = ds.load(ISSUE)
        material = json.loads(paths.facts(ISSUE).read_text(encoding="utf-8"))
        self.assertEqual(set(spec.facts), {f["fact_id"] for f in material["facts"]})

    def test_lexical_probes_are_declared_as_auxiliary(self):
        spec = ds.load(ISSUE)
        self.assertTrue(all(fs.lexical_probes for fs in spec.facts.values()))
        self.assertFalse(spec.lexical_is_primary)


class RecordValidationTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)

    def test_valid_record_passes(self):
        ds.validate_record(self.spec, base_record())

    def test_unknown_preservation_status_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(preservation_status="survived"))

    def test_unknown_mention_mode_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(mention_mode="maybe"))

    def test_unknown_distortion_flag_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(distortion_flags=["vibes_off"]))

    def test_unknown_fact_id_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(fact_id="fact_throne_06"))

    def test_spec_version_mismatch_fails_closed(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(spec_version="99.9"))

    def test_blocked_requires_reason(self):
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(preservation_status="blocked", reason=""))

    def test_absent_with_relation_engaged_true_is_allowed(self):
        """원 사실 대신 더 강한 주장을 한 경우 — absent 로 뭉개지 않는다 (브리프 §4.1)."""
        ds.validate_record(self.spec, base_record(
            preservation_status="absent", relation_engaged=True,
            distortion_flags=["modality_strengthening"],
            evidence="아르넬은 성별식 자격을 공식 인정받았다"))

    def test_lexical_miss_with_semantic_faithful_is_allowed(self):
        ds.validate_record(self.spec, base_record(lexical_hit=False,
                                                  preservation_status="faithful"))

    def test_lexical_hit_with_semantic_contradicted_is_allowed(self):
        ds.validate_record(self.spec, base_record(lexical_hit=True,
                                                  preservation_status="contradicted",
                                                  distortion_flags=["polarity_flip"]))

    def test_semantic_status_cannot_be_derived_from_lexical_alone(self):
        """judge_kind 가 lexical 이면 semantic 판정을 실을 수 없다 (브리프 §4.3·§7)."""
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, base_record(judge_kind="lexical"))

    def test_missing_provenance_class_fails_closed(self):
        rec = base_record()
        del rec["provenance_class"]
        with self.assertRaises(ds.SpecError):
            ds.validate_record(self.spec, rec)


class CodingRecordFileTests(unittest.TestCase):
    """기존 r0 코딩 CSV 를 읽어 검증할 수 있어야 한다 (브리프 §5D).

    그 CSV 는 **v1 재료** 기준이므로 v2 spec 으로 검증하면 fact_id 불일치로 실패해야 한다.
    이것이 판본 혼동을 막는 장치다.
    """

    CSV = Path("experiments/scenario_generalization/THRONE_R0_SEMANTIC_CODING_DRAFT.csv")

    def test_v1_coding_csv_is_readable(self):
        rows = ds.read_coding_csv(self.CSV)
        self.assertEqual(len(rows), 108)
        self.assertEqual({r["text_role"] for r in rows}, {"essay_r0"})

    def test_v1_records_rejected_against_v2_spec(self):
        rows = ds.read_coding_csv(self.CSV)
        spec = ds.load(ISSUE)
        with self.assertRaises(ds.SpecError):
            ds.validate_record(spec, rows[0])

    def test_dataset_role_is_preserved(self):
        rows = ds.read_coding_csv(self.CSV)
        self.assertTrue(all(r["provenance_class"] == "observed/development-only"
                            for r in rows))


class CalibrationFixtureTests(unittest.TestCase):
    def test_calibration_fixture_loads_and_is_independent(self):
        cal = ds.load_calibration(ISSUE)
        self.assertGreaterEqual(len(cal.cases), 24)
        self.assertTrue(all(c["provenance_class"] == "independent-from-observed-output"
                            for c in cal.cases))

    def test_every_fact_has_positive_and_negative_cases(self):
        spec, cal = ds.load(ISSUE), ds.load_calibration(ISSUE)
        by_fact = {}
        for c in cal.cases:
            by_fact.setdefault(c["fact_id"], []).append(c["expected_status"])
        self.assertEqual(set(by_fact), set(spec.facts))
        for fact_id, statuses in by_fact.items():
            self.assertTrue(any(s in ("exact", "faithful") for s in statuses),
                            f"{fact_id}: 양성 사례 없음")
            self.assertTrue(any(s in ("absent", "contradicted", "partial") for s in statuses),
                            f"{fact_id}: 음성·경계 사례 없음")

    def test_calibration_cases_validate_against_spec(self):
        spec, cal = ds.load(ISSUE), ds.load_calibration(ISSUE)
        for c in cal.cases:
            ds.validate_calibration_case(spec, c)

    def test_calibration_case_with_bad_status_fails_closed(self):
        spec, cal = ds.load(ISSUE), ds.load_calibration(ISSUE)
        bad = copy.deepcopy(cal.cases[0])
        bad["expected_status"] = "survived"
        with self.assertRaises(ds.SpecError):
            ds.validate_calibration_case(spec, bad)


if __name__ == "__main__":
    unittest.main()
