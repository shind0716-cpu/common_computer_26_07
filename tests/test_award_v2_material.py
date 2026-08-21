"""issue_award_v2 정본 재료 계약과 v1/파일럿 불변성."""

import hashlib
import importlib
import json
import unittest
from pathlib import Path

from modules import content_hash, paths

ROOT = Path(__file__).resolve().parent.parent
V1 = "issue_award"
V2 = "issue_award_v2"

# 2026-08-20 v2 작업 직전 지문. 두 묶음은 재는 것이 다르다 — 한 이름으로 묶었다가
# 이름값을 잃은 것을 자체 리뷰에서 되돌렸다(같은 날 두 번째 같은 실수였다).
#
# ① 재료: registry·manifest 의 핀과 같은 기준(줄바꿈 정규화)으로 잰다. 내용이 바뀌면
#    잡히고, 체크아웃마다 값이 흔들리지 않는다. 사유는 modules/content_hash.py 머리말.
PRESERVED_MATERIAL_SHA256 = {
    "data/issues/issue_award.json": "6051c482841e15fdd72340356545a27a25206384b72361a36cbd85503387fdf2",
    "data/facts/facts_issue_award.json": "2baf898b254e02842225e036e5caa15aa81de2fae488b84cb4c5a775b5fbcaa2",
    "data/assignments/assignment_issue_award.json": "4af6d26222e4ce68d7f092c8e5b4354bfa03c786efde10178eeee135f9ed8996",
    "시나리오/issue_award.json": "6051c482841e15fdd72340356545a27a25206384b72361a36cbd85503387fdf2",
    "시나리오/facts_issue_award.json": "2baf898b254e02842225e036e5caa15aa81de2fae488b84cb4c5a775b5fbcaa2",
    "시나리오/assignment_issue_award.json": "4af6d26222e4ce68d7f092c8e5b4354bfa03c786efde10178eeee135f9ed8996",
}

# ② 파일럿 실호출 원자료: **바이트 그대로** 잰다. 정규화하면 줄바꿈만 바뀐 판본을 같은
#    것으로 보게 되는데, 원자료 보존(규약 8)에서 그 관용은 곤란하다.
#    한계를 적어 둔다: 이 두 값은 CRLF 작업본 기준이라 LF 체크아웃에서는 맞지 않는다.
#    맞추려면 이 파일들의 정본 바이트를 정하고 .gitattributes 에 -text 로 못 박아야 하며,
#    그건 원자료 정본을 바꾸는 결정이라 owner 몫이다(승격 등급 결정 패킷 §5-1에 기록).
PRESERVED_RAW_SHA256 = {
    "시나리오/prior_issue_award.json": "44f09801037a975cb0f4d66975c240a49dee491629cbf65072c65a80c5165158",
    "시나리오/prior_issue_award.partial.jsonl": "474cee3c64c0a5ab1f93571c3fd4e5b51bbe25eb5fbf9b6730a79eef6d6ee360",
}


def sha(path: Path) -> str:
    return content_hash.sha256_file(path)


class AwardV1PreservationTests(unittest.TestCase):
    def test_old_material_content_is_unchanged(self):
        for relative, expected in PRESERVED_MATERIAL_SHA256.items():
            with self.subTest(path=relative):
                self.assertEqual(sha(ROOT / relative), expected)

    def test_pilot_raw_artifacts_are_byte_identical(self):
        for relative, expected in PRESERVED_RAW_SHA256.items():
            with self.subTest(path=relative):
                raw = (ROOT / relative).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), expected)


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

    def test_builder_and_runtime_canonical_files_are_byte_identical(self):
        pairs = (
            (ROOT / "시나리오" / f"{V2}.json", paths.issue(V2)),
            (ROOT / "시나리오" / f"facts_{V2}.json", paths.facts(V2)),
            (ROOT / "시나리오" / f"assignment_{V2}.json", paths.assignment(V2)),
        )
        for source, runtime in pairs:
            with self.subTest(file=source.name):
                self.assertEqual(source.read_bytes(), runtime.read_bytes())

    def test_v2_material_closes_the_four_audit_blockers(self):
        builder = importlib.import_module("시나리오.build_issue_award_v2")
        texts = {f["fact_id"]: f["text"] for f in
                 json.loads(paths.facts(V2).read_text(encoding="utf-8"))["facts"]}

        self.assertIn("적격 접수작", texts[builder.fid(4)])
        self.assertIn("실제 외주·자동 생성 도구 사용 내역이 일치", texts[builder.fid(12)])
        self.assertIn("제작 전 과정", texts[builder.fid(5)])
        self.assertIn("최종 배경에 반영", texts[builder.fid(6)])
        self.assertIn("올해의 작품 부문에서 신인 창작 부문으로 최종 이관", texts[builder.fid(8)])
        self.assertIn("최종 연출 점수", texts[builder.fid(9)])
        self.assertIn("공식 설계 지표", texts[builder.fid(10)])
        self.assertIn("공식 완성도 평가 기간", texts[builder.fid(11)])

        issue_body = json.loads(paths.issue(V2).read_text(encoding="utf-8"))["body"]
        self.assertIn("초안을 참고한 것도 사용에 포함", issue_body)
        self.assertIn("인터뷰는 확인 자료로 인정", issue_body)
        self.assertIn("세 항목 모두에서 앞선 한 작품", issue_body)

    def test_surface_impressions_are_excluded_from_normative_components(self):
        builder = importlib.import_module("시나리오.build_issue_award_v2")
        facts = json.loads(paths.facts(V2).read_text(encoding="utf-8"))["facts"]
        surface_ids = {f["fact_id"] for f in facts if f["dataset_role"] == "surface_impression"}
        self.assertEqual(surface_ids, {builder.fid(1), builder.fid(2), builder.fid(3)})
        self.assertFalse(surface_ids & set(builder.NORMATIVE_REQUIRED_FACTS))

    def test_each_agent_receives_two_isolated_facts(self):
        assignment = json.loads(paths.assignment(V2).read_text(encoding="utf-8"))
        for agent in assignment["agents"]:
            isolated = [fid for fid in agent["assigned_fact_ids"] if fid.endswith(tuple(
                f"_{n:02d}" for n in range(5, 13)))]
            self.assertEqual(len(isolated), 2, agent["agent_id"])


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
