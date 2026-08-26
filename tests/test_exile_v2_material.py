"""issue_exile_v2 정본 재료 계약과 v1 파일럿 불변성.

DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md 의 owner 승인(E-0A~E-9A)을 재료로 옮긴 것이
계약대로인지 본다. polar_v2 와 같은 골격이되 exile 고유의 결정이 더 많다.

가장 중요한 것은 세 가지다.
1. v1 material·prior 원자료가 한 바이트도 안 바뀌었는가 (승인 §4-2, 불변식 1~3).
2. outcome_policy=descriptive_stance_only 재료가 winner/accuracy 를 만들지 않는가
   (E-0A, 불변식 7).
3. 윤리 sidecar 가 fact preservation 과 분리돼 있고 사람 지정 전까지 blocked 인가
   (E-8A — 사람 coder·독립 adjudicator 미지정이라 ethics 코딩을 수행하지 않는다).

이 과제 범위 밖: registry 항목·DetectionSpec·calibration·실호출. 그래서 그 테스트는 없다.
"""

import importlib
import json
import unittest
from collections import Counter
from pathlib import Path

from modules import content_hash, paths

ROOT = Path(__file__).resolve().parent.parent
V1 = "issue_exile"
V2 = "issue_exile_v2"

# 2026-08-20 v2 작업 직전 지문. old material 과 prior 파일럿 원자료는 불변이다.
PRESERVED_SHA256 = {
    "data/issues/issue_exile.json": "7138c2d7de3db5f661e1b6c7aebb523c7313f5467be62c61c9d79c453a9ef1f2",
    "data/facts/facts_issue_exile.json": "df7532816c55d35c40473c4748be9200e967a9f76b88b07e4ac13c99642c8bb7",
    "data/assignments/assignment_issue_exile.json": "1f598d76761b1a8572a48cb2aa749103e4095148e4467eeb6aac4f05a09158c4",
    "시나리오/issue_exile.json": "7138c2d7de3db5f661e1b6c7aebb523c7313f5467be62c61c9d79c453a9ef1f2",
    "시나리오/facts_issue_exile.json": "df7532816c55d35c40473c4748be9200e967a9f76b88b07e4ac13c99642c8bb7",
    "시나리오/assignment_issue_exile.json": "1f598d76761b1a8572a48cb2aa749103e4095148e4467eeb6aac4f05a09158c4",
    "시나리오/prior_issue_exile.json": "4c02bf13ed99e8ef6b817e4b3e4411317ca016a44ae1ce5c8b1a0b607a0622a7",
    "시나리오/prior_issue_exile.partial.jsonl": "6f713bf00c6e7a2f25db4324d73c3d61fe6c09afa21929a918407a5b0a574a14",
}


def sha(path: Path) -> str:
    return content_hash.sha256_file(path)


class ExileV1PreservationTests(unittest.TestCase):
    def test_old_material_and_pilot_raw_bytes_are_unchanged(self):
        for relative, expected in PRESERVED_SHA256.items():
            with self.subTest(path=relative):
                self.assertEqual(sha(ROOT / relative), expected)


class ExileV2IdentityTests(unittest.TestCase):
    def test_new_material_uses_disjoint_issue_and_fact_identity(self):
        builder = importlib.import_module("시나리오.build_issue_exile_v2")
        self.assertEqual(builder.IID, V2)

        v1 = json.loads(paths.facts(V1).read_text(encoding="utf-8"))
        v2 = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        v1_ids = {f["fact_id"] for f in v1["facts"]}
        v2_ids = {f["fact_id"] for f in v2["facts"]}

        self.assertEqual(len(v2_ids), 12)
        self.assertFalse(v1_ids & v2_ids)
        self.assertTrue(all(fid.startswith("fact_exile_v2_") for fid in v2_ids))
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


