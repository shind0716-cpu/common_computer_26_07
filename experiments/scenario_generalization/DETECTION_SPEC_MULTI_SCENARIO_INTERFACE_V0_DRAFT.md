# 다중 시나리오 DetectionSpec 공통 인터페이스 v0 초안

상태: 설계 초안 / 구현 전

## 1. 원칙

공통화하는 것은 기록·검증·집계 형식뿐이다. 의미 판정 정책은 각 issue가 소유한다.

```text
material
  → issue-owned DetectionSpec
  → coding record validator
  → optional issue-owned chain evaluator
  → common aggregator
  → lexical diagnostics + semantic primary outputs
```

## 2. issue policy

각 spec은 다음을 선언한다.

- `issue_id`
- `spec_id`, `spec_version`
- issue/facts/assignment hash
- calibration version/hash
- supported fact keys
- fact predicates
- distortion vocabulary
- outcome policy
- optional chain definitions
- human-review requirements

`outcome_policy`:

- throne/award-v2: `normative_decision`
- polar/exile: `descriptive_stance_only`

공통 layer가 polar/exile에 accuracy를 만들면 오류다.

## 3. fact coding record

```json
{
  "issue_id": "issue_exile",
  "fact_id": "fact_exile_02",
  "spec_id": "exile-relational-v0",
  "spec_version": "0.0.1",
  "material_hash": "...",
  "dataset_role": "calibration",
  "preservation_status": "faithful",
  "relation_engaged": true,
  "mention_mode": "asserted",
  "distortion_flags": [],
  "evidence_span": "밀수 적발은 정착 전보다 아홉 배 늘었다",
  "reason": "시간 비교를 보존하고 원인을 귀속하지 않았다",
  "lexical_hit": false,
  "provenance": {}
}
```

필수 불변식:

- key는 `(issue_id,fact_id)`
- `relation_engaged=true`는 preservation이 아님
- `absent + relation_engaged=true` 허용
- lexical과 semantic은 서로 덮어쓰지 않음
- blocked/invalid/unjudgeable을 0으로 조용히 변환하지 않음

## 4. chain record

award 같은 복합 사슬에만 사용한다.

```json
{
  "issue_id": "issue_award_v2",
  "chain_id": "lagoon_disqualification",
  "component_fact_keys": [
    ["issue_award_v2", "fact_award_v2_05"],
    ["issue_award_v2", "fact_award_v2_06"]
  ],
  "component_states": ["faithful", "faithful"],
  "chain_state": "true",
  "rule_version": "award-rule-v2",
  "reason": "신고 부정과 확인된 실제 사용이 함께 보존됨"
}
```

`chain_state`: `true|false|unknown|blocked|invalid`.

unknown component가 있으면 기본값은 unknown이다. closed-world는 spec에서 명시적으로 선언돼야 한다.

## 5. scenario adapters

### polar

- fact categories: clinical, flight, alternative access, authority
- chain evaluator: 없음
- stance mapping: 별도 prereg metadata
- final answer: descriptive

### exile

- fact categories: group scope, security observation, causality, return feasibility, treaty, administration
- chain evaluator: 없음
- normative coding: human-reviewed sidecar
- final answer: descriptive

### award

- fact categories: category, disclosure, use, criterion evidence, surface impression
- chain evaluator: category/disqualification/criterion/final selection
- surface heuristic: normative evaluator와 별도
- `award_flat`: `(issue_id,fact_id)` 정체성 필수

### throne

- fact categories: candidate/legal condition/value/threshold/status
- chain evaluator: eligibility and final selection
- old material ambiguous fact blocked

## 6. loader fail-closed rules

다음은 즉시 실패한다.

- spec 없음
- unsupported issue
- material hash mismatch
- calibration version 없음(확증 모드)
- fact 누락·중복·미지 fact
- 허용되지 않은 status/mode/flag
- filename/content issue mismatch
- fact_id만 사용해 award/award_flat 병합
- normative outcome이 없는 issue에 accuracy 요청

## 7. analyzer outputs

공통 aggregate:

- fact preservation counts/rates
- blocked/invalid counts separate
- relation engagement
- distortion flags
- lexical misses among preserved
- lexical hits among contradicted/absent
- evidence trace

issue-specific aggregate:

- polar/exile: stance-conditioned unfavorable-fact preservation
- award: component coverage and chain states
- throne: condition states and eligibility

lexical과 semantic을 하나의 총점으로 합치지 않는다.

## 8. calibration/evaluation boundary

- observed pilot outputs: `development_observed`
- independent authored examples: `calibration`
- later tranche: `held_out`

동일 문장을 calibration과 held-out에 중복하지 않는다. 실제 출력에서 발견한 오류는 codebook 개선에 쓸 수 있지만 같은 출력으로 accuracy를 주장하지 않는다.

## 9. 구현 순서

1. schema + loader + hash validation
2. structured coding record validator
3. lexical auxiliary output 분리
4. polar/exile descriptive aggregates
5. award chain state evaluator — 정본 수정 뒤
6. human/independent coding import
7. calibration fixture tests
8. 자동 detector는 별도 검증을 통과할 때만

## 10. 현재 구현 금지선

- polar/exile의 최종 선택 정오화
- award old `verdict()`를 normative evaluator로 재사용
- 정규식 확장을 semantic detector로 명명
- source ambiguity를 detector가 임의 해소
- old outputs를 new material hash로 재라벨링
