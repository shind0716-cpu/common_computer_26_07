"""[패키지 A · 신동범 · 마감 수 20시] 채점기(judge) — 순수 함수로 구현.
계약: 입력 debate 로그 + facts 목록 → 출력 paths.judgment(issue, run) (스키마 5번)
사양(확정): Sonnet 단일, temperature 0, n_votes=3 다수결, votes 원본 보존.
순수 함수 원칙: 입력→출력만. 대조군에선 사후 오프라인, 실험군에선 루프 안에서 동일 함수 호출."""
# TODO(동범): judge_fact(utterances, fact) -> status 형태의 순수 함수 + CLI 래퍼.
