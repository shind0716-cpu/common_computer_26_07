# 가치관 설계 근거 템플릿 사용 안내

대상 파일: `VALUE_DESIGN_EVIDENCE_TEMPLATE.yaml`

이 템플릿은 사용자가 직접 **카테고리**와 그 안의 **가치관**을 입력하고, 각 가치관이 어떤 근거와 추론으로 설계되었는지 추적하기 위한 개발용 양식이다.

## 가장 빠른 입력 순서

먼저 아래 필드만 채우면 최소 초안이 된다.

1. `category.id`, `category.name`, `category.definition`
2. `values[].id`, `values[].name`, `values[].core_claim`
3. `values[].meaning.moral_priority`, `limit_condition`
4. `values[].evidence_basis[]`
5. `values[].scenario_fit[]`
6. `values[].agent_profile.short_prompt`

한 카테고리에 가치관이 여러 개라면 `values`의 첫 항목 전체를 복제한다.

```yaml
category:
  id: care_harm
  name: 돌봄·피해
  definition: 누구를 어떤 방식으로 보호할 것인가

values:
  - id: autonomy_respecting_care
    name: 자율 존중형 돌봄
    core_claim: 당사자의 의사와 자기결정권을 존중하는 것이 중요한 돌봄이다.
    # 나머지 필드 입력

  - id: preventive_protection
    name: 예방적 보호형 돌봄
    core_claim: 심각하고 회복 불가능한 피해가 예상되면 선제 개입이 정당화될 수 있다.
    # 나머지 필드 입력
```

위 예시는 형식 설명용일 뿐이며, 검증된 연구 근거나 확정된 가치관 목록을 의미하지 않는다.

## 근거 기록 원칙

각 `evidence_basis` 항목은 다음 세 층을 분리한다.

- `verified_claim`: 출처가 직접 말하는 내용
- `inference_to_value`: 그 내용을 가치관 설계로 연결한 작성자의 추론
- `counterevidence_or_limit`: 반대 근거와 적용 한계

출처가 아직 확인되지 않았다면 그럴듯한 내용을 채우지 말고 다음처럼 기록한다.

```yaml
status: pending
verified_claim: ""
inference_to_value: "검증 전 가설"
```

## 가치관과 찬반 입장의 분리

가치관은 특정 선택지와 일대일로 고정하지 않는다. `scenario_fit`에는 가능하면 다음을 모두 적는다.

- `can_support`: 그 가치관이 지지할 수 있는 선택
- `can_oppose`: 같은 가치관이 다른 조건에서 반대할 수 있는 선택
- `stance_locked: false`

이렇게 해야 에이전트가 가치관을 단순한 찬성·반대 라벨로 처리하는 것을 줄일 수 있다.

## 완료 기준

개발용 초안은 다음 조건을 만족하면 된다.

- 카테고리의 포함·제외 경계가 적혀 있다.
- 각 가치관에 핵심 명제와 양보 조건이 있다.
- 근거의 원문 위치와 설계자의 추론이 분리되어 있다.
- 최소 한 시나리오에서 관련 사실과 가치 추론이 연결되어 있다.
- 가장 가까운 경쟁 가치관과의 결정적 차이가 적혀 있다.
- 반증 또는 수정 조건이 적혀 있다.

`governance.intended_use: development_only`와 `confirmatory_use_allowed: false`는 근거 검증과 필요한 승인이 끝나기 전까지 유지한다.
