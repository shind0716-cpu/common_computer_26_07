"""issue_award_v2 정본 재료 계약과 v1/파일럿 불변성."""

import hashlib
import importlib
import json
import unittest
from pathlib import Path

from modules import paths

ROOT = Path(__file__).resolve().parent.parent
V1 = "issue_award"
V2 = "issue_award_v2"

# 2026-08-20 v2 작업 직전 지문. old material과 prior 파일럿 원자료는 불변이다.
PRESERVED_SHA256 = {
    "data/issues/issue_award.json": "ce6c64354fd90b8017d643b59131f7bfc0a3078048f90a9f05e714817a3ba293",
    "data/facts/facts_issue_award.json": "e10393cdde53813a133aa4261f06f6776d3770645f0cf4487ddccdb619aa1078",
    "data/assignments/assignment_issue_award.json": "24ee409a9ee38f668457398a11917a965b811524fa72be1ac3116cf1a0686f7e",
    "시나리오/issue_award.json": "ce6c64354fd90b8017d643b59131f7bfc0a3078048f90a9f05e714817a3ba293",
    "시나리오/facts_issue_award.json": "e10393cdde53813a133aa4261f06f6776d3770645f0cf4487ddccdb619aa1078",
    "시나리오/assignment_issue_award.json": "24ee409a9ee38f668457398a11917a965b811524fa72be1ac3116cf1a0686f7e",
    "시나리오/prior_issue_award.json": "44f09801037a975cb0f4d66975c240a49dee491629cbf65072c65a80c5165158",
    "시나리오/prior_issue_award.partial.jsonl": "474cee3c64c0a5ab1f93571c3fd4e5b51bbe25eb5fbf9b6730a79eef6d6ee360",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AwardV1PreservationTests(unittest.TestCase):
    def test_old_material_and_pilot_raw_bytes_are_unchanged(self):
        for relative, expected in PRESERVED_SHA256.items():
            with self.subTest(path=relative):
                self.assertEqual(sha(ROOT / relative), expected)


class AwardV2IdentityTests(unittest.TestCase):
    def test_new_material_uses_disjoint_issue_and_fact_identity(self):
        builder = importlib.import_module("시나리오.build_issue_award_v2")
        self.assertEqual(builder.IID, V2)

        v1 = json.loads(paths.facts(V1).read_text(encoding="utf-8"))
        v2 = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        v1_ids = {f["fact_id"] for f in v1["facts"]}
        v2_ids = {f["fact_id"] for f in v2["facts"]}

        self.assertEqual(len(v2_ids), 12)
        self.assertFalse(v1_ids & v2_ids)
        self.assertTrue(all(fid.startswith("fact_award_v2_") for fid in v2_ids))
        self.assertEqual(json.loads(paths.issue(V2).read_text(encoding="utf-8"))["issue_id"], V2)
        self.assertEqual(json.loads(paths.assignment(V2).read_text(encoding="utf-8"))["issue_id"], V2)


class AwardV2NormativeEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_award_v2")

    def test_unknown_components_never_become_another_candidate_win(self):
        result = self.builder.normative_award_evaluator_v2(set())
        self.assertEqual(result["decision_state"], "unknown")
        self.assertIsNone(result["winner"])
        self.assertTrue(all(state == "unknown" for state in result["components"].values()))

    def test_partial_chain_remains_unknown(self):
        result = self.builder.normative_award_evaluator_v2({self.builder.fid(5)})
        self.assertEqual(result["components"]["lagoon_disqualified"], "unknown")
        self.assertEqual(result["decision_state"], "unknown")
        self.assertIsNone(result["winner"])

    def test_complete_normative_chain_selects_night_guide(self):
        result = self.builder.normative_award_evaluator_v2(
            set(self.builder.NORMATIVE_REQUIRED_FACTS))
        self.assertTrue(all(state == "true" for state in result["components"].values()))
        self.assertEqual(result["decision_state"], "selected")
        self.assertEqual(result["winner"], self.builder.ANSWER)


if __name__ == "__main__":
    unittest.main()
