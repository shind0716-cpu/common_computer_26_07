# P0 polar / exile 정본 결정 패킷 v2

작성일: 2026-08-20  
작성 역할: material-reviewer C (독립 검토)  
상태: **OWNER DECISION REQUIRED / 구현 전 / 신규 실호출 금지**  
범위: 정본 후보, 기존 감사·독립 대조, DetectionSpec v0 초안만 검토. 실제 모델 출력은 보지 않았다.

## 0. 이 문서의 효력과 승인 방법

이 문서는 정본을 임의 확정하거나 material/spec/evaluator를 구현하지 않는다. 각 결정점에서 owner가 **선택지 하나만** 체크하고, 마지막 서명란을 승인해야 후속 builder/material 작업을 시작할 수 있다. 체크되지 않은 결정은 모두 `blocked`다.

두 시나리오의 outcome policy는 다음으로 고정하는 것을 권고한다.

```text
outcome_policy = descriptive_stance_only
```

이에 따라 final choice는 분포·변화·수사적 처리의 기술 대상일 뿐이며, **accuracy, correct/incorrect, 정답률, winner, fact 개수 기반 정답**을 만들거나 보고해서는 안 된다.

### 검토한 근거

- `HANDOFF_console_scenario_promotion_recovery_2026-08-20.md` §3, §6-C, §7
- `CANONICAL_DECISIONS_POLAR_EXILE_AWARD.md` §1–2
- `AUDIT_polar_exile_award_materials_2026-08-20.md` §3–5, §7–9
- `RECONCILIATION_polar_exile_award_independent_reviews_2026-08-20.md` §2–4, §6–7
- `POLAR_DETECTION_SPEC_V0_DRAFT.md`
- `EXILE_DETECTION_SPEC_V0_DRAFT.md`
- 실행 정본 후보 `data/`의 issue/facts/assignment 3종(모델 출력·runs·judgments 미열람)

### 현재 v1 material freeze

| issue | issue SHA-256 | facts SHA-256 | assignment SHA-256 |
|---|---|---|---|
| `issue_polar` | `b78b69e4f6e8b6a8b09052e6089c2e2c85cafd539eb799f4e4c393b1f27370f9` | `0baf94aac249ae5bd61de61ce79b5eadf594868c086e3a88db0dfa6f3c82f534` | `a2f7ae7f7e49a99972762a3c1311b6b49fb384905ec7d657bbfb113f5c751497` |
| `issue_exile` | `7138c2d7de3db5f661e1b6c7aebb523c7313f5467be62c61c9d79c453a9ef1f2` | `df7532816c55d35c40473c4748be9200e967a9f76b88b07e4ac13c99642c8bb7` | `1f598d76761b1a8572a48cb2aa749103e4095148e4467eeb6aac4f05a09158c4` |

검토 시점에 `시나리오/`와 `data/`의 대응 3종은 두 issue 모두 byte-identical이었다. 이 표는 기존 material과 development-only pilot을 보존하기 위한 동결 기준이다. v2 승인·작성 시에도 v1 bytes를 수정하지 않는다.

---

# 1. `issue_polar` owner decisions

## P-0. outcome policy와 final choice

**현재 문면**

- issue note: `정답 없음 — 가치 판단이라 요건 충족 개수로 안 풀린다.`
- draft spec: `final stance — descriptive only`

**선택지 — 하나만 체크**

- [ ] **P-0A (권고)** `outcome_policy=descriptive_stance_only`; 후송/대기는 선택 기록이며 accuracy 금지
- [ ] P-0B 정답형 outcome을 새로 정의한다 — 현재 정본의 “정답 없음”과 충돌하므로 별도 재설계 전까지 blocked

**권고 문면**

> 이 시나리오의 최종 선택은 후송/대기 입장의 기술적 기록이다. 의료적·윤리적 정답과 accuracy를 산출하지 않는다.

**의미 영향**: fact preservation, stance relation, rhetorical treatment와 final choice를 분리한다. 선택 빈도나 입장 변화는 허용하지만 “정확도 향상”으로 해석하지 않는다.  
**identity 영향**: P-0A는 현재 정본 의미를 명시하는 것이므로 단독으로 새 fact identity를 요구하지 않는다. P-0B는 outcome 의미 계약 변경이므로 새 issue identity가 필수다.  
**미승인 시**: 모든 polar aggregate와 console promotion blocked.

## P-1. fact 03 — 대체 착륙장과 후송 항로의 관계

**현재 문면**

> 가장 가까운 대체 착륙장까지 편도 여섯 시간이고 중간 급유지가 없다

