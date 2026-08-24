# Claude Code 구현 브리프 — throne DetectionSpec v0

상태: **문서 인계 완료 / 실행 미착수**
작성: Hermes
작업 저장소: `D:\ms\common_computer_26_07`
브랜치: `exp/hidden-profile-memory`

실행 미착수 사유:

- Claude Code CLI 설치 확인: `2.1.217`
- 인증 상태: `Expired / Not logged in`
- 사용자 확인: Claude 사용 크레딧이 없어 현재 실행하지 않음
- 따라서 아래의 코드 변경·테스트 결과는 아직 존재하지 않으며, 이 문서는 실행 가능한 인계 계약이다.

## 0. 역할과 목표

당신은 이 브리프를 받은 **Claude Code 구현 에이전트**다. 실제 파일럿 실행 에이전트나 독립 설계 에이전트의 신원을 자신과 합치지 않는다.

목표는 `issue_throne`에서 camp식 단일 문자열 적중을 주지표로 쓰지 않고, 시나리오별 관계형 의미 판독 계약을 실제 코드와 검증 가능한 데이터 계약으로 구현하는 것이다.

이 작업은 구현·테스트까지 수행한다. 새 모델 호출이나 추가 실험 실행은 하지 않는다.

## 1. 반드시 먼저 읽을 자료

순서대로 읽는다.

1. `experiments/scenario_generalization/THRONE_DETECTION_SPEC_V0_DRAFT.md`
2. `experiments/scenario_generalization/THRONE_CALIBRATION_SET_V0_DRAFT.md`
3. `experiments/scenario_generalization/THRONE_R0_ADJUDICATION_2026-08-20.md`
4. `experiments/scenario_generalization/THRONE_R0_SEMANTIC_CODING_DRAFT.csv`
5. `experiments/scenario_generalization/THRONE_CANONICAL_DECISIONS.md`
6. `experiments/scenario_generalization/THRONE_V2_MATERIAL_PATCH_DRAFT.md`
7. `experiments/scenario_generalization/LINEAGE_throne_pilot_55calls_2026-08-20.md`
8. `experiments/scenario_generalization/HANDOFF_throne_pilot_agent_conversation_2026-08-20.md`
9. `SCHEMA.md`, `DESIGN.md`, `WORKLOG.md`
10. 관련 코드:
   - `experiments/memory_structure/analyze_solo.py`
   - `experiments/memory_structure/judge_solo.py`
   - `experiments/memory_structure/run_solo.py`
   - `modules/paths.py`
   - `modules/validate.py`
   - 기존 테스트와 scenario variant 생성 경로

## 2. 변경 금지·안전 경계

현재 작업 트리는 다른 에이전트 변경을 포함하며 다수 파일이 staged 상태다.

절대 하지 말 것:

- `git reset`, `git checkout`, `git restore`, `git clean`
- 기존 index를 변경하는 `git add`
- commit, amend, rebase, push
- 기존 `issue_throne` 3종 파일 또는 54개 파일럿 원자료 수정
- 기존 r0 코딩을 실제 모델 출력에 맞춰 재정의
- 새 LLM/API 호출 또는 파일럿 재실행
- semantic 판정을 regex 목록 확장으로 위장
- lexical과 semantic을 하나의 합산 점수로 병합
- `fact_throne_06`의 old-material 결과를 소급 판정
- 미확인 모델·온도·세션 정보를 추측

작업 시작 전과 종료 후 `git status --short`를 저장하되 index를 바꾸지 않는다.

## 3. 승인된 정본 방향

이 브리프에서 구현 대상으로 삼는 신규 버전은 **측정 명확성 우선 v2**다.

기존 `issue_throne`은 보존하고 새 `issue_id`를 사용한다.

- 신규 ID: `issue_throne_v2`
- 네 조건은 모두 필수인 결합 요건
- 아르넬의 제후 서명 수를 7명으로 명시하여 조건 ③ 충족
- 아르넬의 성별식 자격을 대주교청이 긍정 인정한 사실로 명시
- fact_06은 베스카 본인의 혼인 전 출생 및 베스카 적자 표기 취소로 명확화
- 정답은 아르넬이며 `eligible(아르넬)=true`, `eligible(베스카)=false`

정확한 문면은 `THRONE_V2_MATERIAL_PATCH_DRAFT.md`를 따른다. old ID의 파일을 덮어쓰지 않는다.

## 4. 구현 원칙

