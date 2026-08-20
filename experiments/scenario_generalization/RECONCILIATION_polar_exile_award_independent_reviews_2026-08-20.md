# polar · exile · award 독립 검토 대조

작성일: 2026-08-20
지위: development-only / 실제 모델 출력 미사용
독립 검토: 시나리오별 1명, 총 3명

## 1. 대조 방법

각 독립 검토자는 지정된 issue/facts/assignment/builder/analyzer만 읽었다. 실제 runs·judgments·모델 출력은 보지 않았고 파일도 수정하지 않았다.

Hermes 초안과 다음 축을 대조했다.

- 12팩트 관계 슬롯
- lexical 거짓 음성·거짓 양성 경로
- 정본 모호성
- fact와 stance/decision 분리
- analyzer·builder 경로
- 구현 전 blocker

## 2. 공통 합의

세 독립 검토와 Hermes가 모두 합의한 사항:

1. 12팩트·ID·배분·명목 구조는 정상이다.
2. 앵커 12/12 자기 적중·교차 오검출 0은 정본 원문 재탐지 검사일 뿐 semantic validation이 아니다.
3. lexical hit와 semantic preservation을 분리해야 한다.
4. 주어·관계·값·극성·양태·출처가 팩트별 required slot이다.
5. 후보 문서 지위에서 confirmatory DetectionSpec을 동결할 수 없다.
6. polar/exile의 최종 선택은 accuracy가 아니라 descriptive outcome이다.
7. award/award_flat의 키는 `(issue_id,fact_id)`다.
8. 현재 award 정본으로 밤길 안내인의 유일 수상을 확정할 수 없다.

## 3. issue_polar 대조

### 3.1 일치

- 03의 6시간·무급유는 병원 목적지·도달 불가능을 뜻하지 않는다.
- 05의 과거 회항 사례를 현재 실패 필연으로 확대하면 안 된다.
- 07은 의무관 귀속과 가능성 양태를 보존해야 한다.
- 11은 외과의·200km·설상차 only의 복합 fact이며 접근 가능/불가능은 미확정이다.
- 12의 권한 일임을 승인·면책·지원 거부로 확대하면 안 된다.
- `_unfavorable_to`는 fact truth가 아니라 분석 주석이다.
- final poll은 조작점검/기울기 기록일 뿐 의료적 정답이 아니다.

### 3.2 독립 검토가 추가한 중요 blocker

#### analyzer issue 선택

`analyze_solo.py`는 현재 `ISSUE_ID="issue_camp"`로 시작하며 run issue 불일치 시 종료한다. 이슈별 앵커 선택 helper가 생겼어도 CLI/config issue 선택 경로는 아직 없다.

판정: polar 분석 구현 전 명시적 issue routing 필요.

#### stance 필드 불일치

polar facts는 `_unfavorable_to`를 사용하지만 analyzer의 favors 분해는 `favors`를 읽는다. 그대로 실행하면 12팩트가 모두 중립으로 접힐 수 있다.

판정:

- 공통 표준 필드를 정하거나
- issue adapter가 `_unfavorable_to`를 stance-relative relation으로 변환해야 한다.

fact 파일을 임의로 `favors`로 재해석하지 않는다.

#### 출력 이름

`recall_correct`는 정답 없는 polar와 맞지 않는다. 권고 이름:

- `recall_lexical_hits`
- `carrier_lexical_overlap`
- `lexical_excess_candidates`

#### 토론 라우팅

stance가 `none`이 아니면 콘솔이 재현 트랙으로 분류해 수첩 조건을 막는다는 재료 주석이 있다. solo 분석과 토론 분석을 구분하고, 토론 tranche 전 라우팅을 수리해야 한다.

#### 관점 계약

agent perspective와 assigned fact `_perspective`가 일치하지 않는다. 이는 여러 분야 정보를 가진 역할을 의도한 것일 수 있으나 관점 효과를 분석하려면 계약을 명시해야 한다.

### 3.3 보완 결정

- polar 지위: `CONTRACT-FIX-FIRST`
- fact-level codebook 개발: 가능
- confirmatory aggregation: 금지
- 11·12 orientation: `orientation_blocked` 권고
- `rhetorical_treatment` 축 추가 검토:
  - supports current stance
  - conceded against stance
  - minimized
  - dismissed
  - neutral use

## 4. issue_exile 대조

### 4.1 일치

- 01 명단 등재≠회원/유죄.
- 02 적발 9배≠발생 9배≠정착민 원인.
- 06 거부 행위자는 미상.
- 08 피해 신고자 중 폐업≠갈취 직접 원인.
- 05 현실적 귀환 곤란≠법적·윤리적 금지.
- 12 제3경로 존재≠즉시 실행 가능·정답.
- 집단 일반화·인과·권리 판단은 사람 검토가 필요하다.

