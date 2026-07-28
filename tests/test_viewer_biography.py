# -*- coding: utf-8 -*-
"""뷰어 팩트 전기(biography) 프로토타입 회귀 테스트.

전기 = 상태가 아니라 사건 사슬(배정→언급/침묵→사망→재주입→부활). committed
dryrun2(결정론 정본 픽스처)로 사슬·표 요약을 검증하고, 구버전 votes 구조(dryrun)
에서도 죽지 않는 방어적 강등을 확인한다.
"""
import unittest

from modules import paths

try:
    from fastapi import HTTPException
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
RUN = "dryrun2"


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestBiography(unittest.TestCase):
    def setUp(self):
        if not paths.judgment(ISSUE, RUN).exists():
            self.skipTest("dryrun2 픽스처 없음")
        self.bio = viewer_app.api_biography(ISSUE, RUN)

    def test_shape_and_stages(self):
        self.assertEqual(self.bio["stages"], [0, 1, 2, 3])
        self.assertEqual(len(self.bio["facts"]), 12)
        for f in self.bio["facts"]:
            self.assertEqual(len(f["chain"]), 4)
            self.assertIn("summary", f)

    def test_votes_summary(self):
        """dryrun2 는 offline 스텁(결정론) — 3표 전부 동일이어야 함."""
        for f in self.bio["facts"]:
            for c in f["chain"]:
                self.assertEqual(c["votes"]["n"], 3)
                self.assertTrue(c["votes"]["unanimous"])
                self.assertEqual(c["votes"]["split"], "3/3")
                self.assertEqual(c["votes"]["parse_fail"], 0)

    def test_death_event_chain(self):
        """dryrun2 는 결정론적 소실 모의 — 사망 사건이 실제로 등장하고,
        사망 사건의 stage 는 그 팩트의 first_missing_stage 와 일치해야 한다."""
        deaths = [(f, c) for f in self.bio["facts"] for c in f["chain"]
                  if c["event"] == "died"]
        self.assertTrue(deaths, "결정론 소실 픽스처인데 사망 사건이 없음")
        for f, c in deaths:
            self.assertEqual(f["summary"]["first_missing_stage"], c["stage"])
            self.assertFalse(c["surviving"])

    def test_mentions_carry_snippets(self):
        """언급 에이전트에는 해당 라운드 발화 원문 스니펫이 붙는다(사용자 의심에 원문 즉답)."""
        found = False
        for f in self.bio["facts"]:
            for c in f["chain"]:
                for m in c["mentions"]:
                    found = True
                    self.assertIn("agent_id", m)
        self.assertTrue(found, "언급이 하나도 없는 픽스처는 아님")

    def test_conditions_and_perspectives(self):
        """사이드바 재료: 실험 조건 블록 + 팩트별 관점(배정 에이전트 perspective 유도)."""
        c = self.bio["conditions"]
        self.assertEqual(c["n_agents"], 8)
        self.assertEqual(c["n_rounds"], 4)
        self.assertEqual(c["ledger_mode"], "off")
        self.assertIsNotNone(c["far_system"])
        self.assertTrue(c["perspectives"], "관점 어휘가 비어 있음")
        vocab = set(c["perspectives"]) | {"?"}
        for f in self.bio["facts"]:
            self.assertIsInstance(f["perspectives"], list)
            self.assertTrue(set(f["perspectives"]) <= vocab,
                            f"{f['fact_id']} 관점이 어휘 밖: {f['perspectives']}")

    def test_missing_judgment_404(self):
        with self.assertRaises(HTTPException):
            viewer_app.api_biography(ISSUE, "no_such_run")

    def test_legacy_votes_structure_degrades(self):
        """구버전 dryrun(votes 구조 상이)에서도 죽지 않고 강등 — 스키마 드리프트 방어."""
        if not paths.judgment(ISSUE, "dryrun").exists():
            self.skipTest("dryrun 픽스처 없음")
        bio = viewer_app.api_biography(ISSUE, "dryrun")
        self.assertEqual(len(bio["facts"]), 12)


if __name__ == "__main__":
    unittest.main()
