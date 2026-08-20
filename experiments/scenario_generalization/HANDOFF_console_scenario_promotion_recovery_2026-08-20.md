# 실험 콘솔 시나리오 승격 복구: 공동 작업 배분

작성일: 2026-08-20  
상태: **작업 배분 확정 / 구현 전 / 실호출 금지**  
목표: 후보 재료가 검증 없이 `data/issues`에 놓여 곧바로 콘솔에 노출되는 현재 경로를 복구하고,
시나리오가 정본·DetectionSpec·calibration·prior·배분·계보 게이트를 통과한 뒤에만 실행되게 한다.

## 1. 동료들에게

파일럿을 먼저 돌린 덕분에 lexical anchor의 한계, 정본 모호성, 동일 r0 부재, unknown/default
변환 같은 중요한 실패를 실제로 발견했다. 이 데이터는 폐기물이 아니라 **development-only 증거**다.
다만 원래 계획했던 승격 순서를 건너뛰었으므로, 이제 파일럿을 새 정본의 확증 데이터로 소급
승격하지 않고, 입구를 먼저 고친 뒤 새 tranche를 시작한다.

## 2. 현재 확인된 구조적 원인

`tools/console/app.py::_issues()`는 `data/issues/*.json`을 단순 glob한다. 따라서 issue 파일이
존재하기만 하면 `_issue_rows()`와 `/api/meta`를 통해 콘솔 선택 목록에 나타난다. 현재 콘솔은
다음을 확인하지 않는다.

- 후보/개발/승인 상태
- facts·assignment 3종 완결성과 content ID 일치
- DetectionSpec 존재와 material hash
- 독립 calibration 존재와 version/hash
- prior 완료 상태
- outcome policy
- 사람 승인

즉 현재 `data/issues`는 사실상 **승격 저장소이면서 동시에 후보 투입구**라서, 파일럿 작업이
게이트를 우회했다.

## 3. 복구 불변식

1. 기존 v1 material, 파일럿 raw calls, debates, judgments, prior 파일을 삭제·덮어쓰기·재라벨링하지 않는다.
2. v1 파일럿 출력은 원래 `(issue_id, fact_id, material hash)` 아래 `development_observed`로 유지한다.
3. v2 material에 v1 출력을 붙이지 않는다.
4. 게이트 복구와 정본/spec 작업이 끝날 때까지 신규 실호출을 하지 않는다.
5. 콘솔 목록은 파일 존재가 아니라 **명시적 승인 manifest + 기계 게이트 PASS**로 만든다.
6. lexical anchor는 보조 진단이며 semantic primary 판정으로 승격하지 않는다.
7. polar/exile의 final choice에는 accuracy를 만들지 않는다.
8. 구현자와 독립 검토자의 역할을 분리한다.

## 4. 제안하는 승격 상태 기계

```text
candidate
  → canonical_reviewed
  → spec_ready
  → calibration_ready
  → prior_ready
  → console_approved
  → pilot_only
  → confirmatory_frozen
```

- `candidate`: `시나리오/` 또는 후보 영역에만 존재. 콘솔 비노출.
- `canonical_reviewed`: material owner가 문면과 outcome policy 승인.
- `spec_ready`: DetectionSpec과 material hash 일치.
- `calibration_ready`: 독립 calibration이 spec과 일치.
- `prior_ready`: 필요한 prior probe 완료 또는 사전등록된 면제 사유 존재.
- `console_approved`: 승인 manifest가 있고 모든 기계 게이트 PASS. 이때만 콘솔 목록 노출.
- `pilot_only`: 실행 가능하지만 결과는 development-only.
- `confirmatory_frozen`: prereg·prompt·config·material·spec·calibration hash 동결 후 본실험 가능.

상태를 건너뛰지 않는다. 파일 존재만으로 다음 상태를 추론하지 않는다.

## 5. Identity ledger

