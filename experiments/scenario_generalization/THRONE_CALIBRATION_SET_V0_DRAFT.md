# throne 독립 교정 사례 v0 초안

상태: development-only, 미승인, 구현·확증 평가 사용 금지

생성 경계:

- `data/issues/issue_throne.json`
- `data/facts/facts_issue_throne.json`
- `data/assignments/assignment_issue_throne.json`
- `시나리오/build_issue_throne.py`

위 네 정본 후보만 읽고 작성했다. 파일럿 54개 출력, 감사 문서, 기존 스캔 결과는 보지 않았다. 따라서 아래 문장들은 관측 출력에 사후 적합한 사례가 아니다.

구성:

- 12팩트
- 팩트당 양성 의역 2개
- 팩트당 음성·경계 사례 2개
- 총 48개

주의:

- fact detector 교정용이며 왕위 계승 정답 판정용이 아니다.
- `fact_throne_06`은 원문 주어와 적자 표기 대상이 모호하므로 해당 네 사례를 `pending_canonical_decision`으로 취급한다. 정본 수정 전에는 활성 교정 점수의 분모에서 제외한다.
- lexical probe는 후보 span을 찾는 보조 수단이며 expected semantic status를 결정하지 않는다.

# 4. Fact별 관계 사양과 독립 교정 사례

## fact_throne_01

**정본:** 베스카는 선왕의 유일한 친딸로 궁정 명부에 올라 있다.

```yaml
subject: 베스카
relation: 궁정 명부상 선왕의 유일한 친딸이다
object_or_value:
  parent: 선왕
  kinship: 친딸
  uniqueness: 유일
unit: null
polarity: positive
modality: recorded
source_status: 궁정 명부
required_slots: [subject, parent, kinship, uniqueness, recorded_status, source]
lexical_probes: [친딸, 유일한 딸, 궁정 명부]
```

**양성 교정**

1. “궁정 명부에는 베스카가 선왕의 하나뿐인 친생 딸로 기록돼 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 베스카·선왕·친생 관계·유일성·명부 출처를 모두 보존한다.

2. “기록상 선왕의 친딸은 베스카 한 명뿐이다.”
   - `expected_status: faithful_paraphrase`
   - 이유: “기록상”이 궁정 명부 근거를 압축하지만 핵심 슬롯을 보존한다.

**음성/경계 교정**

1. “베스카는 선왕의 유일한 조카로 명부에 올랐다.”
   - `expected_status: contradiction`
   - 이유: 친딸을 조카로 바꿨다.

2. “베스카가 선왕의 딸이라는 이야기가 궁정에 퍼졌다.”
   - `expected_status: modality_mismatch`
   - 이유: 공식 명부 기록을 소문으로 바꾸고 유일성도 누락했다.

---

## fact_throne_02

**정본:** 궁정 연대기는 베스카를 19세, 아르넬을 16세로 기록했다.

```yaml
subject: [베스카, 아르넬]
relation: 궁정 연대기에 나이가 기록되어 있다
object_or_value:
  베스카: 19
  아르넬: 16
unit: 세
polarity: positive
modality: recorded
source_status: 궁정 연대기
required_slots: [both_subjects, subject_value_alignment, age_relation, unit, source]
lexical_probes: [열아홉, 열여섯, 궁정 연대기]
```

**양성 교정**

1. “연대기상 베스카는 열아홉이고 아르넬은 열여섯이다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 두 인물과 각 나이의 귀속을 정확히 보존한다.

2. “궁정 기록은 두 사람의 나이를 각각 베스카 19세, 아르넬 16세로 적었다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 값·단위·대상 정렬과 기록 출처가 유지된다.

**음성/경계 교정**

1. “연대기에는 아르넬이 열아홉, 베스카가 열여섯으로 나온다.”
   - `expected_status: subject_swap`
   - 이유: 두 숫자는 모두 있지만 귀속 대상이 뒤바뀌었다.

2. “베스카는 실제로 19세이고 아르넬은 실제로 16세다.”
   - `expected_status: unsupported_overreach`
   - 이유: 연대기의 기록값을 실제 나이로 확정한다. fact 07과도 충돌할 수 있다.

---

## fact_throne_03

**정본:** 아르넬이 제후들에게 보낸 서신이 두 달째 회신을 받지 못했다는 말이 돈다.

```yaml
subject: 아르넬이 제후들에게 보낸 서신
relation: 회신을 받지 못한 상태라는 말이 돈다
object_or_value:
  duration: 2
  respondents: 제후들
unit: 달
polarity: negative
modality: rumored
source_status: 출처 불명의 유통되는 말
required_slots: [sender, recipients, no_reply, duration, rumor_modality]
lexical_probes: [회신, 두 달째, 말이 돈다]
```

**양성 교정**

