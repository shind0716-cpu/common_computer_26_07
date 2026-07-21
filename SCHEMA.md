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

## FAR 정의 — 스프린트 잠정 확정 (2026-07-22, 민옥/리더)
동범.md·judge.py가 남긴 열린 질문("FAR 수식 방향, 미확정 시 미니 H1 판정 불성립")을 미니 스프린트 한정으로 잠정 확정한다. **기업 확인(패키지 A Q: FAR 수식 방향) 회신 시 이 절과 judge.py의 SURVIVING/far()를 교체한다.**

- **방향**: 손실↑ = FAR↑ (FAR = 소실 팩트 수 / 대상 팩트 수). 값이 클수록 사실 보존이 나쁨.
- **소실 판정**: status ∉ SURVIVING. 스프린트 SURVIVING = {mentioned, accepted}. 즉 unmentioned·refuted·ignored = 소실.
  - 근거: judge v0는 프롬프트상 mentioned/unmentioned 2종만 산출(동범.md 설계노트). 2종 체계에서 소실 = unmentioned. accepted/refuted/ignored 자리는 v1 상태추적에서 채운다.
- **critical 한정**: far_critical = 위 식을 facts[].critical=true 팩트로만 집계.
- **미니 H1 판정 기준**: 대조군(ledger off) 실호출 1회에서 far_by_stage[]의 far_system·far_critical이 산출되면 H1(현상 재현) 성립으로 본다. 절대 수치 신뢰는 유보(judge 노이즈, W2 검증 과제).
- **미니 H2 판정 기준**: 동일 이슈·시드로 ledger on/off 쌍 비교 시, on의 far_critical이 off보다 낮으면(단조일 필요 없음) v0 유효 신호. 판정은 far_by_stage 곡선(단계별 분해)까지 함께 본다.
- Ledger v0의 '소실=재주입 대상' 정의는 이 SURVIVING과 **동일 소스**를 쓴다(modules/ledger.MISSING = status ∉ SURVIVING). judge와 ledger가 같은 잣대를 쓰도록 강제.

### ⚠ 통합 전 확인 필요 (2026-07-22)
리포의 judgment_issue_esa_dryrun.json(구버전, v1 픽스처 교체 전 산출)과 현재 judge.py 출력 구조가 다름:
- 드라이런: facts[].votes = [{agent_id, votes:[bool×3]}], summary에 far_system_critical/far_agent_mean_critical
- judge.py: facts[].votes = [{status, agents_mentioning, reason}×3], summary에 far_critical
ledger는 stages[].facts[].{fact_id,status} 두 필드만 의존하므로 양쪽 모두에서 동작하나, 수 밤 통합 시 judge 실호출 산출물의 최종 구조를 동범과 확정할 것.
