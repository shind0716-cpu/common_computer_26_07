# -*- coding: utf-8 -*-
"""뷰어 장부 재료 API 회귀 테스트 (dryrun2 — off run 기준).

장부: 소실 잣대 단일 소스(ledger.missing_facts = judge.SURVIVING) 정합 + off run 은
주입 0. 화면은 폐기됐지만 /api/ledger는 격차 화면의 재료 API로 유지한다.
"""
import unittest

from modules import paths, ledger

try:
    from fastapi import HTTPException
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
RUN = "dryrun2"


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestLedgerApi(unittest.TestCase):
    def setUp(self):
        if not paths.judgment(ISSUE, RUN).exists():
            self.skipTest("dryrun2 픽스처 없음")
        self.d = viewer_app.api_ledger(ISSUE, RUN)

    def test_off_run_no_injections(self):
        """off run 이면 주입 0이고, 그 사실을 note 가 말해야 한다.

        문면 가드 갱신(2026-07-30): 종전엔 "off run" 이라는 영문 표기를 요구했으나 뷰어
        문면을 일상어로 옮기면서 "장부를 끈 판" 으로 바뀌었다. 지켜야 할 것은 특정 낱말이
        아니라 **주입이 없었음을 침묵하지 않는 것**이므로 그 뜻을 검사한다(약화 아님).
        """
        self.assertEqual(self.d["ledger_mode"], "off")
        self.assertEqual(self.d["injections"], [])
        self.assertIn("장부를 끈", self.d["note"])
        self.assertIn("다시 넣은 적이 없다", self.d["note"])

    def test_missing_matches_ledger_module(self):
        """페이지의 소실 목록은 ledger.missing_facts 와 글자 단위 일치(잣대 단일 소스)."""
        judgment = ledger.load_judgment(ISSUE, RUN)
        for row in self.d["ledger_by_stage"]:
            expect = ledger.missing_facts(judgment, row["stage"])
            self.assertEqual([f["fact_id"] for f in row["missing"]], expect)
            self.assertEqual(row["n_missing"], len(expect))

    def test_404_without_judgment(self):
        with self.assertRaises(HTTPException):
            viewer_app.api_ledger(ISSUE, "no_such_run")

if __name__ == "__main__":
    unittest.main()