| 라벨 | 담당 | 역할 | 주장 가능한 범위 |
|---|---|---|---|
| orchestrator | Hermes / 현재 세션 | 순서 복구·계약 조정·최종 검증 | 저장소에서 직접 확인한 상태와 합의된 배분 |
| gate-engineer | 코딩 에이전트 A | 콘솔 승격 registry/gate 구현 | 자신이 구현·실행한 테스트와 코드 |
| award-engineer | 코딩 에이전트 B | award_v2 DetectionSpec·calibration | award v2 의미 계약과 산출물 검증 |
| material-reviewer | 사람 소유자 + 독립 검토 에이전트 C | polar/exile 정본 결정 | 승인한 문면과 독립 검토 결과 |
| experiment-engineer | 코딩 에이전트 D | 동일 r0 분기·실행 계보·dry run | 구현한 runner와 0콜 검증 결과 |
| independent-auditor | 구현에 참여하지 않은 에이전트 E | 교차 검증 | 읽은 artifact와 재실행 결과만 |

실행 당시의 모델·재시도·격리 상태는 해당 실행자 또는 raw lineage만 증언할 수 있다.

# 6. 작업 배분

## A. gate-engineer — P0 콘솔 승격 registry와 fail-closed 입구

### 산출물

- `modules/scenario_gate.py` 또는 동등한 단일 게이트 모듈
- 명시적 registry/manifest 파일과 schema
- `tools/console/app.py`의 `_issues()`/`_issue_rows()`가 승인된 issue만 반환하도록 수정
- 콘솔 UI에 상태와 blocking reason 표시
- `tests/test_console_scenario_promotion.py`
- registry 운영 문서

### 제안 registry 필드

```json
{
  "issue_id": "issue_award_v2",
  "state": "candidate",
  "outcome_policy": "normative_decision",
  "material": {
    "issue_sha256": "...",
    "facts_sha256": "...",
    "assignment_sha256": "..."
  },
  "spec": {"required": true, "version": "...", "sha256": "..."},
  "calibration": {"required": true, "version": "...", "sha256": "..."},
  "prior": {"required": true, "status": "pending"},
  "approved_by": null,
  "approved_at": null
}
```

### 수정 가능

- `tools/console/`
- 새 `modules/scenario_gate.py`
- 새 registry/schema 경로
- console gate 테스트

### 수정 금지

- 기존 pilot raw/debate/judgment/prior
- scenario fact 문면
- award/throne evaluator 의미 규칙
- 다른 에이전트의 spec/calibration

### 필수 게이트

- registry 없는 issue: 콘솔 비노출
- `candidate`: 콘솔 비노출
- 승인 state인데 3종 중 하나 없음: 비노출 + blocking reason
- filename/content issue ID 불일치: 실패
- facts와 assignment의 fact ID 불일치·고아·미지 ID: 실패
- spec material hash 불일치: 실패
- required calibration 없음/version 불일치: 실패
- prior pending: 실호출 차단
- descriptive issue에 accuracy 요청: 실패
- 승인된 issue만 `/api/meta.issue_rows`에 노출
- `/api/run`도 목록과 독립적으로 같은 게이트를 재검사

### 레거시 정책 결정 필요

기존 콘솔 시나리오를 자동 승인하지 않는다. 필요한 경우 registry에
`legacy_approved`를 명시하고 UI에 `semantic spec 미적용` 경고를 표시한다. 암묵적 grandfathering 금지.

### 수용 기준

- 임시 data root에서 위 negative tests 모두 PASS
- `issue_award_v2`가 candidate이면 파일이 `data/issues`에 있어도 목록에 나오지 않음
- 승인 manifest의 hash 하나를 변조하면 `/api/run`이 LLM 호출 전에 400
- 기존 console tests 회귀 없음

검토자: independent-auditor E

---

## B. award-engineer — P0 award_v2 의미 패키지 완성

### 선행 입력

- frozen `issue_award_v2` issue/facts/assignment
- `CANONICAL_DECISIONS_POLAR_EXILE_AWARD.md`
- throne_v2 DetectionSpec 구현을 구조 참고로만 사용

