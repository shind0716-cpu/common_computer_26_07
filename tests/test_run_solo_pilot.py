"""Solo development-pilot policy and durable provenance (LLM calls: 0)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from experiments.memory_structure import run_solo


class SoloPilotPolicyTests(unittest.TestCase):
    def test_pilot_policy_fails_closed_on_cap_or_eligibility_mismatch(self):
        invalid = [
            {"max_llm_calls": None},
            {"max_llm_calls": 31},
            {"max_llm_calls": 30, "aggregate_eligible": True},
            {"max_llm_calls": 30, "report_eligible": True},
        ]
        for override in invalid:
            with self.subTest(override=override):
                kwargs = {"promotion_tier": "pilot_unvetted",
                          "max_llm_calls": 30,
                          "aggregate_eligible": False,
                          "report_eligible": False}
                kwargs.update(override)
                with self.assertRaises(SystemExit):
                    run_solo.validate_execution_policy(**kwargs)

    def test_pilot_policy_returns_exact_nonpromotion_labels(self):
        self.assertEqual(
            run_solo.validate_execution_policy(
                promotion_tier="pilot_unvetted", max_llm_calls=30,
                aggregate_eligible=False, report_eligible=False),
            {"promotion_tier": "pilot_unvetted", "max_llm_calls": 30,
             "aggregate_eligible": False, "report_eligible": False},
        )

    def test_dry_run_persists_pilot_labels_in_output(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(run_solo, "RUNS_DIR", Path(td)):
            run_solo.select_issue("issue_camp", None)
            facts = run_solo.load_facts_block(issue_id="issue_camp")
            dst = run_solo.run_one(
                "gpt", "api", "A", "full", 991, facts, 30, True,
                issue_id="issue_camp", promotion_tier="pilot_unvetted",
                max_llm_calls=30, aggregate_eligible=False,
                report_eligible=False,
            )
            meta = json.loads(dst.read_text(encoding="utf-8"))["meta"]
        self.assertEqual(meta["promotion_tier"], "pilot_unvetted")
        self.assertEqual(meta["max_llm_calls"], 30)
        self.assertIs(meta["aggregate_eligible"], False)
        self.assertIs(meta["report_eligible"], False)


if __name__ == "__main__":
    unittest.main()