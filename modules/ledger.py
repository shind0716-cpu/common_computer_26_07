"""[민옥 · 수요일] Fact Ledger v0 + 합의 전 게이트.
v0 계약: judge 판정에서 사라진 팩트를 찾아 다음 라운드 프롬프트에 전량 재주입,
        ledger_inject 이벤트를 debate 로그에 기록.
게이트 계약: 합의문 초안 vs 장부 대조 → 누락 시 재작성 요구(rollback 최대 1회), gate_check 이벤트 기록.
사다리: v0(전량) → v1(무시된 것만, 상태 추적) → v2(pull 전환). 폴백 = a1(무지성 전량 재게시)."""
# TODO(민옥): missing_facts(judgment, stage) -> list[fact_id] 부터.
