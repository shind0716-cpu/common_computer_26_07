"""[패키지 A · 신동범 · 마감 수 20시] 토론 엔진 — DelibTrace 저자 코드(discussion.py) 포팅.
계약: 입력 paths.facts(issue), paths.assignment(issue), config
      → 출력 paths.debate(issue, run)  (스키마 4번, 이벤트 jsonl)
완료 기준: 바닐라(ledger_mode=off) 1회 완주 + validate 통과 + 응답 원문 전량 기록.
막히면: 노션 작업 지시서 #1 패키지 A 항목 아래에 질문."""
# TODO(동범): ../DelibTrace-main/discussion.py 의 프롬프트 조립 로직을 글자 단위로 계승할 것.
# prompt_hash(sha256)를 이벤트마다 기록 — 재현·재생 검증용 (7/16 파일럿 방식).
