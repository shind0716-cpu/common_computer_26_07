"""Regression tests for issue-specific lexical anchor selection."""

import unittest

from experiments.memory_structure.analyze_solo import lexical_anchor_hits


class LexicalAnchorSelectionTests(unittest.TestCase):
    def test_throne_text_uses_throne_anchor_dictionary(self) -> None:
        hits = lexical_anchor_hits("issue_throne", "아르넬의 실제 나이는 스물하나다")

        self.assertEqual(hits, {"fact_throne_07"})

    def test_camp_text_uses_camp_anchor_dictionary(self) -> None:
        hits = lexical_anchor_hits("issue_camp", "견적은 38,000원이고 배관 문제가 있다")

        self.assertEqual(hits, {"fact_camp_01", "fact_camp_07"})

    def test_unknown_issue_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            lexical_anchor_hits("issue_missing", "아무 문장")


if __name__ == "__main__":
    unittest.main()
