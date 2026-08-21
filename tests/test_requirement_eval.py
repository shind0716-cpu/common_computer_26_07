"""requirement / decision evaluator 계약 테스트 (브리프 §4.2·§5E).

세 층을 섞지 않는다.
  fact detector       — 명제가 보존됐는가 (여기서 다루지 않는다)
  requirement evaluator — 각 후보가 조건 i 를 충족하는가
  decision evaluator  — 네 조건을 전부 충족한 후보가 누구인가

fact detector 가 승자를 직접 만들지 않는다. 그래서 evaluator 는 판정 상태를 **입력으로**
받는다. 근거 팩트가 blocked/absent/contradicted 이면 불확실성을 숨기지 않고 undetermined 다.
"""

import unittest

from modules import detection_spec as ds
from modules import requirement_eval as re_eval

ISSUE = "issue_throne_v2"
ANSWER, DECOY = "아르넬", "베스카"


def all_faithful(spec):
    return {fid: "faithful" for fid in spec.facts}


class GroundTruthTests(unittest.TestCase):
    """전 팩트가 충실히 보존된 상태 = 정본 그대로."""

    def setUp(self):
        self.spec = ds.load(ISSUE)
        self.res = re_eval.evaluate(self.spec, all_faithful(self.spec))

    def test_arnel_satisfies_all_four(self):
        c = self.res.candidates[ANSWER]
        self.assertEqual([c.requirements[i] for i in (1, 2, 3, 4)], ["satisfied"] * 4)
        self.assertTrue(c.eligible)

    def test_veska_is_ineligible_with_one_of_four(self):
        c = self.res.candidates[DECOY]
        self.assertEqual(sum(s == "satisfied" for s in c.requirements.values()), 1)
        self.assertFalse(c.eligible)

    def test_decision_selects_arnel(self):
        self.assertEqual(self.res.winner, ANSWER)

    def test_each_requirement_reports_evidence_fact_ids(self):
        for cand in (ANSWER, DECOY):
            for i in (1, 2, 3, 4):
                ev = self.res.candidates[cand].evidence[i]
                self.assertTrue(ev, f"{cand} 조건{i}: 근거 없음")
                self.assertTrue(all(f in self.spec.facts for f in ev))


class UndeterminedTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)

    def _with(self, fact_id, status):
        j = all_faithful(self.spec)
        j[fact_id] = status
        return re_eval.evaluate(self.spec, j)

    def test_blocked_evidence_makes_requirement_undetermined(self):
        res = self._with("fact_throne_v2_10", "blocked")
        self.assertEqual(res.candidates[ANSWER].requirements[3], "undetermined")

    def test_absent_evidence_makes_requirement_undetermined(self):
        res = self._with("fact_throne_v2_07", "absent")
        self.assertEqual(res.candidates[ANSWER].requirements[2], "undetermined")

    def test_contradicted_evidence_makes_requirement_undetermined(self):
        res = self._with("fact_throne_v2_04", "contradicted")
        self.assertEqual(res.candidates[ANSWER].requirements[4], "undetermined")

    def test_undetermined_requirement_blocks_eligibility(self):
        res = self._with("fact_throne_v2_10", "blocked")
        self.assertIsNone(res.candidates[ANSWER].eligible)

    def test_no_winner_when_eligibility_undetermined(self):
        res = self._with("fact_throne_v2_10", "blocked")
        self.assertIsNone(res.winner)
        self.assertIn("undetermined", res.reason)

    def test_partial_does_not_count_as_satisfied(self):
        res = self._with("fact_throne_v2_07", "partial")
        self.assertEqual(res.candidates[ANSWER].requirements[2], "undetermined")


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)

    def test_missing_judgment_fails_closed(self):
        j = all_faithful(self.spec)
        del j["fact_throne_v2_05"]
        with self.assertRaises(ds.SpecError):
            re_eval.evaluate(self.spec, j)

    def test_unknown_fact_in_judgments_fails_closed(self):
        j = all_faithful(self.spec)
        j["fact_throne_06"] = "faithful"      # v1 id — 판본 혼동
        with self.assertRaises(ds.SpecError):
            re_eval.evaluate(self.spec, j)

    def test_unknown_status_fails_closed(self):
        j = all_faithful(self.spec)
        j["fact_throne_v2_05"] = "survived"
        with self.assertRaises(ds.SpecError):
            re_eval.evaluate(self.spec, j)

    def test_lexical_hits_cannot_be_passed_as_judgments(self):
        """lexical 만으로 semantic 점수를 만들지 않는다 (브리프 §4.3)."""
        with self.assertRaises(ds.SpecError):
            re_eval.evaluate(self.spec, {fid: True for fid in self.spec.facts})


if __name__ == "__main__":
    unittest.main()