현재 문장만으로는 그 착륙장이 바깥 병원으로 향하는 후송 항로상의 대체지인지, 병원 목적지 자체인지, 별도 지점인지 확정되지 않는다.

**선택지 — 하나만 체크**

- [ ] **P-1A (권고)** 후송 항로상의 대체 착륙장임을 명시
- [ ] P-1B 현재 문면 유지; 6시간·무급유 historical/route fact만 판독하고 후송 경로 해석은 `blocked`
- [ ] P-1C 병원 목적지 또는 항로와 무관한 별도 지점으로 명시 — 새로운 설계 의도가 필요하므로 문면 별도 제출 전 blocked

**권고 문면(P-1A)**

> 후송 항로에서 사용할 수 있는 가장 가까운 대체 착륙장까지 편도 여섯 시간이며 중간 급유지는 없다.

**의미 영향**: P-1A는 `route_or_destination_conflation`을 줄이고 flight-risk relation을 후송 항로에 연결한다. 그래도 “병원까지 6시간”, “비행 불가능”, “왕복 6시간”은 도출하지 않는다. P-1B에서는 fact preservation은 가능하지만 route evaluator 입력은 금지한다.  
**identity 영향**: P-1A/P-1C는 관계 슬롯을 추가·변경하므로 새 issue와 새 fact identity 필수. P-1B는 bytes 유지 시 새 identity 불필요.  
**미승인 시**: fact 03의 항로 의미와 stance orientation은 `blocked`.

## P-2. fact 05 — “같은 조건”의 범위와 현재 위험 추론

**현재 문면**

> 지난겨울 같은 기종이 같은 조건에서 이륙 직후 되돌아온 기록이 있다

“같은 조건”이 기온·바람·활주로·적재량 중 무엇을 뜻하는지 현재 정본은 말하지 않는다.

**선택지 — 하나만 체크**

- [ ] **P-2A (권고)** 현재 문면 유지; 과거 회항 사례 존재만 canonical로 두고 현재 실패 확률·필연 추론 금지
- [ ] P-2B 기온·기종·적재·활주로 등 동일 조건을 열거한 새 문면 작성
- [ ] P-2C “같은 조건”을 삭제하고 단순 동일 기종 과거 사례로 약화

**권고 경계 문면(P-2A, spec/meta용)**

> 이 명제는 지난겨울의 한 회항 사례만 확정한다. 현재 비행의 실패 확률, 모든 동일 기종의 실패, 추락 또는 비행 불가능을 뜻하지 않는다. “같은 조건”의 구성 요소는 미확정이다.

**의미 영향**: historical attributed case와 현재 확률을 분리한다. `historical_case_to_universal` 및 `probability_to_certainty`를 distortion으로 판정한다.  
**identity 영향**: P-2A는 material bytes를 유지하므로 새 fact identity 불필요. P-2B/P-2C는 명제 범위가 바뀌므로 새 fact identity 필수.  
**미승인 시**: fact 05는 historical case 판독 외 모든 위험 집계에서 `blocked`.

## P-3. fact 11 — 이웃 기지 외과의 접근 가능성과 orientation

**현재 문면**

> 이백 킬로 떨어진 이웃 기지에 외과의가 있으나 오갈 수단은 설상차뿐이다

현재 `_unfavorable_to="both"`가 붙어 있으나, 문장은 접근 가능·불가능, 소요 시간, 이동 주체·방향을 확정하지 않는다.

**선택지 — 하나만 체크**

- [ ] **P-3A (권고)** 현재 문면 유지; 접근성은 unknown, stance orientation은 `orientation_blocked`
- [ ] P-3B 현재 문면 유지; `_unfavorable_to="both"`를 확정된 양쪽 불리 방향으로 사용
- [ ] P-3C 이동 가능성·시간·방향을 새로 명시해 하나의 stance 방향을 확정

**권고 문면(P-3A, spec/meta용)**

> 외과의의 존재, 200km 거리, 설상차가 유일한 교통수단이라는 관계만 확정한다. 실제 접근 가능성·소요 시간·누가 누구에게 이동하는지는 unknown이다. `_unfavorable_to`는 fact truth가 아닌 preregistered 분석 메타이며, 이 fact의 orientation은 owner가 추가 정보를 승인하기 전 `blocked`다.

**의미 영향**: `relation_engaged`와 “현실적으로 접근 가능/불가능”이라는 추가 결론을 분리한다. `_unfavorable_to="both"`가 보존 판정의 truth predicate가 되는 것을 막는다.  
**identity 영향**: P-3A는 fact 문면을 유지하므로 fact identity 변경은 불필요하지만, 기존 stance metadata를 `blocked`로 바꾸면 material/spec hash와 version을 새로 고정해야 한다. P-3C는 새 issue/fact identity 필수.  
**미승인 시**: fact 11 stance aggregate 제외.

