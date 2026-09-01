import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CompareCodersTests(unittest.TestCase):
    def test_pack_b_emits_every_mismatched_fact_field(self):
        from compare_coders import compare_outputs
        base_fact = {"fact_no": 1, "retained": False, "evidence": None, "rationale": "absent", "confidence": 0.6}
        left = {"pack": "PACK_B", "source_sha256": "a" * 64, "items": [{"id": "B-01", "facts": [base_fact]}]}
        changed = {**base_fact, "retained": True, "evidence": "quote", "rationale": "present", "confidence": 0.9}
        right = {"pack": "PACK_B", "source_sha256": "a" * 64, "items": [{"id": "B-01", "facts": [changed]}]}
        source = {"B-01": {"id": "B-01", "last_notes": "quote", "facts": []}}
        rows = compare_outputs(left, right, source)
        self.assertEqual({"fact_1.retained", "fact_1.evidence", "fact_1.rationale", "fact_1.confidence"}, set(rows[0]["fields"]))
        self.assertEqual("quote", rows[0]["source_item"]["last_notes"])
        self.assertNotIn("coder_family", str(rows))

    def test_source_hash_and_item_field_sets_fail_closed(self):
        from compare_coders import compare_outputs
        item = {"id": "A-01", "q1_orientation": "모르겠다", "q2_politics": "모르겠다", "q3_beliefs": [], "evidence": {}, "confidence": {}}
        left = {"pack": "PACK_A", "source_sha256": "a" * 64, "items": [item]}
        right = copy.deepcopy(left); right["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            compare_outputs(left, right, {"A-01": {"id": "A-01"}})
        right = copy.deepcopy(left); right["items"][0]["id"] = "A-02"
        with self.assertRaisesRegex(ValueError, "item ID set mismatch"):
            compare_outputs(left, right, {"A-01": {"id": "A-01"}})

    def test_pack_c_includes_round_and_requested_field_disagreements(self):
        from compare_coders import compare_outputs
        item = {"id": "C-01", "round_options": {"r0": "x", "r1": "x", "r2": "x", "r3": "x"}, "conclusion_relation": "유지", "first_flip": None, "trajectory_type": None, "evidence": {"r0": "q", "r1": "q", "r2": "q", "r3": "q"}, "confidence": 0.5}
        left = {"pack": "PACK_C", "source_sha256": "a" * 64, "items": [item]}
        right = copy.deepcopy(left); right["items"][0]["round_options"]["r3"] = "y"; right["items"][0]["conclusion_relation"] = "바뀜"
        rows = compare_outputs(left, right, {"C-01": {"id": "C-01"}})
        self.assertEqual({"round_options.r3", "conclusion_relation"}, set(rows[0]["fields"]))
        self.assertEqual({"CODER_1", "CODER_2"}, set(rows[0]["fields"]["conclusion_relation"]))


if __name__ == "__main__":
    unittest.main()
