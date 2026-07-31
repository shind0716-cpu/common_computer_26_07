# -*- coding: utf-8 -*-
"""두 판 자기완결 HTML 생성기."""
import tempfile
import unittest
from pathlib import Path

from modules import paths
from scripts.make_pair_page import PLACEHOLDER, make_pair_page


class TestMakePairPage(unittest.TestCase):
    def test_bakes_same_payload_and_keeps_utterance_originals(self):
        issue, a, b = "issue_esa", "dryrun2", "fixture_v03"
        if not paths.judgment(issue, a).exists() or not paths.judgment(issue, b).exists():
            self.skipTest("픽스처 없음")
        with tempfile.TemporaryDirectory() as td:
            out = make_pair_page(issue, a, b, Path(td) / "pair.html")
            text = out.read_text(encoding="utf-8")
        self.assertNotIn(PLACEHOLDER, text)
        self.assertIn('"records":', text)
        # dryrun2 실제 발화 일부가 JSON payload에 전문으로 구워졌는지 확인한다.
        from tools.viewer.app import api_pair
        utterance = api_pair(issue, a, b)["records"][0]["utterances"]["0"][0]["text"]
        self.assertIn(utterance[:80], text)


if __name__ == "__main__":
    unittest.main()
