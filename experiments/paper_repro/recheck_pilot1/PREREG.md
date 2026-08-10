# pilot1 재집계 — 판정 규칙 사전 고정 (2026-08-10, 실행 전 커밋)

지위: **사전고정.** PR#34 리뷰 반영(캐시 정체성·parse_fail=모름 정책) 후, pilot1 의
저자 축 FAR 0.92 가 bridge 결함의 오염이었는지 보존 원문으로 검산한다(LLM 호출 0).
이 문서는 **결과를 보기 전에** 커밋한다 — 규칙을 결과에 맞추는 과적합을 차단한다.

## 무엇을 돌리나

입력(원자료, 무수정 — 읽기 전용):
- `data/raw_calls/axis_author_pilot1.jsonl` (32행) · `data/raw_calls/stance_pilot1.jsonl` (32행)
- `data/facts/facts_issue_ethics_0476.json` (팩트 12) · `data/assignments/assignment_issue_ethics_0476.json`
- 원본 산출물: `data/judgments/judgment_issue_ethics_0476_pilot1_author.json` ·
  `data/stance_summary_issue_ethics_0476_pilot1.json`

계산(수정 후 코드로 재산출, 산출물은 이 폴더에만):
1. 저장된 `raw_response` 를 `parse_matched` 로 **재파싱** → 저장된 `matched_fact_ids` 와 행 단위 대조
2. 재파싱 행 → 수정된 `bridge.author_rows_to_judgment` → far_by_stage 재산출 → 원본과 대조
3. stance 행 → 수정된 `bridge.stance_rows_to_summary` → match_rate_by_round 재산출 → 원본과 대조

## 판정 규칙 (결과가 나오기 전에 고정)

- **R1 (일치)**: 재산출 far_by_stage·stance 유지율이 원본과 전 stage 동일하면 —
  "0.92 는 리뷰 결함의 오염이 아니다" 로 확정하고, 축 분기 실측(0.42 vs 0.92)은
  유효한 관찰로 유지된다. MUTUAL_REVIEW 에 검산 완료를 기록한다.
- **R2 (불일치)**: 어느 stage 든 FAR 이 다르면 — 원본 judgment 를 정정 대상으로
  표기(원본 파일은 보존, 정정은 append), 차이가 **0.05 초과**면 차단급으로
  MUTUAL_REVIEW 에 보고하고 **축 확정 논의를 재개 전 원인 판독이 선행**한다.
- **R3 (재파싱 불일치)**: 재파싱 matched 와 저장 matched 가 다른 행이 1개라도 있으면
  해당 행 원문을 직접 판독(G5)한 뒤에만 보고한다. 기대값은 불일치 0
  (파서는 무수정·결정론이므로) — 불일치는 파서 비결정성 또는 저장 경로 결함 신호다.
- **G5**: 재산출 FAR 의 극단값(0.0/1.0)은 해당 stage 원문 2건 이상 확인 후 보고.
- 어느 쪽이 나와도 **그대로 보고**한다. 1건 검산이므로 가설 언어 금지는 유지.

## 예상 (기록용 — 판정에 불사용)

pilot1 은 파싱실패 0 이므로 parse_fail 정책 변경은 무영향(no-op)이어야 하고,
따라서 R1 이 기대값이다. 이 예상이 틀리는 것이 곧 발견이다.