### 산출물

- `data/detection_specs/issue_award_v2.json`
- `data/detection_specs/calibration_issue_award_v2.json`
- 필요 시 `시나리오/build_detection_spec_award_v2.py`
- award chain evaluator의 구조화된 record 계약
- `tests/test_award_v2_detection_spec.py`
- material/spec/calibration hash manifest

### 의미 계약

- fact 01~03: `surface_impression`, normative chain 제외
- fact 04: 밤길 category eligible
- fact 12: 밤길 disclosure/use alignment
- fact 05+06: 석호 disqualification
- fact 07+08: 종이 category ineligibility
- fact 09+10+11: 밤길 공식 세 criterion 우위
- component 미확인 시 final state=`unknown`
- old `verdict()` 재사용 금지

### calibration

각 fact에 faithful와 negative/boundary 사례가 모두 있어야 한다. 실제 파일럿 출력 문장을 복사하지
않고 `independent-from-observed-output`으로 새로 작성한다. chain 부분 조합도 포함한다.

### 수정 가능

- award_v2 spec/calibration/build/test
- 공통 validator가 scenario-owned distortion vocabulary를 지원하기 위한 최소 확장

### 수정 금지

- frozen award_v2 material 문면과 assignment
- old award/award_flat material
- old prior/raw 파일
- 콘솔 registry 구현

### 수용 기준

- 12 fact ID가 material과 정확히 일치
- material hash 검증 PASS
- fact별 양성·음성 사례 존재
- 빈/부분 known set은 winner 없음
- 전체 required component에서만 밤길 선택
- lexical hit와 semantic status의 불일치 사례 허용
- observed pilot provenance가 calibration에 없음

검토자: independent-auditor E

---

## C. material-reviewer — P0 polar/exile 사람 정본 결정

### 산출물

- polar 결정 서명 또는 `issue_polar_v2` patch 결정
- exile 사람 검토 결과와 `issue_exile_v2` 문면 결정
- `CANONICAL_DECISIONS_POLAR_EXILE_AWARD.md` append-only 결정 기록
- 변경 시 새 issue/fact identity 표
- 각 시나리오 outcome policy 승인

### polar 결정점

- fact 03을 후송 항로상의 대체 착륙장으로 명시할지
- fact 05는 historical case만 유지할지
- fact 11의 접근 가능성을 unknown으로 유지할지
- final choice는 descriptive, accuracy 금지
- `_unfavorable_to`는 truth가 아닌 prereg metadata

### exile 결정점

- fact 01: 수사 관련자 명단과 유죄 분리
- fact 02: 적발 9배와 인과 미확정 분리
- fact 06: refusal actor unknown 유지 여부
- fact 08: 폐업 직접 원인 미확정
- fact 10: 과반 분모 불명 시 계산 blocked
- 윤리 sidecar와 fact preservation 분리

### 수정 가능

- 정본 결정 문서
- 승인 후 새 v2 builder/material 초안

### 수정 금지

- 모호성을 독자적으로 추측하여 evaluator에 하드코딩
- 기존 v1 파일럿 출력 재라벨링
- 실제 출력에 맞춰 문면 변경

### 수용 기준

- 모든 결정점에 owner 승인 또는 blocked가 기록됨
- 명제가 바뀐 fact는 새 identity
- old bytes/hash 보존 테스트
- polar/exile outcome policy가 `descriptive_stance_only`

다음 담당: 결정 완료 후 별도 spec-engineer가 DetectionSpec/calibration 작성. award-engineer와 병렬 가능.

---

## D. experiment-engineer — P1 동일 r0 분기와 실행 계보

### 시작 조건

A의 콘솔 게이트 인터페이스와 최소 하나의 승인된 scenario package가 준비된 뒤 시작한다.

### 산출물

- 동일 initial r0에서 memory/progression arms로 분기하는 runner 설계 및 구현
- parent initial response ID/hash와 child run linkage
- coordinate manifest
- 호출 단위 raw append+flush/resume
- 0콜 fake responder adversarial tests
- console estimate/run 연동
- dry-run report

