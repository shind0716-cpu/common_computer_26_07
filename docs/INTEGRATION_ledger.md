# 통합 노트 — Ledger v0 ↔ debate_engine 결합 (2026-07-22, 민옥)

> 이 문서는 **설계도**다. 오늘(수)은 결합 지점만 확정·문서화하고, 실제 루프 병합은
> 수 밤 통합 세션에서 이 노트대로 수행한다. ledger.py 순수 함수는 완성·테스트 통과.

## 1. DESIGN 프로세스 경계 조항 (다시 확인)
- 대조군(ledger off): debate_engine 완주 → **사후** judge 오프라인 1회. (지금 구조 그대로)
- 실험군(ledger on): 라운드 루프 안에서 4(debate)·5(judge)·6(ledger)이 한 바퀴로 돈다.
- **judge는 순수 함수 유지.** 대조군/실험군이 같은 judge 코드를 호출해야 측정 잣대가 동일하다.

## 2. 결합 지점 — debate_engine.run() 라운드 루프
현재 (modules/debate_engine.py, ledger off 기준):

```
for r in range(1, rounds + 1):
    nxt = []
    for i in range(length):
        others = "".join(f"View {k+1}: {previous[j]}\n" for k, j in enumerate(edges[i]))
        inputs, resp = continue_utterance(question, previous[i], others, setting_text, model, temp)
        nxt.append(resp); emit("utterance", ..., round=r, ...)
    previous = nxt
```

실험군(ledger on)에서 끼울 지점 — **각 라운드 발화 생성 전(주입)과 라운드 종료 후(판정)**:

```
for r in range(1, rounds + 1):
    # (A) 주입: 직전 라운드에서 소실된 팩트를 이번 라운드 프롬프트에 전량 재게시
    if ledger_mode == "v0" and r >= 2:
        inject_ids = ledger.missing_facts(prev_judgment, r - 1)     # 직전 stage 소실
        inject_block = ledger.build_injection_block(inject_ids, facts_by_id)
        emit_record(ledger.make_inject_event(run_id, r, inject_ids))  # 로그에 ledger_inject
    else:
        inject_block = ""

    nxt = []
    for i in range(length):
        others = ...
        # (B) inject_block 을 continue_utterance 입력에 덧붙인다(others 앞/뒤 — 프롬프트 위치 결정 필요)
        inputs, resp = continue_utterance(question, previous[i], others + inject_block, setting_text, model, temp)
        nxt.append(resp); emit("utterance", ..., round=r, ...)
    previous = nxt

    # (C) 판정: 이번 라운드를 judge 순수함수로 즉시 채점 → 다음 라운드 주입 근거
    prev_judgment = judge.judge_debate_from_events(events_so_far, facts, offline?)  # ↓ 4번 항목
```

## 3. 확정해야 할 인터페이스 3건 (수 밤 통합 전 동범과)

1. **judge를 "이벤트 리스트"에서 바로 채점하는 진입점 필요.**
   현 judge.judge_debate(issue, run, cfg)는 **파일에서** debate를 읽는다(load_utterances(paths.debate(...))).
   루프 안 실험군은 아직 파일이 없으므로, `group_by_stage(utterances)`를 in-memory 리스트로 받는
   얇은 진입점(예: judge_stage(utterances_of_round, facts, vote_fn, n_votes))이 있으면 결합이 깔끔.
   → 오늘 ledger는 이 진입점에 의존하지 않음(파일 기반 사후 판정에도 동작). 통합용 요청 사항으로 남김.

2. **재주입 블록의 프롬프트 위치.**
   continue_utterance는 저자 프롬프트를 글자 단위 계승 중(others/previous/setting/question 슬롯).
   inject_block을 others 뒤에 잇는 게 저자 포맷 훼손이 가장 적음(별도 슬롯 신설은 저자 계승 원칙과 충돌).
   → 프롬프트 문구는 authors_prompts 계승 대상이라 신중히. 동범 확인 필요.

3. **judgment 구조 통일 (⚠ SCHEMA 「통합 전 확인 필요」).**
   리포 드라이런 judgment는 구버전 구조(votes:[{agent_id,votes:[bool×3]}], summary far_system_critical).
   현 judge.py 출력은 votes:[{status,agents_mentioning,reason}], summary far_critical.
   ledger는 stages[].facts[].{fact_id,status}만 의존해 양쪽 다 동작하지만,
   목요일 on/off 비교 표를 뽑으려면 judge 실호출 산출물의 최종 구조를 하나로 확정해야 함.

## 4. llm.py 헬퍼 재사용 검토
- ledger 자체는 LLM 호출이 **없다**(순수 함수, 결정론적). llm.py 재사용 불필요.
- 단 (C) 루프-내 judge는 llm.py의 obtain_response 대신 judge._online_vote(client, ...)를 쓴다
  (judge가 이미 자기 클라이언트·JUDGE_SYSTEM 보유). 즉 통합 시 llm 클라이언트는 debate_engine이
  1개 생성해 debate·judge가 공유하면 호출 비용/일관성 유리. → 통합 시 client 주입 경로 정리.

## 5. 비용·안전 (CLAUDE.md 실험무결성)
- 실험군은 라운드마다 judge n_votes=3 × 팩트 12 × 8발화가 추가로 돈다 → 호출량 급증.
- 통합 루프에 반드시: 호출 횟수 상한 + 체크포인트(라운드별 events 중간 저장) 넣을 것.
- 목요일 쌍 비교는 **동일 이슈·동일 seed(42)** 로 off/v0 각 1회 — config 두 벌(ledger_mode만 다름)로 실행.

## 6. 통합 실행 기록 (2026-07-22 수 밤, 민옥)

§2 설계도대로 병합 완료 — `debate_engine.run()`에 (A)주입·(B)others 뒤 잇기·(C)라운드별
즉시판정 반영. `ledger_mode=v0` 지원(off는 기존과 완전 동일, v1/v2/a1은 명시적 거부).

- §3-1은 `judge.judge_stage()` 얇은 진입점으로 구현(**제안** — 동범 확인 대기).
- §3-2는 others 뒤 잇기로 구현(**제안** — 동범 확인 대기).
- §5 안전장치 반영: `max_llm_calls` 상한(기본값=예상 호출수 자동 계산) + 라운드별 flush 체크포인트.
- 루프-내 판정은 **주입 결정 전용** — 정식 judgment는 두 모드 모두 사후 오프라인 judge로
  산출한다(대조군/실험군 잣대 동일). §3-3(judgment 최종 구조)은 여전히 확정 대기.
- 검증: `tests/test_integration_ledger.py` 9종(가짜 utterance_fn/judge_vote_fn 주입, API 불필요)
  포함 전체 42종 통과. run_smoke는 tests/ 자동 발견으로 교체(고정 숫자 제거).