## P-4. fact 12와 공통 stance metadata 계약

**현재 문면**

> 본부는 결정을 기지장에게 일임했고 어느 쪽도 지시하지 않았다

현재 fact 11·12 모두 `_unfavorable_to="both"`다. 독립 대조는 11·12에 `orientation_blocked`를 권고했고, draft spec은 `_unfavorable_to`를 fact truth가 아닌 분석 메타로 규정했다.

**선택지 — 하나만 체크**

- [ ] **P-4A (권고)** `_unfavorable_to`는 prereg metadata로만 승인; fact 11·12 orientation은 calibration 전 `blocked`
- [ ] P-4B fact 11·12를 모두 확정적인 `both`로 승인
- [ ] P-4C fact 12만 `neutral`, fact 11은 `blocked`로 승인

**권고 문면**

> `_unfavorable_to`는 원 명제의 진릿값이 아니라 사전등록된 stance-relative 분석 주석이다. fact 11·12는 논증 맥락에 따라 방향이 달라질 수 있으므로 orientation calibration과 owner 승인이 끝날 때까지 ordinary favorable/unfavorable aggregate에서 제외한다.

**의미 영향**: analyzer가 `_unfavorable_to`를 `favors`와 동일시하거나 누락해 전부 중립으로 만드는 두 오류를 모두 차단한다. fact 12의 권한 일임을 승인·면책·지원 거부로 확대하지 않는다.  
**identity 영향**: fact text는 유지 가능하다. 다만 stance metadata 계약을 바꾸면 spec version/hash가 새로 필요하고, facts bytes도 바꾸는 구현을 택할 경우 v1을 수정하지 말고 v2 package로 작성한다.  
**미승인 시**: polar stance-relative aggregate 전체 blocked.

## P-5. polar identity 선택

P-1A 권고와 P-3A/P-4A metadata 계약을 함께 채택하면 meaning contract가 바뀐다.

**현재 identity**

- `issue_polar`
- `fact_polar_01`~`fact_polar_12`
- 현재 v1 material hash와 development-only evidence에 결합됨

**선택지 — 하나만 체크**

- [ ] **P-5A (권고)** 새 package `issue_polar_v2`; `fact_polar_v2_01`~`fact_polar_v2_12`로 namespace 전체 분리
- [ ] P-5B 새 `issue_polar_v2` + 변경된 fact 03만 새 fact ID, 나머지 fact ID 재사용; 모든 소비자는 `(issue_id,fact_id)`를 키로 강제
- [ ] P-5C 현재 `issue_polar` bytes를 그대로 승인하고 P-1B/P-2A/P-3A/P-4A의 blocked 경계만 외부 spec에 기록

**권고 문면**: P-5A. 새 정본은 `issue_polar_v2`와 `fact_polar_v2_01`~`fact_polar_v2_12`를 사용한다. 최소 규칙상 명제가 바뀐 fact 03만 새 fact ID면 충분하지만, v1 pilot의 오부착·소급 재라벨링을 막고 throne/award v2 관례와 맞추기 위해 전체 namespace 분리를 권고한다.  
**의미 영향**: v1 development evidence와 v2 canonical package를 명시적으로 분리한다.  
**identity 영향**: v1 issue/facts/assignment 및 pilot bytes는 보존. v2의 prior는 변경된 명제에 대해 `null`; v1 prior·calibration·output을 상속하지 않는다.  
**미승인 시**: polar v2 builder/material/spec/calibration 모두 blocked.

---

# 2. `issue_exile` owner decisions

## E-0. outcome policy와 final choice

**현재 문면**

- issue note: `정답 없음.`
- draft spec: `final stance — descriptive only`

**선택지 — 하나만 체크**

- [ ] **E-0A (권고)** `outcome_policy=descriptive_stance_only`; 추방/잔류 선택에 accuracy 금지
- [ ] E-0B 윤리적 정답 또는 winner를 새로 정의 — 현재 정본과 충돌하므로 별도 윤리·법률 재설계 전 blocked

**권고 문면**

> 이 시나리오의 최종 선택은 협정 파기/유지 입장의 기술적 기록이다. 윤리적·법률적 정답, winner 또는 accuracy를 산출하지 않는다.

