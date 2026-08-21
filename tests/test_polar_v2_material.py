"""issue_polar_v2 정본 재료 계약과 v1 파일럿 불변성.

가장 중요한 것은 두 가지다.
1. v1 material·prior 원자료가 한 바이트도 안 바뀌었는가 (승인 §4-2, 불변식 1~3).
2. outcome_policy=descriptive_stance_only 재료가 winner/accuracy 를 만들지 않는가
   (DECISION_PACKET P-0A, 불변식 7).
"""

import importlib
import json
import unittest
from collections import Counter
from pathlib import Path

from modules import content_hash, paths

ROOT = Path(__file__).resolve().parent.parent
V1 = "issue_polar"
V2 = "issue_polar_v2"

# 2026-08-20 v2 작업 직전 지문. old material 과 prior 파일럿 원자료는 불변이다.
PRESERVED_SHA256 = {
    "data/issues/issue_polar.json": "b78b69e4f6e8b6a8b09052e6089c2e2c85cafd539eb799f4e4c393b1f27370f9",
    "data/facts/facts_issue_polar.json": "0baf94aac249ae5bd61de61ce79b5eadf594868c086e3a88db0dfa6f3c82f534",
    "data/assignments/assignment_issue_polar.json": "a2f7ae7f7e49a99972762a3c1311b6b49fb384905ec7d657bbfb113f5c751497",
    "시나리오/issue_polar.json": "b78b69e4f6e8b6a8b09052e6089c2e2c85cafd539eb799f4e4c393b1f27370f9",
    "시나리오/facts_issue_polar.json": "0baf94aac249ae5bd61de61ce79b5eadf594868c086e3a88db0dfa6f3c82f534",
    "시나리오/assignment_issue_polar.json": "a2f7ae7f7e49a99972762a3c1311b6b49fb384905ec7d657bbfb113f5c751497",
    "시나리오/prior_issue_polar.json": "364e0a96a70a4d3c9fd264280240f08c7316cae04d076995805a839059bf5a6f",
    "시나리오/prior_issue_polar.partial.jsonl": "7f4ec9e8cdd0a217da13a1c7dbbbd60085dfc928ddfdaedd3b83a13cc1a0febb",
}


def sha(path: Path) -> str:
    return content_hash.sha256_file(path)


class PolarV1PreservationTests(unittest.TestCase):
    def test_old_material_and_pilot_raw_bytes_are_unchanged(self):
        for relative, expected in PRESERVED_SHA256.items():
            with self.subTest(path=relative):
                self.assertEqual(sha(ROOT / relative), expected)


class PolarV2IdentityTests(unittest.TestCase):
    def test_new_material_uses_disjoint_issue_and_fact_identity(self):
        builder = importlib.import_module("시나리오.build_issue_polar_v2")
        self.assertEqual(builder.IID, V2)

        v1 = json.loads(paths.facts(V1).read_text(encoding="utf-8"))
        v2 = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        v1_ids = {f["fact_id"] for f in v1["facts"]}
        v2_ids = {f["fact_id"] for f in v2["facts"]}

        self.assertEqual(len(v2_ids), 12)
        self.assertFalse(v1_ids & v2_ids)
        self.assertTrue(all(fid.startswith("fact_polar_v2_") for fid in v2_ids))
        self.assertEqual(json.loads(paths.issue(V2).read_text(encoding="utf-8"))["issue_id"], V2)
        self.assertEqual(json.loads(paths.assignment(V2).read_text(encoding="utf-8"))["issue_id"], V2)

    def test_builder_and_runtime_canonical_files_are_byte_identical(self):
        pairs = (
            (ROOT / "시나리오" / f"{V2}.json", paths.issue(V2)),
            (ROOT / "시나리오" / f"facts_{V2}.json", paths.facts(V2)),
            (ROOT / "시나리오" / f"assignment_{V2}.json", paths.assignment(V2)),
        )
        for source, runtime in pairs:
            with self.subTest(file=source.name):
                self.assertEqual(source.read_bytes(), runtime.read_bytes())


