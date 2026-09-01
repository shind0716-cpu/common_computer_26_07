import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
class ArtifactSchemaTests(unittest.TestCase):
    def test_five_stage_schemas_are_separate_strict_and_launch_is_sixth(self):
        import jsonschema
        names=("first_pass","disagreement","adjudication","consensus","freeze","launch_receipt")
        for name in names:
            path=ROOT/"schemas"/f"{name}.schema.json"
            schema=json.loads(path.read_text(encoding="utf-8")); jsonschema.Draft202012Validator.check_schema(schema)
            self.assertFalse(schema.get("additionalProperties",True),name)
            self.assertTrue(schema.get("required"),name)
    def test_consensus_schema_rejects_primary_only_provenance(self):
        from artifact_contracts import validate_artifact
        fields = {}
        for number in range(1, 13):
            for field in ("retained", "evidence", "rationale", "confidence"):
                name = f"fact_{number}.{field}"
                value = False if field == "retained" else (None if field == "evidence" else ("absent" if field == "rationale" else 0.5))
                fields[name] = {"value": value, "coding_status": "audited_agreement", "provenance": {"coder_1": {"coder_id": "C1", "artifact_sha256": "a" * 64, "value": value}, "coder_2": {"coder_id": "C2", "artifact_sha256": "b" * 64, "value": value}}}
        good={"schema":"all11_gpt_consensus_v2","pack":"PACK_B","coder_artifacts":[{"coder_id":"C1","sha256":"a"*64},{"coder_id":"C2","sha256":"b"*64}],"items":[{"id":f"B-{number:02d}","fields":json.loads(json.dumps(fields))} for number in range(1,34)]}
        validate_artifact("consensus",good)
        del good["items"][0]["fields"]["fact_1.retained"]["provenance"]["coder_2"]
        with self.assertRaises(ValueError): validate_artifact("consensus",good)
    def test_freeze_requires_both_coders_consensus_and_launch_hashes(self):
        from artifact_contracts import validate_artifact
        freeze={"schema":"all11_gpt_freeze_v1","created_at":"2026-09-01T00:00:00+00:00","pack_freezes":{"PACK_A":"a"*64,"PACK_B":"b"*64,"PACK_C":"c"*64},"coder_output_sha256":["d"*64,"e"*64,"f"*64,"1"*64,"2"*64,"3"*64],"consensus_sha256":{"PACK_A":"4"*64,"PACK_B":"5"*64,"PACK_C":"6"*64},"launch_receipt_sha256":[f"{digit}"*64 for digit in "789abc"],"unresolved_fields":0,"key_released":False}
        validate_artifact("freeze",freeze)
        freeze["coder_output_sha256"].pop()
        with self.assertRaises(ValueError): validate_artifact("freeze",freeze)
if __name__=="__main__": unittest.main()
