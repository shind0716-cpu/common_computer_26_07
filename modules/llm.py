"""[패키지 A · 신동범] Anthropic API 호출 래퍼 — debate_engine·judge 공용.

저자 코드 utils.py의 재시도·폴백 방식(tenacity, 실패 시 공백 반환)을 계승하되 Anthropic SDK로 옮겼다.
config의 모델 별칭(claude-haiku 등)을 실제 모델 ID로 해석하는 것도 여기 책임.
"""
import os
import time

# anthropic·dotenv 는 실호출 시점에만 지연 import 한다 — SDK 미설치 컴퓨터에서도
# (quickstart·오프라인 테스트) 이 모듈과 debate_engine 을 import 할 수 있어야 한다.
# "API 키 불필요 경로는 끝까지 키·SDK 불필요" (QUICKSTART 약속, judge.py 와 동일 방식).

# config는 사람이 읽기 쉬운 별칭을 쓰고, 실제 ID 해석은 코드가 한다.
# 모델을 바꿀 땐 configs/*.yaml만 고치면 되도록 유지할 것.
MODEL_ALIASES = {
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-sonnet": "claude-sonnet-5",
    "claude-opus": "claude-opus-4-8",
}

MAX_TOKENS = 2048
MAX_ATTEMPTS = 5
FALLBACK = " "  # 저자 코드 fallback()과 동일 — 실패해도 파이프라인을 멈추지 않는다

_client = None


def resolve_model(name: str) -> str:
    """별칭이면 실제 모델 ID로, 이미 실제 ID면 그대로."""
    return MODEL_ALIASES.get(name, name)


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic  # 지연 import — 오프라인 경로는 SDK 불필요

        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 없음. .env.example을 .env로 복사하고 키를 넣을 것 "
                "(Windows: copy .env.example .env)"
            )
        _client = Anthropic(api_key=key)
    return _client


def obtain_response(inputs: str, model: str, temperature: float = 0.0) -> str:
    """프롬프트 하나 → 응답 텍스트 하나. 저자 obtain_response()와 같은 계약.

    재시도 5회(지수 백오프) 후에도 실패하면 공백을 반환한다 — 저자 코드 계승.
    한 발화가 비어도 나머지 토론은 계속돼야 하고, 빈 발화 자체가 관측 대상이다.
    """
    client = _get_client()
    model_id = resolve_model(model)
    for attempt in range(MAX_ATTEMPTS):
        try:
            msg = client.messages.create(
                model=model_id,
                max_tokens=MAX_TOKENS,
                temperature=temperature,
                messages=[{"role": "user", "content": inputs}],
            )
            parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
            text = "".join(parts).strip()
            return text if text else FALLBACK
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 재시도 후 폴백
            if attempt == MAX_ATTEMPTS - 1:
                print(f"[WARN] LLM 호출 {MAX_ATTEMPTS}회 실패, 폴백 반환: {e}")
                return FALLBACK
            time.sleep(min(5 * (2 ** attempt), 30))
    return FALLBACK
