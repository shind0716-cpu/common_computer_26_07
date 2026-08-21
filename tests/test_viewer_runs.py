# -*- coding: utf-8 -*-
"""뷰어 run 발견(debate 스캔) + 부분 상태(run_state/parts) 회귀 테스트.

기존 _available_runs 는 회귀 테스트가 없었다(judgment 앵커). v1① 에서 debate 앵커 +
부분 상태로 바꾸므로 여기서 고정한다. committed esa 픽스처만 사용(walkerhill 은 gitignore).
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules import paths

try:
    from tools.viewer import app as viewer_app
    HAVE_APP = True
except Exception:
    HAVE_APP = False

ISSUE = "issue_esa"
RUN_COMPLETE = "dryrun2"      # committed: 4파일 완비 → complete
RUN_PARTIAL = "vrpartialtest"  # 테스트가 debate 만 만들고 judgment 는 안 만듦 → partial


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestRunDiscovery(unittest.TestCase):
    def test_finds_committed_run_via_debate_scan(self):
        """debate 스캔으로 dryrun2 를 찾고, 언더스코어 issue_id 를 정확히 역추출한다."""
        if not paths.debate(ISSUE, RUN_COMPLETE).exists():
            self.skipTest("dryrun2 픽스처 없음")
        keyed = {(r["issue_id"], r["run_id"]): r for r in viewer_app._available_runs()}
        self.assertIn((ISSUE, RUN_COMPLETE), keyed, "debate 스캔이 dryrun2 를 못 찾음")
        r = keyed[(ISSUE, RUN_COMPLETE)]
        self.assertEqual(r["issue_id"], "issue_esa")   # '_' 포함 issue_id 역추출 정확
        self.assertEqual(r["run_state"], "complete")
        self.assertEqual(r["parts"]["judgment"], "present")


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestPilotVisibility(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.data = self.tmp / "data"
        (self.data / "issues").mkdir(parents=True)
        (self.data / "facts").mkdir(parents=True)
        (self.data / "assignments").mkdir(parents=True)
        (self.data / "debates").mkdir(parents=True)
        (self.data / "judgments").mkdir(parents=True)
        (self.data / "issues" / "issue_pilot.json").write_text(
            json.dumps({"issue_id": "issue_pilot", "title": "pilot"}), encoding="utf-8")
        self.patch = mock.patch.object(paths, "DATA", self.data)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _debate(self, run_id, meta):
        rows = [{"event": "run_meta", "run_id": run_id, "issue_id": "issue_pilot",
                 "ts": "now", **meta},
                {"event": "utterance", "run_id": run_id, "round": 0,
                 "agent_id": "a", "response_text": "x"}]
        paths.debate("issue_pilot", run_id).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8")

    def _judgment(self, run_id, policy):
        paths.judgment("issue_pilot", run_id).write_text(
            json.dumps({"issue_id": "issue_pilot", "run_id": run_id, **policy}),
            encoding="utf-8")

    def test_default_catalog_excludes_pilot_but_explicit_inspection_can_include(self):
        policy = {"promotion_tier": "pilot_unvetted", "aggregate_eligible": False,
                  "report_eligible": False}
        self._debate("source-labelled", policy)
        self._judgment("source-labelled", {})  # judgment label mutation/removal
        self._debate("judgment-labelled", {})  # source label mutation/removal
        self._judgment("judgment-labelled", policy)

        self.assertEqual(viewer_app._available_runs(), [])
        included = viewer_app._available_runs(include_unvetted=True)
        self.assertEqual({row["run_id"] for row in included},
                         {"source-labelled", "judgment-labelled"})
        self.assertTrue(all(row["unvetted"] for row in included))


@unittest.skipUnless(HAVE_APP, "fastapi/viewer app 미설치")
class TestPartialRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # issue_esa·facts_esa 는 committed. debate 만 만들고 judgment 는 안 만듦 → partial.
        cls._skip = not paths.issue(ISSUE).exists()
        if cls._skip:
            return
        dbg = paths.debate(ISSUE, RUN_PARTIAL)
        dbg.parent.mkdir(parents=True, exist_ok=True)
        ev = {"event": "utterance", "run_id": RUN_PARTIAL, "ts": "2026-01-01T00:00:00+00:00",
              "ledger_mode": "off", "round": 0, "agent_id": "agent_1", "stance": "pro",
              "perspective": "계약·재정", "response_text": "부분 run 테스트 발화"}
        dbg.write_text(json.dumps(ev, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        Path(paths.debate(ISSUE, RUN_PARTIAL)).unlink(missing_ok=True)

    def test_run_parts_partial(self):
        if self._skip:
            self.skipTest("issue_esa 픽스처 없음")
        run_state, parts = viewer_app._run_parts(ISSUE, RUN_PARTIAL)
        self.assertEqual(run_state, "partial")
        self.assertEqual(parts["judgment"], "absent")
        self.assertEqual(parts["debate"], "partial")   # run_end 없고 judgment 없음

    def test_api_viewmodel_partial_no_exception(self):
        """judgment 없는 run 에서 예외 없이 부분 뷰모델(발화만)을 낸다."""
        if self._skip:
            self.skipTest("issue_esa 픽스처 없음")
        vm = viewer_app.api_viewmodel(ISSUE, RUN_PARTIAL)
        self.assertEqual(vm["run_state"], "partial")
        self.assertEqual(vm["matrix"], {})           # 매트릭스 빈값
        self.assertEqual(vm["far_by_stage"], [])
        self.assertTrue(vm["utterances"]["0"])       # 발화는 실림
        self.assertEqual(vm["parts"]["judgment"], "absent")


if __name__ == "__main__":
    unittest.main()