class ExileV2CanonicalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_exile_v2")
        self.facts_doc = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        self.facts = {f["fact_id"]: f for f in self.facts_doc["facts"]}
        self.issue = json.loads(paths.issue(V2).read_text(encoding="utf-8"))

    def fid(self, n):
        return self.builder.fid(n)

    def test_fact01_city_guard_investigation_list_count_and_guilt_unknown(self):
        # E-1A: source=시 경비대 수사 관련자 명단, count 31/2000, 유죄 수는 unknown
        text = self.facts[self.fid(1)]["text"]
        self.assertIn("시 경비대", text)
        self.assertIn("수사", text)
        self.assertIn("서른한", text)
        self.assertIn("이천", text)
        self.assertIn("유죄", text)
        self.assertIn(self.fid(1), self.builder.GUILT_UNKNOWN_FACTS)
        sem = self.builder.FACT01_SEMANTIC
        self.assertEqual(sem["source"], "시 경비대")
        self.assertEqual(sem["count"], "31/2000")
        self.assertEqual(sem["guilt"], "unknown")

    def test_fact02_detected_ninefold_but_cause_unconfirmed(self):
        # E-2A: 적발 9배지만 원인 미확정
        text = self.facts[self.fid(2)]["text"]
        self.assertIn("아홉 배", text)
        self.assertIn("원인", text)
        self.assertIn(self.fid(2), self.builder.CAUSAL_ATTRIBUTION_UNCONFIRMED)

    def test_fact06_refusal_actor_unknown_and_not_filled(self):
        # E-3A: 거부 행위자 unknown, 조직원/위원회/정착민 전체로 채우지 않는다
        text = self.facts[self.fid(6)]["text"]
        self.assertIn(self.fid(6), self.builder.REFUSAL_ACTOR_UNKNOWN_FACTS)
        for filler in ("검은 갈대 조직원", "자치위원회", "정착민 전체"):
            self.assertNotIn(filler, text)

    def test_fact06_forbidden_actor_fill_is_rejected(self):
        for actor in ("검은 갈대 조직원", "정착지 자치위원회", "정착민 전체", "조직", "위원회"):
            with self.subTest(actor=actor):
                with self.assertRaises(ValueError):
                    self.builder.reject_refusal_actor_fill(actor)

    def test_fact08_temporal_closure_direct_cause_unconfirmed(self):
        # E-4A: 이후 폐업(시간 순서)은 보존, 각 폐업의 직접 원인은 미확정
        text = self.facts[self.fid(8)]["text"]
        self.assertIn("예순둘", text)
        self.assertIn("이후", text)
        self.assertIn("직접 원인", text)
        self.assertIn(self.fid(8), self.builder.CLOSURE_CAUSE_UNCONFIRMED)

    def test_fact10_seats_and_majority_preserved_vote_threshold_blocked(self):
        # E-5A: 11석·단순 과반 보존, 최소 가결표 계산 blocked
        text = self.facts[self.fid(10)]["text"]
        self.assertIn("열한 자리", text)
        self.assertIn("단순 과반", text)
        self.assertIn(self.fid(10), self.builder.VOTE_THRESHOLD_BLOCKED)

    def test_fact11_internal_cause_preserved_no_universalization(self):
        # E-6A: 미갱신→넉 달 내부 인과 보존, 모든 사람·절차로 보편화 금지
        text = self.facts[self.fid(11)]["text"]
        self.assertIn("갱신되지 않아", text)
        self.assertIn("넉 달", text)
        self.assertIn(self.fid(11), self.builder.INTERNAL_CAUSE_NO_UNIVERSALIZATION)

    def test_fact12_option_existence_only_feasibility_unknown(self):
        # E-7A: 개별 송환 조항 존재·미사용만, 실행 가능성·효과 unknown
        text = self.facts[self.fid(12)]["text"]
        self.assertIn("따로 송환", text)
        self.assertIn("쓰인 적이 없다", text)
        self.assertIn(self.fid(12), self.builder.OPTION_FEASIBILITY_UNKNOWN)

    def test_outcome_policy_is_descriptive_stance_only(self):
        # E-0A: accuracy 금지
        self.assertEqual(self.facts_doc["outcome_policy"], "descriptive_stance_only")
        self.assertEqual(self.issue["outcome_policy"], "descriptive_stance_only")

    def test_no_answer_key_fields(self):
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

    def test_unfavorable_to_is_prereg_metadata_present_on_facts(self):
        for f in self.facts.values():
            self.assertIn("_unfavorable_to", f)

    def test_body_and_question_identical_to_v1(self):
        v1_issue = json.loads(paths.issue(V1).read_text(encoding="utf-8"))
        self.assertEqual(self.issue["body"], v1_issue["body"])
        self.assertEqual(self.issue["question"], v1_issue["question"])

    def test_prior_is_probed_and_note_records_it(self):
        """2026-08-21 prior 프로브 완료(gpt-mini·camp-prior-v0.2·known 0/12). 원 '미실행' 문장은 이력."""
        for f in self.facts.values():
            self.assertEqual(f["prior"]["score"], 0.0)
            self.assertEqual(f["prior"]["probe_model"], "gpt-mini")
            self.assertEqual(f["prior"]["probe_prompt_ver"], "camp-prior-v0.2")
            self.assertIsNotNone(f["prior"]["probed_at"])
        self.assertIn("prior 프로브 완료", self.facts_doc["_note"])


