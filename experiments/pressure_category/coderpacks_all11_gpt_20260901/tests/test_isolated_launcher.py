import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONTROLS = {"tools_sent": 0, "tool_choice": "none", "mcp_servers": 0, "session_persistence": False, "agent_loop": False}


class LauncherTests(unittest.TestCase):
    def test_sol_runner_preserves_provider_response_id_without_tools(self):
        from sol_toolless_runner import _run_stateless_codex_response

        output = SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text='{"probe":"ok"}')])
        final = SimpleNamespace(id="resp-provider-owned", model="gpt-5.6-sol", output=[output])

        class Responses:
            def __init__(self):
                self.kwargs = None

            def create(self, **kwargs):
                self.kwargs = kwargs
                return final

        responses = Responses()
        client = SimpleNamespace(_real_client=SimpleNamespace(responses=responses))
        content, model, request_id = _run_stateless_codex_response(client, "gpt-5.6-sol", "probe")
        self.assertEqual('{"probe":"ok"}', content)
        self.assertEqual("gpt-5.6-sol", model)
        self.assertEqual("resp-provider-owned", request_id)
        self.assertFalse(responses.kwargs["store"])
        self.assertTrue(responses.kwargs["stream"])
        self.assertNotIn("tools", responses.kwargs)
        self.assertNotIn("tool_choice", responses.kwargs)

    def test_fake_runtime_receipt_is_orchestrator_owned_and_complete(self):
        from isolated_launcher import launch, fake_adapter
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack, prompt, output, receipt = root/"PACK_A_final.md", root/"prompt.txt", root/"out.json", root/"receipt.json"
            pack.write_text("PACK", encoding="utf-8")
            prompt.write_text("PROMPT", encoding="utf-8")
            result = launch(fake_adapter(), pack, prompt, output, receipt, requested_model="claude-test")
            required = {"schema", "launch_nonce", "executable", "arguments", "requested_identity", "provider_resolved_identity", "pid", "ppid", "process_create_time", "bundle_path", "bundle_sha256", "input_sha256", "session_id", "provider_request_id", "provider_auxiliary_models", "resumed", "runtime_controls", "started_at", "ended_at", "exit_code", "stdout_sha256", "stderr_sha256", "output_sha256", "preexisting_family_pids", "fresh_process"}
            self.assertEqual(required, set(result))
            self.assertTrue(result["fresh_process"])
            self.assertEqual("Claude", result["provider_resolved_identity"]["family"])
            self.assertEqual("provider-response", result["provider_resolved_identity"]["source"])
            self.assertEqual(CONTROLS, result["runtime_controls"])
            self.assertEqual(result, json.loads(receipt.read_text(encoding="utf-8")))

    def test_false_identity_resumed_nonce_and_pid_collision_are_rejected(self):
        from isolated_launcher import validate_receipt
        base = {"launch_nonce":"n", "provider_resolved_identity":{"family":"Claude","model":"claude-test","provider":"fake","source":"provider-response"}, "requested_identity":{"family":"Claude","model":"claude-test","provider":"fake"}, "pid":200, "ppid":100, "process_create_time":2.0, "preexisting_family_pids":[199], "fresh_process":True, "session_id":"fresh", "provider_request_id":"req", "resumed":False, "runtime_controls":CONTROLS, "exit_code":0, "bundle_sha256":"a"*64, "input_sha256":"b"*64, "stdout_sha256":"c"*64, "stderr_sha256":"d"*64, "output_sha256":"e"*64}
        validate_receipt(base, expected_nonce="n", expected_family="Claude")
        for field, value in (("launch_nonce", "copied"), ("pid", 199), ("resumed", True)):
            bad = json.loads(json.dumps(base)); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_receipt(bad, expected_nonce="n", expected_family="Claude")
        bad = json.loads(json.dumps(base)); bad["provider_resolved_identity"]["source"] = "self-report"
        with self.assertRaises(ValueError):
            validate_receipt(bad, expected_nonce="n", expected_family="Claude")

    def test_same_family_rejected_and_distinct_real_adapters_exist(self):
        from isolated_launcher import assert_distinct_families, claude_adapter, sol_adapter
        with self.assertRaisesRegex(ValueError, "same-family"):
            assert_distinct_families("Claude", "Claude")
        claude, sol = claude_adapter(requested_model="claude-opus-5"), sol_adapter(requested_model="gpt-5.6-sol")
        assert_distinct_families(claude.family, sol.family)
        self.assertEqual(("anthropic", "openai-codex"), (claude.provider, sol.provider))

    def test_claude_adapter_and_bundle_allowlist_remove_capabilities_and_key(self):
        from isolated_launcher import capability_deny_log, claude_adapter, create_bundle
        adapter = claude_adapter("claude", requested_model="claude-opus-5")
        args = " ".join(adapter.arguments)
        for flag in ("--tools", "--no-session-persistence", "--safe-mode", "--strict-mcp-config", "--mcp-config", "--output-format", "--model"):
            self.assertIn(flag, args)
        self.assertFalse(adapter.allow_filesystem)
        self.assertFalse(adapter.allow_web)
        self.assertFalse(adapter.allow_session_history)
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory)/"src", Path(directory)/"bundle"
            src.mkdir()
            for name in ("prompt.txt", "PACK_A_final.md", "coding_output.schema.json", "_KEY_all11_gpt.json", "PACK_B_factcheck.md"):
                (src/name).write_text(name, encoding="utf-8")
            manifest = create_bundle(dst, {"prompt.txt":src/"prompt.txt", "PACK_A_final.md":src/"PACK_A_final.md", "coding_output.schema.json":src/"coding_output.schema.json"})
            self.assertEqual({"prompt.txt", "PACK_A_final.md", "coding_output.schema.json", "BUNDLE_MANIFEST.json"}, {path.name for path in dst.iterdir()})
            self.assertNotIn("_KEY", json.dumps(manifest))
            denied = capability_deny_log({"runtime_controls": CONTROLS})
            self.assertTrue(all(row["status"] == "DENIED" for row in denied))
            self.assertTrue(all(row["basis"] == "observed provider request/launch controls" for row in denied))


if __name__ == "__main__":
    unittest.main()
