"""[패키지 A · 신동범] judge 진행 계기판 테스트 (보드 요청 2026-07-23 · 민옥).

관측 계기판이 (1) 표마다 진행 한 줄을 찍고 (2) summary.judge_health 에 표 수·파싱실패 수를
기록하는지, 그리고 기존 판정 구조엔 영향이 없는지(추가만) 확인한다. API 불필요(offline).
"""
import contextlib
import io
import unittest

from modules import judge


class TestJudgeHealth(unittest.TestCase):
    def test_offline_records_health_and_prints_progress(self):
        cfg = judge._load_config(None)
        n_votes = int(cfg["judge_n_votes"])

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = judge.judge_debate("issue_esa", "dryrun", cfg, offline=True)
        out = buf.getvalue()

        # (1) 진행 라인 — 표마다 한 줄, 요청 형식(stage·팩트·표·파싱실패 누적) 포함
        prog = [ln for ln in out.splitlines() if ln.startswith("[judge] stage")]
        self.assertTrue(prog, "진행 라인이 하나도 출력되지 않았다")
        for label in ("stage", "팩트", "표", "파싱실패 누적"):
            self.assertIn(label, prog[0])

        # (2) 건강 카운트 — summary.judge_health 기록
        health = result["summary"]["judge_health"]
        self.assertIn("n_calls", health)
        self.assertIn("n_parse_fail", health)
        # 총 표 수 = 각 stage 팩트 수 합 x n_votes (매 stage 는 전 팩트 완전 스냅샷)
        expected_calls = sum(len(st["facts"]) for st in result["stages"]) * n_votes
        self.assertEqual(health["n_calls"], expected_calls)
        self.assertEqual(len(prog), expected_calls)  # 표마다 정확히 한 줄
        self.assertEqual(health["n_parse_fail"], 0)  # 오프라인 스텁은 파싱실패 없음

        # 판정 구조 불변 — 기존 summary 필드가 그대로 존재(추가만)
        for key in ("far_by_stage", "far_system", "far_agent_mean", "far_critical"):
            self.assertIn(key, result["summary"])

    def test_is_parse_fail_reads_reason_only(self):
        # _parse_vote 가 파싱 실패 시 남기는 접두사만 True
        self.assertTrue(judge._is_parse_fail({"reason": "parse_fail: {깨진 JSON"}))
        # 정상 근거·오프라인 스텁·빈 값은 False (판정 결과에 영향 없음)
        self.assertFalse(judge._is_parse_fail({"reason": "발화에 팩트가 명시됨"}))
        self.assertFalse(judge._is_parse_fail({"reason": "offline-stub(substring)"}))
        self.assertFalse(judge._is_parse_fail({}))


if __name__ == "__main__":
    unittest.main()