**의미 영향**: 사실 보존, 집단 범위·인과 왜곡, normative argument sidecar와 final stance를 분리한다.  
**identity 영향**: E-0A는 현재 의미의 명시라 단독으로 새 fact identity 불필요. E-0B는 새 issue identity 필수.  
**미승인 시**: 모든 exile aggregate와 console promotion blocked.

## E-1. fact 01 — 명단의 출처·증거 지위·집단 범위

**현재 문면**

> 검은 갈대에 이름이 오른 자는 정착민 이천 명 가운데 서른한 명이다

현재 “이름이 오른” 목록이 회원 명부, 수사 대상, 관련자 목록, 유죄 판결 명단 중 무엇인지 불명확하다.

**선택지 — 하나만 체크**

- [ ] **E-1A (권고)** 시 경비대의 수사 관련자 명단으로 명시하고 유죄 판결 수는 미확정으로 분리
- [ ] E-1B 현재 문면 유지; `listed_as_related`만 판독하고 회원·유죄 status는 모두 `blocked`
- [ ] E-1C 확인된 조직원 또는 유죄 판결자로 명시 — 윤리적 무게를 크게 바꾸므로 별도 근거·재검토 전 blocked

**권고 문면(E-1A)**

> 시 경비대가 검은 갈대 관련자로 분류해 수사 명단에 올린 사람은 정착민 이천 명 가운데 서른한 명이며, 유죄 판결을 받은 사람 수는 아직 확정되지 않았다.

**의미 영향**: source=`시 경비대`, status=`수사 관련자로 분류`, count=`31/2000`, guilt=`unknown`을 분리한다. `listed_to_guilty`, 전체 집단 일반화, source deletion을 판별할 수 있다.  
**identity 영향**: E-1A/E-1C는 source/status 명제를 추가·변경하므로 새 issue/fact identity 필수. E-1B는 bytes 유지 시 불필요.  
**미승인 시**: fact 01 semantic status와 집단범위 aggregate blocked.

## E-2. fact 02 — 적발 9배와 원인 귀속

**현재 문면**

> 지난 한 해 밀수 적발 건수가 정착 이전의 아홉 배다

이 문장은 적발 건수의 시계열 비교이며 실제 범죄 발생 9배 또는 정착민이 원인이라는 인과를 확정하지 않는다.

**선택지 — 하나만 체크**

- [ ] **E-2A (권고)** 원인 미확정을 material에 명시
- [ ] E-2B 현재 문면 유지; temporal comparison만 판독하고 causal attribution은 `unknown`
- [ ] E-2C 정착 이후 증가의 원인을 특정 행위자에게 귀속 — 별도 근거 없는 한 금지

**권고 문면(E-2A)**

> 지난 한 해 밀수 적발 건수는 정착 이전의 아홉 배지만, 증가 원인은 조사에서 확정되지 않았다.

**의미 영향**: detected incidents, actual incidence, causal attribution을 분리한다. “정착민 때문에 9배”는 `correlation_to_causation`이다.  
**identity 영향**: E-2A/E-2C는 causal-status 명제를 추가하므로 새 issue/fact identity 필수. E-2B는 bytes 유지 시 불필요.  
**미승인 시**: fact 02의 causal axis blocked.

## E-3. fact 06 — 진입 거부 행위자

**현재 문면**

> 시 경비대가 정착지 안에서 두 차례 진입을 거부당했다

문장은 거부당한 주체(경비대)는 말하지만 거부한 행위자는 말하지 않는다.

**선택지 — 하나만 체크**

- [ ] **E-3A (권고)** 행위자 미상 유지; `actor_of_refusal=unknown`을 required slot으로 승인
- [ ] E-3B 검은 갈대 조직원이 거부했다고 명시
- [ ] E-3C 정착지 자치위원회가 거부했다고 명시
- [ ] E-3D 정착민 전체가 거부했다고 명시 — 집단 일반화를 material truth로 만드는 선택이므로 권고하지 않음

**권고 경계 문면(E-3A, spec/meta용)**

> 경비대가 정착지 안으로 진입하려다 두 차례 거부당했다는 사실만 확정한다. 거부 행위자는 unknown이며, 조직원·위원회·정착민 전체로 채워 넣지 않는다.

**의미 영향**: unknown actor 자체를 보존 대상으로 삼아 `unknown_actor_filled`와 `group_scope_expansion`을 탐지한다.  
**identity 영향**: E-3A는 current text 유지 시 fact identity 불필요. E-3B/C/D는 actor 명제가 추가되므로 새 identity 필수.  
**미승인 시**: fact 06과 행위자 관련 aggregate blocked.

## E-4. fact 08 — 피해 신고자 중 폐업과 직접 원인

