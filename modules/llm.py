"""[패키지 A · 신동범 / 2026-07-30 민옥: 다중 공급자 확장] LLM 호출 래퍼 — debate_engine·judge 공용.

저자 코드 utils.py의 재시도·폴백 방식(tenacity, 실패 시 공백 반환)을 계승하되 SDK를 갈아끼운다.
config의 모델 별칭(claude-haiku 등)을 실제 모델 ID로 해석하는 것도 여기 책임.

[2026-07-30 · 민옥] **공급자 3종 확장 (Anthropic / OpenAI / Gemini).**
계기: Anthropic 키 없이 GPT 키만 있는 상태에서 본실험을 돌려야 했다. 종전 이 모듈은
Anthropic 전용이라 `debate_model`에 무엇을 적어도 Anthropic 으로 갔고, 키가 죽으면
5회 재시도 후 **공백을 반환하며 조용히 완주**했다 — 전 발화가 빈 로그가 "성공"으로
남는 구조였다. 공급자를 모델 이름에서 유도하게 바꾸고, 그 유도 결과를 로그에 적는다.

**설계 원칙 3개**

1. **공급자는 모델 이름이 결정한다** (`resolve_provider`). config 에 공급자 칸을
   따로 만들지 않는다 — 칸이 둘이면 "gpt 모델인데 공급자는 anthropic" 같은 모순
   상태가 config 에 적힐 수 있고, 그건 조용히 틀리는 종류의 오류다.
2. **호출 계약은 불변.** `obtain_response(inputs, model=, temperature=) -> str` 은
   글자 하나 안 바뀐다. debate_engine·judge·테스트가 전부 이 시그니처에 걸려 있고,
   저자 코드 계승 관계도 이 계약이다.
3. **키 부재는 즉사, 호출 실패는 폴백.** 종전엔 둘 다 폴백이라 "키가 없다"가
   빈 발화로 위장됐다. 시작 전에 알 수 있는 것(키 없음·미지 공급자)은 시작 전에
   죽이고, 돌다가 나는 것(레이트리밋·타임아웃)만 폴백한다. `preflight()` 가
   그 관문이며 debate_engine 이 run 시작 전에 부른다.

편차 기록: OpenAI 신형 모델은 `max_tokens` 를 거부하고 `max_completion_tokens` 를
요구하며, 일부는 `temperature` 를 아예 안 받는다. 두 경우 다 파라미터를 갈아 재시도하고
무엇을 갈았는지 `LAST_DEVIATIONS` 에 남긴다 — 조용한 파라미터 변경은 재현성을 깬다.
(같은 처리를 experiments/discourse_progression/run_experiment.py 가 이미 하고 있고,
 이 모듈은 그 실측 검증된 로직을 파이프라인 본류로 들여온 것이다.)
"""
import os
import time

# anthropic·dotenv 등을 호출 시점에만 지연 import 한다 — SDK 미설치 컴퓨터에서도
# (quickstart·오프라인 테스트) 이 모듈과 debate_engine 을 import 할 수 있어야 한다.
# "API 키 불필요 경로엔 키·SDK 불필요" (QUICKSTART 약속, judge.py 와 동일 방식).

# config엔 사람이 읽기 쉬운 별칭을 쓰고, 실제 ID 해석은 코드가 한다.
# 모델을 바꿀 땐 configs/*.yaml만 고치면 되도록 별칭을 둔다.
MODEL_ALIASES = {
    # Anthropic
    "claude-haiku": "claude-haiku-4-5-20251001",
    "claude-sonnet": "claude-sonnet-5",
    "claude-opus": "claude-opus-4-8",
    # OpenAI — 실제 ID는 .env 의 OPENAI_MODEL 로도 덮어쓸 수 있다(실험 러너 전례).
    "gpt-mini": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
    "gpt": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
    # Gemini
    "gemini-flash": os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"),
    "gemini": os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"),
}

