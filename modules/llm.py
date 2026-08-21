"""[공용 코어 · 8/21 요한 결정 (구 패키지 A · 신동범, 8/21 이적 / 7-30 민옥: 다중 공급자 확장)] LLM 호출 래퍼 — debate_engine·judge 공용.

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

[2026-07-30 · 동범] **재시도 화이트리스트 복원 + 절단 감지 + 키 위생 (리뷰 ⑥ 후속).**
독스트링이 근거로 든 run_experiment._post() 에는 fail-fast 화이트리스트(429/5xx 만
재시도, 나머지 즉시 raise)가 있는데 본류 이식에서 유실됐다 — 회귀 복구다. 원칙 3의
정밀한 문면: **폴백은 "돌다가 나는 일시 장애"(429·5xx·타임아웃)에만 허용**되고,
같은 입력이면 같은 실패가 나는 것(4xx 설정·인증 오류, SDK 부재, 출력 절단)은 즉시
예외로 죽는다 — 재시도 5회는 그 실패를 65초 위장한 뒤 공백으로 바꿀 뿐이다.
절단 감지는 참조 러너의 finishReason 검사를 3공급자로 이식(편차 D1 재발 방지).
예외·경고 문자열은 _mask() 로 키를 가린다(키가 URL·본문에 실려 로그로 새는 경로 차단).

[2026-08-14 · 요한] **GLM 공급자 추가 (자체 호스팅 · OpenAI 호환).**
계기: 히든 프로필 기억 축 실험(340콜)을 자체 엔드포인트로 돌리기로 함. 종전 구조에서
`glm-5.2` 는 `resolve_provider` 가 접두사를 못 찾아 즉사했다(설계 원칙 1이 의도한 동작).
주소가 고정이 아니므로 키와 함께 `.env`(`GLM_BASE_URL`)를 정본으로 두고, `preflight`
에서 주소 부재도 키 부재와 같이 시작 전에 죽인다. 사고 끄기는 OpenAI 의
`reasoning_effort` 가 아니라 `chat_template_kwargs.enable_thinking` 이라 공급자별
추론 사전(`REASONING_PARAM`)에 값 형태만 다르게 등재했다 — 호출 계약은 불변.

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
    # GLM (OpenAI 호환 자체 엔드포인트) — 주소는 .env 의 GLM_BASE_URL.
    "glm": os.environ.get("GLM_MODEL", "glm-5.2"),
}

# 공급자 판별 — 해석된 실제 모델 ID의 접두사로 정한다.
PROVIDER_PREFIXES = (
    ("claude", "anthropic"),
    ("gpt", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("gemini", "gemini"),
    ("glm", "glm"),
)
PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "glm": "GLM_API_KEY",
}
# GLM 은 자체 호스팅이라 주소가 고정이 아니다 — 키와 함께 .env 가 정본이다.
GLM_BASE_URL_ENV = "GLM_BASE_URL"

# 공급자별 temperature 허용 범위 (2026-07-30 · 민옥 — 온도 관문).
# 범위 밖 값은 API 가 400 을 돌려주고, 400 은 재시도해도 400 이다. 그런데
# obtain_response 는 어떤 예외든 5회 백오프 뒤 공백을 반환하므로(저자 계승), 범위를
# 벗어난 온도는 **전 발화가 빈 로그를 종료코드 0 으로 완주**시킨다 — 키 자리표시자
# 사고와 정확히 같은 모양이며, preflight 는 키만 보므로 이걸 통과시켰다.
# 동범 님 7/23 선결 ①이 지적한 위험(configs/mini_h2_*.yaml 의 haiku + 1.2)의 실현 경로.
# 시작 전에 알 수 있는 실패는 시작 전에 죽인다.
TEMPERATURE_RANGE = {
    "anthropic": (0.0, 1.0),
    "openai": (0.0, 2.0),
    "gemini": (0.0, 2.0),
    "glm": (0.0, 2.0),
}

# ⑨ 추론(사고) 모드 — 공급자별 값 사전 (2026-07-30 · 민옥).
#
# 왜 축으로 올리는가: 종전엔 **공급자마다 추론 상태가 제각각인데 아무도 지정하지 않았고
# 로그에도 안 남았다.** Gemini 만 GEMINI_THINKING 으로 눌러뒀고(편차 D1), Anthropic 은
# 파라미터를 안 넘겨 모델 기본값(Sonnet 5 는 adaptive thinking 이 기본 ON — 동범 7/23),
# OpenAI 도 모델 기본값이었다. 즉 같은 실험을 공급자만 바꿔 돌리면 사고량이 달라지는데
# 그 사실이 산출물 어디에도 없었다 — 온도 지뢰와 같은 종류의 "조용히 달라진 조건".
#
# 연구상 의미: 추론은 4관문의 **보유와 발화 사이**에 앉는다. "생각에선 꺼냈는데 발화엔
# 안 실었다"가 담화 전진 가설의 직접 증거이므로, 이 축은 나중에 1급 변수가 될 수 있다.
# ⚠ 단 공급자마다 추론 원문 접근성이 달라(Anthropic=블록 반환 / OpenAI·Gemini=요약 또는
# 없음) **추론 on/off 비교는 같은 공급자 안에서만** 유효하다.
#
# off = 끌 수 있으면 끈다, on = 켠다, default = 지정하지 않는다(모델 기본값 — 종전 동작).
# default 를 남겨두는 이유: 과거 run 과의 연속성. 지정 안 함과 꺼짐은 다른 상태다.
REASONING_MODES = ("default", "off", "on")
# 공급자별로 실제 무엇을 보내는지. None 이면 그 공급자에서 그 값은 "파라미터 미전송".
REASONING_PARAM = {
    "anthropic": {"off": {"type": "disabled"},
                  "on": {"type": "enabled", "budget_tokens": 2048}},
    # OpenAI 신형은 reasoning_effort. 구형은 이 파라미터를 거부하므로 폴백으로 제거한다.
    "openai": {"off": "minimal", "on": "high"},
    # Gemini 3 thinkingLevel. 종전 하드코딩 값(minimal)이 곧 off 였다.
    "gemini": {"off": "minimal", "on": "high"},
    # GLM 은 채팅 템플릿 인자로 사고를 켜고 끈다(chat_template_kwargs.enable_thinking).
    # 끄지 않으면 <think> 가 본문 예산(MAX_TOKENS)을 먹어 finish_reason=length 로
    # 절단된다 — 이 모듈은 절단을 성공으로 넘기지 않으므로 그대로 즉사한다.
    "glm": {"off": False, "on": True},
}

MAX_TOKENS = 2048
GEMINI_MAX_TOKENS = 4096   # 편차 D1 계승: thinking 토큰이 예산을 잠식해 본문 절단
GEMINI_THINKING = "minimal"
MAX_ATTEMPTS = 5
FALLBACK = " "  # 저자 코드 fallback()과 동일 — 실패해도 파이프라인을 멈추지 않는다

# 재시도가 의미 있는 HTTP 상태 — run_experiment._post() 화이트리스트와 동일(회귀 복구).
# 이 밖의 상태(400 설정·401 인증·403 권한·404 모델명 오타)는 재시도해도 같은 답이다.
RETRYABLE_STATUS = {429, 500, 502, 503, 529}


class LLMCallError(RuntimeError):
    """공급자 HTTP 오류. status 를 예외에 실어 재시도 판별이 본문 문자열 파싱에
    걸리지 않게 한다 — 종전엔 429 본문에 'temperature' 가 스치기만 해도 파라미터
    폴백이 발동해 temperature 를 영구 제거할 수 있었다(무음 실패 ⓒ)."""

    def __init__(self, provider: str, status: int, body: str):
        self.provider, self.status = provider, status
        super().__init__(f"{provider} {status}: {_mask(body)}")


class LLMTruncated(RuntimeError):
    """출력 절단(finish/stop reason 기준) — 같은 입력이면 같은 절단이라 재시도 무의미.
    참조 러너(run_experiment)의 finishReason==MAX_TOKENS raise 이식(편차 D1 교훈:
    절단본은 폐기 대상이지 폴백 대상이 아니다 — 조용히 넘기면 절단 발화가 채점에 섞인다).

    [2026-08-10 · 동범] **생성 시 자동 계수** (요한 7/31 절단 논쟁 회신의 숙제 이행 —
    A안 지지 + "발생하지 않았다는 실측 216건이 계속 참인지 확인하려면 절단 횟수는
    세야 한다"). run 은 A안대로 죽지만 빈도 데이터는 남아야 하므로, 예외가 만들어지는
    순간 TRUNCATIONS 에 한 줄 적고 LAST_DEVIATIONS 에도 한 줄 얹는다 — 후자는
    `run_meta.settings.deviations` 계약(요한 7/31 확정: 그 칸만 실행 중 재기록 허용)을
    타고 산출물까지 닿는다. 스키마 필드 추가 0. 세 공급자 raise 지점을 한 곳에서
    커버하려고 raise 측이 아니라 생성자에서 센다 — 새 공급자가 늘어도 빠뜨릴 수 없다."""

    def __init__(self, *args):
        super().__init__(*args)
        detail = _mask(args[0]) if args else "상세 미상"
        TRUNCATIONS.append(detail)
        LAST_DEVIATIONS.append(f"절단 {len(TRUNCATIONS)}회째: {detail}")


def _mask(text) -> str:
    """문자열에서 실키 값을 가린다 — 예외 본문·URL 에 키가 실려 콘솔·CI 로그로 새는
    경로 차단(보안 1건). 키 앞 6자만 남겨 어느 키인지 사람이 식별은 할 수 있게 한다."""
    out = str(text)
    for env in PROVIDER_KEY_ENV.values():
        val = os.environ.get(env, "")
        if len(val) >= 8:   # 자리표시자 수준의 짧은 값까지 치환하면 무관한 본문이 깨진다
            out = out.replace(val, val[:6] + "…<마스킹>")
    return out


def _retryable(exc: Exception) -> bool:
    """이 실패는 다시 시도하면 결과가 달라질 수 있는가.

    판별 순서: ① 절단·의존성 부재는 결정론적 실패 — 즉사. ② 상태를 아는 HTTP 오류는
    화이트리스트로. ③ 상태 미상(타임아웃·연결 끊김)은 일시 장애로 보고 재시도."""
    if isinstance(exc, (LLMTruncated, ImportError)):   # ModuleNotFoundError 포함
        return False
    if isinstance(exc, LLMCallError):
        return exc.status in RETRYABLE_STATUS
    status = getattr(exc, "status_code", None)         # anthropic SDK 예외가 실어 온다
    if isinstance(status, int):
        return status in RETRYABLE_STATUS
    return True

# 이번 프로세스에서 실제로 일어난 파라미터 편차(조용한 변경 금지).
LAST_DEVIATIONS: list[str] = []

# 이번 프로세스에서 일어난 출력 절단의 기록 (요한 7/31: "절단 횟수는 세야 한다").
# 216건 전수 스캔에서 절단 0건이었다는 실측이 앞으로도 참인지는 이 목록이 말한다 —
# LLMTruncated 생성자가 자동으로 채우며, 항목 = 마스킹된 절단 상세 한 줄.
TRUNCATIONS: list[str] = []

_clients: dict = {}
_openai_maxtok = "max_tokens"    # 한 번 폴백하면 이후 호출은 처음부터 새 이름 사용
_openai_no_temp = False          # temperature 미지원 모델로 판명되면 이후 생략
_glm_no_temp = False             # 같은 이유 — GLM 서버가 온도를 거부하면 이후 생략


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


def check_temperature(model: str, temperature: float) -> None:
    """온도가 공급자 허용 범위 안인가. 밖이면 SystemExit (2026-07-30 · 민옥).

    왜 폴백이 아니라 즉사인가: 온도를 코드가 알아서 깎으면 로그의 temperature 와 실제
    호출값이 갈라져 재현성이 깨진다(LAST_DEVIATIONS 로 남기는 편차와 성격이 다르다 —
    저쪽은 파라미터 '이름'이 달라 못 보내는 것이고, 이쪽은 사람이 정한 실험 조건이다).
    조건을 조용히 바꾸느니 시끄럽게 멈추고 사람이 config 를 고치게 한다."""
    provider = resolve_provider(model)
    lo, hi = TEMPERATURE_RANGE[provider]
    if not (lo <= float(temperature) <= hi):
        raise SystemExit(
            f"[llm] temperature={temperature} 는 {provider} 허용 범위 {lo}~{hi} 밖입니다 "
            f"(모델 '{model}' → {resolve_model(model)}).\n"
            f"  이 값으로 호출하면 API 가 400 을 돌려주고, 재시도해도 400 이라 5회 뒤 "
            f"공백 폴백으로 넘어갑니다 — 빈 발화 로그가 성공처럼 완주합니다.\n"
            f"  · 논문 상수 1.2 를 지키려면 공급자를 바꾸세요 (gpt-mini·gemini-flash 는 0~2).\n"
            f"  · Anthropic 으로 갈 거면 1.0 으로 내리고 \"1.2 는 API 제약으로 재현 불가\"를 "
            f"편차로 문서화하세요.")


def check_reasoning(model: str, reasoning: str) -> None:
    """추론 모드 값이 이 공급자에서 유효한가. 아니면 SystemExit (2026-07-30 · 민옥).

    온도 관문과 같은 자리·같은 이유다 — 지원하지 않는 값을 보내면 400 이고, 400 은
    재시도해도 400 이라 5회 뒤 공백 폴백으로 넘어가 빈 발화 로그가 완주한다."""
    if reasoning not in REASONING_MODES:
        raise SystemExit(
            f"[llm] reasoning={reasoning!r} 은 허용값이 아닙니다. "
            f"{list(REASONING_MODES)} 중 하나여야 합니다.")
    if reasoning == "default":
        return                      # 파라미터를 안 보내므로 공급자 검사 불필요
    provider = resolve_provider(model)
    if provider not in REASONING_PARAM:
        raise SystemExit(
            f"[llm] 공급자 {provider} 는 추론 모드 지정을 지원하지 않습니다 "
            f"(모델 '{model}'). reasoning=default 로 두세요.")


def preflight(model: str, temperature: float | None = None,
              reasoning: str | None = None) -> dict:
    """run 시작 **전에** 부르는 관문. 키가 없으면 여기서 죽는다.

    temperature 를 주면 공급자 허용 범위까지 함께 검사한다(check_temperature).
    기본값 None 은 "온도를 아직 모르는 호출자"(키 점검 단독 실행 등)를 위한 것이며,
    실호출 경로는 반드시 온도를 넘긴다.

    왜 필요한가: obtain_response 는 어떤 실패도 공백으로 폴백한다(저자 계승). 그래서
    키가 없으면 전 발화가 빈 로그가 조용히 완주해버린다 — 24콜을 다 태운 뒤에야
    폴백 카운터로 알게 된다. 시작 전에 알 수 있는 실패는 시작 전에 알린다."""
    _load_env()
    provider = resolve_provider(model)
    # 온도를 키보다 **먼저** 본다. 온도는 순수한 설정 오류라 키가 있든 없든 틀린 것이고,
    # 키 오류가 앞서면 키를 채워 넣은 뒤에야 온도 문제를 알게 된다(두 번 걸리는 길).
    if temperature is not None:
        check_temperature(model, temperature)
    if reasoning is not None:
        check_reasoning(model, reasoning)
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
    # 자체 호스팅 공급자는 주소도 시작 전에 본다 — 주소가 비면 requests 가 던지는
    # MissingSchema 가 폴백 경로로 새서 빈 발화로 위장될 수 있다(키 부재와 같은 구멍).
    if provider == "glm" and not os.environ.get(GLM_BASE_URL_ENV, "").strip():
        raise SystemExit(
            f"[llm] {GLM_BASE_URL_ENV} 없음 — GLM 은 자체 엔드포인트라 .env 에 "
            f"주소가 있어야 합니다.")
    # 의존성 관문 (무음 실패 ⓐ): 키가 멀쩡해도 SDK 가 없으면 호출 시점
    # ModuleNotFoundError 가 나고, 종전엔 그게 재시도 5회 뒤 공백으로 위장됐다 —
    # 401 위장 경로와 이름만 다른 같은 구멍. 시작 전에 알 수 있는 실패는 시작 전에.
    sdk = "anthropic" if provider == "anthropic" else "requests"
    try:
        __import__(sdk)
    except ImportError:
        raise SystemExit(
            f"[llm] {sdk} 패키지 미설치 — 모델 '{model}'({provider}) 호출에 필요합니다. "
            f"`pip install {sdk}` 후 다시 실행하세요.") from None
    return {"model": model, "model_id": resolve_model(model), "provider": provider,
            "key_env": env}


# ─── 공급자별 호출 ────────────────────────────────────────────────────────────
def _note_deviation(dev: str) -> None:
    """편차를 한 번만 기록한다. 조용한 파라미터 변경은 재현성을 깬다."""
    if dev not in LAST_DEVIATIONS:
        LAST_DEVIATIONS.append(dev)


def _call_anthropic(model_id: str, inputs: str, temperature: float,
                    reasoning: str = "default") -> str:
    if "anthropic" not in _clients:
        from anthropic import Anthropic  # 지연 import
        _load_env()
        _clients["anthropic"] = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs = {"model": model_id, "max_tokens": MAX_TOKENS,
              "temperature": temperature,
              "messages": [{"role": "user", "content": inputs}]}
    think = REASONING_PARAM["anthropic"].get(reasoning)
    if think is not None:
        # 사고 예산은 출력 예산과 별도가 아니라 그 안에서 나뉜다 — 켜면 본문 몫이
        # 줄어 절단이 난다(편차 D1 과 같은 기전). 켤 때는 상한을 함께 올린다.
        kwargs["thinking"] = think
        if think.get("type") == "enabled":
            kwargs["max_tokens"] = MAX_TOKENS + int(think.get("budget_tokens", 0))
            # 확장 사고는 temperature 를 받지 않는다(API 제약).
            kwargs.pop("temperature", None)
            _note_deviation("anthropic 확장 사고 — temperature 미전송(API 제약)")
    msg = _clients["anthropic"].messages.create(**kwargs)
    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()
    # 절단은 무음 통과 금지 — 7/27 에 제미나이 팔 전체를 폐기하게 만든 사고가
    # "잘렸는데 성공으로 보인 것"이었다(편차 D1). 예외로 올려 재시도·폴백에 태운다.
    if getattr(msg, "stop_reason", None) == "max_tokens":
        raise LLMTruncated(
            f"anthropic 출력 절단(max_tokens {kwargs['max_tokens']}) — "
            f"reasoning={reasoning}. 사고 토큰이 본문 예산을 잠식했을 수 있습니다.")
    return text


def _call_openai(model_id: str, inputs: str, temperature: float,
                 reasoning: str = "default") -> str:
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
    effort = REASONING_PARAM["openai"].get(reasoning)
    if effort is not None:
        payload["reasoning_effort"] = effort
        if effort == "high":
            # 사고 토큰이 출력 예산을 먹는다 — 켤 때 상한을 함께 올린다(편차 D1 기전).
            payload[_openai_maxtok] = MAX_TOKENS * 3
    for _ in range(4):   # 신형 모델 파라미터 명 변화 폴백
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=180)
        if r.status_code == 200:
            choice = r.json()["choices"][0]
            # 절단 무음 통과 금지(편차 D1 기전) — 사고 토큰이 본문 예산을 먹으면
            # finish_reason 이 length 로 오는데, 종전엔 그대로 성공 처리됐다.
            if choice.get("finish_reason") == "length":
                raise LLMTruncated(
                    f"OpenAI 출력 절단(finish_reason=length) — reasoning={reasoning}. "
                    f"사고 토큰이 본문 예산을 잠식했을 수 있습니다.")
            return choice["message"]["content"].strip()
        body = r.text[:400]
        # 파라미터 폴백은 **400에서만** 발동한다. 종전엔 상태를 안 보고 본문 문자열만
        # 봐서, 429 본문에 'temperature' 가 스치면 temperature 를 영구 제거할 수
        # 있었다 — 로그엔 1.0 인데 실제 호출엔 빠진 채 도는, 이 팀이 연구하는 바로 그
        # 기록-실체 괴리다(무음 실패 ⓒ). 400 = "요청이 틀렸다"일 때만 요청을 고친다.
        if r.status_code == 400 and "reasoning_effort" in body and "reasoning_effort" in payload:
            # 구형 모델은 이 파라미터를 거부한다. 제거하고 재시도하되 편차로 남긴다 —
            # "추론 off 로 돌렸다"와 "추론 파라미터가 안 먹혔다"는 다른 상태다.
            payload.pop("reasoning_effort")
            _note_deviation(f"openai reasoning_effort 미지원 — 제거됨(요청값 {effort})")
            continue
        if r.status_code == 400 and "max_tokens" in body and "max_tokens" in payload:
            payload["max_completion_tokens"] = payload.pop("max_tokens")
            _openai_maxtok = "max_completion_tokens"
            dev = "max_tokens→max_completion_tokens"
            if dev not in LAST_DEVIATIONS:
                LAST_DEVIATIONS.append(dev)
            continue
        if r.status_code == 400 and "temperature" in body and "temperature" in payload:
            payload.pop("temperature")
            _openai_no_temp = True
            dev = "temperature 미지원 — 제거됨(보고서에 명기할 것)"
            if dev not in LAST_DEVIATIONS:
                LAST_DEVIATIONS.append(dev)
            continue
        raise LLMCallError("openai", r.status_code, body)
    raise LLMCallError("openai", 400, "파라미터 폴백 3회 소진 — 같은 400이 반복됨")


def _call_gemini(model_id: str, inputs: str, temperature: float,
                 reasoning: str = "default") -> str:
    import requests
    _load_env()
    key = os.environ["GEMINI_API_KEY"]
    # 키는 URL 쿼리스트링이 아니라 **헤더**로 보낸다(보안 1건). 쿼리스트링에 실으면
    # 네트워크 예외 문자열·프록시 로그·CI 콘솔에 URL 이 통째로 남을 때 실키가 평문
    # 노출된다 — 공식 권장 헤더 x-goog-api-key 사용.
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_id}:generateContent")
    # reasoning=default 는 종전 동작(GEMINI_THINKING="minimal")을 그대로 유지한다 —
    # 과거 run 과의 연속성. off 도 값이 같지만 **의도가 기록된다**는 점이 다르다.
    level = REASONING_PARAM["gemini"].get(reasoning) or GEMINI_THINKING
    out_tokens = GEMINI_MAX_TOKENS * 2 if level == "high" else GEMINI_MAX_TOKENS
    payload = {"contents": [{"parts": [{"text": inputs}]}],
               "generationConfig": {
                   "temperature": temperature,
                   "maxOutputTokens": out_tokens,
                   "thinkingConfig": {"thinkingLevel": level}}}
    r = requests.post(url, headers={"x-goog-api-key": key}, json=payload, timeout=180)
    if r.status_code != 200:
        raise LLMCallError("gemini", r.status_code, r.text[:400])
    cand = r.json()["candidates"][0]
    # 절단 무음 통과 금지 — 편차 D1 의 원본 사고가 정확히 이 자리였다(사고 토큰이
    # 1024 예산을 잠식해 문장 중간에서 끊겼고, 판정상으론 "완전 복제"로 보였다).
    if cand.get("finishReason") == "MAX_TOKENS":
        raise LLMTruncated(
            f"Gemini 출력 절단(MAX_TOKENS {out_tokens}) — reasoning={reasoning} "
            f"thinkingLevel={level}. 편차 D1 재발.")
    return "".join(p.get("text", "")
                   for p in cand.get("content", {}).get("parts", [])).strip()


def _call_glm(model_id: str, inputs: str, temperature: float,
              reasoning: str = "default") -> str:
    """OpenAI 호환 자체 엔드포인트(GLM). 주소는 .env 의 GLM_BASE_URL 이 정본.

    _call_openai 에 분기를 더하지 않고 함수를 나눈 이유 둘: ① 주소가 고정이 아니다
    (자체 호스팅이라 실행 때마다 바뀔 수 있다) ② 사고를 끄는 방법이 reasoning_effort 가
    아니라 chat_template_kwargs.enable_thinking 이다. 한 함수 안에서 갈라놓으면
    "이 run 이 어디로 갔나"가 코드에서 안 보인다."""
    global _glm_no_temp
    import requests
    _load_env()
    key = os.environ["GLM_API_KEY"]
    base = os.environ.get(GLM_BASE_URL_ENV, "").strip().rstrip("/")
    if not base:
        raise SystemExit(f"[llm] {GLM_BASE_URL_ENV} 없음 — .env 에 엔드포인트 주소를 넣으세요.")
    url = f"{base}/chat/completions"
    payload = {"model": model_id,
               "messages": [{"role": "user", "content": inputs}],
               "max_tokens": MAX_TOKENS}
    if not _glm_no_temp:
        payload["temperature"] = temperature
    think = REASONING_PARAM["glm"].get(reasoning)
    if think is not None:
        payload["chat_template_kwargs"] = {"enable_thinking": think}
        if think:
            # 사고를 켜면 <think> 가 본문 예산을 먹는다 — 켤 때 상한을 함께 올린다
            # (OpenAI reasoning_effort=high 와 같은 처리·같은 이유).
            payload["max_tokens"] = MAX_TOKENS * 3
    for _ in range(3):
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=180)
        if r.status_code == 200:
            choice = r.json()["choices"][0]
            if choice.get("finish_reason") == "length":
                raise LLMTruncated(
                    f"GLM 출력 절단(finish_reason=length) — reasoning={reasoning}. "
                    f"사고가 켜진 채 돌았을 수 있습니다(enable_thinking).")
            return (choice["message"].get("content") or "").strip()
        body = r.text[:400]
        if r.status_code == 400 and "temperature" in body and "temperature" in payload:
            payload.pop("temperature")
            _glm_no_temp = True
            _note_deviation("glm temperature 미지원 — 제거됨(보고서에 명기할 것)")
            continue
        if (r.status_code == 400 and "chat_template_kwargs" in body
                and "chat_template_kwargs" in payload):
            # 서버가 이 인자를 모르면 사고가 켜진 채로 돈다 — 조건이 달라진 것이므로
            # 편차로 남긴다. 절단이 나면 위의 LLMTruncated 가 잡는다.
            payload.pop("chat_template_kwargs")
            _note_deviation("glm chat_template_kwargs 미지원 — 제거됨(사고 켜진 채 호출)")
            continue
        raise LLMCallError("glm", r.status_code, body)
    raise LLMCallError("glm", 400, "파라미터 폴백 3회 소진 — 같은 400이 반복됨")


_DISPATCH = {"anthropic": _call_anthropic, "openai": _call_openai,
             "gemini": _call_gemini, "glm": _call_glm}


def obtain_response(inputs: str, model: str, temperature: float = 0.0,
                    reasoning: str = "default") -> str:
    """프롬프트 하나 → 응답 텍스트 하나. 저자 obtain_response()와 같은 계약.

    reasoning 은 **기본값이 종전 동작("default" = 파라미터 미전송)** 이므로 기존
    호출자는 한 글자도 안 고쳐도 된다 — 호출 계약(설계 원칙 2)을 깨지 않는 확장이다.

    **일시 장애만** 재시도 5회 지수 백오프, 끝에도 실패하면 공백을 반환한다 — 저자
    코드 계승. 한 발화가 비어도 나머지 토론은 계속돼야 하고, 빈 발화 자체가 관측
    대상이다. 단 재시도해도 같은 결과인 실패(4xx 설정·인증 오류, SDK 부재, 출력
    절단)는 즉시 예외로 죽는다 — run_experiment._post() 화이트리스트 복원(회귀 복구).
    폴백을 이런 실패에까지 허용하면 "키가 죽었다"가 "모델이 침묵했다"로 위장된다.

    공급자는 model 이름에서 유도한다(resolve_provider). 미지 모델은 폴백하지 않고
    즉사한다 — 그건 돌다가 나는 실패가 아니라 설정 오류다."""
    provider = resolve_provider(model)      # 미지 모델이면 여기서 KeyError
    model_id = resolve_model(model)
    fn = _DISPATCH[provider]
    for attempt in range(MAX_ATTEMPTS):
        try:
            text = fn(model_id, inputs, temperature, reasoning)
            return text if text else FALLBACK
        except Exception as e:  # noqa: BLE001 — 일시 장애만 재시도 후 폴백
            if not _retryable(e):
                raise      # 결정론적 실패 — 65초 위장 없이 그 자리에서 원인을 말한다
            if attempt == MAX_ATTEMPTS - 1:
                print(f"[WARN] LLM 호출 {MAX_ATTEMPTS}회 실패, 폴백 반환: {_mask(e)}")
                return FALLBACK
            time.sleep(min(5 * (2 ** attempt), 30))
    return FALLBACK