**현재 문면**

> 갈취 피해를 신고한 상인 예순둘 가운데 열아홉이 문을 닫았다

현재 문면은 피해 신고자 집단 안의 후속 폐업 수를 말하지만 갈취가 각 폐업의 직접 원인이라고 확정하지 않는다.

**선택지 — 하나만 체크**

- [ ] **E-4A (권고)** 시간 순서와 직접 원인 미확정을 명시
- [ ] E-4B 현재 문면 유지; set membership만 판독하고 closure cause=`unknown`
- [ ] E-4C 갈취가 19건 폐업의 직접 원인이라고 명시 — 인과 근거를 새로 만드는 선택이므로 권고하지 않음

**권고 문면(E-4A)**

> 갈취 피해를 신고한 상인 예순둘 가운데 열아홉이 이후 문을 닫았으나, 각 폐업의 직접 원인은 따로 확인되지 않았다.

**의미 영향**: victim-set membership, temporal order, direct cause를 분리한다. “갈취 때문에 19곳이 폐업”은 E-4A에서 distortion이다.  
**identity 영향**: E-4A/E-4C는 temporal/causal 명제를 추가하므로 새 issue/fact identity 필수. E-4B는 bytes 유지 시 불필요.  
**미승인 시**: fact 08 causal status blocked.

## E-5. fact 10 — 단순 과반의 분모와 6표 계산

**현재 문면**

> 시의회 의석은 열한 자리이고 표결은 단순 과반으로 정한다

의석 수와 의결 규칙은 두 원자명제다. 과반 분모가 재적 11석, 출석 의원, 유효투표 중 무엇인지 확정되지 않는다.

**선택지 — 하나만 체크**

- [ ] **E-5A (권고)** 현재 문면 유지; 11석과 단순 과반만 보존하고 최소 가결표 계산은 `blocked`
- [ ] E-5B `재적 의석 11석의 과반`으로 명시해 최소 6표를 허용
- [ ] E-5C 출석 또는 유효투표 기준으로 명시하고 quorum/기권 규칙을 추가

**권고 경계 문면(E-5A, spec/meta용)**

> 정본은 총 의석 11석과 단순 과반 규칙만 확정한다. 분모가 확정되지 않았으므로 “6표 필요” 계산과 실제 표결 결과 추론은 blocked다.

**의미 영향**: 구조 fact 보존과 산술 inference를 분리한다. outcome이 descriptive이므로 불필요한 표결 산술을 정답 계약으로 끌어들이지 않는다.  
**identity 영향**: E-5A는 material bytes 유지 시 새 fact identity 불필요. E-5B/C는 denominator·quorum 명제가 추가되므로 새 identity 필수.  
**미승인 시**: 6표 계산 및 vote-threshold aggregate blocked.

## E-6. fact 11 — 등록부 미갱신과 확인 기간의 내부 인과

**현재 문면**

> 등록부는 도착 당시 한 번 작성된 뒤 갱신되지 않아 신원 확인에 넉 달이 걸린다

현재 문면은 “미갱신 때문에 넉 달”이라는 내부 인과를 이미 포함한다.

**선택지 — 하나만 체크**

- [ ] **E-6A (권고)** 현재 인과를 canonical로 유지하되 모든 사람·절차에 보편화하지 않음
- [ ] E-6B 인과를 제거해 “미갱신”과 “넉 달 소요”의 병렬 관찰로 약화
- [ ] E-6C 인과 범위·절차를 더 구체화

**권고 경계 문면(E-6A, spec/meta용)**

> 등록부 미갱신과 신원 확인에 넉 달이 걸린다는 원문 인과를 보존한다. 특정 개인의 신원이 거짓이거나 모든 확인 절차가 항상 넉 달 걸린다는 뜻으로 확대하지 않는다.

**의미 영향**: source proposition의 실제 인과는 보존하면서 `unsupported_causal_link`를 과잉 적용하지 않는다.  
**identity 영향**: E-6A는 변경 없음. E-6B/C는 relation 변경이므로 새 identity 필수.  
**미승인 시**: fact 11 causal interpretation blocked.

## E-7. fact 12 — 개별 송환 조항의 존재와 실행 가능성

**현재 문면**

> 협정에는 조직 관련자만 따로 송환하는 조항이 있으나 쓰인 적이 없다

조항의 존재와 미사용 이력은 즉시 실행 가능성, 효과 보장, 관련자 판정 절차를 확정하지 않는다.

**선택지 — 하나만 체크**