### 필수 좌표

- issue/material/spec/calibration hash
- model/model ID/provider
- temperature/reasoning
- seed/assignment
- initial response ID/hash
- memory arm/progression arm
- rounds/replicate
- prompt/config version
- run ID/parent run ID

### 수정 가능

- runner/config/manifest 관련 코드와 테스트
- console의 실행 요청 필드(게이트 인터페이스는 A와 합의)

### 수정 금지

- scenario material/spec/calibration
- 기존 파일럿 로그
- 결과를 본 뒤 prereg 주지표 변경

### 수용 기준

- 같은 parent r0 bytes/hash가 여러 child arm에 연결됨
- child가 parent를 수정하지 않음
- 강제 중단 후 완료 좌표 재호출 0, 남은 좌표만 호출
- parse failure가 `unmentioned`로 변환되지 않음
- fallback·partial·invalid 상태가 manifest에 보존
- 실호출 0인 dry run에서 전체 좌표와 예상 호출 수 산출

검토자: independent-auditor E

---

## E. independent-auditor — P1 독립 승격 감사

### 산출물

- `AUDIT_console_scenario_promotion_<date>.md`
- gate mutation 결과
- scenario package completeness 표
- 남은 blocker와 severity

### 검증 항목

- candidate가 목록에 노출되지 않는지
- registry state만 바꾸고 hash를 틀리게 했을 때 차단되는지
- spec/calibration/prior 파일을 각각 하나씩 제거했을 때 차단되는지
- filename/content ID 불일치 차단
- descriptive scenario accuracy 차단
- partial award chain default winner 없음
- old pilot artifact hash 불변
- runner 중단/재개 계보

### 수정 금지

독립 감사 중 구현 파일을 직접 고치지 않는다. findings를 남기고 A/B/D가 수정한 뒤 재검증한다.

### 수용 기준

- 모든 P0 blocker 해결
- gate negative mutation 전부 기대대로 실패
- 승인 scenario 1개가 console에서 0콜 dry run PASS
- 파일 수정 여부와 실행 명령을 보고서에 명시

# 7. 직렬·병렬 실행 순서

```text
즉시 동결: 신규 실호출 금지
        │
        ├── A console promotion gate ───────────────┐
        ├── B award_v2 spec/calibration ───────────┤  병렬
        └── C polar/exile owner decisions ─────────┘
                                                    │
                         E 독립 P0 감사 ◀───────────┘
                                                    │
                       승인 scenario package 1개
                                                    │
                         D 동일 r0 runner + dry run
                                                    │
                         E 재감사 + promotion 승인
                                                    │
                     prior probe → mini pilot only
                                                    │
                     prereg/hash freeze → 본실험
```

C의 결정 전에는 polar/exile spec 구현을 시작하지 않는다. D는 A의 gate API가 정해지기 전에
console integration을 구현하지 않는다.

# 8. 현재 시나리오 분류 초안

| issue | 현재 지위 | 콘솔 정책 | 다음 게이트 |
|---|---|---|---|
| `issue_throne` | 과거 pilot material | 개발 증거 보존 | 신규 실행 비승인 |
| `issue_throne_v2` | material+spec+calibration 있음, prior 확인 필요 | candidate | prior + registry + independent audit |
| `issue_award` | 과거 material/prior | 개발 증거 보존 | 신규 실행 비승인 |
| `issue_award_flat` | old variant | 개발 증거 보존 | v2 flat 필요 여부 결정 |
| `issue_award_v2` | material/evaluator 완료 | candidate | spec + calibration + prior + registry |
| `issue_polar` | 후보 정본 | candidate | owner 결정 + routing/spec/calibration |
| `issue_exile` | 사람 검토 전 | blocked | owner 결정 후 v2 여부 결정 |

이 표는 실행 승인표가 아니다. gate-engineer가 registry를 만들고 owner가 승인해야 상태가 승격된다.

# 9. 완료 정의