# 공급자 판별 — 해석된 실제 모델 ID의 접두사로 정한다.
PROVIDER_PREFIXES = (
    ("claude", "anthropic"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("gemini", "gemini"),
)
PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

MAX_TOKENS = 2048
GEMINI_MAX_TOKENS = 4096   # 편차 D1 계승: thinking 토큰이 예산을 잠식해 본문 절단
GEMINI_THINKING = "minimal"
MAX_ATTEMPTS = 5
FALLBACK = " "  # 저자 코드 fallback()과 동일 — 실패해도 파이프라인을 멈추지 않는다

# 이번 프로세스에서 실제로 일어난 파라미터 편차(조용한 변경 금지).
LAST_DEVIATIONS: list[str] = []

_clients: dict = {}
_openai_maxtok = "max_tokens"    # 한 번 폴백하면 이후 호출은 처음부터 새 이름 사용
_openai_no_temp = False          # temperature 미지원 모델로 판명되면 이후 생략


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def resolve_model(name: str) -> str:
    """별칭이면 실제 모델 ID로, 아니면 실제 ID로 그대로."""
    return MODEL_ALIASES.get(name, name)


def resolve_provider(name: str) -> str:
    """모델 이름(별칭 또는 실제 ID) → 공급자. 미지 모델은 즉사한다.

    조용히 기본 공급자로 흘리지 않는 이유: 오타 하나가 "다른 모델이 돌았는데 로그엔
    맞다고 적힌" run 을 만든다(stance·window 가드와 같은 자리)."""
    model_id = resolve_model(name).lower()
    for prefix, provider in PROVIDER_PREFIXES:
        if model_id.startswith(prefix):
            return provider
    raise KeyError(
        f"공급자를 알 수 없는 모델: {name} (해석: {resolve_model(name)}) — "
        f"llm.PROVIDER_PREFIXES 에 접두사를 등록하거나 별칭을 쓰세요 "
        f"(등록된 별칭: {sorted(MODEL_ALIASES)})")


def preflight(model: str) -> dict:
    """run 시작 **전에** 부르는 관문. 키가 없으면 여기서 죽는다.

    왜 필요한가: obtain_response 는 어떤 실패도 공백으로 폴백한다(저자 계승). 그래서
    키가 없으면 전 발화가 빈 로그가 조용히 완주해버린다 — 24콜을 다 태운 뒤에야
    폴백 카운터로 알게 된다. 시작 전에 알 수 있는 실패는 시작 전에 알린다."""
    _load_env()
    provider = resolve_provider(model)
    env = PROVIDER_KEY_ENV[provider]
    key = os.environ.get(env, "")
    if not key:
        raise SystemExit(
            f"[llm] {env} 없음 — 모델 '{model}'({provider}) 을 쓰려면 .env 에 이 키가 "
            f"있어야 합니다. (.env.example 을 .env 로 복사 후 키를 넣으세요)")
    if len(key) < 24:
        # 자리표시자 조기 발견 — 실측 사고: sk-ant-... 10자가 들어 있어 401 이 났고,
        # 5회 백오프 뒤 공백 폴백으로 넘어가 로그가 성공처럼 보였다(7/30).
        raise SystemExit(
            f"[llm] {env} 가 너무 짧습니다(길이 {len(key)}) — 자리표시자로 보입니다. "
            f"실제 키를 넣으세요.")
    return {"model": model, "model_id": resolve_model(model), "provider": provider,
            "key_env": env}


# ─── 공급자별 호출 ────────────────────────────────────────────────────────────
def _call_anthropic(model_id: str, inputs: str, temperature: float) -> str:
    if "anthropic" not in _clients:
        from anthropic import Anthropic  # 지연 import
        _load_env()
        _clients["anthropic"] = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = _clients["anthropic"].messages.create(
        model=model_id, max_tokens=MAX_TOKENS, temperature=temperature,
        messages=[{"role": "user", "content": inputs}],
    )
    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def _call_openai(model_id: str, inputs: str, temperature: float) -> str:
    """raw HTTP — SDK 버전 차이에 안 걸리게. 파라미터 명 폴백 포함."""
    global _openai_maxtok, _openai_no_temp
    import requests
    _load_env()
    key = os.environ["OPENAI_API_KEY"]
    url = "https://api.openai.com/v1/chat/completions"
    payload = {"model": model_id,
               "messages": [{"role": "user", "content": inputs}],
               _openai_maxtok: MAX_TOKENS}
    if not _openai_no_temp:
        payload["temperature"] = temperature
    for _ in range(3):   # 신형 모델 파라미터 명 변화 폴백
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        body = r.text[:400]
        if "max_tokens" in body and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            _openai_maxtok = "max_completion_tokens"
            dev = "max_tokens→max_completion_tokens"
            if dev not in LAST_DEVIATIONS:
                LAST_DEVIATIONS.append(dev)
            continue
        if "temperature" in body and "temperature" in payload:
            payload.pop("temperature")
            _openai_no_temp = True
            dev = "temperature 미지원 — 제거됨(보고서에 명기할 것)"
            if dev not in LAST_DEVIATIONS:
                LAST_DEVIATIONS.append(dev)
            continue
        raise RuntimeError(f"OpenAI {r.status_code}: {body}")
    raise RuntimeError("OpenAI 파라미터 폴백 3회 소진")


def _call_gemini(model_id: str, inputs: str, temperature: float) -> str:
    import requests
    _load_env()
    key = os.environ["GEMINI_API_KEY"]
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_id}:generateContent?key={key}")
    payload = {"contents": [{"parts": [{"text": inputs}]}],
               "generationConfig": {
                   "temperature": temperature,
                   "maxOutputTokens": GEMINI_MAX_TOKENS,
                   "thinkingConfig": {"thinkingLevel": GEMINI_THINKING}}}
    r = requests.post(url, json=payload, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini {r.status_code}: {r.text[:400]}")
    cand = r.json()["candidates"][0]
    return "".join(p.get("text", "")
                   for p in cand.get("content", {}).get("parts", [])).strip()


_DISPATCH = {"anthropic": _call_anthropic, "openai": _call_openai,
             "gemini": _call_gemini}


def obtain_response(inputs: str, model: str, temperature: float = 0.0) -> str:
    """프롬프트 하나 → 응답 텍스트 하나. 저자 obtain_response()와 같은 계약.

    재시도 5회 지수 백오프, 끝에도 실패하면 공백을 반환한다 — 저자 코드 계승.
    한 발화가 비어도 나머지 토론은 계속돼야 하고, 빈 발화 자체가 관측 대상이다.

    공급자는 model 이름에서 유도한다(resolve_provider). 미지 모델은 폴백하지 않고
    즉사한다 — 그건 돌다가 나는 실패가 아니라 설정 오류다."""
    provider = resolve_provider(model)      # 미지 모델이면 여기서 KeyError
    model_id = resolve_model(model)
    fn = _DISPATCH[provider]
    for attempt in range(MAX_ATTEMPTS):
        try:
            text = fn(model_id, inputs, temperature)
            return text if text else FALLBACK
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 재시도 후 폴백
            if attempt == MAX_ATTEMPTS - 1:
                print(f"[WARN] LLM 호출 {MAX_ATTEMPTS}회 실패, 폴백 반환: {e}")
                return FALLBACK
            time.sleep(min(5 * (2 ** attempt), 30))
    return FALLBACK