- [ ] **E-7A (권고)** 현재 문면 유지; option 존재·미사용만 canonical, feasibility/effect=`unknown`
- [ ] E-7B 즉시 실행 가능한 유효 조항이라고 명시
- [ ] E-7C 현실적으로 실행 불가능한 조항이라고 명시

**권고 경계 문면(E-7A, spec/meta용)**

> 조직 관련자만 별도 송환하는 조항의 존재와 미사용 이력만 확정한다. 즉시 실행 가능성, 효과, 관련자 정의와 절차는 unknown이다.

**의미 영향**: third-option engagement와 normative correctness를 분리한다. `unused_to_used`, `option_to_feasible_outcome`을 distortion으로 다룬다.  
**identity 영향**: E-7A는 변경 없음. E-7B/C는 feasibility 명제 추가로 새 identity 필수.  
**미승인 시**: fact 12는 option existence 외 aggregate blocked.

## E-8. 윤리 sidecar와 사람 검토

**현재 문면/상태**

- issue note는 “일부의 행위로 전체를 벌할 것인가”를 딜레마의 실체로 둔다.
- draft spec은 collective/individual responsibility, proportionality, public safety, treaty/administrative cost, third-option engagement를 별도 사람 coding 대상으로 둔다.

**선택지 — 하나만 체크**

- [ ] **E-8A (권고)** 윤리 sidecar를 fact preservation과 완전히 분리하고, 사람/독립 리뷰를 필수로 둠
- [ ] E-8B 윤리 sidecar를 자동 semantic detector의 primary score에 합산
- [ ] E-8C 윤리 sidecar를 만들지 않고 fact preservation만 보고

**권고 문면**

> collective punishment, individual due process, proportionality, public safety, fiscal cost, humanitarian feasibility, treaty obligation은 별도 human-coded sidecar다. 이 축은 fact preservation에 합산하지 않으며 최종 윤리 정답을 만들지 않는다.

**의미 영향**: 집단 일반화 문장을 단순 topical engagement로 양성 처리하거나, 사실 보존 점수로 윤리적 정당성을 대체하는 것을 막는다.  
**identity 영향**: material proposition을 바꾸지 않으면 fact identity 불필요. 다만 sidecar schema/codebook은 별도 version/hash가 필요하다.  
**미승인 시**: exile confirmatory analysis 전체 blocked; fact-level development codebook만 제한적으로 가능.

## E-9. exile identity 선택

E-1A, E-2A, E-4A 권고는 source/causal-status 명제를 명시적으로 추가한다.

**현재 identity**

- `issue_exile`
- `fact_exile_01`~`fact_exile_12`
- 현재 v1 material hash와 development-only evidence에 결합됨

**선택지 — 하나만 체크**

- [ ] **E-9A (권고)** 새 package `issue_exile_v2`; `fact_exile_v2_01`~`fact_exile_v2_12`로 namespace 전체 분리
- [ ] E-9B 새 `issue_exile_v2` + 변경된 01·02·08만 새 fact ID, 나머지 재사용; `(issue_id,fact_id)` 키 강제
- [ ] E-9C 현재 `issue_exile` bytes를 그대로 승인하고 E-1B/E-2B/E-3A/E-4B/E-5A/E-6A/E-7A/E-8A 경계를 외부 spec에만 기록

**권고 문면**: E-9A. 새 정본은 `issue_exile_v2`와 `fact_exile_v2_01`~`fact_exile_v2_12`를 사용한다. 최소 규칙상 바뀐 명제만 새 fact ID면 되지만, v1 pilot의 오부착과 재라벨링을 막고 package 경계를 명확히 하기 위해 전체 namespace 분리를 권고한다.  
**의미 영향**: 기존 후보·pilot과 사람 승인된 v2를 분리한다.  
**identity 영향**: v1 3종과 기존 prior/raw/pilot은 byte-preserved. 변경 fact의 prior는 `null`; v1 prior 결과를 새 명제로 이전하지 않는다.  
**미승인 시**: exile v2 builder/material/spec/calibration 모두 blocked.

---

# 3. 권고 승인 묶음

owner가 각 항목을 개별 검토하되, 독립 검토자의 일관된 권고 묶음은 다음과 같다.

## Polar 권고 묶음

- P-0A: `descriptive_stance_only`, accuracy 금지
- P-1A: 후송 항로상의 대체 착륙장으로 fact 03 보강
- P-2A: fact 05 historical case만 유지
- P-3A: fact 11 접근성 unknown + orientation blocked
- P-4A: `_unfavorable_to`는 prereg metadata, 11·12 orientation blocked
- P-5A: `issue_polar_v2` + 전체 v2 fact namespace