다음 조건을 모두 만족해야 “시나리오가 실험 콘솔에 들어갔다”고 말한다.

- canonical owner approval
- issue/facts/assignment schema와 ID 일치
- old material/pilot 보존 증거
- DetectionSpec과 material hash 일치
- 독립 calibration과 version/hash 일치
- prior 완료 또는 사전등록된 명시적 면제
- outcome policy 등록
- console registry `console_approved`
- console list와 `/api/run` 양쪽이 동일 gate 재검사
- 0콜 dry run PASS
- independent audit PASS

본실험 완료에는 추가로 동일 r0 분기, preregistration, frozen hashes, raw append/resume,
held-out tranche가 필요하다.

# 10. Append-only status

에이전트는 아래에 자신의 작업만 append한다. 다른 참가자의 상태를 대신 쓰지 않는다.

## gate-engineer A

- 상태: 미착수
- 브랜치/세션:
- 변경 파일:
- 실행 검증:
- 남은 blocker:

## award-engineer B

- 상태: 미착수
- 브랜치/세션:
- 변경 파일:
- 실행 검증:
- 남은 blocker:

- 2026-08-20 실행 에이전트 append (요한 위임 — "B랑 C는 너가 해줘야 함"):
  - 상태: **수용 기준 대조 완료 / 구멍 하나 메움**
  - **먼저 확인한 것**: spec·calibration·manifest·빌드·테스트가 이미 있었다. 다시 만들지
    않고 §6-B 수용 기준으로 대조했다 — fact 12개 material 일치 · material hash PASS ·
    fact 별 양성/음성 사례 있음 · calibration 48건 전부 `independent-from-observed-output`
    (관측 provenance 0건) · decision_role 12/12.
  - **메운 구멍**: `normative_award_evaluator_v2` 가 `시나리오/build_issue_award_v2.py`
    안에 있었고 서명이 `(known_fact_ids: set[str])` 였다. 두 가지가 문제였다.
    ① 분석 층이 빌드 스크립트를 import 하게 되어 빌드를 다시 돌리면 과거 결과 재현이 깨진다
    ② 「아는 팩트 집합」을 받으므로 **lexical 적중을 그대로 부어 넣어도 안 막힌다**
    (throne 평가기는 막아 뒀는데 award 는 안 막혀 있었다)
  - **한 것**: `modules/chain_eval.py` 신설 — 명세의 `decision_contract` 를 읽어 계산하고
    입력을 `fact_id -> preservation_status` 로 바꿨다. 판정값 검증은
    `detection_spec.validate_judgments` 로 요건형 평가기와 한 벌로 묶었다
    (`requirement_eval._check_judgments` 를 그쪽에 위임).
  - **부재를 반증으로 안 바꾼다**: 반증 팩트가 없는 재료이므로 덜 모인 성분은 `false` 가
    아니라 `unknown`. 근거가 `blocked` 면 `blocked` 로 따로 남긴다.
  - **표면 정보 격리**: 01~03 이 성분 근거로 쓰이면 로드 시점에 죽는다. 표면 셋을 전부
    잃어도 결정이 안 바뀌는 것을 테스트로 고정.
  - 변경 파일: `modules/chain_eval.py`(신설) · `modules/detection_spec.py`(+validate_judgments) ·
    `modules/requirement_eval.py`(위임) · `tests/test_award_chain_eval.py`(신설 20종)
  - 실행 검증: 전체 discover **477종 통과**. 실호출 0.
  - **자체 발견 — 도중에 내 테스트가 틀렸다**: 「분석 층이 빌드를 import 하지 않는다」를
    본문 문자열 검색으로 짜서 **내 독스트링에 걸렸다**(왜 옮겼는지 설명하며 그 이름을 썼다).
    AST 의 import 구문만 보게 고쳤다.
  - 남은 blocker: award v2 **prior 미실행**(prior=null) · calibration 이 세 축 중 보존 축만
    훈련한다(`mention_mode` 기대값 0건 · `blocked` 0건 — throne 과 같은 공백) ·
    **E 독립 감사 미수행**(구현자가 나라서 내 자체 점검을 감사로 읽지 마라)