1. “아르넬의 편지에 제후들이 두 달 동안 답하지 않았다는 소문이 돌고 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 발신자·수신자·무회신·기간·소문 양태를 보존한다.

2. “제후들에게 보낸 아르넬의 서신이 두 달째 답장을 못 받았다는 말이 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 원문의 소문 수준을 유지한다.

**음성/경계 교정**

1. “제후들은 아르넬의 서신을 받고 두 달 만에 회신했다.”
   - `expected_status: contradiction`
   - 이유: 무회신을 회신 완료로 뒤집는다.

2. “아르넬은 확실히 두 달 동안 제후 전원의 답변을 받지 못했다.”
   - `expected_status: modality_mismatch`
   - 이유: 소문을 확정 사실로 높이고 “전원”이라는 범위를 추가한다.

---

## fact_throne_04

**정본:** 대주교청은 두 후보 어느 쪽에도 성별식 거부를 통보하지 않았다.

```yaml
subject: 대주교청
relation: 성별식 거부 통보를 하지 않았다
object_or_value: [아르넬, 베스카]
unit: null
polarity: absence
modality: asserted
source_status: 통보 행위의 부재
required_slots: [authority, both_candidates, refusal_notice, absence]
forbidden_inferences: [양쪽 자격 인정, 양쪽 성별식 승인, 양쪽 적격 확정]
lexical_probes: [거부를 통보, 어느 쪽에도, 두 후보]
```

**양성 교정**

1. “대주교청은 아르넬과 베스카 모두에게 성별식을 거부한다는 통지를 보내지 않았다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 양 후보와 거부 통보의 부재를 보존한다.

2. “성별식 거절 통보를 받은 후보는 둘 중 아무도 없다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 통보 부재를 수동형으로 정확히 표현한다.

**음성/경계 교정**

1. “대주교청은 두 후보 모두의 성별식 자격을 공식 인정했다.”
   - `expected_status: unsupported_overreach`
   - 이유: 거부 통보의 부재를 긍정적 인정으로 바꾼다.

2. “대주교청은 베스카에게만 거부 통보를 하지 않았다.”
   - `expected_status: partial_preservation`
   - 이유: 아르넬까지 포함하는 양 후보 범위를 보존하지 못했다.

---

## fact_throne_05

**정본:** 선왕의 계승 서약서에는 아르넬의 이름만 인장과 함께 올라 있다.

```yaml
subject: 선왕의 계승 서약서
relation: 인장이 수반된 등재 후보가 오직 한 명이다
object_or_value: 아르넬
unit: null
polarity: positive_exclusive
modality: recorded
source_status: 선왕의 계승 서약서
required_slots: [document, candidate, royal_seal, listed_status, exclusivity]
lexical_probes: [서약서, 인장, 이름만]
```

**양성 교정**

1. “선왕의 인장이 찍힌 계승 서약에 이름이 있는 사람은 아르넬뿐이다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 문서·인장·등재·배타성을 모두 보존한다.

2. “계승 서약서는 인장과 함께 아르넬 한 사람만 명시한다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 유일 등재라는 관계가 유지된다.

**음성/경계 교정**

1. “서약서에는 아르넬과 베스카의 이름이 모두 올라 있다.”
   - `expected_status: contradiction`
   - 이유: 아르넬만 등재되었다는 배타성을 부정한다.

2. “아르넬의 이름이 계승 서약서에 적혀 있다.”
   - `expected_status: partial_preservation`
   - 이유: 인장과 “아르넬만”이라는 핵심 슬롯이 빠졌다.

---

## fact_throne_06

**정본 표면 해석:** 베스카의 생모가 혼인 전 소생으로 기록되었고, 그 생모에 대한 적자 표기가 취소되었다.

```yaml
subject: 베스카의 생모
relation:
  - 정식 혼인 전 소생으로 기록되어 있다
  - 적자 표기가 취소되었다
object_or_value:
  birth_context: 정식 혼인 전 소생
  status_change: 적자 표기 취소
unit: null
polarity: positive_event
modality: recorded
source_status: 출처가 명시되지 않은 기록
required_slots: [literal_subject, premarital_birth_record, legitimacy_label_cancelled]
ambiguity:
  status: unresolved
  alternative_subject: 베스카
  alternative_cancelled_status_holder: 베스카
forbidden_inferences: [베스카의 적자 지위 취소 확정, 베스카의 계승 부적격 확정]
lexical_probes: [적자, 정식 혼인 전, 생모]
```

**양성 교정**

1. “기록에는 베스카의 생모가 정식 혼인 전에 태어난 소생으로 되어 있고, 그 적자 표기는 취소돼 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 문법상 주어를 생모로 유지하며 두 관계를 모두 보존한다.