class ExileV2EthicsSidecarTests(unittest.TestCase):
    """E-8A: 윤리 sidecar 는 fact preservation 과 분리하고 사람 지정 전까지 blocked."""

    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_exile_v2")
        self.facts_doc = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        self.issue = json.loads(paths.issue(V2).read_text(encoding="utf-8"))

    def test_status_is_blocked_pending_human_assignment(self):
        self.assertEqual(self.builder.ETHICS_SIDECAR_STATUS,
                         "blocked_pending_human_assignment")

    def test_issue_and_facts_carry_blocked_sidecar_separated(self):
        for doc in (self.issue, self.facts_doc):
            sc = doc["ethics_sidecar"]
            self.assertEqual(sc["status"], "blocked_pending_human_assignment")
            self.assertTrue(sc["separated_from_fact_preservation"])
            self.assertTrue(sc["requires_human_coder"])
            self.assertTrue(sc["requires_independent_adjudicator"])
            self.assertIsNone(sc["human_coder"])
            self.assertIsNone(sc["independent_adjudicator"])

    def test_performing_ethics_coding_is_blocked_fail_closed(self):
        with self.assertRaises(RuntimeError):
            self.builder.require_human_ethics_assignment()

    def test_evaluator_reports_status_but_no_ethics_scores(self):
        all_ids = {self.builder.fid(n) for n in range(1, 13)}
        result = self.builder.descriptive_stance_evaluator_v2(all_ids)
        self.assertEqual(result["ethics_sidecar_status"],
                         "blocked_pending_human_assignment")
        # sidecar 축을 점수로 만들지 않는다 — fact preservation 과 합산 금지
        for banned in ("collective_punishment", "proportionality", "ethics_score",
                       "public_safety", "ethics_verdict"):
            self.assertNotIn(banned, result)


class ExileV2AssignmentTests(unittest.TestCase):
    def setUp(self):
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


class ExileV2EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.builder = importlib.import_module("시나리오.build_issue_exile_v2")

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

    def test_boundary_sets_surface_only_known_facts(self):
        known = {self.builder.fid(2), self.builder.fid(8)}
        result = self.builder.descriptive_stance_evaluator_v2(known)
        self.assertEqual(result["causal_attribution_unconfirmed"], [self.builder.fid(2)])
        self.assertEqual(result["closure_cause_unconfirmed"], [self.builder.fid(8)])
        self.assertEqual(result["guilt_unknown"], [])

    def test_full_known_prereg_counts_four_to_four(self):
        all_ids = {self.builder.fid(n) for n in range(1, 13)}
        result = self.builder.descriptive_stance_evaluator_v2(all_ids)
        self.assertEqual(result["unfavorable_prereg_counts"][self.builder.PRO], 4)
        self.assertEqual(result["unfavorable_prereg_counts"][self.builder.CON], 4)

    def test_unknown_fact_id_is_rejected_fail_closed(self):
        with self.assertRaises(ValueError):
            self.builder.descriptive_stance_evaluator_v2({"fact_exile_v2_99"})

    def test_accuracy_request_is_rejected_fail_closed(self):
        for token in ("accuracy", "winner", "정답률"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    self.builder.reject_accuracy_request(token)


class ExileV2RegistryTests(unittest.TestCase):
    def setUp(self):
        registry = json.loads(paths.scenario_registry().read_text(encoding="utf-8"))
        self.entry = next((e for e in registry["entries"] if e["issue_id"] == V2), None)

    def test_registry_has_approved_entry_with_signature(self):
        self.assertIsNotNone(self.entry, "issue_exile_v2 registry 항목이 없다")
        # 2026-08-21 요한 승인(console_approved). prior completed, approved_by/at 채워짐.
        self.assertEqual(self.entry["state"], "console_approved")
        self.assertEqual(self.entry["outcome_policy"], "descriptive_stance_only")
        self.assertEqual(self.entry["prior"], {"required": True, "status": "completed"})
        self.assertTrue(str(self.entry["approved_by"]).strip())
        self.assertTrue(str(self.entry["approved_at"]).strip())
        self.assertEqual(self.entry["material"]["issue_sha256"], sha(paths.issue(V2)))
        self.assertEqual(self.entry["material"]["facts_sha256"], sha(paths.facts(V2)))
        self.assertEqual(self.entry["material"]["assignment_sha256"], sha(paths.assignment(V2)))


if __name__ == "__main__":
    unittest.main()
