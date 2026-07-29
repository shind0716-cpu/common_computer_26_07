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

## judgment 구조 확정 (2026-07-22, 민옥/리더 — 동범 승인 7/22 보드)
7/21 리더 확정 체제(스키마는 리더 측이 확정, 구현상 문제 제기는 보드 패키지 A 항목)에 따라 「⚠ 통합 전 확인 필요」의 구조 드리프트를 확정한다. **근거**: docs/P2_INPUT_CONTRACT.md(요한, 7/22) + 코드 확인 3건(D1·B·C, 보드 7/22 민옥 측 답변) + **담당자 승인(동범, 7/22 보드 회신 — "이의 없음" + 코드 사실 보강)**. 코드 수정 0줄 — 현행 구현을 정본으로 문서화하는 확정이다.

1. **정본 = 현행 judge.py 출력 구조.**
   - stages[].facts[]: `{fact_id, status, votes[{status, agents_mentioning, reason} × n_votes], agents_mentioning[]}`
   - summary: `{far_by_stage[], far_system, far_agent_mean, far_critical}`
   - 구 드라이런(judgment_issue_esa_dryrun.json)은 레거시 강건성 픽스처로 보존(동범 7/22 결정), 현행 구조 정본은 judgment_issue_esa_dryrun2.json — 신규 소비자는 dryrun2를 참조한다.
2. **stage 키는 모든 stage 레코드에 필수, 정렬 가능한 정수** (P2 질문 A). 실험 트랙 기점 = 0-기반 [0..N], round 0(초기 발화) 포함.
3. **각 stage의 facts[]는 추적 대상 전 팩트의 완전 스냅샷** (P2 질문 C) — 델타/변경분 기록 금지. "레코드 부재 = 소실"(P2 결정 2)의 전제 조건으로 명문화. 오프라인·루프-내 판정 모두 충족(동범 코드 사실 보강).
4. **관찰 트랙(stage_type=summary_layer)의 stage 시간 단조성은 loader가 보장** (P2 질문 B) — 전이 지표(P2) 적용 가능 여부는 호출 측 계약이다.
5. **judge v0 산출 status는 mentioned/unmentioned 2종** (judge-v0.2-binary, 저자 evaluate_fact 규칙 계승) — lost_by_status의 refuted/ignored 칸은 judge v1(5종 상태 실산출) 전까지 구조적으로 0이며, 결과 보고 시 이 주석을 의무로 단다 (P2 질문 E).
6. **SURVIVING 최종값(P2 질문 D)은 본 확정과 별개 트랙** — 기업 회신 시 「FAR 정의」절과 judge.SURVIVING/far()만 교체한다(기존 강제 유지). 교체 절차는 docs/proposals/FAR_SWAP_PLAN.md 참조.

구현상 문제 제기는 보드 패키지 A 항목 아래로(append-only).

## v0.3 — 발화 입력 기록 추가 (2026-07-28, 요한 확정 — 규약 7 소관 확정, 보드 회신 게시)

추가 2건, 기존 이벤트·필드 변경·삭제 0 (append 호환 — 구 로그는 prompt_assembly 부재 시 종전 재구성 방식으로 유효).

### 4′. debates jsonl 이벤트 추가
- **`prompt_assembly`** (새 이벤트): run_id, round, agent_id, template, prompt_ver, setting_key,
  slots{assigned_fact_ids[], others[]:{round,agent_id}, previous:{round,agent_id}, inject:{round}|null},
  prompt_hash(sha256 — 같은 (round,agent_id)의 utterance.prompt_hash와 동일값 = 결합 키), ts
- **`ledger_inject.injected_text`** (필드 추가): 프롬프트에 붙은 재주입 블록 원문 전문 (요약 금지).
- 검증 계약: 레시피 재조립 텍스트의 sha256 == prompt_hash. validate `--deep` 옵션에서 검사(기본 검사는 구조만).

### 경계 조항 (개정 1 — 정제 시나리오 과적합 방지·드리프트 강건성)
1. **복원 불가 텍스트 전문 저장(일반 조항)**: 저장된 사건들로부터 결정론적으로 재조립할 수 없는
   신규 텍스트가 프롬프트에 들어가는 채널은 그 원문을 해당 이벤트에 전문 저장한다 (injected_text는 첫 사례).
2. **노출 어휘 한정**: 파생 뷰의 노출은 직접 노출(원문/원문 발화 참조 포함, 조립 참조에서 결정론 유도)만
   정의. 매개 노출(파생 텍스트 경유)은 예약 개념 — 해당 통신 구조 도입 시 별도 정의 없이 적용 금지.
3. **template 등록제 + 창 정책**: 정본 등록값 discussion_initial|discussion_continue. 새 조건은 새
   template명 등록(스키마 본체 불변), 등록 시 창 정책(rolling|cumulative) 명시.

노출표 (agent, fact, round, 경로 assigned|neighbor|ledger)는 저장하지 않고 사건에서 유도한다(사건 원장 1급, 지표는 뷰). 상세·근거: docs/proposals/SCHEMA_v0.3_PROMPT_ASSEMBLY.md (부록 A 포함).

### 4″. 개인 수첩 슬롯 (2026-07-29, 요한 확정 — 규약 7 소관 확정)

민옥 측 「실험 설정 사전 v0」(2026-07-29)의 개인 수첩 신설분. 추가 2건, 기존 이벤트·필드 변경·삭제 0
(구 로그는 note 슬롯 부재 시 `--deep`이 종전대로 통과).

- **`note_update`** (새 이벤트): run_id, ts, agent_id, round(이 갱신이 일어난 라운드),
  note_text(원문 전량 — 요약·절단 금지), origin(model|intervention), source(utterance|dedicated).
  경계 조항 1(복원 불가 텍스트 전문 저장)의 **두 번째 사례**. 수첩의 "현재 값"은 저장하지 않는다
  (사건 1급·상태는 뷰) — 이벤트 부재가 곧 미갱신이다.
- **`prompt_assembly.note`** (슬롯 추가): {agent_id, source_round} | null. `source_round`는 "직전
  라운드"로 계산하지 않고 **실제 사용한 판본의 라운드를 그대로** 적는다(round 0 및 갱신 생략 라운드
  때문). null이면 슬롯 블록 **자체를 생략**한다(빈 문자열 삽입과 해시가 다르다). 참조 대상
  `note_update`가 없으면 `--deep`은 실패로 처리한다.
- **A-2 발동 (경계 조항 2의 매개 노출 첫 사례)**: 수첩 경유 도달은 **매개 노출**로 분류하며 직접
  노출과 합산하지 않는다. 수첩이 켜진 조건(`memory: note`)에서 **P3 층1 지표(전달 폭 B·TSR·획득
  hazard)는 산출하지 않는다.** 정량 정의는 판정 없이 성립하는 방법이 나올 때까지 예약을 유지한다.
  층1은 수첩 없는 조건에서 종전대로 유효하다.
- **설정 좌표 분리**: `memory: none|note` 와 `note_budget`(기본 500)은 별개 칸이다. `window`(창
  정책, 경계 조항 3)와 `memory`는 직교하며 수첩을 창 정책 값으로 넣지 않는다.

상세·근거: docs/proposals/SCHEMA_v0.3_NOTE_SLOT.md (사전고정 커밋 a5af1bb — 고정 이후 변경은 append 전용).
