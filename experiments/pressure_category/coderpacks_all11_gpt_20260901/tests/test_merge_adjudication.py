import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _digest(data):
    return hashlib.sha256((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).hexdigest()


def coders():
    left = {"pack": "PACK_A", "coder_id": "C1", "source_sha256": "1" * 64, "items": [{"id": "A-01", "q1_orientation": "모르겠다", "q2_politics": "좌파", "q3_beliefs": [], "evidence": {}, "confidence": {}}]}
    right = {"pack": "PACK_A", "coder_id": "C2", "source_sha256": "1" * 64, "items": [{"id": "A-01", "q1_orientation": "모르겠다", "q2_politics": "우파", "q3_beliefs": [], "evidence": {}, "confidence": {}}]}
    from compare_coders import compare_outputs
    source_items = {"A-01": {"id": "A-01"}}
    disagreements = {"schema": "all11_gpt_disagreements_v2", "pack": "PACK_A", "coder_labels": ["CODER_1", "CODER_2"], "coder_artifact_sha256": [_digest(left), _digest(right)], "disagreements": compare_outputs(left, right, source_items)}
    return left, right, disagreements


def call_merge(left, right, disagreements, adjudication):
    from merge_adjudication import merge_consensus
    left.setdefault("source_sha256", "1" * 64)
    right.setdefault("source_sha256", "1" * 64)
    source_items = {item["id"]: {"id": item["id"]} for item in left["items"]}
    disagreements.setdefault("schema", "all11_gpt_disagreements_v2")
    disagreements.setdefault("coder_labels", ["CODER_1", "CODER_2"])
    disagreements.setdefault("coder_artifact_sha256", [_digest(left), _digest(right)])
    return merge_consensus(left, right, disagreements, adjudication, source_items=source_items, left_sha256=_digest(left), right_sha256=_digest(right))


class MergeAdjudicationTests(unittest.TestCase):
    def test_merge_rejects_missing_resolution(self):
        left, right, disagreements = coders()
        with self.assertRaisesRegex(ValueError, "missing adjudication"):
            call_merge(left, right, disagreements, {"pack": "PACK_A", "resolutions": []})

    def test_merge_rejects_disagreement_field_set_mismatch(self):
        left, right, disagreements = coders()
        disagreements["disagreements"][0]["fields"] = {"q1_orientation": {}}
        with self.assertRaisesRegex(ValueError, "disagreement content mismatch"):
            call_merge(left, right, disagreements, {"pack": "PACK_A", "resolutions": []})

    def test_consensus_preserves_status_and_both_coder_provenance(self):
        left, right, disagreements = coders()
        adjudication = {"pack": "PACK_A", "resolutions": [{"id": "A-01", "fields": {"q2_politics": {"coding_status": "adjudicated", "value": "모르겠다", "session_handle": "adj-1"}}}]}
        result = call_merge(left, right, disagreements, adjudication)
        q1 = result["items"][0]["fields"]["q1_orientation"]
        q2 = result["items"][0]["fields"]["q2_politics"]
        self.assertEqual("audited_agreement", q1["coding_status"])
        self.assertEqual("adjudicated", q2["coding_status"])
        self.assertEqual({"coder_1", "coder_2", "adjudication"}, set(q2["provenance"]))
        self.assertEqual("좌파", q2["provenance"]["coder_1"]["value"])
        self.assertEqual("우파", q2["provenance"]["coder_2"]["value"])
        self.assertEqual(_digest(left), q2["provenance"]["coder_1"]["artifact_sha256"])
        self.assertEqual(_digest(right), q2["provenance"]["coder_2"]["artifact_sha256"])

    def test_pack_b_consensus_has_one_record_per_fact_and_never_primary_only(self):
        fact = {"fact_no": 1, "retained": False, "evidence": None, "rationale": "absent", "confidence": .5}
        left = {"pack":"PACK_B","coder_id":"C1","source_sha256":"1"*64,"items":[{"id":"B-01","facts":[fact]}]}
        right = copy.deepcopy(left); right["coder_id"]="C2"
        result = call_merge(left,right,{"pack":"PACK_B","disagreements":[]},{"pack":"PACK_B","resolutions":[]})
        fields=result["items"][0]["fields"]
        self.assertEqual({"fact_1.retained","fact_1.evidence","fact_1.rationale","fact_1.confidence"},set(fields))
        for record in fields.values():
            self.assertEqual("audited_agreement",record["coding_status"])
            self.assertEqual({"coder_1","coder_2"},set(record["provenance"]))

    def test_unresolved_requires_null_value(self):
        left, right, disagreements = coders()
        adjudication = {"pack": "PACK_A", "resolutions": [{"id": "A-01", "fields": {"q2_politics": {"coding_status": "unresolved", "value": "좌파"}}}]}
        with self.assertRaisesRegex(ValueError, "unresolved value must be null"):
            call_merge(left, right, disagreements, adjudication)


if __name__ == "__main__":
    unittest.main()