### 4.1 다축 판정

단일 `mentioned: bool`로 축소하지 않는다. 최소 출력 계약:

- `issue_id`
- `spec_version`
- `material_hash`
- `fact_id`
- `preservation_status`
  - `exact`, `faithful`, `partial`, `absent`, `contradicted`, `blocked`
- `relation_engaged: bool`
- `mention_mode`
  - `asserted`, `attributed`, `hypothetical`, `counterargument`, `none`
- `distortion_flags: list[str]`
- `evidence_span`
- `reason`
- `lexical_hit`
- provenance 필드

`absent + relation_engaged=true`가 가능해야 한다. 예: 원 사실인 “거부 통보 없음”은 보존하지 않고 “자격이 인정됐다”는 더 강한 주장을 한 경우.

### 4.2 fact detector와 decision evaluator 분리

- fact detector: 관계 명제의 보존·왜곡 판정
- requirement evaluator: 각 후보가 네 조건을 충족하는지 계산
- decision evaluator: 모든 필수 조건을 충족하는 후보를 선택

fact detector가 승자를 직접 생성하지 않는다.

### 4.3 lexical은 보조지표

lexical probe는 후보 span 탐색과 빠른 QA에만 사용한다.

- lexical miss + semantic faithful 허용
- lexical hit + semantic absent/contradicted 허용
- semantic 주지표와 lexical 보조지표를 별도 필드·별도 집계로 유지

### 4.4 자동화의 정직한 경계

신뢰 가능한 자동 semantic classifier를 만들 수 없다면 만들었다고 주장하지 않는다.

최소 구현은 다음을 정직하게 지원해야 한다.

1. DetectionSpec schema/loader/validator
2. 구조화된 human/independent-judge coding record validator
3. requirement/decision evaluator
4. lexical auxiliary probe
5. calibration fixture validator
6. material/spec hash fail-closed 검사

자동 semantic detector는 독립 교정 48사례에서 기대 상태를 검증할 수 있을 때만 추가한다. 정규식만 늘려 semantic detector라고 부르지 않는다.

## 5. 구현 작업

엄격한 RED → GREEN → REFACTOR 순서를 지킨다.

### A. v2 재료

- `issue_throne_v2` issue/facts/assignment 3종을 기존 파일과 분리해 생성
- fact 수 12, assignment 완전성, source/holder 계약 유지
- `fact_throne_v2_06`, `_10`, 조건④ 관련 팩트 문면을 승인안과 일치
- 기존 validator로 통과
- old `issue_throne` 해시 불변 검증 테스트

ID 전략은 저장소 관례를 먼저 조사한다. `(issue_id, fact_id)`가 전역 식별자다. old/new가 같은 fact_id를 공유하면 혼동 위험이 있으므로, 저장소 validator·variant 관례와 일치하는 안전한 ID를 선택하고 브리프 상태란에 근거를 적는다.

### B. DetectionSpec 선언 파일

저장소 관례에 맞는 위치에 machine-readable spec을 만든다. 예시 위치는 `data/detection_specs/issue_throne_v2.json`이나 동등한 명시적 경로다.

12팩트 각각에 최소한 다음 관계 슬롯이 있어야 한다.

- subject
- relation
- object/value
- unit
- polarity
- modality/source_status
- required_slots
- accepted paraphrase 정책
- contradiction/boundary 정책
- lexical probes

spec에 version과 material hash를 포함한다.

### C. loader/validator

- 알 수 없는 issue/spec version은 fail-closed
- material hash 불일치는 fail-closed
- fact 누락·중복·미지 fact는 fail-closed
- 허용되지 않은 status/mode/flag는 fail-closed
- `(issue_id, fact_id)`를 키로 사용
- old-material `fact_throne_06` blocked 계약을 소급 해제하지 않음

### D. structured coding records

`THRONE_R0_SEMANTIC_CODING_DRAFT.csv` 같은 구조화 기록을 읽고 검증할 수 있어야 한다.

- 보존 상태와 관계 관여를 별도 유지
- evidence span과 reason을 보존
- development-only/provenance를 보존
- 같은 자료로 규칙을 만들고 같은 자료의 detector 성능을 주장하지 않도록 dataset role을 명시

### E. requirement/decision evaluator

v2 정본에 한해:

- 네 조건을 논리곱으로 평가
- 아르넬 4/4, eligible=true
- 베스카는 eligible=false
- 조건별 근거 fact_id를 반환
- required fact가 blocked/absent/contradicted이면 불확실성을 숨기지 않고 fail-closed 또는 `undetermined`

### F. analyze_solo 통합 경계

현재 `analyze_solo.py`의 lexical 경로는 이슈별 사전을 선택하도록 최소 수리돼 있다.

- 그 수리를 보존
- `lexical_anchor_hits(issue_id, text)`를 semantic detector로 개명하지 않음
- semantic judgment가 있으면 주지표로 읽고 lexical은 별도 보조 필드로 출력
- semantic judgment가 없을 때 lexical만으로 semantic 점수를 만들어내지 않음
- analyzer의 `ISSUE_ID="issue_camp"` 같은 고정 경로가 v2 사용을 조용히 오염시키지 않도록 명시적 issue 선택 또는 fail-closed 처리

### G. calibration fixtures

Markdown의 독립 교정 48사례를 machine-readable fixture로 옮기거나 검증 가능한 테스트 fixture로 만든다.

- 실제 파일럿 출력 문장을 calibration fixture로 사용하지 않음
- fact_06 old-material 사례는 pending/blocked로 유지
- v2 fact_06용 양성·음성 사례는 새 정본에 맞춰 별도 추가
- fixture provenance에 independent-from-observed-output를 표시

## 6. 테스트 및 검증

최소 acceptance criteria:

1. 새 테스트를 먼저 작성하고 예상 이유로 실패 확인
2. v2 material validator PASS
3. DetectionSpec 12팩트 완전성 PASS
4. material/spec hash 일치 PASS, 변조 시 실패 테스트 PASS
5. unknown issue/version/status/fact fail-closed 테스트 PASS
6. `absent + relation_engaged=true` round-trip PASS
7. lexical miss + semantic faithful가 보존되는 테스트 PASS
8. lexical hit + semantic contradicted가 보존되는 테스트 PASS
9. requirement evaluator에서 Arnel 4/4, Veska ineligible PASS
10. old `issue_throne` 파일 해시 불변 PASS
11. 기존 `tests/test_analyze_solo_anchors.py` PASS
12. 가능한 전체 canonical test suite 실행; 불가능하면 정확한 blocker와 targeted test 결과를 분리 보고
13. Python 문법 검사 PASS

## 7. 완료 보고 형식

이 파일 맨 아래 `## Claude Code 실행 결과`를 추가하고 다음을 기록한다.

- 실제 모델/세션 정보: CLI 결과에서 확인되는 범위만
- 시작/종료 Git 상태 요약
- 만든 파일
- 수정한 파일
- RED 실패 명령과 이유
- GREEN 명령과 실제 결과
- 전체 테스트 명령과 실제 결과
- acceptance criteria 체크리스트
- 남은 blocker/결정
- 자동 semantic detector를 구현했는지 여부와 정직한 한계
- commit/push 하지 않았음을 확인

작업 중 발견한 설계 충돌은 임의로 숨기지 말고 이 파일에 append한다. 이미 staged된 타 에이전트 변경을 되돌리거나 자기 작업으로 주장하지 않는다.

## 8. 인계받는 코딩 에이전트의 시작 프롬프트

다음 문장을 그대로 작업 지시로 사용할 수 있다.

> `experiments/scenario_generalization/CLAUDE_IMPLEMENTATION_BRIEF_throne_detection_v0.md`를 정본 작업 계약으로 읽고 구현하라. 먼저 §1의 자료를 순서대로 읽고 현재 Git 상태를 기록하라. 기존 staged index와 old `issue_throne`·파일럿 원자료를 건드리지 말라. strict TDD로 §5를 구현하고 §6의 acceptance criteria를 실제 명령으로 검증하라. lexical probe를 semantic detector로 위장하지 말고, 자동 의미 판정이 교정셋으로 입증되지 않으면 schema/loader/structured coding validator/requirement evaluator까지만 정직하게 구현하라. commit·push하지 말고 이 문서의 `## Claude Code 실행 결과`에 실제 변경·RED/GREEN 명령·검증 결과·blocker를 append하라.

## 9. 인계 완료 체크

- [x] 연구 의도와 측정 계약 기록
- [x] 관련 설계·교정·r0·계보 문서 경로 기록
- [x] 정본 v2 방향 기록
- [x] 변경 금지 범위 기록
- [x] 구현 단계와 acceptance criteria 기록
- [x] append 가능한 완료 보고 형식 기록
- [x] Claude Code 실행 미착수 사유 기록
- [ ] 구현 에이전트 착수
- [ ] RED/GREEN 검증
- [ ] 구현 결과 독립 리뷰