## material-reviewer C

- 상태: 사람 결정 대기
- 승인자:
- 결정 기록:
- 남은 blocker:
- 2026-08-20 독립 검토 append:
  - 상태: **결정 패킷 작성 완료 / owner 승인 전 BLOCKED / 구현·신규 실호출 금지**
  - 결정 패킷: `experiments/scenario_generalization/DECISION_PACKET_POLAR_EXILE_V2_2026-08-20.md`
  - 남은 owner decisions — polar: outcome policy, fact 03 항로 관계, fact 05 historical 범위, fact 11 접근성/orientation, `_unfavorable_to` 지위, v2 identity 전략
  - 남은 owner decisions — exile: outcome policy, fact 01 source/guilt, fact 02 causal status, fact 06 refusal actor, fact 08 closure cause, fact 10 과반 분모, fact 11 내부 인과 범위, fact 12 option feasibility, 윤리 sidecar/human review, v2 identity 전략
  - 공통 고정 권고: polar/exile `outcome_policy=descriptive_stance_only`; accuracy 금지; 변경 명제는 새 identity; old material/pilot/raw 재라벨링 금지

- 2026-08-20 위임 서명 append (실행 에이전트 기입):
  - 상태: **결정 열여섯 중 열다섯 기입 완료 / E-8 사람 책임자 지정만 BLOCKED**
  - 성격: 소유자 본인 체크가 아니라 요한 구두 위임에 따른 대리 기입. 개별 항목 번복 가능
  - 기록 위치: `DECISION_PACKET_…_2026-08-20.md` §6 · `CANONICAL_DECISIONS_POLAR_EXILE_AWARD.md` A9
  - 채택: polar·exile 모두 `descriptive_stance_only`, accuracy 금지 / 불확실은 unknown·blocked /
    변경 명제는 새 identity(`issue_polar_v2`·`issue_exile_v2`, fact namespace 전량 v2) /
    prior=null, old prior·output 미이전
  - 남은 blocker: **exile 윤리 sidecar 의 사람 coder·독립 adjudication 책임자 미지정** —
    사람 이름을 정하는 일이라 대리할 수 없다. 지정 전까지 exile v2 material 착수 금지
  - polar 는 v2 builder/material 초안부터 열림

## experiment-engineer D

- 상태: A의 gate 인터페이스 대기
- 브랜치/세션:
- 변경 파일:
- 실행 검증:
- 남은 blocker:

### 2026-08-20 · 실행 에이전트 기입

- **상태**: D 본작업 **미착수**. §7 순서를 지켜 A의 gate 인터페이스를 기다린다.
  다만 D 산출물 목록 중 **「실행 계보」는 선행 제출됨** —
  `LINEAGE_throne_pilot_55calls_2026-08-20.md` (55행, 검증 전건 통과).
- **브랜치/세션**: `exp/hidden-profile-memory`. 오늘 커밋 5개, **push 안 함**.

- **변경 파일** (오늘 내가 만들거나 고친 것만)
  - `시나리오/build_issue_throne_v2.py` · `시나리오/build_detection_spec_throne_v2.py`
  - `data/{issues,facts,assignments}/…issue_throne_v2…` · `data/detection_specs/` 2종
  - `modules/detection_spec.py` · `modules/requirement_eval.py`
  - `modules/paths.py` — `detection_spec()` · `calibration_set()` 추가
    (그 뒤 A가 `scenario_registry()` · `scenario_registry_schema()` 를 같은 파일에 더했다)
  - `tests/` 4종 · `experiments/scenario_generalization/LINEAGE_…`
  - 파일럿 원자료: `runs/claude-haiku-4-5/issue_throne/` 9런 · `hermes/answers/` 54

- **실행 검증**: RED(ImportError) → GREEN 58종 → 전체 discover 434종 통과.
  v1 재료 3종 해시 불변을 테스트로 고정. material_lint v2 전항목 통과. **실호출 0.**

