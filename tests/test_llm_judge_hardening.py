"""llm·judge 수리 회귀 테스트 (2026-07-30 · 동범 — 보드 회신 ⑤·⑥ 후속). 실호출 0 — 전부 모의.

이 테스트가 지키는 것은 "고쳐졌다"가 아니라 **다시 안 무너진다**다:
  · F3 회귀 복구 — 재시도는 429/5xx 만, 4xx 는 즉사 (실패의 공백 위장 금지)
  · 절단 감지 — finish/stop reason 이 절단이면 폴백이 아니라 예외 (편차 D1 재발 방지)
  · 파라미터 폴백은 400 에서만 — 429 본문에 'temperature' 가 스쳐도 발동하지 않음
  · Gemini 키는 URL 이 아니라 헤더 + 예외 문자열 키 마스킹 (로그 평문 노출 차단)
  · judge 별칭은 llm 단일 소스 위임 (사본 분기 구조적 차단)
  · judge.temperature 기록 = 실제 전송값 (cfg 가 아니라 — 기록과 실체의 일치)
  · judge_health 가 입력 공백 발화를 센다 (far_system=1.0 오염 경로 가시화)
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules import judge, llm


class _Resp:
    def __init__(self, code, payload=None, text=""):
        self.status_code = code
        self._p = payload or {}
        self.text = text

    def json(self):
        return self._p


def _run_openai(responses, temperature=1.0):
    """가짜 requests 로 obtain_response(gpt-mini) 실행. (응답열, 보낸 payload 열) 반환."""
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": dict(headers or {}), "json": dict(json)})
        return responses[min(len(calls) - 1, len(responses) - 1)]

    fake_requests = mock.MagicMock()
    fake_requests.post = fake_post
    with mock.patch.dict("sys.modules", {"requests": fake_requests}):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-" + "x" * 60},
                             clear=False):
            with mock.patch.object(llm, "_load_env", lambda: None):
                with mock.patch.object(llm.time, "sleep", lambda s: None):  # 백오프 대기 생략
                    out = llm.obtain_response("prompt", model="gpt-mini",
                                              temperature=temperature)
    return out, calls


class TestFailFastWhitelist(unittest.TestCase):
    """F3 회귀 복구 — run_experiment._post() 화이트리스트가 본류에도 있는가."""

    def setUp(self):
        llm._openai_maxtok = "max_tokens"
        llm._openai_no_temp = False
        llm.LAST_DEVIATIONS.clear()

    def test_401_dies_immediately_not_65s_blank(self):
        # 종전(회귀): 401 → 5회 백오프(~65초) → 공백 폴백 = 키 오류가 침묵으로 위장.
        with self.assertRaises(llm.LLMCallError) as ctx:
            _run_openai([_Resp(401, text="Incorrect API key provided")])
        self.assertEqual(ctx.exception.status, 401)

    def test_401_costs_exactly_one_call(self):
        calls = []

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append(1)
            return _Resp(401, text="Incorrect API key provided")

        fake_requests = mock.MagicMock()
        fake_requests.post = fake_post
        with mock.patch.dict("sys.modules", {"requests": fake_requests}):
            with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-" + "x" * 60},
                                 clear=False):
                with mock.patch.object(llm, "_load_env", lambda: None):
                    with self.assertRaises(llm.LLMCallError):
                        llm.obtain_response("p", model="gpt-mini")
        self.assertEqual(len(calls), 1)   # 재시도 무의미 실패에 재시도 0회

    def test_429_still_retries_then_succeeds(self):
        # 일시 장애는 종전대로 재시도 — 화이트리스트가 폴백까지 없애면 안 된다.
        ok = _Resp(200, {"choices": [{"message": {"content": "답"},
                                      "finish_reason": "stop"}]})
        out, calls = _run_openai([_Resp(429, text="rate limit"), ok])
        self.assertEqual(out, "답")
        self.assertEqual(len(calls), 2)

    def test_429_exhausted_still_falls_back_to_blank(self):
        # 저자 계승 계약 유지: 일시 장애가 5회 다 실패하면 공백 폴백(파이프라인 계속).
        out, calls = _run_openai([_Resp(429, text="rate limit")] * llm.MAX_ATTEMPTS)
        self.assertEqual(out, llm.FALLBACK)
        self.assertEqual(len(calls), llm.MAX_ATTEMPTS)

    def test_retryable_reads_anthropic_style_status_code(self):
        # anthropic SDK 예외는 .status_code 를 실어 온다 — 문자열 파싱 없이 판별.
        class _SdkErr(Exception):
            status_code = 400

        class _SdkOverloaded(Exception):
            status_code = 529

        self.assertFalse(llm._retryable(_SdkErr()))
        self.assertTrue(llm._retryable(_SdkOverloaded()))
        self.assertFalse(llm._retryable(ModuleNotFoundError("anthropic")))  # SDK 부재 즉사
        self.assertTrue(llm._retryable(TimeoutError()))  # 상태 미상 = 일시 장애로 재시도


class TestTruncationDetected(unittest.TestCase):
    """절단은 폴백이 아니라 예외 — 절단본이 채점에 섞이는 경로 차단(편차 D1 이식)."""

    def test_openai_finish_reason_length_raises(self):
        trunc = _Resp(200, {"choices": [{"message": {"content": "잘린 답"},
                                         "finish_reason": "length"}]})
        with self.assertRaises(llm.LLMTruncated):
            _run_openai([trunc])

    def test_gemini_max_tokens_raises_and_key_in_header_not_url(self):
        calls = []
        payload = {"candidates": [{"content": {"parts": [{"text": "잘린 답"}]},
                                   "finishReason": "MAX_TOKENS"}]}

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append({"url": url, "headers": dict(headers or {})})
            return _Resp(200, payload)

        fake_requests = mock.MagicMock()
        fake_requests.post = fake_post
        key = "AIza" + "g" * 35
        with mock.patch.dict("sys.modules", {"requests": fake_requests}):
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY": key}, clear=False):
                with mock.patch.object(llm, "_load_env", lambda: None):
                    with self.assertRaises(llm.LLMTruncated):
                        llm.obtain_response("p", model="gemini-flash")
        # 보안 1건: 키가 URL 쿼리스트링에 없고 헤더로만 간다.
        self.assertNotIn("key=", calls[0]["url"])
        self.assertNotIn(key, calls[0]["url"])
        self.assertEqual(calls[0]["headers"].get("x-goog-api-key"), key)


class TestParamFallbackOnlyOn400(unittest.TestCase):
    """무음 실패 ⓒ — 429 본문에 'temperature' 가 스쳐도 파라미터를 제거하지 않는다."""

    def setUp(self):
        llm._openai_maxtok = "max_tokens"
        llm._openai_no_temp = False
        llm.LAST_DEVIATIONS.clear()

    def test_429_mentioning_temperature_does_not_drop_it(self):
        bad = _Resp(429, text="Rate limit: reduce temperature of requests")
        out, calls = _run_openai([bad] * llm.MAX_ATTEMPTS)
        self.assertEqual(out, llm.FALLBACK)          # 429 는 재시도→폴백 (종전 계약)
        self.assertFalse(llm._openai_no_temp)        # sticky 오염 없음
        for c in calls:                              # 모든 재시도에 temperature 유지
            self.assertIn("temperature", c["json"])

    def test_400_unsupported_temperature_still_falls_back(self):
        # 진짜 400 파라미터 오류는 종전대로 폴백 + 편차 기록 (기존 동작 보존).
        ok = _Resp(200, {"choices": [{"message": {"content": "답"},
                                      "finish_reason": "stop"}]})
        bad = _Resp(400, text="Unsupported value: 'temperature' is not supported")
        out, calls = _run_openai([bad, ok])
        self.assertEqual(out, "답")
        self.assertNotIn("temperature", calls[1]["json"])
        self.assertTrue(any("temperature" in d for d in llm.LAST_DEVIATIONS))


class TestKeyMasking(unittest.TestCase):
    def test_mask_hides_key_values_in_error_text(self):
        key = "sk-" + "z" * 60
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": key}, clear=False):
            masked = llm._mask(f"HTTPSConnectionPool auth failed for token {key} retry")
        self.assertNotIn(key, masked)
        self.assertIn("sk-zzz", masked)   # 앞 6자는 남겨 어느 키인지 식별 가능


class TestJudgeAliasSingleSource(unittest.TestCase):
    """사본 제거 1단계 — judge 별칭·해석이 llm 을 그대로 가리키는가."""

    def test_alias_table_is_same_object(self):
        self.assertIs(judge.MODEL_ALIASES, llm.MODEL_ALIASES)

    def test_resolve_delegates_including_non_anthropic(self):
        # 종전 judge 사본엔 gpt/gemini 별칭이 없어 config 로 지정할 방법이 없었다(ⓐ).
        self.assertEqual(judge._resolve_model("gpt-mini"), llm.resolve_model("gpt-mini"))
        self.assertEqual(judge._resolve_model("claude-sonnet"),
                         llm.resolve_model("claude-sonnet"))
        # 별칭이 아닌 실제 ID 는 그대로 통과(종전 동작 보존 — sprint_mini 가 쓰는 형태).
        self.assertEqual(judge._resolve_model("claude-sonnet-4-6"), "claude-sonnet-4-6")


class TestJudgeMetadataTruth(unittest.TestCase):
    """judge.temperature 기록 = 실제 전송값 (7/30 보드 회신 ② 불일치 수정)."""

    def test_cfg_temperature_is_ignored_and_actual_recorded(self):
        import contextlib
        import io
        cfg = {"judge_model": "claude-sonnet", "judge_temperature": 0.7,
               "judge_n_votes": 3}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = judge.judge_debate("issue_esa", "dryrun", cfg, offline=True)
        # 기록은 cfg(0.7)가 아니라 실제 전송 상수(0) — 기록과 실체의 일치.
        self.assertEqual(result["judge"]["temperature"], judge.JUDGE_TEMPERATURE)
        # 그리고 조용히 무시하지 않는다 — 경고가 찍힌다.
        self.assertIn("사용되지 않습니다", buf.getvalue())


class TestBlankUtteranceCounter(unittest.TestCase):
    """judge_health.n_blank_utterances — far_system=1.0 오염 경로의 가시화(회신 ⑤)."""

    def _fixture(self, tmp: Path, issue_id: str, run_id: str, blanks: int):
        from modules import paths
        facts_p = paths.facts(issue_id)
        facts_p.parent.mkdir(parents=True, exist_ok=True)
        facts_p.write_text(json.dumps({"facts": [
            {"fact_id": "f1", "text": "보증금 500달러", "critical": True}]},
            ensure_ascii=False), encoding="utf-8")
        deb_p = paths.debate(issue_id, run_id)
        deb_p.parent.mkdir(parents=True, exist_ok=True)
        events = [{"event": "utterance", "round": 0, "agent_id": "a1",
                   "response_text": "보증금 500달러 조항이 있습니다"}]
        for i in range(blanks):
            events.append({"event": "utterance", "round": 0,
                           "agent_id": f"b{i}", "response_text": llm.FALLBACK})
        deb_p.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events),
                         encoding="utf-8")

    def test_counts_llm_fallback_blanks_in_input(self):
        import contextlib
        import io
        from modules import paths
        tmp = Path(tempfile.mkdtemp())
        orig = paths.DATA
        paths.DATA = tmp / "data"
        try:
            self._fixture(tmp, "issue_hard", "blankrun", blanks=2)
            with contextlib.redirect_stdout(io.StringIO()):
                result = judge.judge_debate("issue_hard", "blankrun",
                                            judge._load_config(None), offline=True)
            health = result["summary"]["judge_health"]
            self.assertEqual(health["n_blank_utterances"], 2)
            # 기존 계기판 필드 불변(추가만).
            self.assertIn("n_calls", health)
            self.assertIn("n_parse_fail", health)
        finally:
            paths.DATA = orig
            shutil.rmtree(tmp, ignore_errors=True)

    def test_zero_when_no_blanks(self):
        import contextlib
        import io
        from modules import paths
        tmp = Path(tempfile.mkdtemp())
        orig = paths.DATA
        paths.DATA = tmp / "data"
        try:
            self._fixture(tmp, "issue_hard", "cleanrun", blanks=0)
            with contextlib.redirect_stdout(io.StringIO()):
                result = judge.judge_debate("issue_hard", "cleanrun",
                                            judge._load_config(None), offline=True)
            self.assertEqual(
                result["summary"]["judge_health"]["n_blank_utterances"], 0)
        finally:
            paths.DATA = orig
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