### 4.2 독립 검토가 추가한 중요 blocker

#### fact 10 복합·분모 모호성

“의석 11 + 단순 과반”은 두 원자명제다. 단순 과반의 분모가 재적·출석·유효투표 중 무엇인지 없다. “6표 필요”는 조건부 산술 추론이지 무조건적 정본이 아니다.

권고:

- 두 슬롯을 모두 보존하도록 하되
- 최소 가결표 계산은 quorum/분모 결정 전 blocked.

#### fact 11 내부 인과

원문은 등록부 미갱신 때문에 신원 확인에 4개월이 걸린다고 인과를 포함한다. detector는 이 원문 인과는 보존하되, 모든 사람·모든 절차에 보편화하지 않는다.

#### builder/data 정본 경로 분리

builder는 `시나리오/` 아래에 쓰고 현재 실험 정본은 `data/` 아래에 있다. prior guard도 builder 출력 경로만 보호한다.

위험:

- builder 정본과 data 정본 drift
- prior 보호 범위 착오
- 어떤 파일이 실행에 사용됐는지 provenance 혼동

권고:

- material manifest에 실행에 사용된 `data/` 3종 해시 기록
- builder→data 승격 절차를 명시
- builder 산출 자체를 곧 실행 정본으로 부르지 않음

#### analyzer 분해

polar와 마찬가지로 `_unfavorable_to`를 analyzer가 읽지 않으며, 기존 favors side 이름도 camp 후보명에 고정돼 있다.

### 4.3 보완 결정

- exile 지위: `HUMAN-REVIEW-FIRST + PIPELINE-FIX`
- `mention_mode`에 negated를 별도 둘지 공통 계약에서 결정
- 윤리 sidecar 축 제안:
  - collective punishment invoked
  - individual due process invoked
  - public safety invoked
  - fiscal cost invoked
  - humanitarian feasibility invoked
  - treaty obligation invoked
- sidecar는 fact preservation에 합산하지 않음

## 5. issue_award 대조

### 5.1 완전 합의

독립 검토는 Hermes와 동일하게 전체 결론을 `blocked/indeterminate`로 판정했다.

#### 05+06

결격 사슬은 세 사슬 중 가장 견고하나 “참고 사용”의 규정 범위는 명시하는 편이 안전하다.

#### 07+08

부문 이관의 출발·도착·효력 시점이 없으므로 종이 낚시 탈락은 도출되지 않는다.

#### 09+10+11

- 09: preliminary direct score
- 10: design proxy
- 11: completeness proxy

공식 항목 우위와 항목별 다수결·가중치·동점 규칙은 정본에 없다.

#### 01~04·12

surface impression이며 normative criterion winner가 아니다.

### 5.2 실행으로 확인된 unknown/default 변환

독립 검토자가 기존 함수를 비수정 상태로 실행했다.

- `verdict(set())` → 석호의 계단
- 공유 팩트만 → 석호의 계단
- 05 또는 06 한 조각만 → 석호의 계단
- 05+06 → 종이 낚시
- 09+10+11 → 밤길 안내인
- 공유 01~04를 각각 제거해도 → 석호의 계단

판정:

- 공유 fact가 실제 조건식에 쓰이지 않는다.
- unknown component가 다른 후보의 항목 승리로 변환된다.
- `verdict()`는 normative evaluator가 아니다.
- 보존 시 이름을 `surface_response_heuristic_v0`로 낮춘다.

### 5.3 award_flat

`ANCHORS_BY_ISSUE`에 flat entry가 없어 현재 fail-closed한다. 이는 조용히 award 사전을 재사용하는 것보다 안전하다. flat을 분석할 때는 별도 issue/spec identity로 등록해야 한다.

## 6. 조정된 구현 진입 판정

### 공통 schema/loader

진입 가능:

- identity/hash validator
- multi-axis coding record
- lexical auxiliary record
- structured human coding import
- outcome-policy guard

### polar

조건부 진입:

- owner가 후보 재료 지위를 승인
- explicit issue routing
- `_unfavorable_to` adapter
- 11·12 orientation 처리
- final outcome 분리

### exile

진입 보류:

- 사람 문면 검토
- 01·06·08·10·12 경계 확정
- builder/data provenance 절차
- ethical sidecar contract

### award

진입 차단:

- v2 정본 필요
- 08 이관 방향
- rubric/aggregation 규칙
- closed-world 또는 긍정 적격 사실
- heuristic/normative evaluator 분리

## 7. 다음 산출물

- 실제 출력과 분리된 high-risk calibration 사례
- award v2 material patch
- exile 사람 검토 선택지
- polar stance adapter 계약

이 대조 과정에서 기존 재료·builder·analyzer는 수정하지 않았다.
