# -*- coding: utf-8 -*-
"""§11 이원 recall probe 러너 테스트 (LLM 호출 0)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import recall_probe as rp  # noqa: E402
from modules import paths  # noqa: E402


class RecallProbePathTests(unittest.TestCase):
    def test_paths_module_derives_checkpoint_and_pre_mapping_paths(self):
        old = paths.DATA
        try:
            paths.DATA = Path("root")
            self.assertEqual(paths.raw_calls("recall_probe_calls.jsonl"),
                             Path("root/raw_calls/recall_probe_calls.jsonl"))
            self.assertEqual(
                paths.recall_probe_pre_mapping("issue_x", "run_y"),
                Path("root/judgments/recall_probe_pre_mapping_issue_x_run_y.json"),
            )
        finally:
            paths.DATA = old


class RecallProbeParserTests(unittest.TestCase):
    def test_full_parser_preserves_statement_and_validates_attribution(self):
        raw = json.dumps([
            {"statement": "fact A", "source": "assigned", "heard_from": None},
            {"statement": "fact B", "source": "heard", "heard_from": "agent_2"},
            {"statement": "fact C", "source": "inferred", "heard_from": None},
        ])
        self.assertEqual(
            rp.parse_full(raw, {"agent_1", "agent_2"})[1],
            {"statement": "fact B", "source": "heard", "heard_from": "agent_2"},
        )
        for bad in (
            '[{"statement":"x","source":"heard","heard_from":null}]',
            '[{"statement":"x","source":"assigned","heard_from":"agent_2"}]',
            '[{"statement":"x","source":"heard","heard_from":"ghost"}]',
        ):
            with self.subTest(raw=bad), self.assertRaises(rp.ProbeParseError):
                rp.parse_full(bad, {"agent_1", "agent_2"})

    def test_note_parser_reuses_note_slot_and_applies_500_character_budget(self):
        text, truncated = rp.parse_note(json.dumps({"note": "가" * 501}), budget=500)
        self.assertEqual(text, "가" * 500)
        self.assertTrue(truncated)


class RecallProbePromptTests(unittest.TestCase):
    def test_each_arm_has_two_wording_options_and_active_prompts_share_input_verbatim(self):
        self.assertGreaterEqual(len(rp.PROMPT_OPTIONS["probe_full"]), 2)
        self.assertGreaterEqual(len(rp.PROMPT_OPTIONS["probe_note"]), 2)
        shared = "SAME FINAL WINDOW\nView 1 = agent_2"
        full = rp.build_prompt("probe_full", shared)
        note = rp.build_prompt("probe_note", shared)
        self.assertIn(shared, full)
        self.assertIn(shared, note)
        self.assertEqual(full.count(shared), 1)
        self.assertEqual(note.count(shared), 1)
        self.assertNotIn("probe_full", note)
        self.assertNotIn("probe_note", full)


class RecallProbeDryIntegrationTests(unittest.TestCase):
    def test_pilot1_dry_completes_16_planned_calls_with_zero_external_calls_and_no_writes(self):
        data_root = HERE / "data"
        checkpoint = data_root / "raw_calls" / "recall_probe_calls.jsonl"
        before = checkpoint.read_bytes() if checkpoint.exists() else None
        result = rp.run(
            data_root=data_root,
            targets=[rp.Target("issue_ethics_0476", "pilot1")],
            config_path=HERE / "configs" / "pilot1_gpt41.yaml",
            dry=True,
            max_calls=0,
            responder=lambda prompt: self.fail("dry에서 외부 호출 금지"),
        )
        after = checkpoint.read_bytes() if checkpoint.exists() else None
        self.assertEqual(result["planned_calls"], 16)
        self.assertEqual(result["actual_calls"], 0)
        self.assertEqual(result["parsed_rows"], 16)
        self.assertEqual(before, after)

    def test_checkpoint_reentry_reuses_same_prompt_and_rejects_prompt_drift(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "recall.jsonl"
            seen = []
            first = rp.make_checkpoint(
                path, max_calls=1,
                responder=lambda p: seen.append(p) or '[{"statement":"x","source":"inferred","heard_from":null}]',
            )
            first.call("prompt A", "issue|run|agent_1|probe_full")
            resumed = rp.make_checkpoint(
                path, max_calls=0,
                responder=lambda p: self.fail("체크포인트 재사용이어야 함"),
            )
            resumed.call("prompt A", "issue|run|agent_1|probe_full")
            self.assertEqual(seen, ["prompt A"])
            with self.assertRaises(rp.CheckpointMismatch):
                resumed.call("prompt B", "issue|run|agent_1|probe_full")


if __name__ == "__main__":
    unittest.main()
