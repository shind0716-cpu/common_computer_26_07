import unittest

from merge_adjudication import merge_pack_a


class MergeAdjudicationTests(unittest.TestCase):
    def test_pack_a_uses_agreement_and_adjudicated_disagreement(self):
        left = {"items": [{"id": "A-01", "q1_orientation": "정한 것 지킴", "q2_politics": "우파", "q3_beliefs": [8], "evidence": {"q1": "q1-left", "q2": "q2-left", "q3": {"8": "q3-left"}}, "confidence": {"q1": 0.8, "q2": 0.7, "q3": 0.8}, "ambiguity_note": None}]}
        right = {"items": [{"id": "A-01", "q1_orientation": "정한 것 지킴", "q2_politics": "모르겠다", "q3_beliefs": [8], "evidence": {"q1": "q1-right", "q2": "q2-right", "q3": {"8": "q3-right"}}, "confidence": {"q1": 0.9, "q2": 0.6, "q3": 0.9}, "ambiguity_note": None}]}
        adjudication = {"resolutions": [{"id": "A-01", "fields": {"q2_politics": {"value": "모르겠다", "evidence": "q2-adj", "rationale": "판정", "confidence": 0.95}}}]}
        merged = merge_pack_a(left, right, adjudication)
        self.assertEqual(merged[0]["q1_orientation"], "정한 것 지킴")
        self.assertEqual(merged[0]["evidence"]["q1"], "q1-left")
        self.assertEqual(merged[0]["q2_politics"], "모르겠다")
        self.assertEqual(merged[0]["evidence"]["q2"], "q2-adj")
        self.assertEqual(merged[0]["q3_beliefs"], [8])


if __name__ == "__main__":
    unittest.main()
