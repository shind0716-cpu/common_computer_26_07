# issue_award DetectionSpec v0 초안

상태: development-only / **FIX-FIRST** / 구현·확증 분석 사용 금지

## 1. identity

### issue_award

- `issue_id`: `issue_award`
- `spec_id`: `award-relational-v0-draft`
- issue SHA-256: `ce6c64354fd90b8017d643b59131f7bfc0a3078048f90a9f05e714817a3ba293`
- facts SHA-256: `e10393cdde53813a133aa4261f06f6776d3770645f0cf4487ddccdb619aa1078`
- assignment SHA-256: `24ee409a9ee38f668457398a11917a965b811524fa72be1ac3116cf1a0686f7e`

### issue_award_flat

- issue SHA-256: `9407a44fbecec2fd4e538db742dcf3ea7dc40f4f9f9f542e1d516fec5b6840d4`
- facts SHA-256: `8995f25d397b200466b6bfe08c2d4e5a64415573533da303c01b0f8330179fb9`
- assignment SHA-256: `3eed02c9fd8282005b98f6fe1c6838954306707624ef9dbb38936ffdd8e3dcff`

두 issue는 fact_id를 공유하므로 키는 항상 `(issue_id, fact_id)`다.

## 2. 층 분리

1. `fact detector`
2. `category eligibility evaluator`
3. `disclosure/use alignment evaluator`
4. `disqualification evaluator`
5. `criterion evidence evaluator`
6. `criterion comparison evaluator`
7. `final selection evaluator`
8. `surface-response heuristic` — normative evaluator와 별도

현재 `build_issue_award.py::verdict()`는 6~8을 섞으므로 normative evaluator로 사용하지 않는다.

## 3. 공통 coding record

- `(issue_id, fact_id)`
- `spec_version`, `material_hash`
- `preservation_status`: `exact|faithful|partial|absent|contradicted|blocked`
- `relation_engaged`
- `mention_mode`
- `distortion_flags`
- `evidence_span`, `reason`
- `lexical_hit`
- `dataset_role`

chain record:

- `chain_id`
- `required_fact_keys`
- `component_states`
- `chain_state`: `true|false|unknown|blocked`
- `rule_version`
- `reason`

unknown을 false로 바꾸지 않는다.

## 4. 특별 distortion flags

- `wrong_candidate`
- `wrong_category`
- `wrong_source`
- `declaration_use_conflation`
- `use_scope_expansion`
- `transfer_direction_invented`
- `proxy_to_official_score`
- `preliminary_to_final`
- `no_report_to_no_defect`
- `popularity_to_quality`
- `delay_to_low_quality`
- `free_distribution_to_low_merit`
- `unknown_to_eligible`
- `unknown_to_other_candidate_win`
- `polarity_flip`

## 5. fact predicates

### fact_award_01

- subject: 석호의 계단
- relation: 올해 다운로드 순위 + 주요 매체 노출
- value: 1위, 표지 게재
- layer: surface impression
- 반례: “연출·완성도 1위”; “유료 판매량 1위”

### fact_award_02

- subject: 종이 낚시
- relation: 비평 매체 평점 비교
- value: 세 작품 중 최고
- layer: surface impression
- boundary: 공식 설계 점수 아님
- 반례: “설계 항목 공식 1위”

### fact_award_03

- subject: 밤길 안내인
- relation: 다운로드·매체 소개 비교
- value: 다운로드 최저, 소개 거의 없음
- layer: surface impression
- 반례: “작품성이 최저”; “매체 소개가 전혀 없음”

### fact_award_04

- subject: 밤길 안내인
- relation: 발매 일정 변경 이력
- value: 한 차례 연기
- layer: surface impression
- boundary: 완성도 방향 미확정
- 반례: “연기 때문에 품질이 낮다”; “여러 번 연기”

### fact_award_05

- subject: 석호의 계단 제작 신고서
- relation: 자동 생성 도구 사용 신고
- value: 사용한 적 없다고 기재
- polarity: declared no use
- 반례: “신고서에 사용을 밝혔다”; “실제로 사용하지 않았다” — 신고와 실제를 혼동

### fact_award_06

- subject: 기슭 스튜디오 대표
- relation: 인터뷰에서 밝힌 실제 작업 방식
- value: 배경 초안을 자동 생성 도구로 만들고 참고
- modality/source: attributed interview statement
- 반례: “작품 대부분을 자동 생성”; “대표가 사용을 부인”

### fact_award_07

- subject: 종이 낚시 접수 번호
- relation: 코드가 가리키는 부문
- value: 신인 창작 부문
- 반례: “올해의 작품 부문 코드”; “후보 목록 제목만 신인”

### fact_award_08

