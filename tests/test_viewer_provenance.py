# -*- coding: utf-8 -*-
"""뷰어 run 기록(provenance·건강 판정) 회귀 테스트.

베이스라인 자격 판별의 핵심 = 공백 발화(llm 무음 폴백 흔적) 탐지와 judgment 유무.
committed esa 픽스처 + 합성 run 만 사용 (walkerhill 은 gitignore — 동결).
"""
import json
import unittest
from pathlib import Path

from modules import paths

try:
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
RUN_COMPLETE = "dryrun2"       # committed: debate+judgment 완비
RUN_SICK = "provsicktest"      # 테스트가 만드는 합성 run — 공백 발화 1 + judgment 없음


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestProvenanceComplete(unittest.TestCase):
    def test_dryrun2_identity_and_clean_debate(self):
        """완비 run: 신원 필드가 채워지고 공백 발화 0. judge_health 는 계기판 이전
        산출물이면 '미계측' 이슈로만 표시(자격 판정은 이슈 유무에 따름)."""
        if not paths.debate(ISSUE, RUN_COMPLETE).exists():
            self.skipTest("dryrun2 픽스처 없음")
        d = viewer_app.api_provenance(ISSUE, RUN_COMPLETE)
        pv, h = d["provenance"], d["health"]
        self.assertEqual(h["blank_utterances"], 0)
        self.assertGreater(h["n_utterances"], 0)
        self.assertGreater(pv["n_rounds"], 0)
        self.assertIsNotNone(pv["ledger_mode"])
        if paths.assignment(ISSUE).exists():
            self.assertIsNotNone(pv["seed"])
        # 자격 판정과 이슈 목록은 서로 정합해야 한다.
        self.assertEqual(h["baseline_eligible"], not h["issues"])


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestProvenanceSickRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._skip = not paths.issue(ISSUE).exists()
        if cls._skip:
            return
        dbg = paths.debate(ISSUE, RUN_SICK)
        dbg.parent.mkdir(parents=True, exist_ok=True)
        evs = [
            {"event": "utterance", "run_id": RUN_SICK, "round": 0, "agent_id": "agent_1",
             "ledger_mode": "off", "stance": "pro", "perspective": "계약",
             "response_text": "정상 발화"},
            {"event": "utterance", "run_id": RUN_SICK, "round": 0, "agent_id": "agent_2",
             "ledger_mode": "off", "stance": "con", "perspective": "안전",
             "response_text": " "},  # llm.py 무음 폴백이 남기는 공백
        ]
        dbg.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in evs) + "\n",
                       encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        Path(paths.debate(ISSUE, RUN_SICK)).unlink(missing_ok=True)

    def test_blank_utterance_detected_and_ineligible(self):
        """공백 발화 1건 + judgment 없음 → 자격 미충족, 이슈 2건 모두 보고."""
        if self._skip:
            self.skipTest("issue_esa 픽스처 없음")
        d = viewer_app.api_provenance(ISSUE, RUN_SICK)
        h = d["health"]
        self.assertEqual(h["blank_utterances"], 1)
        self.assertEqual(h["n_utterances"], 2)
        self.assertFalse(h["baseline_eligible"])
        joined = " / ".join(h["issues"])
        self.assertIn("공백 발화 1건", joined)
        self.assertIn("judgment 없음", joined)


if __name__ == "__main__":
    unittest.main()
