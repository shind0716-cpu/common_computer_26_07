"""award_v2 사슬 평가기 계약 테스트 (핸드오프 §6-B 수용 기준).

원래 `normative_award_evaluator_v2` 는 빌드 스크립트 안에 있었고 「아는 fact_id 집합」을
받았다. 그 서명으로는 **lexical 적중을 그대로 부어 넣어도 막히지 않는다.** 여기서는
의미 판정만 받는다는 것을 못 박는다.
"""

import copy
import unittest

from modules import chain_eval, detection_spec as ds

ISSUE = "issue_award_v2"
WINNER = "밤길 안내인"


def all_faithful(spec):
    return {fid: "faithful" for fid in spec.facts}


class GroundTruthTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)
        self.res = chain_eval.evaluate(self.spec, all_faithful(self.spec))

    def test_all_components_true_selects_night(self):
        self.assertEqual(set(self.res.components.values()), {"true"})
        self.assertEqual(self.res.decision_state, "selected")
        self.assertEqual(self.res.winner, WINNER)

    def test_seven_components_are_evaluated(self):
        self.assertEqual(len(self.res.components), 7)

    def test_every_component_reports_evidence(self):
        for name, ev in self.res.evidence.items():
            self.assertTrue(ev, f"{name}: 근거 없음")
            self.assertTrue(all(f in self.spec.facts for f in ev))


class IncompleteChainTests(unittest.TestCase):
    """빈·부분 집합에서 승자가 나오면 안 된다 (수용 기준)."""

    def setUp(self):
        self.spec = ds.load(ISSUE)

    def _with(self, fact_id, status):
        j = all_faithful(self.spec)
        j[fact_id] = status
        return chain_eval.evaluate(self.spec, j)

    def test_empty_known_set_has_no_winner(self):
        j = {fid: "absent" for fid in self.spec.facts}
        res = chain_eval.evaluate(self.spec, j)
        self.assertIsNone(res.winner)
        self.assertEqual(res.decision_state, "unknown")

    def test_single_missing_component_removes_winner(self):
        res = self._with("fact_award_v2_09", "absent")
        self.assertIsNone(res.winner)
        self.assertEqual(res.components["night_directing_winner"], "unknown")

    def test_partial_two_fact_component_is_unknown(self):
        """석호 결격은 05+06 둘 다 있어야 한다 — 하나만으로는 성립하지 않는다."""
        res = self._with("fact_award_v2_06", "absent")
        self.assertEqual(res.components["lagoon_disqualified"], "unknown")
        self.assertIsNone(res.winner)

    def test_absence_is_not_turned_into_false(self):
        """반증 팩트가 없는 재료다. 덜 모인 것을 false 로 내리면 없는 근거를 만드는 것이다."""
        res = self._with("fact_award_v2_04", "absent")
        self.assertNotIn("false", set(res.components.values()))

    def test_blocked_evidence_is_kept_separate_from_unknown(self):
        res = self._with("fact_award_v2_07", "blocked")
        self.assertEqual(res.components["paper_ineligible"], "blocked")
        self.assertIsNone(res.winner)

    def test_partial_status_does_not_satisfy_component(self):
        res = self._with("fact_award_v2_11", "partial")
        self.assertEqual(res.components["night_completeness_winner"], "unknown")


class SurfaceIsolationTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)

    def test_surface_facts_declared(self):
        res = chain_eval.evaluate(self.spec, all_faithful(self.spec))
        self.assertEqual(set(res.surface_fact_ids),
                         {"fact_award_v2_01", "fact_award_v2_02", "fact_award_v2_03"})

    def test_losing_all_surface_facts_does_not_change_decision(self):
        """인상 정보는 규범 사슬에 기여하지 않는다."""
        j = all_faithful(self.spec)
        for fid in ("fact_award_v2_01", "fact_award_v2_02", "fact_award_v2_03"):
            j[fid] = "absent"
        res = chain_eval.evaluate(self.spec, j)
        self.assertEqual(res.winner, WINNER)

    def test_surface_fact_used_as_component_fails_closed(self):
        spec = ds.load(ISSUE)
        spec.decision_contract = copy.deepcopy(spec.decision_contract)
        spec.decision_contract["components"]["night_category_eligible"] = ["fact_award_v2_01"]
        with self.assertRaises(ds.SpecError) as cm:
            chain_eval.evaluate(spec, all_faithful(spec))
        self.assertIn("표면 정보", str(cm.exception))


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        self.spec = ds.load(ISSUE)

    def test_lexical_hits_cannot_be_passed_as_judgments(self):
        with self.assertRaises(ds.SpecError):
            chain_eval.evaluate(self.spec, {fid: True for fid in self.spec.facts})

    def test_known_fact_id_set_is_not_accepted(self):
        """옛 서명(집합)을 그대로 넘기면 죽어야 한다."""
        with self.assertRaises(ds.SpecError):
            chain_eval.evaluate(self.spec, set(self.spec.facts))

    def test_missing_judgment_fails_closed(self):
        j = all_faithful(self.spec)
        del j["fact_award_v2_05"]
        with self.assertRaises(ds.SpecError):
            chain_eval.evaluate(self.spec, j)

    def test_v1_fact_id_fails_closed(self):
        j = all_faithful(self.spec)
        j["fact_award_07"] = "faithful"
        with self.assertRaises(ds.SpecError):
            chain_eval.evaluate(self.spec, j)

    def test_unknown_selection_rule_fails_closed(self):
        spec = ds.load(ISSUE)
        spec.decision_contract = dict(spec.decision_contract, selection_rule="majority")
        with self.assertRaises(ds.SpecError) as cm:
            chain_eval.evaluate(spec, all_faithful(spec))
        self.assertIn("selection_rule", str(cm.exception))

    def test_spec_without_decision_contract_fails_closed(self):
        """throne 은 요건형이라 사슬 계약이 없다 — 사슬 평가기로 부르면 죽어야 한다."""
        throne = ds.load("issue_throne_v2")
        with self.assertRaises(ds.SpecError):
            chain_eval.evaluate(throne, {fid: "faithful" for fid in throne.facts})


class EvaluatorLocationTests(unittest.TestCase):
    def test_analyzer_layer_does_not_import_build_script(self):
        """분석 층이 빌드 스크립트를 import 하면 재현이 깨진다.

        본문 문자열 검색으로는 못 잰다 — 독스트링에 「왜 옮겼는가」를 적으면서 그 이름을
        쓰기 때문이다(실제로 처음에 그렇게 짰다가 자기 독스트링에 걸렸다). AST 의 import
        구문만 본다.
        """
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(chain_eval))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertTrue(all(not m.startswith("시나리오") and "build_" not in m
                            for m in imported), f"빌드 층 import: {sorted(imported)}")
        self.assertTrue(all(m.startswith("modules") or m in ("__future__", "dataclasses")
                            for m in imported), f"예상 밖 import: {sorted(imported)}")


if __name__ == "__main__":
    unittest.main()