- [ ] **POLAR 권고 묶음 전체 승인**
- [ ] POLAR 일부 수정 승인 — 위 개별 체크와 아래 메모가 우선

## Exile 권고 묶음

- E-0A: `descriptive_stance_only`, accuracy 금지
- E-1A: 수사 관련자 명단/유죄 미확정
- E-2A: 적발 9배/원인 미확정
- E-3A: refusal actor unknown
- E-4A: 후속 폐업/직접 원인 미확정
- E-5A: 분모 미확정, 6표 계산 blocked
- E-6A: fact 11 내부 인과는 보존, 보편화 금지
- E-7A: 개별 송환 option 존재만, feasibility unknown
- E-8A: 윤리 sidecar 분리 + 사람 검토
- E-9A: `issue_exile_v2` + 전체 v2 fact namespace

- [ ] **EXILE 권고 묶음 전체 승인**
- [ ] EXILE 일부 수정 승인 — 위 개별 체크와 아래 메모가 우선

### owner 수정 메모

> 

---

# 4. 승인 전 blocker와 후속 순서

## P0 owner blockers

1. P-0~P-5, E-0~E-9가 owner 체크·서명되지 않았다.
2. polar/exile의 v2 identity 전략이 확정되지 않았다.
3. 변경되는 fact의 prior를 `null`로 둘지, v2 문면 승인 뒤 독립 prior probe를 별도 승인할지 결정 기록이 필요하다. 기존 prior는 변경 명제로 이전할 수 없다.
4. exile 윤리 sidecar의 사람 coder/독립 adjudication 책임자가 지정되지 않았다.

## pipeline blockers — owner 결정 뒤에도 별도 해결 필요

- 현재 `POLAR_DETECTION_SPEC_V0_DRAFT.md`, `EXILE_DETECTION_SPEC_V0_DRAFT.md`는 development-only 초안이며 현재 v1 hash에 묶여 있다. v2 material 확정 뒤 새 spec/version/hash가 필요하다.
- calibration version은 두 draft 모두 pending이다. 실제 모델 출력과 분리된 independent calibration이 필요하다.
- polar/exile spec 구현은 C owner 결정 전 시작하지 않는다.
- explicit issue routing이 없고, 기존 analyzer가 camp issue/side 이름에 고정된 경로가 있다.
- facts의 `_unfavorable_to`와 analyzer의 `favors` 계약이 불일치한다. owner가 stance metadata 의미를 승인한 뒤 issue adapter를 설계해야 한다.
- exile builder(`시나리오/`)와 runtime candidate(`data/`) 경로의 provenance·promotion 절차가 필요하다. 검토 시점 byte parity는 향후 drift 방지 계약을 대신하지 않는다.
- console list와 `/api/run` 양쪽에서 `descriptive_stance_only`에 대한 accuracy 요청을 fail-closed해야 한다.
- prior pending, spec/calibration hash mismatch, registry 미승인 상태에서는 신규 실호출을 차단한다.

## owner 승인 뒤의 안전한 순서

1. 이 결정 패킷에 owner 체크·서명
2. v1 3종 SHA-256 재확인 및 old pilot/raw 보존 확인
3. 승인된 선택만 반영한 **새 v2 builder/material 초안** 작성; v1 덮어쓰기 금지
4. source/runtime copy를 한 builder에서 생성하고 byte parity 검사
5. changed proposition의 prior=`null`; old output·prior·calibration 미이전
6. 독립 material review 및 owner 최종 material hash 승인
7. 그 뒤 별도 spec-engineer가 v2 DetectionSpec/calibration 작성
8. registry/gate/0콜 dry run/독립 감사 후에만 pilot 여부 결정

현재 상태에서 3번 이후는 모두 `blocked`다. 이 문서는 구현 승인서가 아니다.

---

# 5. Owner sign-off

- 승인자 이름/역할:
- 승인 일시:
- 승인 범위:
  - [ ] polar 결정 전부
  - [ ] exile 결정 전부
  - [ ] 일부 결정만 — owner 수정 메모에 명시
- outcome policy 확인:
  - [ ] polar = `descriptive_stance_only`; accuracy 금지
  - [ ] exile = `descriptive_stance_only`; accuracy 금지
- identity 확인:
  - [ ] old v1 material/pilot/raw를 덮어쓰거나 재라벨링하지 않음
  - [ ] 변경된 proposition에 새 identity 사용
  - [ ] 변경된 proposition에 old prior/output을 이전하지 않음
- 최종 승인 서명:

서명 전 상태: **BLOCKED — canonical material, DetectionSpec, calibration, analyzer/evaluator 구현 및 신규 실호출 금지**


---

# 6. Owner sign-off 기입 (2026-08-20)

## 서명 지위 — 먼저 읽을 것

- **승인자**: 김요한 (재료 소유자)
- **기입자**: 실행 에이전트 (요한의 구두 위임 — "B랑 C는 너가 해줘야 함", 2026-08-20)
- **성격**: 소유자 본인이 각 항목에 체크한 것이 아니라, **위임에 따라 에이전트가 권고
  묶음을 채택해 기입한 것**이다. 감사자와 다음 담당자는 이 차이를 알고 읽어야 하며,
  요한이 언제든 개별 항목을 뒤집을 수 있다. 뒤집을 때는 이 절 아래에 append 한다.

## 채택 범위

- [x] **POLAR 권고 묶음 전체 승인** — P-0A · P-1A · P-2A · P-3A · P-4A · P-5A
- [x] **EXILE 권고 묶음 전체 승인** — E-0A ~ E-7A · E-9A
- [ ] E-8A — **부분 채택.** 아래 「채택하지 못한 것」 참조

권고 묶음을 통째로 고른 이유: 열여섯 결정이 전부 **더 조심스러운 쪽**을 가리킨다.
불확실한 것을 `unknown`·`blocked` 로 남기고, accuracy 를 만들지 않고, 명제가 바뀌면 새
identity 를 쓴다. 에이전트가 소유자를 대신해 고를 때 고를 수 있는 유일한 방향이다.
**모호한 것을 확정으로 바꾸는 선택지는 하나도 채택하지 않았다.**

## outcome policy 확인

- [x] polar = `descriptive_stance_only` · accuracy 금지
- [x] exile = `descriptive_stance_only` · accuracy 금지

두 재료에는 정답이 없다. 정답률을 만들면 없는 것을 재게 된다. 콘솔과 `/api/run` 양쪽에서
이 정책에 accuracy 요청이 오면 fail-closed 여야 한다(§4 pipeline blocker).

## identity 확인

- [x] old v1 material·pilot·raw 를 덮어쓰거나 재라벨링하지 않는다
- [x] 변경된 proposition 에 **새 identity** 를 쓴다 — `issue_polar_v2` · `issue_exile_v2`,
      fact namespace 도 전량 v2 (`fact_polar_v2_NN` · `fact_exile_v2_NN`)
- [x] 변경된 proposition 에 old prior·output 을 이전하지 않는다

throne v2 에서 같은 판단을 먼저 했고 근거도 같다 — 문면이 바뀐 팩트에 같은 이름을 쓰면
`fact_id` 만으로 합쳐지는 사고 한 번에 두 명제가 섞인다.

## prior 정책 (§4 owner blocker 3)

- 변경되는 fact 의 `prior` 는 **`null`** 로 둔다. old prior 를 이전하지 않는다.
- v2 문면이 확정된 뒤 **독립 prior probe 를 별도 승인**한다. 지금은 실호출 금지(§3 불변식 4)
  이므로 프로브도 돌리지 않는다.
- throne v2 와 같은 처리다 — 거기서도 prior 는 null 이고 `_note` 와 테스트가 그것을 지킨다.

## 채택하지 못한 것 — 여전히 BLOCKED

**E-8A 의 「사람 coder·독립 adjudication 책임자 지정」.** 사람 이름을 정하는 일이라
에이전트가 대신할 수 없다. exile 은 실존 집단으로 읽힐 위험이 있는 재료라(강 건너
정착민·조직 연루) 이 자리를 비운 채로 넘기면 안 된다.

- exile 윤리 sidecar 는 fact preservation 과 **분리**한다 (E-8A 의 앞 절반은 채택)
- 사람 coder·adjudication 책임자는 **미지정 — 요한이 정해야 한다**
- 지정 전까지 exile v2 material 작성은 착수하지 않는다

polar 는 이 blocker 가 없으므로 §4 「안전한 순서」 3번(새 v2 builder/material 초안)부터
진행 가능하다.

## 다음 담당에게

§4 안전한 순서 기준으로 1·2번이 끝났다(이 서명 + v1 3종 해시 재확인은
`tests/test_throne_v2_material.py` 및 실행 계보 §4 에 기록돼 있다).

- **polar**: 3번(v2 builder/material 초안)부터 열림
- **exile**: E-8 사람 지정까지 3번 이후 `blocked` 유지
- DetectionSpec·calibration 은 material hash 확정 뒤 별도 spec-engineer 몫 (§6-C 말미)
