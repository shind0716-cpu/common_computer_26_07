# throne r0 의미 코딩 독립 대조 및 조정 기록

상태: development-only, 확증 분석 사용 금지

대상:

- Hermes 초안: `THRONE_R0_SEMANTIC_CODING_DRAFT.csv`
- 독립 코더: 9런 × 12팩트 = 108레코드
- lexical 기준: 당시 `analyze_solo.py`의 `issue_throne` 정규식

## 1. 완전성

- Hermes 레코드: 108
- 독립 레코드: 108
- 고유 `(run_id, fact_id)`: 양쪽 108
- 누락·중복: 0
- r0는 입장문이므로 양쪽 모두 `absent`를 기억 실패나 부호화 실패로 해석하지 않았다.

## 2. 비교 방법

원시 상태명은 서로 달랐다.

- Hermes는 보존과 왜곡을 별도 축으로 기록했다.
- 독립 코더는 `fabricated_extension` 같은 왜곡을 단일 status에 넣었다.
- 독립 코더의 `exact`와 Hermes의 `faithful` 경계도 달랐다.

따라서 다음처럼 정규화해 비교했다.

- `exact`, `faithful`, `faithful_paraphrase` → preserved
- `partial` → partial
- `absent` → absent
- `contradicted` → contradicted
- `fabricated_extension`, `weakened` → distorted

정본 주어가 모호한 `fact_throne_06` 9건은 자동 의미 판정 대상에서 제외했다. 독립 코더가 해당 문장을 판정했더라도 최종 초안에는 적용하지 않았다.

## 3. 정규화 대조

fact_06을 제외한 99건에서:

- 의미 영역 언급 여부 일치: 94/99, 1차 조정 전
- 거친 보존 상태 일치: 89/99, 1차 조정 전

불일치 10건을 원문으로 다시 판독해 Hermes 초안 7건을 수정했다.

수정 후:

- 원 명제 보존 또는 관계 영역 관여 경계를 포함한 실질 불일치: 아래 5건
- 그 외 94건은 거친 상태가 일치하거나 상태 어휘 차이로 설명됨

단일 일치율을 최종 성능처럼 사용하지 않는다. 이 대조는 판정 계약의 경계를 찾기 위한 개발 절차다.

## 4. 수정한 7건

### A_prev × fact_10

- 변경: partial → absent
- 이유: “베스카가 8명으로 우위”만 말하며 아르넬의 4명, 정족수 7명, 미달 상태를 발화하지 않는다.

### B_prev × fact_04

- 변경: 단순 absent → absent + `relation_engaged=true` + `modality_strengthening`
- 이유: 두 후보 모두 거부 통보를 받지 않았다는 명제는 없고 “성별식 자격에 문제가 없다”는 더 강한 결론만 있다.

### P_full × fact_10

- 변경: absent → partial + `unsupported_causal_link`
- 이유: 아르넬의 제후 서명 열세는 발화하지만 4/7은 생략하고, 이를 서신 미응답 탓으로 설명한다.

### P_prev × fact_04

- 변경: partial → absent + `relation_engaged=true` + `modality_strengthening`
- 이유: 거부 통보 부재가 아니라 긍정적 자격 인정을 주장한다.

### P_note × fact_04

- 변경: partial → absent + `relation_engaged=true` + `modality_strengthening` + `unsupported_concrete_extension`
- 이유: 비통보 명제를 보존하지 않고 “대주교청의 자격 인정”을 새 사실로 만든다.

### B_full × fact_08

- 변경: partial → faithful
- 이유: 20세 숫자는 생략했지만 베스카의 현재 미성년과 성년 도달 시점인 이듬해 파종제 이후를 충실히 보존한다.

### B_note × fact_02

- 변경: partial → faithful
- 이유: 같은 문맥에서 연대기상 아르넬 16세와 베스카 19세를 모두 보존한다.

## 5. 남은 경계 5건과 현재 판정

### A_note × fact_09

- Hermes: contradicted, relation engaged
- 독립: absent
- 현재 판정: Hermes 유지
- 이유: “양쪽 모두 정족수 미달”은 베스카 8명과 정족수 7명이라는 명제의 반대 결과를 직접 주장한다. 정확한 8이라는 수치를 반복하지 않아도 관계 영역에 관여한 모순이다.

### B_prev × fact_04

- Hermes: 원 명제 absent, 관계 관여와 양태 강화
- 독립: partial
- 현재 판정: Hermes 다축 판정 유지
- 이유: “자격에 문제가 없다”는 두 후보에 대한 거부 통보 부재를 부분 보존한 것이 아니라, 다른 긍정 명제다.

### P_note × fact_04

- Hermes: 원 명제 absent, 관계 관여와 비근거 강화
- 독립: fabricated_extension
- 현재 판정: 의미상 같은 발견
- 이유: 독립 코더는 왜곡을 status에 넣었고 Hermes는 보존·관여·왜곡을 분리했다.

### B_full × fact_10

- Hermes: partial
- 독립: preserved
- 현재 판정: partial 유지
- 이유: 아르넬 4명과 미달 맥락은 있으나 정족수 7명 슬롯을 직접 보존하지 않는다. compound fact의 full 보존 기준을 엄격히 적용한다.

### B_note × fact_07

- Hermes: faithful
- 독립: partial
- 현재 판정: faithful 유지, 교정셋 검토 항목으로 표시
- 이유: 연대기 16세와 세례 기록상 실제 21세의 대조가 5년 차이와 실제 나이를 함께 전달한다. 다만 기록 오류의 방향을 얼마나 명시해야 full 보존인지 교정셋에서 고정해야 한다.

## 6. 다축 계약으로 추가된 `relation_engaged`

독립 대조를 통해 `absent` 하나만으로는 다음 두 경우를 구분할 수 없음을 확인했다.

1. 관련 명제를 전혀 말하지 않음
2. 원 명제는 보존하지 않았지만 같은 관계 영역에서 더 강하거나 틀린 명제를 말함

따라서 다음을 별도 기록한다.

- `preservation_status`: 원 명제 보존 상태
- `relation_engaged`: 같은 관계 영역에 관여했는가
- `distortion_flags`: 어떤 방식으로 변형했는가

예:

```text
출력: “대주교청이 아르넬의 성별식 자격을 인정했다.”
preservation_status: absent
relation_engaged: true
distortion_flags: [modality_strengthening, unsupported_concrete_extension]
```

## 7. 조정 후 r0 초안 요약

fact_06 9건을 제외한 평가 가능 레코드 99건:

- faithful: 27
- partial: 35
- contradicted: 1
- absent: 36
- faithful + partial: 62
- 관계 영역 관여: 66
- lexical hit: 35
- 의미상 faithful/partial인데 lexical miss: 27
- 왜곡 플래그가 있는 평가 가능 레코드: 39

이 숫자는 r0 텍스트의 개발용 기술 통계다. 기억 효과, 부호화 실패율 또는 모델 일반 특성으로 해석하지 않는다.

## 8. 결론

- camp식 lexical hit는 throne의 의미 보존 주지표로 사용할 수 없다.
- lexical은 후보 span과 누출·회귀 디버깅용 보조지표로 유지한다.
- throne은 관계 슬롯, 보존 상태, 관계 관여, 발화 양태, 왜곡 플래그를 분리해야 한다.
- fact_06과 decision rule은 정본 결정 전 fail-closed다.
- 구현 전에 독립 교정 48사례와 compound fact 경계를 승인해야 한다.
