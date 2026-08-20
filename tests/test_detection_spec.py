"""DetectionSpec 로더·검증기 계약 테스트.

브리프 CLAUDE_IMPLEMENTATION_BRIEF_throne_detection_v0.md §5C·§6 을 그대로 옮긴 것이다.
핵심은 **fail-closed** — 모르는 것을 0점이나 absent 로 조용히 바꾸지 않는다.
"""

import copy
import json
import tempfile
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

    **이 절의 테스트 이름은 실제 거부 사유와 같아야 한다.** 처음에는
    `test_v1_records_rejected_against_v2_spec` 하나로 두고 "판본 격리가 된다"고 읽었는데,
    실제 거부 사유는 CSV 에 `issue_id` 칼럼이 없다는 것이었다 — fact_id 검사에 닿지도
    못했다. 통과하는데 무엇이 통과했는지 모르는 테스트라 아래처럼 갈랐다.
    """

    CSV = Path("experiments/scenario_generalization/THRONE_R0_SEMANTIC_CODING_DRAFT.csv")
    # 이 표는 v1 재료를 보고 손으로 적었고, 그때는 명세가 없었다.
    V1_DECL = {"issue_id": "issue_throne", "spec_version": "pre-spec"}

    def rows(self):
        return ds.read_coding_csv(self.CSV, **self.V1_DECL)

    def test_v1_coding_csv_is_readable(self):
        rows = self.rows()
        self.assertEqual(len(rows), 108)
        self.assertEqual({r["text_role"] for r in rows}, {"essay_r0"})

    def test_reader_requires_explicit_version_declaration(self):
        """기본값이 있으면 판본 없는 표가 아무 명세로나 통과한다."""
        with self.assertRaises(TypeError):
            ds.read_coding_csv(self.CSV)

    def test_reader_stamps_declared_identity(self):
        r = self.rows()[0]
        self.assertEqual(r["issue_id"], "issue_throne")
        self.assertEqual(r["spec_version"], "pre-spec")

    def test_v1_records_rejected_by_issue_mismatch(self):
        """진짜 거부 사유. v1 표를 v2 명세에 대면 이슈가 다르다."""
        spec = ds.load(ISSUE)
        with self.assertRaises(ds.SpecError) as cm:
            ds.validate_record(spec, self.rows()[0])
        self.assertIn("이슈 불일치", str(cm.exception))

    def test_v1_fact_id_rejected_even_when_issue_is_stamped_v2(self):
        """fact_id 판본 격리를 **따로** 잰다. 이슈를 v2 로 찍어도 v1 fact_id 는 막혀야 한다."""
        spec = ds.load(ISSUE)
        rec = dict(self.rows()[0], issue_id=ISSUE, spec_version=spec.spec_version,
                   judge_kind="human")
        self.assertTrue(rec["fact_id"].startswith("fact_throne_0"))   # v1 이름
        with self.assertRaises(ds.SpecError) as cm:
            ds.validate_record(spec, rec)
        self.assertIn("명세에 없는 fact_id", str(cm.exception))

    def test_missing_spec_version_fails_closed(self):
        """「없으면 통과」 구멍이 다시 생기지 않게 못 박는다."""
        spec = ds.load(ISSUE)
        rec = base_record()
        del rec["spec_version"]
        with self.assertRaises(ds.SpecError):
            ds.validate_record(spec, rec)

    def test_reader_refuses_to_overwrite_conflicting_identity(self):
        """파일에 이미 판본이 적혀 있는데 다르게 선언하면 죽는다 — 조용히 덮지 않는다."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "coding.csv"
            p.write_text(
                "issue_id,spec_version,fact_id,preservation_status,mention_mode,"
                "relation_engaged,provenance_class\n"
                "issue_throne,pre-spec,fact_throne_01,faithful,asserted,true,obs\n",
                encoding="utf-8")
            ds.read_coding_csv(p, issue_id="issue_throne", spec_version="pre-spec")  # 일치 OK
            with self.assertRaises(ds.SpecError) as cm:
                ds.read_coding_csv(p, issue_id="issue_throne_v2", spec_version="pre-spec")
            self.assertIn("충돌", str(cm.exception))

    def test_dataset_role_is_preserved(self):
        self.assertTrue(all(r["provenance_class"] == "observed/development-only"
                            for r in self.rows()))


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
