"""[민옥] 콘솔 실행 전 키 점검 — 어떤 모델을 실제로 쓸 수 있나.

왜 필요한가: 엔진은 호출 실패를 5회 재시도 후 **공백 발화**로 넘긴다(저자 코드
계승 — "빈 발화 자체가 관측 대상"). 그래서 키가 죽어 있으면 전 발화가 빈 로그가
조용히 완주하고, 24콜을 다 태운 뒤에야 폴백 카운터로 알게 된다.

실측 사고(2026-07-30): .env 의 ANTHROPIC_API_KEY 가 10자 자리표시자였고 401 이
났는데, 로그만 보면 성공처럼 보였다. 그래서 **돌리기 전에** 사람에게 알린다.

판정 기준은 llm.preflight() 와 같다(24자 미만 = 자리표시자). 이 파일이 기준을
따로 들고 있으면 둘이 갈라지므로 llm 의 상수를 그대로 읽는다.

단독 실행: python -m tools.console.keycheck
"""
import os
import sys

CANDIDATES = ("claude-haiku", "gpt-mini", "gemini-flash")
MIN_KEY_LEN = 24   # llm.preflight() 와 같은 기준


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from modules import llm

    usable, missing = [], []
    for alias in CANDIDATES:
        try:
            provider = llm.resolve_provider(alias)
        except KeyError:
            continue
        env = llm.PROVIDER_KEY_ENV[provider]
        key = os.environ.get(env, "")
        if len(key) >= MIN_KEY_LEN:
            usable.append((alias, llm.resolve_model(alias)))
        else:
            why = "없음" if not key else f"{len(key)}자 — 자리표시자로 보임"
            missing.append((alias, env, why))

    for alias, env, why in missing:
        print(f"     [X] {alias:<14} {env} {why}")
    if usable:
        names = ", ".join(f"{a}({m})" for a, m in usable)
        print(f"     [O] 사용 가능: {names}")
        return 0
    print("     [!] 사용 가능한 모델이 없습니다 — .env 에 실제 키를 넣으세요.")
    print("         (화면은 볼 수 있지만 실행 버튼은 실패합니다)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
