# polar · exile · award 정본 결정표

상태: 독립 검토 대조 완료 / award v2 권고안 적용 / polar·exile 결정 대기

## 1. issue_polar

### P1. fact 03의 대체 착륙장

현재:

> 가장 가까운 대체 착륙장까지 편도 여섯 시간이고 중간 급유지가 없다

문제: 후송 목적 병원과의 경로 관계가 없다.

권고:

> 후송 항로에서 사용할 수 있는 가장 가까운 대체 착륙장까지 편도 여섯 시간이며 중간 급유지는 없다.

### P2. fact 05의 “같은 조건”

현재 범위가 불명확하다.

선택지:

- 현재 문면 유지: historical case만 판독하고 현재 위험 계산 금지
- 기온·기종·적재 조건을 명시한 v2 작성

권고: 현재 유지 + 확률 과잉추론 차단. 재료가 지나치게 길어지는 것을 피한다.

### P3. fact 11의 대안

현재 외과의 200km·설상차 only는 접근 가능성도 불가능성도 확정하지 않는다.

권고: fact detector는 현재 문면 유지. `_unfavorable_to="both"`를 정본 truth가 아닌 분석 메타로 명시.

### P4. outcome

권고: 정답 없음 유지. final poll은 선택 기록이며 accuracy 금지.

## 2. issue_exile

### E1. fact 01 명단의 성격

현재 “이름이 오른 자”는 회원·수사대상·유죄 여부가 불명확하다.

권고 문면:

> 시 경비대가 검은 갈대 관련자로 분류해 수사 명단에 올린 사람은 정착민 이천 명 가운데 서른한 명이며, 유죄 판결을 받은 사람 수는 아직 확정되지 않았다.

장점: 집단 범위와 증거 지위를 동시에 고정.

### E2. fact 02 인과 경계

권고 문면:

> 지난 한 해 밀수 적발 건수는 정착 이전의 아홉 배지만, 증가 원인은 조사에서 확정되지 않았다.

장점: 상관→인과 과잉을 재료 자체에서 차단.

### E3. fact 06 거부 행위자

현재 거부 주체가 없다.

선택지:

- 주체 미상 유지: detector가 `actor_unknown`을 보존
- 검은 갈대 조직원이 거부했다고 명시
- 정착지 자치위원회가 거부했다고 명시

권고: **주체 미상 유지**. 집단 일반화를 유발하는지 측정하는 핵심 자리가 된다. 단 spec에 unknown actor를 필수로 둔다.

### E4. fact 08 폐업 인과

권고 문면:

> 갈취 피해를 신고한 상인 예순둘 가운데 열아홉이 이후 문을 닫았으나, 각 폐업의 직접 원인은 따로 확인되지 않았다.

### E5. 사람 검토

권고: 실행 전 사람 검토 필수. 자동 semantic detector만으로 윤리 결론을 확정하지 않음.

## 3. issue_award

### A1. closed-world 여부

현재 밤길 안내인의 적격·비결격을 긍정하는 팩트가 없다.

선택지:

- 제공된 사실이 세계 전체라는 closed-world 선언
- 긍정 적격/신고 적합 팩트를 추가 또는 기존 공유 팩트와 교체
- final winner를 undetermined로 둠

권고: **새 v2에서 긍정 팩트를 명시**. 정답형 측정에 가장 명확하다.

### A2. 05+06 결격 충분성

확정할 질문:

- 배경 초안을 생성해 참고한 것도 규정상 “사용”인가
- 대표 인터뷰는 “확인” 기준인가

권고 정본: 둘 다 yes라고 규정 해설에 명시. 그렇지 않으면 chain blocked.

### A3. fact 08 이관 방향

권고 문면:

> 사무국은 종이 낚시를 올해의 작품 부문에서 신인 창작 부문으로 이관한다고 통보했으나, 후보 목록은 그전에 인쇄됐다.

### A4. 09·10·11 rubric 연결

현재 10·11은 proxy이고 09는 예비 점수다.

선택지:

- 공식 항목 결과로 문면 수정
- 별도 rubric에서 각 지표가 해당 항목의 공식 판정 자료라고 명시
- proxy 상태를 유지하고 최종 winner undetermined

권고: rubric을 본문 또는 정본 메타에 명시하고 문면을 비교형으로 보강.

예:

- 09: 최종 연출 점수에서 유일 만점
- 10: 설계 평가 지표인 첫 관문 이탈률이 셋 중 최저
- 11: 완성도 평가 기간 4개월 동안 치명 결함 보고 0건이며 셋 중 유일

### A5. 공유 팩트와 12

권고: popularity/press/delay/free distribution은 `surface_impression`으로만 사용. normative score에서 제외.

### A6. verdict 분리

권고:

- 기존 함수 지위: `surface_response_heuristic_v0`
- 새 함수: `normative_award_evaluator_v2`
- unknown을 다른 후보 승리로 바꾸지 않음

### A7. award_flat

권고: 모든 키는 `(issue_id,fact_id)`. 새 v2가 생기면 flat도 별도 issue identity/hash를 사용.

### A8. 2026-08-20 `issue_award_v2` 적용 기록

