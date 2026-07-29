"""[민옥] debate 진행 계기판 테스트 (judge 계기판의 debate 쪽 절반 — 보드 7/23 요청서 참고).

계기판이 (1) 발화마다 진행 한 줄을 찍고 (2) 폴백(무음 공백)을 누적 집계하며,
(3) 산출물(debate.jsonl)에는 아무것도 추가하지 않는지(관측 전용) 확인한다. API 불필요.
표시 규칙: judge 계기판과 통일해 1-기반 — 파일의 round 필드는 종전대로 0-기반.
"""
import contextlib
import io
import unittest

from modules import debate_engine, llm

from tests.test_integration_ledger import N_AGENTS, ROUNDS, IntegrationBase


class TestDebateProgress(IntegrationBase):
    def _run_captured(self, cfg_path, utterance_fn=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            debate_engine.run("issue_esa", "t1", cfg_path,
                              utterance_fn=utterance_fn or self.fake_utterance,
                              judge_vote_fn=None)
        return buf.getvalue()

    def test_progress_line_per_utterance(self):
        out = self._run_captured(self.write_config(ledger_mode="off"))
        prog = [ln for ln in out.splitlines() if ln.startswith("[debate] round")]
        # 발화마다 정확히 한 줄: 초기 8 + 라운드 3 x 8 = 32
        self.assertEqual(len(prog), N_AGENTS * (ROUNDS + 1))
        for label in ("round", "발화", "폴백 누적"):
            self.assertIn(label, prog[0])
        # 첫 줄 = 초기 라운드 첫 발화, 폴백 0 (가짜 발화는 전부 비어 있지 않음)
        self.assertEqual(prog[0],
                         f"[debate] round 1/{ROUNDS + 1} · 발화 1/{N_AGENTS} · 폴백 누적 0")
        self.assertTrue(prog[-1].endswith("폴백 누적 0"))

    def test_display_one_based_file_zero_based(self):
        """표시(1-기반)와 파일(0-기반)의 관계 명문화 — judge 계기판과 동일 규칙."""
        out = self._run_captured(self.write_config(ledger_mode="off"))
        first = next(ln for ln in out.splitlines() if ln.startswith("[debate] round"))
        self.assertIn(f"round 1/{ROUNDS + 1}", first)          # 표시는 1부터
        events = self.read_events()
        first_utt = next(e for e in events if e["event"] == "utterance")
        self.assertEqual(first_utt["round"], 0)                # 파일은 0부터

    def test_fallback_counted_and_output_unchanged(self):
        """폴백(무음 공백) 발화가 정확히 집계되고, 산출물에는 원문 그대로 남는다."""
        calls = {"n": 0}

        def flaky_utterance(inputs, model=None, temperature=None):
            calls["n"] += 1
            return llm.FALLBACK if calls["n"] == 1 else f"발화{calls['n']}"

        out = self._run_captured(self.write_config(ledger_mode="off"),
                                 utterance_fn=flaky_utterance)
        prog = [ln for ln in out.splitlines() if ln.startswith("[debate] round")]
        self.assertTrue(prog[0].endswith("폴백 누적 1"))   # 첫 발화가 폴백
        self.assertTrue(prog[-1].endswith("폴백 누적 1"))  # 이후 증가 없음
        self.assertIn("폴백 1건", out)                     # [OK] 요약 라인
        self.assertIn("⚠ 폴백", out)                       # 경고 표시
        # 산출물 불변: 폴백 발화도 원문(공백) 그대로 기록 — 계기판은 읽기만 한다.
        events = self.read_events()
        first_utt = next(e for e in events if e["event"] == "utterance")
        self.assertEqual(first_utt["response_text"], llm.FALLBACK)

    def test_no_new_event_types_in_output(self):
        """관측 전용 증명: 이벤트 종류가 계약에 있는 것뿐 — progress/run_end 파일 이벤트 없음
        (계기판은 콘솔 전용). prompt_assembly 는 v0.3 확정(7/28 보드)으로 계약에 추가된
        이벤트라 허용 집합에 포함한다 — 이 가드의 목적은 '미합의 이벤트 차단'이다.

        2026-07-29 추가: run_meta 도 계약 이벤트다(스키마 v0.3 §4‴ — 조건 좌표 기록,
        요한 소관 확정). 계기판 산물이 아니므로 같은 이유로 허용 집합에 포함한다."""
        self._run_captured(self.write_config(ledger_mode="off"))
        kinds = {e["event"] for e in self.read_events()}
        self.assertEqual(kinds, {"utterance", "seating", "prompt_assembly", "run_meta"})

    def test_is_fallback_definition(self):
        self.assertTrue(debate_engine._is_fallback(llm.FALLBACK))
        self.assertTrue(debate_engine._is_fallback(""))
        self.assertTrue(debate_engine._is_fallback("   "))
        self.assertTrue(debate_engine._is_fallback(None))
        self.assertFalse(debate_engine._is_fallback("정상 발화"))


if __name__ == "__main__":
    unittest.main()
