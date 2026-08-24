"""analyze_solo 통합 경계 (브리프 §5F).

지킬 것 셋.
  1. 이슈별 lexical 사전 선택 수리를 보존한다 (2026-08-20 결함 수정분).
  2. `lexical_anchor_hits` 를 semantic detector 로 개명하지 않는다 — 이름이 계약이다.
  3. 모듈 상수 `ISSUE_ID="issue_camp"` 가 다른 이슈 런을 조용히 오염시키지 않는다.

3번이 핵심이다. camp 로 고정된 분석기가 throne_v2 런을 읽으면 조용히 camp 앵커로
채점해 0에 가까운 값을 내놓을 수 있다. 그건 실패가 아니라 위장이다 — 죽어야 한다.
"""

import inspect
import unittest

from experiments.memory_structure import analyze_solo as a
from modules import detection_spec as ds


class LexicalRepairPreservedTests(unittest.TestCase):
    def test_issue_specific_lexical_helper_exists(self):
        self.assertTrue(callable(getattr(a, "lexical_anchor_hits", None)))

    def test_helper_takes_issue_id_first(self):
        params = list(inspect.signature(a.lexical_anchor_hits).parameters)
        self.assertEqual(params[0], "issue_id")

    def test_camp_alias_is_not_iterated_in_main(self):
        """하위 호환 별칭은 남아도 되지만 소비 경로에서 직접 돌면 안 된다."""
        self.assertNotIn("ANCHORS.items()", inspect.getsource(a.main))

    def test_helper_is_not_named_as_semantic(self):
        names = [n for n in dir(a) if "semantic" in n.lower()]
        self.assertEqual(names, [], f"lexical 층에 semantic 이름 금지: {names}")


class IssueContaminationTests(unittest.TestCase):
    def test_main_guards_issue_mismatch(self):
        self.assertIn("분석 이슈 불일치", inspect.getsource(a.main))

    def test_unknown_issue_fails_closed_in_helper(self):
        with self.assertRaises(SystemExit):
            a.lexical_anchor_hits("issue_throne_v2", "아무 글")

    def test_throne_v1_text_does_not_score_under_camp_dictionary(self):
        """camp 사전으로 throne 문장을 재면 0 이 나온다 — 그 0 이 「소실」로 읽히면 안 된다."""
        self.assertEqual(a.lexical_anchor_hits("issue_camp", "아르넬의 실제 나이는 스물하나다"),
                         set())
        self.assertEqual(a.lexical_anchor_hits("issue_throne", "아르넬의 실제 나이는 스물하나다"),
                         {"fact_throne_07"})


class LexicalStaysAuxiliaryTests(unittest.TestCase):
    """lexical 결과만으로 semantic 점수를 만들 수 없다 (브리프 §4.3)."""

    def test_lexical_hits_are_not_accepted_as_semantic_judgments(self):
        from modules import requirement_eval as re_eval
        spec = ds.load("issue_throne_v2")
        hits = {fid: True for fid in spec.facts}
        with self.assertRaises(ds.SpecError):
            re_eval.evaluate(spec, hits)

    def test_detection_spec_declares_lexical_not_primary(self):
        self.assertFalse(ds.load("issue_throne_v2").lexical_is_primary)


if __name__ == "__main__":
    unittest.main()
