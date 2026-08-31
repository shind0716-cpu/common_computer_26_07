import unittest

from compare_coders import compare_outputs


class CompareCodersTests(unittest.TestCase):
    def test_pack_a_reports_only_requested_field_mismatches(self):
        left = {
            "pack": "PACK_A",
            "items": [{"id": "A-01", "q1_orientation": "정한 것 지킴", "q2_politics": "우파", "q3_beliefs": [7, 8]}],
        }
        right = {
            "pack": "PACK_A",
            "items": [{"id": "A-01", "q1_orientation": "정한 것 지킴", "q2_politics": "모르겠다", "q3_beliefs": [8]}],
        }
        self.assertEqual(
            compare_outputs(left, right),
            [{"id": "A-01", "fields": {"q2_politics": {"CODER_1": "우파", "CODER_2": "모르겠다"}, "q3_beliefs": {"CODER_1": [7, 8], "CODER_2": [8]}}}],
        )

    def test_pack_b_reports_disagreement_by_fact_number(self):
        base = [{"fact_no": i, "retained": False} for i in range(1, 13)]
        changed = [dict(row) for row in base]
        changed[4]["retained"] = True
        left = {"pack": "PACK_B", "items": [{"id": "B-06", "facts": base}]}
        right = {"pack": "PACK_B", "items": [{"id": "B-06", "facts": changed}]}
        self.assertEqual(
            compare_outputs(left, right),
            [{"id": "B-06", "fields": {"fact_5": {"CODER_1": False, "CODER_2": True}}}],
        )


if __name__ == "__main__":
    unittest.main()