---

#### 역할 겸직 고지 — E가 알아야 한다

불변식 8("구현자와 독립 검토자 분리")에 비추어 스스로 적는다. 나는 오늘 **세 역할을 겸했다.**

1. throne 파일럿 54콜을 실제로 돌렸다 (D)
2. throne DetectionSpec v0 를 구현했다 (구현 에이전트)
3. **그 구현을 내가 리뷰했다**

3번이 문제다. 그 자체 리뷰로 결함 둘을 찾아 고쳤지만(`spec_version` 검증 구멍,
이름과 거부 사유가 다른 테스트 — 커밋 `ae43b00`), **자체 점검은 독립 감사가 아니다.**
E의 수용 기준은 "구현에 참여하지 않은 에이전트"이고 나는 참여했다.

내가 못 본 것이 무엇인지는 나도 모른다. 오늘 Hermes 감사가 내 앵커 숫자를 뒤집은 자리가
정확히 그런 자리였다. **`modules/detection_spec.py`·`requirement_eval.py`·`시나리오/build_*_v2.py`
와 그 테스트는 E의 독립 검토 대상으로 남겨 둔다.** 내 자체 리뷰 결과를 감사 통과로 읽지 마라.

자체 리뷰에서 **고치지 않고 남긴 것 셋**도 E가 확인해 주면 좋겠다.

- 교정 48사례가 세 축 중 **보존 축만** 훈련한다. `mention_mode` 기대값 0건, `blocked` 0건.
  fact_03 이 소문 양태인데 양태 교정이 없다.
- `data/` 사본이 손복사다. 빌드는 `시나리오/` 에만 쓰므로 재실행하면 조용히 어긋난다.
- `requirement_eval` 의 `satisfied` 는 judgments 가 아니라 명세에서 온다. 그래서 재는 것은
  "에이전트가 옳게 결론냈나"가 아니라 "살아남은 팩트로 적격을 세울 수 있나"다. 이름이 오해를 부른다.

---

#### A에게 넘기는 증언 — `data/` 반입을 누가 왜 했는가

§2가 지적한 「후보 재료가 검증 없이 `data/issues` 에 놓인」 상태를 만든 것은 나다.
게이트를 설계하려면 그 경위가 필요할 것 같아 적는다.

- **2026-08-20 낮**, 재료화 보드 제안의 이의 창(당일 21시)이 **닫히기 전에**
  `시나리오/` → `data/` 로 throne·polar·exile·award 를 복사했다. 사용자 판단에 따른 것이다.
- 그 뒤 `issue_throne_v2` 도 같은 방식으로 넣었다. `Copy-Item` 손복사다.
- 내가 확인한 것은 「러너가 `paths.facts()` 로만 읽으니 `data/` 에 없으면 못 돈다」까지였다.
  **`data/issues/` 가 승격 저장소이면서 동시에 콘솔 입구라는 것은 못 봤다.**
  §2 표현대로 "파일럿 작업이 게이트를 우회했다"가 맞다.
- 8/19 에 같은 파일들을 `data/` 에서 `시나리오/` 로 되돌린 적이 있다(커밋 `2269b7c`,
  사유: "검증 안 된 재료가 data/ 정본 칸에 있으면 안 된다"). **그 판단을 오늘 내가 뒤집었다.**

**되돌릴지는 A의 설계에 달렸다고 보고 내가 먼저 움직이지 않는다.** registry 로 막는 방식이면
파일은 두고 상태로 걸면 되고, 후보 영역 분리 방식이면 `시나리오/` 로 되돌려야 한다.
어느 쪽이든 지시하면 그날 안에 처리한다.

---

#### 남은 blocker (내 몫)

