import unittest

from merge_adjudication import merge_pack_a, merge_pack_b, merge_pack_c


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

    def test_pack_b_replaces_only_audited_disagreement(self):
        primary = {"items": [{"id": "B-01", "facts": [{"fact_no": 1, "retained": False, "evidence": None, "rationale": "primary", "confidence": 0.8}], "ambiguity_note": None}, {"id": "B-02", "facts": [{"fact_no": 1, "retained": True, "evidence": "agreed", "rationale": "primary", "confidence": 0.9}], "ambiguity_note": None}]}
        audit = {"items": [{"id": "B-01", "facts": [{"fact_no": 1, "retained": True, "evidence": "audit", "rationale": "audit", "confidence": 0.7}]}]}
        adjudication = {"resolutions": [{"id": "B-01", "fields": {"fact_1": {"value": True, "evidence": "adjudicated", "rationale": "resolved", "confidence": 0.95}}}]}
        merged = merge_pack_b(primary, audit, adjudication)
        self.assertTrue(merged[0]["facts"][0]["retained"])
        self.assertEqual(merged[0]["facts"][0]["evidence"], "adjudicated")
        self.assertEqual(merged[0]["facts"][0]["rationale"], "resolved")
        self.assertEqual(merged[1]["facts"][0]["evidence"], "agreed")

    def test_pack_c_uses_adjudicated_rounds_and_disputed_fields(self):
        first = {"items": [{"id": "C-01", "round_options": {"r0": "A", "r1": "A", "r2": "B", "r3": "B"}, "conclusion_relation": "바뀜", "first_flip": "r2", "change_type": "설득", "evidence": {"r0": "first r0", "decisive": "first r2"}, "confidence": 0.8, "ambiguity_note": None}]}
        second = {"items": [{"id": "C-01", "round_options": {"r0": "A", "r1": "B", "r2": "B", "r3": "B"}, "conclusion_relation": "바뀜", "first_flip": "r1", "change_type": "오락가락", "evidence": {"r0": "second r0", "decisive": "second r1"}, "confidence": 0.7, "ambiguity_note": None}]}
        adjudication = {"resolutions": [{"id": "C-01", "round_options": {"r0": "A", "r1": "B", "r2": "B", "r3": "B"}, "evidence": {"r0": "adj r0", "decisive": "adj r1"}, "fields": {"first_flip": {"value": "r1", "rationale": "resolved", "confidence": 0.95}, "change_type": {"value": "설득", "rationale": "resolved", "confidence": 0.9}}}]}
        merged = merge_pack_c(first, second, adjudication)
        self.assertEqual(merged[0]["round_options"]["r1"], "B")
        self.assertEqual(merged[0]["conclusion_relation"], "바뀜")
        self.assertEqual(merged[0]["first_flip"], "r1")
        self.assertEqual(merged[0]["change_type"], "설득")
        self.assertEqual(merged[0]["evidence"], {"r0": "adj r0", "decisive": "adj r1"})
        self.assertEqual(merged[0]["confidence"], 0.9)


if __name__ == "__main__":
    unittest.main()
