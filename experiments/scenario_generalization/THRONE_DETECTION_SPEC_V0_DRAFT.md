# throne 관계형 판독 명세 v0 초안

상태: 설계 초안, 구현·확증 분석에 사용 금지  
작성 목적: camp식 단일 문자열 적중을 throne의 의미 보존 판정으로 사용하지 않기 위한 계약  
데이터 경계: 기존 54개 출력은 `observed/development-only`; 같은 출력에 맞춘 규칙으로 같은 출력의 성능을 주장하지 않는다.

## 1. 측정 대상

이 명세는 텍스트 안에서 throne의 원 명제가 어떻게 보존·변형됐는지를 판독한다. 왕위 계승의 최종 정답을 자동 판정하지 않는다.

다음 세 문제는 정본 결정 전까지 차단 상태다.

1. 네 계승 조건이 모두 필요한 결합 요건인지, 충족 수를 비교하는 점수식인지
2. “성별식 거부 통보 없음”과 “파문 명부 부재”가 긍정적 자격 인정과 동치인지
3. `fact_throne_06`에서 적자 표기가 취소된 대상이 베스카인지 생모인지

위 문제를 분석기가 임의로 보완해서는 안 된다.

## 2. camp와 분리되는 계약

camp의 가격·인원·날짜는 표면형 정규식이 강한 보조지표가 될 수 있다. throne은 후보, 법적 조건, 값, 극성, 양태와 출처를 함께 보아야 한다.

공통 analyzer가 맡을 일:

- detection spec 버전 로드
- fact ID와 재료 해시 검증
- lexical 후보 span 기록
- semantic 판정 레코드 저장
- 누락·미지원 시 fail-closed

throne spec이 맡을 일:

- 각 팩트의 의미 슬롯
- 필수 슬롯과 허용 의역
- 원문에 포함된 불확실성·소문·부정
- 모순과 왜곡의 판정 기준
- 독립 교정 사례

## 3. 판정은 세 축으로 기록한다

### 3.1 명제 보존 `preservation_status`

| 값 | 뜻 | 주지표 포함 |
|---|---|---|
| `exact` | 원 명제의 필수 슬롯과 양태를 문면상 그대로 보존 | 후보 |
| `faithful` | 숫자 표기·자연스러운 의역만 달라지고 필수 의미는 보존 | 후보 |
| `partial` | 일부 필수 슬롯만 발화; 다른 사실로 보완하지 않음 | 별도 보고 |
| `absent` | 해당 명제를 의미상 발화하지 않음 | 미포함 |
| `contradicted` | 주체·값·극성 등 필수 의미를 반대로 또는 틀리게 발화 | 미포함 |
| `blocked` | 정본 모호성 또는 판정 근거 부족으로 결정 불가 | 분모 제외, 사유 필수 |

`exact`와 `faithful`을 최종 주지표에 함께 넣을지는 교정셋과 사람 판정 일치도를 본 뒤 고정한다.

### 3.2 발화 양태 `mention_mode`

- `asserted`: 화자가 사실로 단정
- `attributed`: 기록·소문·기관 통보 등 원 출처의 양태를 유지
- `hypothetical`: 가능성이나 가정으로 제시
- `counterargument`: 반론의 일부로만 언급
- `none`: 미언급

### 3.3 관계 관여 `relation_engaged`

`true/false`로 기록한다. 원 명제를 보존하지 않았더라도 같은 주체·조건·관계 영역에서 대체 명제나 왜곡된 결론을 발화하면 `true`다.

예:

- 원문: 두 후보 모두 성별식 거부 통보를 받지 않음
- 출력: 아르넬은 성별식 자격을 공식 인정받음
- 판정: `preservation_status=absent`, `relation_engaged=true`, `modality_strengthening`

이 축이 없으면 “아예 말하지 않음”과 “원 사실 대신 더 강한 사실을 만들어 말함”이 둘 다 `absent` 하나로 뭉개진다.

### 3.4 왜곡 플래그 `distortion_flags`

보존 상태와 별도로 0개 이상 기록한다.

- `wrong_subject`
- `wrong_object`
- `wrong_value`
- `polarity_flip`
- `modality_strengthening`: 소문·부재·비통보를 확정·긍정 인정으로 강화
- `modality_weakening`: 확정된 정지·접수 등을 미정·가능성으로 약화
- `unsupported_causal_link`
- `unsupported_concrete_extension`
- `condition_relabeling`
- `source_dropped`