---

## Claude Code 실행 결과

작성: 실행 에이전트(오늘 throne 파일럿 54콜을 돌린 그 에이전트) · 2026-08-20
실호출: **0** (새 모델 호출·실험 재실행 없음)

### 0. 브리프 머리말 정정

브리프 §0 은 실행 미착수 사유를 `인증 만료 / 크레딧 없음` 으로 적었다. **그 판단은 별도
CLI 를 띄우려던 시도에 대한 것이고, 나는 지금 돌고 있다.** 이 절이 그 증거다. 다음 사람이
"실행 불가"로 읽지 않도록 여기 적어 둔다.

또 §2 는 「현재 index 에 다수 파일이 staged 상태이므로 `git add`·commit 금지」라고 했는데,
그 사이 원자료 커밋(`06784b6`)이 끝나 index 가 비었다. 그래서 **보존할 staged 상태가
없었다.** 이 작업에서도 commit·push 는 하지 않았다.

정본 §3 세 결정(A/A/A)은 요한 승인을 받았다(2026-08-20). `THRONE_CANONICAL_DECISIONS.md`
머리말은 아직 "사용자 응답이 없어 임시 채택"으로 남아 있으니 그 줄이 갱신돼야 한다.

### 1. Git 상태

시작 (HEAD `06784b6`):

```
M experiments/scenario_generalization/HANDOFF_throne_pilot_agent_conversation_2026-08-20.md
?? .hermes/
?? experiments/scenario_generalization/CLAUDE_IMPLEMENTATION_BRIEF_throne_detection_v0.md
```

종료:

```
M experiments/scenario_generalization/HANDOFF_throne_pilot_agent_conversation_2026-08-20.md
 M modules/paths.py
?? .hermes/
?? data/assignments/assignment_issue_throne_v2.json
?? data/detection_specs/
?? data/facts/facts_issue_throne_v2.json
?? data/issues/issue_throne_v2.json
?? experiments/scenario_generalization/AUDIT_polar_exile_award_materials_2026-08-20.md
?? experiments/scenario_generalization/AWARD_DETECTION_SPEC_V0_DRAFT.md
?? experiments/scenario_generalization/CALIBRATION_HIGH_RISK_POLAR_EXILE_AWARD_V0_DRAFT.csv
?? experiments/scenario_generalization/CANONICAL_DECISIONS_POLAR_EXILE_AWARD.md
?? experiments/scenario_generalization/CLAUDE_IMPLEMENTATION_BRIEF_throne_detection_v0.md
?? experiments/scenario_generalization/DETECTION_SPEC_MULTI_SCENARIO_INTERFACE_V0_DRAFT.md
?? experiments/scenario_generalization/EXILE_DETECTION_SPEC_V0_DRAFT.md
?? experiments/scenario_generalization/POLAR_DETECTION_SPEC_V0_DRAFT.md
?? experiments/scenario_generalization/RECONCILIATION_polar_exile_award_independent_reviews_2026-08-20.md
?? modules/detection_spec.py
?? modules/requirement_eval.py
?? tests/test_analyze_solo_boundary.py
?? tests/test_award_v2_material.py
?? tests/test_detection_spec.py
?? tests/test_requirement_eval.py
?? tests/test_throne_v2_material.py
?? "\354\213\234\353\202\230\353\246\254\354\230\244/assignment_issue_throne_v2.json"
?? "\354\213\234\353\202\230\353\246\254\354\230\244/build_detection_spec_throne_v2.py"
?? "\354\213\234\353\202\230\353\246\254\354\230\244/build_issue_throne_v2.py"
?? "\354\213\234\353\202\230\353\246\254\354\230\244/facts_issue_throne_v2.json"
?? "\354\213\234\353\202\230\353\246\254\354\230\244/issue_throne_v2.json"
```

commit·push·amend·rebase 없음. `git reset/checkout/restore/clean` 사용 없음.

### 2. 만든 파일

