"""tools/viewer 파이프라인 노드 엔드포인트 회귀 — 실 ESA 산출물 대상.

엔드포인트 함수를 직접 호출(순수 읽기, HTTP·API 호출 0). fastapi 미설치나
data/ 실파일 부재 시 SkipTest(리포 관례: 뷰어 의존성은 스코프됨, 코어 테스트는 무의존).
"""
import unittest

from modules import paths

try:
    from fastapi import HTTPException
    from tools.viewer import app as viewer_app
    _HAVE = True
except Exception:  # fastapi 미설치 등
    _HAVE = False

ISSUE, RUN = "issue_esa", "dryrun2"
_READY = _HAVE and paths.issue(ISSUE).exists()


@unittest.skipUnless(_READY, "fastapi 미설치 또는 issue_esa 산출물 없음")
class ViewerNodeEndpoints(unittest.TestCase):
    def test_issue_node(self):
        d = viewer_app.api_issue(ISSUE)
        self.assertEqual(d["issue_id"], ISSUE)
        self.assertTrue(d.get("body"), "로더 노드: issue body 존재해야")

    def test_facts_node(self):
        d = viewer_app.api_facts(ISSUE)
        self.assertTrue(d["facts"])
        self.assertIn("prior", d["facts"][0], "추출기 노드: prior 포함해야")
        self.assertIn("critical", d["facts"][0])

    def test_assignment_node(self):
        d = viewer_app.api_assignment(ISSUE)
        self.assertIn("seed", d)
        self.assertTrue(d["agents"])
        for k in ("agent_id", "perspective", "stance", "assigned_fact_ids"):
            self.assertIn(k, d["agents"][0])

    def test_analysis_node(self):
        if not paths.judgment(ISSUE, RUN).exists():
            self.skipTest("judgment 없음")
        d = viewer_app.api_analysis(ISSUE, RUN)
        # report: 조건부 hazard·누적·FAR
        self.assertIn("transitions", d["report"])
        self.assertIn("far_by_stage", d["report"])
        # fact-clock: w=0,1 병기 + 분해
        self.assertIn(0, d["fact_clock"]["by_w"])
        self.assertIn(1, d["fact_clock"]["by_w"])
        self.assertIn("w_divergence", d["fact_clock"])
        # critical 스코프 병기
        self.assertIn("transitions", d["report_critical"])

    def test_missing_issue_404(self):
        with self.assertRaises(HTTPException) as cm:
            viewer_app.api_issue("nope_no_such_issue")
        self.assertEqual(cm.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
