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
                Path("root/recall_probe/recall_probe_pre_mapping_issue_x_run_y.json"),
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

    def test_one_parse_failure_in_48_rows_is_recorded_without_blocking_file_write(self):
        good = json.dumps([
            {"statement": "fact", "source": "inferred", "heard_from": None},
        ])
        rows = []
        for idx in range(48):
            payload = rp.parse_payload("not-json" if idx == 17 else good,
                                       "probe_full", {"agent_1"})
            rows.append({"agent_id": "agent_1", "arm": "probe_full",
                         "probe_round": idx, "checkpoint_tag": f"tag-{idx}", **payload})

        self.assertEqual(sum(row["parse_status"] == "ok" for row in rows), 47)
        self.assertEqual(sum(row["parse_status"] == "parse_fail" for row in rows), 1)
        with tempfile.TemporaryDirectory() as td:
            old = paths.DATA
            try:
                paths.DATA = Path(td)
                output = rp._write_pre_mapping(rp.Target("issue_x", "run_y"), 3, rows)
            finally:
                paths.DATA = old
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["rows"]), 48)
        failed = [row for row in saved["rows"] if row["parse_status"] == "parse_fail"]
        self.assertEqual(failed[0]["checkpoint_tag"], "tag-17")


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
    def test_shared_inputs_reject_noncontiguous_rounds_before_replay(self):
        with tempfile.TemporaryDirectory() as td:
            data_root = Path(td)
            issue_id = "issue_ethics_0476"
            run_id = "pilot1"
            source_root = HERE / "data"
            for source, destination in (
                (source_root / "issues" / f"{issue_id}.json",
                 data_root / "issues" / f"{issue_id}.json"),
                (source_root / "facts" / f"facts_{issue_id}.json",
                 data_root / "facts" / f"facts_{issue_id}.json"),
                (source_root / "debates" / f"debate_{issue_id}_{run_id}.jsonl",
                 data_root / "debates" / f"debate_{issue_id}_{run_id}.jsonl"),
            ):
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            debate = data_root / "debates" / f"debate_{issue_id}_{run_id}.jsonl"
            events = [json.loads(line) for line in debate.read_text(encoding="utf-8").splitlines()
                      if line.strip()]
            events = [event for event in events
                      if not (event.get("round") == 1 and
                              event.get("event") in {"utterance", "prompt_assembly"})]
            debate.write_text("".join(json.dumps(event, ensure_ascii=False) + "\n"
                                      for event in events), encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "연속.*r0"):
                rp.load_shared_inputs(
                    data_root,
                    rp.Target(issue_id, run_id),
                    HERE / "configs" / "pilot1_gpt41.yaml",
                )

    def test_pilot1_dry_completes_full_timeseries_and_final_note_with_zero_external_calls(self):
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
        self.assertEqual(result["planned_calls"], 40)
        self.assertEqual(result["actual_calls"], 0)
        self.assertEqual(result["parsed_rows"], 40)
        self.assertEqual(result["parse_failed_rows"], 0)
        self.assertEqual(before, after)

    def test_shared_inputs_cover_every_round_for_every_agent(self):
        shared, final_round = rp.load_shared_inputs(
            HERE / "data",
            rp.Target("issue_ethics_0476", "pilot1"),
            HERE / "configs" / "pilot1_gpt41.yaml",
        )
        self.assertEqual(final_round, 3)
        self.assertEqual(set(shared), {f"agent_{idx}" for idx in range(1, 9)})
        self.assertTrue(all(set(by_round) == {0, 1, 2, 3}
                            for by_round in shared.values()))

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