| 파일 | 무엇 |
|---|---|
| `시나리오/build_issue_throne_v2.py` | v2 재료 빌더 + 자체 검사 |
| `시나리오/build_detection_spec_throne_v2.py` | 판독 명세·교정셋 생성기 |
| `data/issues/issue_throne_v2.json` | v2 이슈 |
| `data/facts/facts_issue_throne_v2.json` | v2 팩트 12 |
| `data/assignments/assignment_issue_throne_v2.json` | v2 배분 |
| `data/detection_specs/issue_throne_v2.json` | DetectionSpec v0.1 |
| `data/detection_specs/calibration_issue_throne_v2.json` | 독립 교정 48사례 |
| `modules/detection_spec.py` | 명세 로더·검증기·코딩 기록 검증 |
| `modules/requirement_eval.py` | 요건·결정 평가기 |
| `tests/test_throne_v2_material.py` | 재료 계약 13종 |
| `tests/test_detection_spec.py` | 명세·레코드·교정 계약 26종 |
| `tests/test_requirement_eval.py` | 요건·결정 계약 14종 |
| `tests/test_analyze_solo_boundary.py` | 통합 경계 8종 |

### 3. 수정한 파일

`modules/paths.py` — `detection_spec(issue_id)` · `calibration_set(issue_id)` 두 함수 추가.
기존 함수 무수정. 경로 하드코딩 금지(규약 2) 때문에 새 산출물도 여기를 거쳐야 한다.

**old `issue_throne` 3종·54개 파일럿 원자료·기존 r0 코딩 CSV 는 건드리지 않았다.**

### 4. RED → GREEN

RED (구현 전):

```
python -m unittest tests.test_detection_spec tests.test_requirement_eval tests.test_throne_v2_material
→ ImportError: cannot import name 'detection_spec' from 'modules'
   Ran 15 tests, FAILED (errors=2)
```

예상한 이유로 실패했다 — 모듈이 없어서다. 재료 테스트 13종은 재료를 먼저 만들었으므로 통과.

GREEN:

```
python -m unittest tests.test_detection_spec tests.test_requirement_eval                    tests.test_throne_v2_material tests.test_analyze_solo_anchors
→ Ran 58 tests, OK
```

전체:

```
python -m unittest discover -s tests -t .
→ Ran 420 tests in 7.689s, OK
```

pytest 는 이 환경에 없다. `unittest discover` 로 전 스위트를 돌렸고 420종 전부 통과했다.

### 5. 도중에 테스트를 하나 고쳤다 — 숨기지 않는다

`test_every_fact_declares_required_slots` 가 전 팩트에 `subject` 슬롯을 요구했는데
fact_09·10 은 `beneficiary` 를 쓴다(누구를 위한 서명인가). **명세 초안이 의도한 역할
이름이라 테스트가 틀린 것이었다.**

통과시키려고 검사를 무르게 하지 않고 둘로 갈라 강화했다.

- `test_required_slots_are_all_declared_in_slots` — 필수라 적어 놓고 슬롯에 없으면 실패
- `test_every_fact_names_the_entity_it_is_about` — 이름을 강제하지 말고 존재를 강제

### 6. acceptance criteria (브리프 §6)

| # | 항목 | 결과 |
|---|---|---|
| 1 | 새 테스트 먼저 작성·예상 이유로 실패 | PASS (§4) |
| 2 | v2 material validator | PASS — validate 3종 |
| 3 | DetectionSpec 12팩트 완전성 | PASS |
| 4 | material/spec 해시 일치 · 변조 시 실패 | PASS — `test_material_hash_mismatch_fails_closed` |
| 5 | unknown issue/version/status/fact fail-closed | PASS — 6종 |
| 6 | `absent + relation_engaged=true` round-trip | PASS |
| 7 | lexical miss + semantic faithful 보존 | PASS |
| 8 | lexical hit + semantic contradicted 보존 | PASS |
| 9 | 아르넬 4/4 · 베스카 부적격 | PASS |
| 10 | old `issue_throne` 해시 불변 | PASS — 3파일 |
| 11 | 기존 `test_analyze_solo_anchors` | PASS |
| 12 | 전체 스위트 | PASS 420종 (pytest 부재 → unittest discover) |
| 13 | 문법 검사 | PASS |

추가로 `material_lint` 를 v2 에 걸었다 — 자기적중 12/12 · 교차 오발 0 · 본문 누출 0 ·
432자 < 500 · 태그 12/12. 전 항목 통과.

### 7. 자동 semantic detector — 만들지 않았다