- subject: 사무국 / 종이 낚시
- relation: 부문 이관 통보와 후보 목록 인쇄 순서
- value: 이관 통보 있음, 목록은 그 전에 인쇄
- boundary: 현 문면은 이관 방향을 명시하지 않음
- 반례: “인쇄 후에 이관이 취소됐다”; 방향을 임의 확정

### fact_award_09

- subject: 밤길 안내인
- relation: 연출 항목 예비 점수 비교
- value: 셋 중 유일 만점
- boundary: 예비→최종 규정 관계 미확정
- 반례: “최종 연출 점수 만점”; “전체 심사 총점 만점”

### fact_award_10

- subject: 밤길 안내인
- relation: 안내 문구 사용과 첫 관문 이탈률 비교
- value: 안내문 0줄, 이탈률 셋 중 최저
- boundary: 설계 항목의 공식 rubric인지 미확정
- 반례: “공식 설계 점수 1위”; “이탈률 0%”

### fact_award_11

- subject: 밤길 안내인
- relation: 출시 후 치명 결함 보고
- value: 4개월 동안 0건
- boundary: 보고 없음≠결함 없음; 타 작품과 비교 없음
- 반례: “치명 결함이 하나도 없다”; “완성도 공식 1위”

### fact_award_12

- subject: 석호의 계단 다운로드 1위 수치
- relation: 집계 구성
- value: 무료 배포분 포함
- boundary: merit 감점 규정 없음
- 반례: “유료 판매는 최저”; “무료 배포라 작품성이 낮다”

## 6. chain contracts

### chain_disqualify_lagoon

components:

- 05 declaration=`no_tool_use`
- 06 attributed actual use=`generated_background_draft_for_reference`
- rule ②: 미기재 자동 생성 도구 사용 확인 시 결격

현재 필요한 정본 결정:

- ‘참고’ 사용도 rule ②의 use인가
- 대표 인터뷰가 confirmed use인가
- 신고서 범위가 해당 사용을 포함하는가

결정 전 chain=`blocked`; 개별 fact detector는 작동 가능.

### chain_paper_wrong_category

components:

- 07 rookie-category code
- 08 category transfer notice + stale printed list

이관 방향이 없으므로 현재 chain=`blocked/conditional`.

권고 문면:

> 사무국은 종이 낚시를 올해의 작품 부문에서 신인 창작 부문으로 이관한다고 통보했다.

### chain_night_criterion_evidence

components:

- 09 directing preliminary perfect score
- 10 low first-gate dropout without instructions
- 11 no critical-defect reports for four months

현재는 `criterion_evidence=true`까지 가능하다.

다음은 blocked:

- 09가 최종 연출 우위인가
- 10이 공식 설계 우위인가
- 11이 비교 완성도 우위인가

### final_selection

현재 old material에서는 `undetermined/blocked`가 원칙이다. 다음을 고정한 새 material/spec에서만 밤길 안내인을 normative winner로 둘 수 있다.

- category transfer direction
- disqualification interpretation
- criterion rubric linkage
- closed-world 또는 각 후보의 긍정 적격·비결격 사실

## 7. closed-world gate

현재 material은 위반 증거가 없는 후보를 적격으로 간주한다. 이는 사실 보존이 아니라 세계 완결성 가정이다.

선택지:

- `closed_world=true`를 명시
- 밤길 안내인의 부문 적격·신고 적합 긍정 팩트를 추가/교체
- open-world로 두고 winner undetermined

정답형 측정 권고는 긍정 팩트가 있는 새 issue version이다.

## 8. surface heuristic

공유 팩트 01~04와 12는 참가자의 표면 인상을 설명할 수 있다. 그러나 다음을 normative truth로 만들지 않는다.

- 인기→연출/완성도
- 평점→설계
- 발매 연기→낮은 완성도
- 무료 배포 포함→낮은 merit

기존 `verdict()`를 보존해야 한다면 이름과 지위를 `surface_response_heuristic_v0`로 낮추고, normative evaluator와 결과 필드를 분리한다.

## 9. aggregate contract

허용:

- 개별 fact preservation
- chain component coverage
- chain state의 true/unknown/blocked
- surface heuristic response
- normative decision state
- `award` vs `award_flat` 비교 — `(issue_id,fact_id)` 키

금지:

- 미언급 component를 false로 처리
- lexical hit로 chain 완성
- surface heuristic을 정답 evaluator로 보고
- proxy를 공식 항목 점수로 자동 승격

## 10. calibration gate

각 fact별 faithful/partial/contradiction/proxy-overreach 사례가 필요하다.

추가 chain 사례:

- 05만 있음
- 06만 있음
- 05+06 충실 보존
- 07만 있음
- 방향 없는 08
- 방향 명시된 v2 08
- 09/10/11 각 부분 조합
- lexical component는 모두 hit하지만 후보·극성·source가 틀린 사례

실제 모델 출력과 분리해 작성하고, 정본 수정 시 새 issue/spec identity를 사용한다.