class PolarV2CanonicalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_polar_v2")
        self.facts_doc = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        self.facts = {f["fact_id"]: f for f in self.facts_doc["facts"]}
        self.issue = json.loads(paths.issue(V2).read_text(encoding="utf-8"))

    def fid(self, n):
        return self.builder.fid(n)

    def test_fact03_names_evacuation_route_alternate_landing_site(self):
        # P-1A: 후송 항로상의 대체 착륙장, 편도 여섯 시간, 중간 급유지 없음
        text = self.facts[self.fid(3)]["text"]
        self.assertIn("후송 항로", text)
        self.assertIn("여섯 시간", text)
        self.assertIn("급유", text)

    def test_fact05_preserves_only_historical_turnback_case(self):
        # P-2A: 과거 회항 사례만 canonical, 현재 실패확률·필연 금지
        fact = self.facts[self.fid(5)]
        self.assertEqual(fact["text"],
                         "지난겨울 같은 기종이 같은 조건에서 이륙 직후 되돌아온 기록이 있다")
        self.assertIn(self.fid(5), self.builder.PRESENT_RISK_FORBIDDEN_FACTS)

    def test_fact11_accessibility_unknown_and_orientation_blocked(self):
        # P-3A: 접근성 unknown, orientation blocked
        self.assertIn(self.fid(11), self.builder.ACCESSIBILITY_UNKNOWN_FACTS)
        self.assertIn(self.fid(11), self.builder.ORIENTATION_BLOCKED_FACTS)

    def test_fact11_and_fact12_orientation_blocked_pending_calibration(self):
        # P-4A: fact11/12 orientation blocked
        self.assertEqual(self.builder.ORIENTATION_BLOCKED_FACTS,
                         frozenset({self.fid(11), self.fid(12)}))

    def test_unfavorable_to_is_prereg_metadata_present_on_facts(self):
        # P-4A: _unfavorable_to 는 fact truth 가 아니라 prereg 분석 메타
        for f in self.facts.values():
            self.assertIn("_unfavorable_to", f)

    def test_outcome_policy_is_descriptive_stance_only(self):
        # P-0A: accuracy 금지
        self.assertEqual(self.facts_doc["outcome_policy"], "descriptive_stance_only")
        self.assertEqual(self.issue["outcome_policy"], "descriptive_stance_only")

    def test_no_answer_key_fields(self):
        # 정답형 필드 없음 — requirement/share/favors 를 두지 않는다
        for f in self.facts.values():
            self.assertNotIn("requirement", f)
            self.assertNotIn("share", f)
            self.assertNotIn("favors", f)

    def test_unfavorable_symmetry_four_to_four(self):
        c = Counter(f["_unfavorable_to"] for f in self.facts.values())
        self.assertEqual(c[self.builder.PRO], 4)
        self.assertEqual(c[self.builder.CON], 4)
        self.assertEqual(c[None], 2)
        self.assertEqual(c["both"], 2)

    def test_body_and_question_identical_to_v1(self):
        v1_issue = json.loads(paths.issue(V1).read_text(encoding="utf-8"))
        self.assertEqual(self.issue["body"], v1_issue["body"])
        self.assertEqual(self.issue["question"], v1_issue["question"])

    def test_prior_is_null_and_note_warns(self):
        self.assertTrue(all(f["prior"]["score"] is None for f in self.facts.values()))
        self.assertIn("prior 프로브 미실행", self.facts_doc["_note"])


class PolarV2AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_polar_v2")
        self.assign = json.loads(paths.assignment(V2).read_text(encoding="utf-8"))
        self.unfav = {f["fact_id"]: f["_unfavorable_to"]
                      for f in json.loads(paths.facts(V2).read_text(encoding="utf-8"))["facts"]}

    def test_four_agents_all_facts_isolated(self):
        agents = self.assign["agents"]
        self.assertEqual(len(agents), 4)
        owned = Counter(i for a in agents for i in a["assigned_fact_ids"])
        self.assertEqual(set(owned.values()), {1})
        self.assertEqual(len(owned), 12)

    def test_each_agent_holds_self_and_opponent_unfavorable(self):
        for a in self.assign["agents"]:
            mine = [i for i in a["assigned_fact_ids"] if self.unfav[i] == a["stance"]]
            theirs = [i for i in a["assigned_fact_ids"]
                      if self.unfav[i] not in (a["stance"], None, "both")]
            self.assertGreaterEqual(len(mine), 1, a["agent_id"])
            self.assertGreaterEqual(len(theirs), 1, a["agent_id"])

    def test_no_agent_trivially_holds_full_decision_chain(self):
        all_ids = set(self.unfav)
        for a in self.assign["agents"]:
            self.assertFalse(all_ids <= set(a["assigned_fact_ids"]), a["agent_id"])