2. “베스카의 어머니는 혼인 전 소생으로 기록된 탓에 적자로 적힌 표기가 말소됐다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 표면 문법 해석을 유지한다.

**음성/경계 교정**

1. “베스카는 정식 혼인 전에 태어나 적자 지위가 취소됐다.”
   - `expected_status: unjudgeable`
   - 이유: 의도했을 가능성은 있지만 원문 표면 주어와 다르다. 정본 모호성이 해소되기 전 자동 양성으로 확정할 수 없다.

2. “베스카의 생모는 혼인 뒤에 태어난 적자로 계속 인정됐다.”
   - `expected_status: contradiction`
   - 이유: 혼인 전 출생 기록과 적자 표기 취소를 모두 뒤집는다.

---

## fact_throne_07

**정본:** 아르넬의 세례 기록은 출생을 실제보다 5년 앞서 적었고, 실제 나이는 21세다.

```yaml
subject: 아르넬
relation:
  - 세례 기록의 출생 연도가 실제보다 5년 앞서 있다
  - 실제 나이는 21세다
object_or_value:
  record_offset: 5
  actual_age: 21
unit:
  record_offset: 해
  actual_age: 세
polarity: positive
modality: asserted_with_record_discrepancy
source_status: 세례 기록과 실제값의 대조
required_slots: [subject, baptism_record, direction_of_error, offset, actual_age]
lexical_probes: [세례 기록, 다섯 해, 스물하나]
```

**양성 교정**

1. “세례대장에는 아르넬의 출생이 실제보다 5년 이르게 적혀 있으며, 그의 실제 나이는 21세다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 오차 방향·크기와 실제 나이를 모두 보존한다.

2. “아르넬은 실제로 스물한 살이고 세례 기록의 출생 시점은 그보다 다섯 해 앞당겨져 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 실제 나이와 기록 오류 관계를 보존한다.

**음성/경계 교정**

1. “아르넬의 실제 나이는 열여섯 살이다.”
   - `expected_status: contradiction`
   - 이유: 실제 나이 21세를 16세로 뒤집는다.

2. “세례 기록은 아르넬의 출생을 실제보다 다섯 해 늦게 적었다.”
   - `expected_status: contradiction`
   - 이유: 오차 크기는 같지만 방향이 반대다.

---

## fact_throne_08

**정본:** 베스카가 성년 기준인 20세가 되는 시점은 이듬해 파종제 이후다.

```yaml
subject: 베스카
relation: 성년 연령에 도달하는 시점
object_or_value:
  majority_age: 20
  timing: 이듬해 파종제 이후
unit:
  majority_age: 세
polarity: future_not_yet
modality: future
source_status: 시점에 관한 진술
required_slots: [subject, majority_threshold, future_timing, after_sowing_festival]
lexical_probes: [파종제, 스무 살, 이듬해]
```

**양성 교정**

1. “베스카가 성년인 스무 살이 되는 때는 내년 파종제가 지난 뒤다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 기준 나이와 미래 시점을 모두 보존한다.

2. “이듬해 파종제 전까지 베스카는 아직 20세 성년에 이르지 않는다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 원문의 미래 도달 시점을 논리적으로 동등한 부정형으로 표현한다.

**음성/경계 교정**

1. “베스카는 이미 스무 살 성년이다.”
   - `expected_status: contradiction`
   - 이유: 미래 도달을 현재 완료로 뒤집는다.

2. “베스카는 이듬해 파종제가 열리기 전에 스무 살이 된다.”
   - `expected_status: contradiction`
   - 이유: 파종제 이후를 이전으로 바꾼다.

---

## fact_throne_09

**정본:** 베스카 지지 제후 8명의 서명이 봉인되어 대주교청에 접수됐다.

```yaml
subject: 베스카를 지지한 제후들의 서명
relation: 봉인된 상태로 대주교청에 접수되었다
object_or_value:
  supporter_count: 8
  beneficiary: 베스카
  recipient: 대주교청
unit: 명
polarity: positive
modality: asserted_completed
source_status: 대주교청 접수 완료
required_slots: [beneficiary, supporter_count, signatures, sealed_status, recipient, received_status]
lexical_probes: [봉인, 제후 여덟, 접수]
```

**양성 교정**

1. “베스카를 지지하는 제후 여덟 명의 서명은 봉인된 채 대주교청에 제출됐다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 대상·인원·봉인·접수 관계를 보존한다.

2. “대주교청은 봉인된 베스카 지지 서명 8건을 접수했다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 수동·능동 전환만 있고 모든 핵심 슬롯이 유지된다.

**음성/경계 교정**

1. “아르넬을 지지한 제후 여덟 명의 서명이 접수됐다.”
   - `expected_status: subject_swap`
   - 이유: 숫자는 같지만 지지 대상이 바뀌었다.

