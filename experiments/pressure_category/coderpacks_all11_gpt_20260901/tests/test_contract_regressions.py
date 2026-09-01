import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT))


def tiny_coders():
    left = {"pack": "PACK_A", "coder_id": "C1", "source_sha256": "1" * 64, "items": [{"id": "A-01", "q1_orientation": "모르겠다", "q2_politics": "좌파", "q3_beliefs": [], "evidence": {}, "confidence": {}}]}
    right = copy.deepcopy(left)
    right["coder_id"] = "C2"
    right["items"][0]["q2_politics"] = "우파"
    return left, right


class ContractRegressionTests(unittest.TestCase):
    def test_first_pass_contract_is_v2_and_excludes_coder_self_identity(self):
        for name in ("coding_output.schema.json", "schemas/first_pass.schema.json"):
            schema = json.loads((ROOT / name).read_text(encoding="utf-8"))
            self.assertEqual("20260901-all11-v2", schema["properties"]["instruction_version"]["const"])
            for forbidden in ("coder_family", "resolved_model", "session_handle"):
                self.assertNotIn(forbidden, schema["required"])
                self.assertNotIn(forbidden, schema["properties"])

    def test_consensus_requires_exact_pack_matrix_not_one_item(self):
        from artifact_contracts import validate_artifact
        tiny = {"schema": "all11_gpt_consensus_v2", "pack": "PACK_B", "coder_artifacts": [{"coder_id": "C1", "sha256": "a" * 64}, {"coder_id": "C2", "sha256": "b" * 64}], "items": [{"id": "B-01", "fields": {"fact_1.retained": {"value": False, "coding_status": "audited_agreement", "provenance": {"coder_1": {"coder_id": "C1", "artifact_sha256": "a" * 64, "value": False}, "coder_2": {"coder_id": "C2", "artifact_sha256": "b" * 64, "value": False}}}}}]}
        with self.assertRaisesRegex(ValueError, "exact consensus matrix"):
            validate_artifact("consensus", tiny)

    def test_merge_binds_common_source_actual_byte_hashes_and_disagreement_values(self):
        from merge_adjudication import merge_consensus
        left, right = tiny_coders()
        left_raw = json.dumps(left, ensure_ascii=False, indent=2).encode() + b"\n"
        right_raw = json.dumps(right, ensure_ascii=False, indent=4).encode() + b"\n"
        lh, rh = hashlib.sha256(left_raw).hexdigest(), hashlib.sha256(right_raw).hexdigest()
        from compare_coders import compare_outputs
        source_items = {"A-01": {"id": "A-01"}}
        disagreement = {"schema": "all11_gpt_disagreements_v2", "pack": "PACK_A", "coder_labels": ["CODER_1", "CODER_2"], "coder_artifact_sha256": [lh, rh], "disagreements": compare_outputs(left, right, source_items)}
        adjudication = {"pack": "PACK_A", "resolutions": [{"id": "A-01", "fields": {"q2_politics": {"coding_status": "adjudicated", "value": "모르겠다"}}}]}
        result = merge_consensus(left, right, disagreement, adjudication, source_items=source_items, left_sha256=lh, right_sha256=rh)
        self.assertEqual(lh, result["coder_artifacts"][0]["sha256"])
        self.assertEqual(rh, result["coder_artifacts"][1]["sha256"])
        bad_source = copy.deepcopy(right); bad_source["source_sha256"] = "2" * 64
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            merge_consensus(left, bad_source, disagreement, adjudication, source_items={"A-01": {"id": "A-01"}}, left_sha256=lh, right_sha256=rh)
        bad = copy.deepcopy(disagreement); bad["coder_artifact_sha256"][0] = "f" * 64
        with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
            merge_consensus(left, right, bad, adjudication, source_items={"A-01": {"id": "A-01"}}, left_sha256=lh, right_sha256=rh)
        bad = copy.deepcopy(disagreement); bad["disagreements"][0]["fields"]["q2_politics"]["CODER_1"] = "거짓"
        with self.assertRaisesRegex(ValueError, "disagreement content mismatch"):
            merge_consensus(left, right, bad, adjudication, source_items={"A-01": {"id": "A-01"}}, left_sha256=lh, right_sha256=rh)

    def test_builder_requires_key_directory_outside_repository(self):
        from build_packs import build
        with tempfile.TemporaryDirectory() as d:
            public = Path(d) / "public"
            with self.assertRaisesRegex(ValueError, "outside repository"):
                build(public, repo=REPO, key_output_dir=ROOT / "private-test")
            with self.assertRaisesRegex(ValueError, "required"):
                build(public, repo=REPO)

    def test_real_adapters_are_structured_toolless_and_not_synthetic_denials(self):
        from isolated_launcher import claude_adapter, sol_adapter, capability_deny_log
        claude = claude_adapter("claude", requested_model="claude-opus-5")
        args = list(claude.arguments)
        self.assertIn("--output-format", args)
        self.assertIn("json", args)
        self.assertIn("--model", args)
        self.assertIn("claude-opus-5", args)
        self.assertIn("--safe-mode", args)
        self.assertIn("--mcp-config", args)
        sol = sol_adapter(requested_model="gpt-5.6-sol")
        self.assertEqual("Hermes-Sol", sol.family)
        self.assertIn("sol_toolless_runner.py", " ".join(sol.arguments))
        receipt = {"runtime_controls": {"tools_sent": 0, "tool_choice": "none", "mcp_servers": 0, "session_persistence": False, "agent_loop": False}}
        rows = capability_deny_log(receipt)
        self.assertTrue(all(row["basis"] == "observed provider request/launch controls" for row in rows))


if __name__ == "__main__":
    unittest.main()
