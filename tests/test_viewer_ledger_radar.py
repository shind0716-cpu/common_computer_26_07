# -*- coding: utf-8 -*-
"""뷰어 장부·전달 레이더 페이지 API 회귀 테스트 (dryrun2 — off run 기준).

장부: 소실 잣대 단일 소스(ledger.missing_facts = judge.SURVIVING) 정합 + off run 은
주입 0. 레이더: transmission.report() 현장 유도 + 영점 미적용 강등 표기(침묵 실패 방지).
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
        self.assertEqual(self.d["ledger_mode"], "off")
        self.assertEqual(self.d["injections"], [])
        self.assertIn("off run", self.d["note"])

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


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestTransmissionApi(unittest.TestCase):
    def setUp(self):
        if not paths.judgment(ISSUE, RUN).exists():
            self.skipTest("dryrun2 픽스처 없음")
        self.d = viewer_app.api_transmission(ISSUE, RUN)

    def test_zero_point_downgrade_notice(self):
        """스캔 산출물이 없으면 '영점 미적용'을 침묵하지 않고 명시해야 한다."""
        zp = self.d["zero_point"]
        if not zp["applied"]:
            self.assertIsNotNone(zp["note"])
            self.assertIn("영점 미적용", zp["note"])

    def test_dryrun2_zero_acquisition(self):
        """dryrun2 영점 확인(7/27 G2 실측 재현): 획득 0 정판정 + 쌍 수 양수."""
        s = self.d["system"]
        self.assertGreater(s["n_pairs_tracked"], 0)
        self.assertEqual(s["kinds"]["acquisition"], 0)
        self.assertEqual(s["n_acq_strict"], 0)

    def test_status_note_present(self):
        """지위 표기가 화면에 실리는지 지킨다.

        2026-07-29 갱신: 종전 가드는 "탐색적"을 요구했으나, 같은 날 동기화에서 층1이 팀
        확정되면서 지위 문면이 바뀌었다. 지금 떨어뜨리면 안 되는 것은 **용도 한정** —
        이 수치는 본실험 주지표가 아니라 논문 재현용이라는 단서다(본실험 과정 관측은
        수첩 원문). 가드를 약화한 것이 아니라 지켜야 할 문구를 옮긴 것이다.
        """
        self.assertIn("용도 한정", self.d["status_note"])
        self.assertIn("주지표가 아니", self.d["status_note"])
        self.assertTrue(self.d["fact_metrics"])

    def test_404_without_judgment(self):
        with self.assertRaises(HTTPException):
            viewer_app.api_transmission(ISSUE, "no_such_run")


if __name__ == "__main__":
    unittest.main()