class PolarV2EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_polar_v2")

    def test_empty_known_set_makes_no_winner_or_accuracy(self):
        result = self.builder.descriptive_stance_evaluator_v2(set())
        self.assertIsNone(result["winner"])
        self.assertIsNone(result["accuracy"])
        self.assertEqual(result["outcome_policy"], "descriptive_stance_only")

    def test_full_known_set_still_makes_no_winner_or_accuracy(self):
        all_ids = {self.builder.fid(n) for n in range(1, 13)}
        result = self.builder.descriptive_stance_evaluator_v2(all_ids)
        self.assertIsNone(result["winner"])
        self.assertIsNone(result["accuracy"])

    def test_orientation_blocked_facts_excluded_from_prereg_counts(self):
        all_ids = {self.builder.fid(n) for n in range(1, 13)}
        result = self.builder.descriptive_stance_evaluator_v2(all_ids)
        for fid in self.builder.ORIENTATION_BLOCKED_FACTS:
            self.assertEqual(result["stance_orientation"][fid], "orientation_blocked")
        # 양쪽/blocked/neutral 은 방향 집계에 들어가지 않는다 — 4:4 만 남는다
        self.assertEqual(result["unfavorable_prereg_counts"][self.builder.PRO], 4)
        self.assertEqual(result["unfavorable_prereg_counts"][self.builder.CON], 4)

    def test_unknown_fact_id_is_rejected_fail_closed(self):
        with self.assertRaises(ValueError):
            self.builder.descriptive_stance_evaluator_v2({"fact_polar_v2_99"})

    def test_accuracy_request_is_rejected_fail_closed(self):
        for token in ("accuracy", "winner", "정답률"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    self.builder.reject_accuracy_request(token)


class PolarV2RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(paths.scenario_registry().read_text(encoding="utf-8"))
        self.entry = next((e for e in self.registry["entries"] if e["issue_id"] == V2), None)

    def test_registry_has_candidate_prior_pending_entry(self):
        self.assertIsNotNone(self.entry, "issue_polar_v2 registry 항목이 없다")
        self.assertEqual(self.entry["state"], "candidate")
        self.assertEqual(self.entry["outcome_policy"], "descriptive_stance_only")
        self.assertIsNone(self.entry["approved_by"])
        self.assertIsNone(self.entry["approved_at"])

    def test_spec_and_calibration_coordinates_match_manifest(self):
        manifest = json.loads(paths.detection_manifest(V2).read_text(encoding="utf-8"))
        self.assertEqual(self.entry["spec"]["version"], manifest["spec_version"])
        self.assertEqual(self.entry["spec"]["sha256"], manifest["sha256"]["spec"])
        self.assertEqual(self.entry["calibration"]["version"], manifest["calibration_version"])
        self.assertEqual(
            self.entry["calibration"]["sha256"], manifest["sha256"]["calibration"])

    def test_prior_is_pending(self):
        self.assertTrue(self.entry["prior"]["required"])
        self.assertEqual(self.entry["prior"]["status"], "pending")

    def test_registry_material_hashes_match_actual_v2_bytes(self):
        self.assertEqual(self.entry["material"]["issue_sha256"], sha(paths.issue(V2)))
        self.assertEqual(self.entry["material"]["facts_sha256"], sha(paths.facts(V2)))
        self.assertEqual(self.entry["material"]["assignment_sha256"], sha(paths.assignment(V2)))


if __name__ == "__main__":
    unittest.main()