2. “베스카에게 지지를 약속한 제후가 여덟 명이라는 소문이 있다.”
   - `expected_status: modality_mismatch`
   - 이유: 공식 접수 완료를 소문·약속 수준으로 약화하고 봉인 서명도 누락한다.

---

## fact_throne_10

**정본:** 아르넬 지지 제후는 4명뿐이며, 필요한 정족수 7명에 미달한다.

```yaml
subject: 아르넬을 지지한 제후
relation:
  - 지지자 수가 4명이다
  - 정족수 7명에 미달한다
object_or_value:
  observed_supporters: 4
  quorum: 7
unit: 명
polarity: below_threshold
modality: asserted
source_status: 지지 수와 법정 정족수의 비교
required_slots: [beneficiary, observed_count, exclusivity_or_exactness, quorum, below_threshold]
lexical_probes: [넷뿐, 정족수 일곱, 못 미친다]
```

**양성 교정**

1. “아르넬 편에 선 제후는 네 명뿐이어서 필요한 일곱 명을 채우지 못한다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 관측값·기준값·미달 관계를 모두 보존한다.

2. “정족수는 7명인데 아르넬의 지지자는 4명에 그친다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 수치 귀속과 비교 방향이 정확하다.

**음성/경계 교정**

1. “아르넬은 제후 일곱의 지지를 받아 정족수를 충족했다.”
   - `expected_status: contradiction`
   - 이유: 4명·미달을 7명·충족으로 뒤집는다.

2. “아르넬을 지지하는 제후가 최소 네 명 있다.”
   - `expected_status: partial_preservation`
   - 이유: “넷뿐”이라는 정확한 상한과 정족수 7 미달을 보존하지 않는다.

---

## fact_throne_11

**정본:** 베스카는 3년 전 이단 재판에 연루되었고, 그에 따라 성별식 자격이 정지됐다.

```yaml
subject: 베스카
relation:
  - 이단 재판에 연루되었다
  - 성별식 자격이 정지되었다
object_or_value:
  elapsed_time: 3
  proceeding: 이단 재판
  status: 자격 정지
unit: 해 전
polarity: negative_status
modality: asserted
source_status: 과거 사건과 현재/후속 자격 상태
required_slots: [subject, heresy_trial_involvement, elapsed_time, consecration_eligibility, suspension]
lexical_probes: [이단, 세 해 전, 자격이 정지]
```

**양성 교정**

1. “베스카는 3년 전 이단 재판에 얽힌 일로 성별식 자격이 정지돼 있다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 사건·시점·자격 상태를 보존한다.

2. “성별식 자격 정지의 근거는 베스카가 세 해 전 이단 재판에 연루된 일이다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 문장 순서만 바뀌고 관계가 유지된다.

**음성/경계 교정**

1. “베스카는 이단 재판에서 무혐의가 되어 성별식 자격을 회복했다.”
   - `expected_status: contradiction`
   - 이유: 자격 정지를 회복으로 바꾸며 무혐의라는 새 사실도 추가한다.

2. “베스카가 이단 재판에 연루됐다는 의혹이 있지만 자격 상태는 알려지지 않았다.”
   - `expected_status: partial_preservation`
   - 이유: 재판 연루만 남고 핵심인 성별식 자격 정지가 빠졌다.

---

## fact_throne_12

**정본:** 아르넬의 이름은 대주교청 파문 명부 어디에도 없다.

```yaml
subject: 아르넬
relation: 대주교청 파문 명부에 이름이 존재하지 않는다
object_or_value: 전체 파문 명부
unit: null
polarity: absence
modality: asserted
source_status: 명부 전 범위 부재
required_slots: [subject, archbishopric_registry, excommunication_registry, complete_absence]
forbidden_inferences: [성별식 자격 긍정 인정, 성별식 승인, 계승 적격 확정]
lexical_probes: [파문 명부, 어디에도 없다, 대주교청]
```

**양성 교정**

1. “대주교청의 파문자 명단에는 아르넬이 전혀 등재돼 있지 않다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 명부와 전면적 부재를 보존한다.

2. “아르넬의 이름은 대주교청이 보유한 어느 파문 명부에서도 찾을 수 없다.”
   - `expected_status: faithful_paraphrase`
   - 이유: 전 범위 부재를 동등하게 표현한다.

**음성/경계 교정**

1. “아르넬은 대주교청의 성별식 자격 인정을 받았다.”
   - `expected_status: unsupported_overreach`
   - 이유: 파문 명부 부재를 긍정적 자격 인정으로 확장한다.

2. “아르넬의 이름이 일부 파문 명부에서는 발견되지 않았다.”
   - `expected_status: partial_preservation`
   - 이유: “어디에도 없다”는 전칭 부재를 일부 명부의 부재로 약화한다.

---
