# -*- coding: utf-8 -*-
"""논문 재현 러너의 계약·안전장치 테스트 (LLM 호출 0)."""
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

import assign_perspective as assign  # noqa: E402
import extract_facts as extract  # noqa: E402


class ExtractFactsTests(unittest.TestCase):
    def test_build_facts_doc_matches_fixture_shape_and_positional_ids(self):
        doc = extract.build_facts_doc(
            issue_id="issue_ethics_0036",
            refined=["one", "two"],
            important=[True, False],
            created_at="2026-08-10T00:00:00+00:00",
            prompt_ver="delibtrace@test",
        )
        fixture = json.loads((HERE / "fixtures" / "data" / "facts" /
                              "facts_issue_repro_fx.json").read_text(encoding="utf-8"))
        self.assertEqual(set(doc), set(fixture))
        self.assertEqual(set(doc["facts"][0]), set(fixture["facts"][0]))
        self.assertEqual([f["fact_id"] for f in doc["facts"]],
                         ["fact_ethics_0036_01", "fact_ethics_0036_02"])
        self.assertEqual([f["origin_index"] for f in doc["facts"]], [0, 1])
        self.assertEqual([f["critical"] for f in doc["facts"]], [True, False])

    def test_build_facts_doc_rejects_mismatched_select_length(self):
        with self.assertRaises(ValueError):
            extract.build_facts_doc("issue_ethics_0001", ["one"], [True, False],
                                    "2026-08-10T00:00:00+00:00", "test")

    def test_build_facts_doc_accepts_probe_integer_flags_as_contract_bools(self):
        probe = json.loads((HERE / "probe" / "probe_result.json").read_text(encoding="utf-8"))
        important = probe["results"][0]["by_model"]["gpt-5"]["important_title"]
        refined = [f"fact {i}" for i in range(len(important))]
        doc = extract.build_facts_doc(
            "issue_ethics_0001", refined, important,
            "2026-08-10T00:00:00+00:00", "delibtrace@test")
        critical = [fact["critical"] for fact in doc["facts"]]
        self.assertEqual(critical, [bool(value) for value in important])
        self.assertTrue(all(isinstance(value, bool) for value in critical))
        for invalid in (2, -1, 1.0, "1"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                extract.build_facts_doc(
                    "issue_ethics_0001", ["fact"], [invalid],
                    "2026-08-10T00:00:00+00:00", "delibtrace@test")

    def test_checkpoint_appends_raw_and_resumes_by_tag_without_second_call(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "calls.jsonl"
            seen = []
            calls = extract.CallCheckpoint(path, max_calls=1,
                                           responder=lambda prompt: seen.append(prompt) or '["ok"]')
            self.assertEqual(calls.call("prompt", "x|initial"), '["ok"]')
            resumed = extract.CallCheckpoint(path, max_calls=0,
                                             responder=lambda prompt: self.fail("must resume"))
            self.assertEqual(resumed.call("ignored", "x|initial"), '["ok"]')
            record = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(record["raw"], '["ok"]')
            self.assertEqual(seen, ["prompt"])

    def test_checkpoint_raises_at_global_call_cap(self):
        with tempfile.TemporaryDirectory() as td:
            calls = extract.CallCheckpoint(Path(td) / "calls.jsonl", max_calls=0,
                                           responder=lambda prompt: '["unexpected"]')
            with self.assertRaises(RuntimeError):
                calls.call("prompt", "x|initial")


class AssignPerspectiveTests(unittest.TestCase):
    def test_build_assignment_matches_fixture_shape_and_pairs(self):
        facts = [
            {"fact_id": f"fact_ethics_0036_{i + 1:02d}", "origin_index": i,
             "text": f"fact {i}", "tags": [], "critical": i == 0,
             "prior": {"score": None, "probe_model": None,
                       "probe_prompt_ver": None, "probed_at": None}}
            for i in range(5)
        ]
        sets = [[0, 1], [0, 2], [0, 3], [0, 4]]
        doc = assign.build_assignment_doc(
            "issue_ethics_0036", facts, sets,
            "2026-08-10T00:00:00+00:00")
        fixture = json.loads((HERE / "fixtures" / "data" / "assignments" /
                              "assignment_issue_repro_fx.json").read_text(encoding="utf-8"))
        self.assertEqual(set(doc), set(fixture))
        self.assertEqual(set(doc["agents"][0]), set(fixture["agents"][0]))
        self.assertEqual(doc["seed"], 20260810)
        self.assertEqual(doc["perspective_sets"]["sets"], sets)
        for i in range(0, 8, 2):
            self.assertEqual(doc["agents"][i]["assigned_fact_ids"],
                             doc["agents"][i + 1]["assigned_fact_ids"])

    def test_author_rule_audit_counts_semantic_violations(self):
        facts = [{"critical": i == 0} for i in range(5)]
        ok = assign.audit_perspective_sets([[0, 1], [0, 2], [0, 3], [0, 4]], facts)
        self.assertEqual(ok, [])
        bad = assign.audit_perspective_sets([[1], [1], [1], [1]], facts)
        self.assertIn("critical_missing", bad)
        self.assertIn("fact_uncovered", bad)

    def test_author_check_available_requires_exactly_four_lists(self):
        self.assertTrue(assign.check_available("body", "question", [], [[], [], [], []]))
        self.assertFalse(assign.check_available("body", "question", [], [[], [], []]))
        self.assertFalse(assign.check_available("body", "question", [], "not-a-list"))


if __name__ == "__main__":
    unittest.main()