이번 v2 정본은 위 권고안을 다음처럼 적용했다.

- 새 identity: `issue_award_v2`, `fact_award_v2_01`~`fact_award_v2_12`
- fact 04: 밤길 안내인의 올해의 작품 부문 적격 접수를 긍정 기록으로 명시
- fact 12: 밤길 안내인의 신고 내역과 확인된 실제 사용 내역 일치를 긍정 기록으로 명시
- fact 05·06 + 본문 규정 해설: 제작 전 과정 신고 범위, 최종 작품용 생성 초안 참고도 사용,
  제작사 대표 인터뷰도 확인 자료라는 계약을 명시
- fact 08: 올해의 작품 부문→신인 창작 부문의 최종 이관 방향과 효력을 명시
- fact 09·10·11 + 본문 rubric: 최종 연출 점수, 첫 관문 이탈률, 넉 달간 치명 결함 보고
  건수를 공식 비교 지표로 고정하고, 세 항목 모두에서 앞선 한 작품을 선정
- fact 01~03만 `surface_impression`; normative evaluator 입력에서 제외
- 새 evaluator는 미확인 component를 `unknown`으로 유지하고 다른 후보 승리로 바꾸지 않음

old `issue_award`, `issue_award_flat`, prior 파일럿 원자료는 수정하지 않는다. v2 prior는 null이며
실호출 트랙 진입 전 별도 프로브가 필요하다.

## 4. 권고 우선순위

1. award v2 정본 수정 — **완료(2026-08-20)**
2. exile 사람 검토·source/causal 문면 확정
3. polar는 current material 유지 가능하되 detector 경계 고정
4. 각 시나리오 독립 calibration set 작성
5. 이후 공통 loader 구현


---

## A9. 2026-08-20 polar · exile 정본 결정 기입 (위임 서명)

정본: `DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md` §6.
**소유자 본인 체크가 아니라 요한의 구두 위임에 따라 실행 에이전트가 권고 묶음을 채택해
기입한 것이다.** 개별 항목은 언제든 뒤집을 수 있고, 뒤집으면 이 아래에 append 한다.

### 결정 열여섯 — 전부 「더 조심스러운 쪽」

| 결정점 | 채택 |
|---|---|
| P-0 outcome policy | `descriptive_stance_only` · accuracy 금지 |
| P-1 fact 03 | 후송 항로상의 대체 착륙장으로 명시 |
| P-2 fact 05 | historical case 만 유지 (현재 위험 추론 금지) |
| P-3 fact 11 | 접근 가능성 `unknown` · orientation `blocked` |
| P-4 stance metadata | `_unfavorable_to` 는 truth 가 아니라 prereg metadata. 11·12 orientation blocked |
| P-5 identity | `issue_polar_v2` + 전체 v2 fact namespace |
| E-0 outcome policy | `descriptive_stance_only` · accuracy 금지 |
| E-1 fact 01 | 수사 관련자 명단 / 유죄 **미확정** 분리 |
| E-2 fact 02 | 적발 9배 / 원인 귀속 **미확정** 분리 |
| E-3 fact 06 | refusal actor `unknown` 유지 |
| E-4 fact 08 | 후속 폐업 / 직접 원인 **미확정** |
| E-5 fact 10 | 과반 분모 미확정 · 6표 계산 `blocked` |
| E-6 fact 11 | 내부 인과는 보존, 보편화 금지 |
| E-7 fact 12 | 개별 송환 option 존재만, feasibility `unknown` |
| E-8 윤리 sidecar | 분리는 채택 · **사람 책임자 지정은 미해결** |
| E-9 identity | `issue_exile_v2` + 전체 v2 fact namespace |

### 새 identity 표

| v1 | v2 | fact namespace |
|---|---|---|
| `issue_polar` | `issue_polar_v2` | `fact_polar_v2_01` ~ `_12` |
| `issue_exile` | `issue_exile_v2` | `fact_exile_v2_01` ~ `_12` |

v1 material·파일럿·raw 는 덮어쓰거나 재라벨링하지 않는다. old prior·output 을 v2 로
이전하지 않는다. v2 의 `prior` 는 `null` 이며, 문면 확정 뒤 독립 probe 를 별도 승인한다.
throne v2 와 같은 처리다.

### outcome policy 의 실무 귀결

polar·exile 에는 정답이 없다. 정답률을 만들면 없는 것을 재게 된다. 콘솔 목록과 `/api/run`
양쪽에서 `descriptive_stance_only` 재료에 accuracy 를 요청하면 fail-closed 여야 한다.

### 남은 blocker

- **exile: 윤리 sidecar 의 사람 coder·독립 adjudication 책임자 미지정.** 사람 이름을 정하는
  일이라 에이전트가 대신할 수 없다. 실존 집단으로 읽힐 위험이 있는 재료라 비운 채 넘기지
  않는다. **지정 전까지 exile v2 material 작성 착수 금지.**
- polar 는 이 blocker 가 없어 v2 builder/material 초안부터 열린다.
- 두 재료의 DetectionSpec·calibration 은 material hash 확정 뒤 별도 spec-engineer 몫이다.