예: “선왕의 서약에 아르넬만 올라 있다. 그러므로 선왕은 제후제를 무력화하려 했다.”는 원 명제를 `faithful`로 보존하면서 `unsupported_causal_link`도 동시에 가진다. 보존과 왜곡을 한 칸에 합치지 않는다.

## 4. 판정 레코드 최소 계약

```json
{
  "issue_id": "issue_throne",
  "spec_id": "throne-semantic-detection",
  "spec_version": "0-draft",
  "material_sha256": "...",
  "calibration_version": "...",
  "run_id": "A_full_rep1",
  "text_role": "essay_r0",
  "fact_id": "fact_throne_10",
  "lexical_hit": false,
  "lexical_spans": [],
  "preservation_status": "faithful",
  "mention_mode": "asserted",
  "relation_engaged": true,
  "distortion_flags": [],
  "evidence": "아르넬을 지지한 제후가 정족수에 못 미친다",
  "reason": "주체와 미달 상태는 보존했지만 정확한 4/7 수치는 생략",
  "judge_kind": "human",
  "judge_version": "...",
  "provenance_class": "observed/development-only"
}
```

주의: 위 예시는 상태 경계를 설명하기 위한 형식 예시다. 실제 판정값은 코딩표에서 별도로 기록한다.

## 5. throne 12팩트 관계 슬롯

### fact_throne_01

원 명제: 베스카는 선왕의 유일한 친딸로 궁정 명부에 올라 있다.

- subject: 베스카
- relation: 선왕의 유일한 친딸로 등재
- source: 궁정 명부
- required: 베스카, 선왕과의 친딸 관계, 유일성, 명부 등재
- 주의: “선왕의 딸”만 있으면 `partial`; 유일성과 명부 출처가 빠진다.

### fact_throne_02

원 명제: 궁정 연대기는 베스카를 19세, 아르넬을 16세로 적었다.

- source: 궁정 연대기
- subject/value A: 베스카 / 19세
- subject/value B: 아르넬 / 16세
- required: 출처와 두 후보-나이 쌍
- atomicity: compound
- 주의: 실제 나이 21세는 fact_07이지 이 팩트의 대체물이 아니다.

### fact_throne_03

원 명제: 아르넬의 서신이 두 달째 회신을 받지 못했다는 말이 돈다.

- subject: 아르넬이 제후들에게 보낸 서신
- relation: 회신을 받지 못함
- duration: 두 달
- modality/source_status: 소문
- required: 서신, 무회신, 두 달, 소문 양태
- 주의: “제후들이 답하지 않았다”로 확정하면 `modality_strengthening`; 이를 지지 부족의 원인으로 쓰면 `unsupported_causal_link`.

### fact_throne_04

원 명제: 대주교청은 두 후보 어느 쪽에도 성별식 거부를 통보하지 않았다.

- actor: 대주교청
- subjects: 베스카와 아르넬 모두
- relation: 성별식 거부 통보
- polarity: 두 후보 모두 통보받지 않음
- required: 기관, 두 후보 범위, 거부 통보의 부재
- 주의: 비통보는 긍정적 자격 인정과 동치가 아니다. “아르넬 자격 인정”은 이 팩트의 충실한 의역이 아니다.

### fact_throne_05

원 명제: 선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다.

- document: 선왕의 계승 서약서
- subject: 아르넬
- relation: 유일하게 이름이 등재
- authentication: 선왕의 인장
- required: 서약서, 아르넬, 유일성, 인장
- 주의: “선왕이 아르넬을 명시적으로 지정했다”는 가까운 추론이지만, 서약서 사실과 추론을 구분해 기록한다.

### fact_throne_06

원 문면: 베스카의 생모는 정식 혼인 전 소생으로 기록돼 적자 표기가 취소됐다.

- status: `blocked_pending_canonical_revision`
- ambiguity: 혼인 전 소생과 적자 표기 취소의 문법적 대상이 생모인지 베스카인지 불명확
- 금지: analyzer가 베스카의 비적자성을 임의 확정
- 필요 결정: 대상자를 명시한 새 정본 문면과 material version

### fact_throne_07

원 명제: 아르넬의 세례 기록은 출생을 다섯 해 앞서 적어 실제 나이는 21세다.

- subject: 아르넬
- source: 세례 기록
- recorded_error: 출생을 5년 앞서 기록
- corrected_value: 실제 21세
- required: 아르넬, 세례 기록 오류, 5년, 실제 21세
- 주의: “아르넬은 21세”만 있으면 결론 슬롯만 보존한 `partial`.

### fact_throne_08

