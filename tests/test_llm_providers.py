"""다중 공급자 라우팅 테스트 (2026-07-30 · 민옥). 실호출 0 — 전부 모의.

이 테스트가 지키는 것은 "GPT가 돌아간다"가 아니라 **조용히 틀리지 않는다**다:
  · 모델 이름 → 공급자 유도가 맞나 (오타가 기본 공급자로 흘러가지 않나)
  · 키가 없거나 자리표시자면 **시작 전에** 죽나 (실측 사고 재발 방지)
  · 호출 계약 `obtain_response(inputs, model=, temperature=)` 이 불변인가
  · OpenAI 파라미터 명 폴백이 작동하고 **편차가 기록되나**
"""
import os
import unittest
from unittest import mock

from modules import llm


class TestProviderRouting(unittest.TestCase):
    def test_aliases_route_to_right_provider(self):
        self.assertEqual(llm.resolve_provider("claude-haiku"), "anthropic")
        self.assertEqual(llm.resolve_provider("gpt-mini"), "openai")
        self.assertEqual(llm.resolve_provider("gemini-flash"), "gemini")

    def test_raw_ids_route_too(self):
        # 별칭이 아닌 실제 ID 를 config 에 적어도 유도돼야 한다.
        self.assertEqual(llm.resolve_provider("claude-sonnet-5"), "anthropic")
        self.assertEqual(llm.resolve_provider("gpt-5.4-mini"), "openai")
        self.assertEqual(llm.resolve_provider("gemini-3-flash-preview"), "gemini")

    def test_unknown_model_dies_not_defaults(self):
        # 종전 구조의 함정: 무엇을 적어도 Anthropic 으로 갔다. 이제는 즉사한다.
        with self.assertRaises(KeyError):
            llm.resolve_provider("llama-9")

    def test_obtain_response_rejects_unknown_model_without_fallback(self):
        # 폴백(공백)으로 삼키지 않는다 — 설정 오류는 실행 중 실패가 아니다.
        with self.assertRaises(KeyError):
            llm.obtain_response("x", model="llama-9")


class TestPreflight(unittest.TestCase):
    def test_missing_key_exits(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with mock.patch.object(llm, "_load_env", lambda: None):
                with self.assertRaises(SystemExit):
                    llm.preflight("gpt-mini")

    def test_placeholder_key_exits(self):
        # 실측 사고: sk-ant-... 10자가 들어 있어 401 → 5회 백오프 → 공백 폴백으로
        # 로그가 성공처럼 보였다. 짧은 키는 시작 전에 잡는다.
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-"}, clear=False):
            with mock.patch.object(llm, "_load_env", lambda: None):
                with self.assertRaises(SystemExit):
                    llm.preflight("claude-haiku")

    def test_real_looking_key_passes_and_reports(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-" + "x" * 60},
                             clear=False):
            with mock.patch.object(llm, "_load_env", lambda: None):
                m = llm.preflight("gpt-mini")
        self.assertEqual(m["provider"], "openai")
        self.assertEqual(m["key_env"], "OPENAI_API_KEY")
        self.assertTrue(m["model_id"])


class _Resp:
    def __init__(self, code, payload=None, text=""):
        self.status_code = code
        self._p = payload or {}
        self.text = text

    def json(self):
        return self._p


class TestOpenAIFallback(unittest.TestCase):
    def setUp(self):
        llm._openai_maxtok = "max_tokens"
        llm._openai_no_temp = False
        llm.LAST_DEVIATIONS.clear()

    def _run_with(self, responses):
        calls = []

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append(dict(json))
            return responses[len(calls) - 1]

        fake_requests = mock.MagicMock()
        fake_requests.post = fake_post
        with mock.patch.dict("sys.modules", {"requests": fake_requests}):
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-" + "x" * 60},
                                 clear=False):
                with mock.patch.object(llm, "_load_env", lambda: None):
                    out = llm.obtain_response("prompt", model="gpt-mini",
                                              temperature=1.0)
        return out, calls

    def test_max_tokens_renamed_and_recorded(self):
        ok = _Resp(200, {"choices": [{"message": {"content": "답"}}]})
        bad = _Resp(400, text="Unsupported parameter: 'max_tokens' is not supported")
        out, calls = self._run_with([bad, ok])
        self.assertEqual(out, "답")
        self.assertIn("max_tokens", calls[0])
        self.assertIn("max_completion_tokens", calls[1])
        # 조용한 파라미터 변경 금지 — 편차가 남아야 한다.
        self.assertTrue(any("max_completion_tokens" in d for d in llm.LAST_DEVIATIONS))

    def test_temperature_dropped_and_recorded(self):
        ok = _Resp(200, {"choices": [{"message": {"content": "답"}}]})
        bad = _Resp(400, text="Unsupported value: 'temperature' is not supported")
        out, calls = self._run_with([bad, ok])
        self.assertEqual(out, "답")
        self.assertIn("temperature", calls[0])
        self.assertNotIn("temperature", calls[1])
        self.assertTrue(any("temperature" in d for d in llm.LAST_DEVIATIONS))

    def test_empty_response_becomes_fallback_not_crash(self):
        ok = _Resp(200, {"choices": [{"message": {"content": "   "}}]})
        out, _ = self._run_with([ok])
        self.assertEqual(out, llm.FALLBACK)   # 빈 발화 자체가 관측 대상


class TestEngineGate(unittest.TestCase):
    def test_engine_skips_preflight_when_fn_injected(self):
        # 테스트 경로(utterance_fn 주입)는 키가 없어도 돌아야 한다 —
        # "API 키 불필요 경로엔 키 불필요"(QUICKSTART 약속).
        import json
        import shutil
        import tempfile
        from pathlib import Path

        from modules import debate_engine, paths
        from tests.test_note_slot import FakeLLM, _cfg, _write_fixture

        tmp = Path(tempfile.mkdtemp())
        orig = paths.DATA
        paths.DATA = tmp / "data"
        try:
            iid = _write_fixture(paths.DATA)
            cfg = _cfg(tmp, debate_model="gpt-mini")
            called = {"n": 0}

            def boom(model):
                called["n"] += 1
                raise SystemExit("preflight 이 불렸다")

            with mock.patch.object(llm, "preflight", boom):
                out = debate_engine.run(iid, "nokey", cfg, utterance_fn=FakeLLM())
            self.assertEqual(called["n"], 0)
            self.assertTrue(out.exists())
            ev = [json.loads(x) for x in
                  out.read_text(encoding="utf-8").splitlines() if x.strip()]
            # 가짜 경로이므로 공급자 필드는 비어 있다(실호출이 아님을 로그가 안다).
            self.assertIsNone(ev[0]["settings"]["provider"])
        finally:
            paths.DATA = orig
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
