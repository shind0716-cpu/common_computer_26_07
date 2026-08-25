"""issue_throne_v2 재료 계약 테스트 (브리프 §5A·§6).

가장 중요한 항목은 마지막이다 — **v1 이 한 바이트도 안 바뀌었는가.**
54콜 파일럿의 근거가 그 세 파일이다.
"""

import json
import unittest
from pathlib import Path

from modules import content_hash, paths

V1, V2 = "issue_throne", "issue_throne_v2"

# 2026-08-20 파일럿 실행 시점 지문. Hermes 감사 §2 와 실행 계보 §4 가 같은 값을 기록한다.
V1_SHA256 = {
    "issues": "a818e61afc6eab6d986ae0f44c90b007a706975cf71c5099e487ebad1d194044",
    "facts": "2d156dfbc7f369ef9d9d479d584cd3037e87cb608f639f33037cdec1a035a0e5",
    "assignments": "b1a12d57cd18710ee2af0a1c0717bf8c85f71097dd810ecf1e37fee63d8c0df6",
}


def sha(p: Path) -> str:
    return content_hash.sha256_file(p)


class V1ImmutabilityTests(unittest.TestCase):
    def test_v1_issue_unchanged(self):
        self.assertEqual(sha(paths.issue(V1)), V1_SHA256["issues"])

    def test_v1_facts_unchanged(self):
        self.assertEqual(sha(paths.facts(V1)), V1_SHA256["facts"])

    def test_v1_assignment_unchanged(self):
        self.assertEqual(sha(paths.assignment(V1)), V1_SHA256["assignments"])


class V2StructureTests(unittest.TestCase):
    def setUp(self):
        self.facts = json.loads(paths.facts(V2).read_text(encoding="utf-8"))
        self.issue = json.loads(paths.issue(V2).read_text(encoding="utf-8"))
        self.assign = json.loads(paths.assignment(V2).read_text(encoding="utf-8"))

    def test_twelve_facts(self):
        self.assertEqual(len(self.facts["facts"]), 12)

    def test_fact_ids_do_not_collide_with_v1(self):
        v1_ids = {f["fact_id"] for f in
                  json.loads(paths.facts(V1).read_text(encoding="utf-8"))["facts"]}
        v2_ids = {f["fact_id"] for f in self.facts["facts"]}
        self.assertEqual(v1_ids & v2_ids, set())

    def test_body_and_stub_identical_to_v1(self):
        """바꾼 것은 팩트 셋뿐이다 — 본문이 같아야 비교가 성립한다."""
        v1_issue = json.loads(paths.issue(V1).read_text(encoding="utf-8"))
        self.assertEqual(self.issue["body"], v1_issue["body"])
        self.assertEqual(self.issue["question"], v1_issue["question"])

    def test_three_facts_changed_nine_kept(self):
        v1_texts = {f["fact_id"][-2:]: f["text"] for f in
                    json.loads(paths.facts(V1).read_text(encoding="utf-8"))["facts"]}
        v2_texts = {f["fact_id"][-2:]: f["text"] for f in self.facts["facts"]}
        changed = {k for k in v1_texts if v1_texts[k] != v2_texts[k]}
        self.assertEqual(changed, {"04", "06", "10"})

    def test_shared_four_unshared_eight(self):
        fs = self.facts["facts"]
        self.assertEqual(sum(f["share"] == "shared" for f in fs), 4)
        self.assertEqual(sum(f["share"] == "unshared" for f in fs), 8)

    def test_unshared_tilt_is_seven_to_one(self):
        """v1 은 6:2 였다. v2 는 fact_10 이 넘어와 7:1 — 의도된 변화이므로 못 박는다."""
        un = [f for f in self.facts["facts"] if f["share"] == "unshared"]
        self.assertEqual(sum(f["favors"] == "아르넬" for f in un), 7)
        self.assertEqual(sum(f["favors"] == "베스카" for f in un), 1)

    def test_shared_trap_still_favors_decoy(self):
        sh = [f for f in self.facts["facts"] if f["share"] == "shared"]
        self.assertEqual(sum(f["favors"] == "베스카" for f in sh), 3)

    def test_prior_is_probed_independently_of_v1(self):
        """문면이 바뀐 재료라 v1 의 known 0/12 를 물려받지 않았다 — 2026-08-21 독립 프로브 0/12."""
        for f in self.facts["facts"]:
            self.assertEqual(f["prior"]["score"], 0.0)
            self.assertEqual(f["prior"]["probe_prompt_ver"], "camp-prior-v0.2")
            self.assertIsNotNone(f["prior"]["probed_at"])

    def test_note_records_prior_probe(self):
        self.assertIn("prior 프로브 완료", self.facts["_note"])

    def test_assignment_has_no_unassigned_fact(self):
        owned = {i for a in self.assign["agents"] for i in a["assigned_fact_ids"]}
        self.assertEqual(owned, {f["fact_id"] for f in self.facts["facts"]})


if __name__ == "__main__":
    unittest.main()