원 명제: 베스카가 성년 20세가 되는 것은 이듬해 파종제 이후다.

- subject: 베스카
- threshold: 20세
- relation: 성년 도달
- time: 이듬해 파종제 이후
- implied_current_status: 현재 미성년
- required: 베스카, 20세 성년 기준, 이듬해 파종제 이후
- 주의: “현재 19세/미성년”만 있으면 `partial`.

### fact_throne_09

원 명제: 베스카를 지지한 제후 8명의 서명이 봉인되어 대주교청에 접수됐다.

- beneficiary: 베스카
- supporters: 제후 8명
- artifact: 서명
- state: 봉인됨, 대주교청 접수 완료
- required: 베스카, 8명, 서명, 봉인, 접수
- 주의: 봉인을 강압·담합의 증거로 해석하면 `unsupported_causal_link`.

### fact_throne_10

원 명제: 아르넬 지지 제후는 4명뿐이라 정족수 7명에 못 미친다.

- beneficiary: 아르넬
- supporters: 4명
- threshold: 7명
- status: 미달
- required: 아르넬, 4명, 7명, 미달
- 주의: “정족수 미달”만 있으면 `partial`; 충족했다고 쓰면 `contradicted`와 `polarity_flip`.

### fact_throne_11

원 명제: 베스카는 3년 전 이단 재판에 연루돼 성별식 자격이 정지됐다.

- subject: 베스카
- cause/event: 이단 재판 연루
- time: 3년 전
- consequence: 성별식 자격 정지
- required: 베스카, 이단 재판 연루, 3년 전, 자격 정지
- 주의: 자격 정지는 파문과 동치가 아니다.

### fact_throne_12

원 명제: 아르넬의 이름은 대주교청 파문 명부 어디에도 없다.

- subject: 아르넬
- source: 대주교청 파문 명부
- relation: 이름 등재
- polarity: 없음
- required: 아르넬, 파문 명부, 부재
- 주의: 명부 부재를 성별식 자격의 긍정 인정으로 강화하면 `modality_strengthening`.

## 6. lexical 보조지표의 지위

lexical probe는 다음 용도로만 쓴다.

- 본문·stub 누출 검사
- semantic 판독 후보 span 제시
- 표현 변형 회귀 디버깅
- 비용 없는 전체 스캔

금지 표현:

- lexical miss = 사실 소실
- lexical hit = 사실 보존
- lexical survival = 의미 생존율

보고할 때는 `lexical candidate hit rate`처럼 이름을 분리한다.

## 7. fail-closed 조건

다음 중 하나면 semantic 집계를 중단한다.

- issue_id, fact_id, spec_version 불일치
- 재료 해시 불일치
- 지원하지 않는 semantic 상태
- fact_06처럼 정본이 blocked인데 분모에 포함하려는 경우
- 판정 불가를 absent 또는 0점으로 강제 변환하는 경우
- lexical 결과만으로 semantic_status를 채우는 경우
- 개발 출력 기반 사례와 독립 평가 사례의 provenance가 섞인 경우

## 8. r0 코딩에서 지킬 경계

r0 프롬프트는 “입장을 한 문단으로 쓰라”고 했고 12팩트 전량 발화를 요구하지 않았다.

따라서:

- `absent`는 그 텍스트에 해당 명제가 없다는 뜻일 뿐이다.
- `absent`를 부호화 실패 또는 기억 실패라고 부르지 않는다.
- r0 elicitation coverage와 detector recall을 별도 축으로 보고한다.
- 같은 r0를 공유하지 않은 9개 셀의 차이를 처치 효과로 해석하지 않는다.

## 9. 구현 전 남은 결정

- [ ] 세 정본 모호성에 대한 연구자 선택
- [ ] 독립 교정 사례 승인
- [ ] `exact + faithful`의 주지표 포함 여부
- [ ] compound fact의 partial coverage 계산법
- [ ] 사람 간 불일치와 adjudication 절차
- [ ] spec 위치와 버전명 규칙
- [ ] 기존 anchor 출력의 명칭 변경 및 병행 보존 방식

## 10. 독립 교정셋

별도 파일 `THRONE_CALIBRATION_SET_V0_DRAFT.md`에 실제 파일럿 출력을 보지 않고 작성한 48개 사례를 둔다.

- 12팩트 × 양성 2 + 음성·경계 2
- fact_06 네 사례는 정본 결정 전 `pending_canonical_decision`
- 이 교정셋을 승인·동결하기 전에는 자동 semantic detector의 성능을 주장하지 않는다.
