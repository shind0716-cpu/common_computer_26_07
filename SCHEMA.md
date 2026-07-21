# SCHEMA — 파일 계약 v0.2 (원본: 노션 「스키마 — 파일 계약 5종 (현행 v0.2)」)

공통: UTF-8, snake_case. 모든 파일에 schema_ver/created_by/created_at.
경로는 modules/paths.py로만 유도. 검사는 modules/validate.py.

## 1. issues/{issue_id}.json
issue_id, source(company_json|paper|synthetic), source_meta{url, fetched_at, usage_approved}, title, body

## 2. facts/facts_{issue_id}.json
extractor{model, temperature, prompt_ver}
facts[]: fact_id, text, tags[condition|exception|counter_evidence|stance_support], critical(bool),
         prior{score 0~1|null, probe_model, probe_prompt_ver, probed_at}
주의: 라운드별 상태(언급/반박/무시)는 여기 없음 — 동적 정보라 judgment에서 관리

## 3. assignments/assignment_{issue_id}.json
seed(필수), agents[]: agent_id, perspective, stance(pro|con), assigned_fact_ids[]

## 4. debates/debate_{issue_id}_{run_id}.jsonl  (한 줄 = 이벤트 하나)
utterance: run_id, ledger_mode(off|v0|v1|v2|a1), round, agent_id, model, temperature,
           prompt_ver, prompt_hash(sha256), response_text(원문, 요약 금지), ts
ledger_inject: round, injected_fact_ids[], reason(v0_all_missing|v1_ignored_only), ts
gate_check: draft_text, missing_fact_ids[], verdict(pass|rollback), rollback_count(최대 1), ts

## 5. judgments/judgment_{issue_id}_{run_id}.json
judge{model: sonnet, temperature: 0, n_votes: 3, aggregation: majority, prompt_ver}
stage_type: "round"(실험 트랙) | "summary_layer"(관찰 트랙)
stages[]: stage, facts[]: fact_id, status(unmentioned|mentioned|accepted|refuted|ignored),
          votes[](3표 원본 보존 — 불일치율 = judge 신뢰도 지표), agents_mentioning[]
recall_probe[](선택, A4용): agent_id, recalled_fact_ids[], extra_lines
summary: far_by_stage[], far_system, far_agent_mean(관찰 트랙은 null), far_critical

## 버전 규칙
수정 시 이 파일과 노션 양쪽에 새 버전 절을 아래로 추가. 구현 중 문제 제기는 노션 패키지 A 항목으로.