브리프 §4.4 대로다. 만든 것은 schema/loader/validator, 코딩 기록 검증, 요건·결정 평가기,
lexical 보조 probe, 교정 fixture 검증, 해시 fail-closed 까지다.

**정규식을 늘려 semantic detector 라고 부르지 않았다.** 교정 48사례로 성능이 입증되기
전에는 자동 판정기를 붙이지 않는다. `modules/detection_spec.py` 독스트링에도 적어 뒀고,
`test_helper_is_not_named_as_semantic` 이 lexical 층에 semantic 이름이 붙는 것을 막는다.

### 8. 설계 판단 둘 — 이견 있으면 말해 달라

**(가) fact_id 를 새로 팠다** (`fact_throne_v2_NN`).

저장소 관례는 판본끼리 fact_id 공유다(`issue_hire_a6`→`fact_hire_*`,
`issue_award_flat`→`fact_award_*`). 그 둘은 **팩트 문면이 바이트 동일**하고 본문·배분만
다르다. v2 는 세 팩트의 **명제 자체가 바뀐다** — 같은 `fact_throne_06` 이 v1 에서는
"생모가 혼인 전 소생", v2 에서는 "베스카가 혼인 전 출생"을 뜻하게 된다. fact_id 만으로
합쳐지는 사고가 한 번 나면 두 명제가 조용히 섞인다. **문면이 바뀔 때는 이름도 바꾼다.**
관례를 어긴 것을 알고 어겼고 build 독스트링에 근거를 적었다.

`test_v1_records_rejected_against_v2_spec` 이 이 장치를 실증한다 — v1 코딩 CSV 를 v2
명세로 검증하면 fact_id 불일치로 죽는다.

**(나) v2 는 v1 보다 쉬운 재료다. 수치로 적었다.**

- 미공유 기울기: v1 정답 6 : 오답 2 → **v2 7 : 1** (fact_10 이 오답 쪽에서 정답 쪽으로 넘어감)
- 조건④: v1 은 공유 팩트가 중립이고 미공유 둘이 판단을 만들었다. **v2 는 공유 팩트
  (fact_04)가 아르넬의 자격 인정을 직접 말한다** — 조건④가 공개 정보로 풀린다.

남는 긴장은 공유 4 중 3이 여전히 베스카 쪽으로 기운다는 것이다(친딸·연대기 나이·서신
무회신 소문). 취합을 안 하면 베스카로 가고, 미공유를 모으면 아르넬이 4/4 임이 드러난다 —
고전 히든 프로필의 모양이다. 다만 **v1 결과와 직접 이어 붙이면 안 된다.**
`test_unshared_tilt_is_seven_to_one` 이 이 변화를 못 박아 둔다.

### 9. 남은 blocker

1. **prior 프로브 미실행.** 문면이 바뀐 세 팩트는 v1 의 known 0/12 를 물려받을 수 없다.
   v2 facts 의 `prior` 는 전부 null 이고 `_note` 에 경고를 넣었으며
   `test_prior_is_unprobed` 가 지킨다. **실호출 트랙에 올리기 전에 12콜이 필요하다.**
2. **자동 semantic 판정기 없음.** 지금 요건 평가기는 판정 상태를 입력으로 받는다.
   사람·독립 판정 없이는 v2 로 생존율을 못 낸다.
3. **동일 r0 분기 미구현.** 브리프 범위 밖이었다. Hermes 의 r0 의미 코딩(v1 기준)이
   나왔으므로 그 위에서 설계할 수 있다 — 다만 코딩은 v1 재료 기준이라 v2 에 그대로
   못 옮긴다.
4. **`THRONE_CANONICAL_DECISIONS.md` 머리말 갱신 필요** (§0).
5. **v2 는 아직 `run_solo.ISSUE_PROMPTS` 에 없다.** 등록하지 않았다 — 새 실행을 하지
   말라는 지시(§2)에 따라 실행 경로를 열지 않았다.

### 10. commit·push 하지 않았음

확인했다. `git log` 최신은 여전히 `06784b6` 이고 index 는 비어 있다.

### 11. 후속 — 커밋함 (위 §10 정정)

§10 을 쓴 시점에는 커밋하지 않았고 그것이 브리프 §2·§7 의 지시였다. 그 뒤 **요한이 커밋을
지시해** 이 작업분을 올린다. 문서의 지시보다 사용자의 지시가 앞선다.

푸시는 하지 않는다. 되돌릴 일이 있으면 이 커밋 하나만 되돌리면 된다.