1. **D 시작 조건 미충족** — A의 gate 인터페이스 + 승인된 scenario package 1개 대기.
2. **`issue_throne_v2` prior 미실행** — §8 표는 "prior 확인 필요"로 적었으나 **확정이다.**
   문면이 바뀐 팩트 셋(04·06·10)은 v1 의 known 0/12 를 물려받을 수 없다. facts `_note` 와
   `test_prior_is_unprobed` 가 이를 지킨다. **12콜 필요** — 불변식 4에 걸려 지금은 못 돈다.
3. **v2 를 `run_solo.ISSUE_PROMPTS` 에 일부러 등록하지 않았다.** 실행 경로를 열지 않기
   위해서다. D 착수 시 A의 게이트와 합의한 뒤 연다.
4. **`THRONE_CANONICAL_DECISIONS.md` 머리말이 아직 "사용자 응답이 없어 임시 채택"** 이다.
   요한 승인이 2026-08-20 에 났으므로(A/A/A) 그 줄은 갱신돼야 한다. 남의 문서라 안 고쳤다.

## independent-auditor E

- 상태: A/B/C P0 산출물 대기
- 감사 파일:
- 재실행 결과:
- 남은 blocker:

---

## 2026-08-20 · gate-engineer A 완료 append

- **상태**: P0 registry/gate 구현 및 회귀 검증 완료. 파일 존재만으로 노출하던 경로를
  `deny_unless_explicit_legacy_approved` 원장 + 현재 바이트 재검사 경로로 교체했다.
  목록과 `/api/run`은 같은 `modules.scenario_gate` 판정을 각각 새로 실행한다. **신규 실호출 0.**
- **브랜치/세션**: `exp/hidden-profile-memory` / session unavailable.
- **변경 파일** (A 작업만):
  - `modules/scenario_gate.py`
  - `modules/paths.py` — scenario registry/schema 경로 helper
  - `data/scenario_registry.json`
  - `data/scenario_registry.schema.json`
  - `tools/console/app.py`
  - `tools/console/index.html`
  - `tests/test_console_scenario_promotion.py`
  - `tests/scenario_gate_helpers.py`
  - `tests/test_console.py`
  - `tests/test_console_gates.py`
  - `docs/SCENARIO_REGISTRY_OPERATIONS.md`
  - 이 handoff 문서의 본 append
- **strict TDD 실행 증거**:
  - 최초 `python -m unittest tests.test_console_scenario_promotion -v` → **FAIL (exit 1)**,
    구현 전 `modules.scenario_gate` import 불가.
  - `python -m unittest tests.test_console_scenario_promotion.TestMachineGate.test_registry_without_explicit_legacy_policy_is_blocked -v`
    → **FAIL 1 (exit 1)**; 최소 정책 검증 추가 후 같은 명령 → **OK 1 (exit 0)**.
  - `python -m unittest tests.test_console_scenario_promotion tests.test_console tests.test_console_gates -q`
    → **Ran 69 tests, OK (exit 0)**.
  - `python -m unittest discover -s tests -q` → **Ran 458 tests in 7.561s, OK (exit 0)**.
  - registry JSON Schema 검증 → **PASS (exit 0)**.
  - `python -m modules.validate` throne_v2 재료 3종 → **전부 OK (exit 0)**.
  - `git diff --check` → **exit 0** (기존 CRLF→LF 경고만 있음).
- **현재 기계 판정**: registry 6개 항목 모두 candidate/불완전으로 차단되어
  `approved_count=0`. 이는 신규 실호출 동결을 지키는 의도된 fail-closed 상태다.
- **남은 blocker**:
  1. E의 독립 mutation 감사와 owner 승인 전에는 `console_approved` 항목이 없다.
  2. `issue_throne_v2` prior가 pending이다.
  3. 병렬 B 작업으로 현재 `issue_award_v2` spec/calibration bytes/version이 A 원장 초안과
     불일치한다. candidate라 이미 차단되며, B 재료 동결 뒤 owner/E가 새 해시를 검토해 원장을
     갱신해야 한다. A가 이를 암묵 승인하지 않았다.
  4. polar/exile은 spec/calibration 및 owner 결정을 기다린다.
- **커밋/push**: 하지 않음.
