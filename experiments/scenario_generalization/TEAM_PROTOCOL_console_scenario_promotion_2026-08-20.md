# 콘솔 시나리오 승격 복구 — 에이전트 팀 통합 프로토콜

작성일: 2026-08-20  
상태: 1차 전문 작업 A/B/C 실행 중 (`deleg_c57236e3`)  
공유 작업 계약: `HANDOFF_console_scenario_promotion_recovery_2026-08-20.md`

## 1. 팀 목표

A/B/C를 서로 무관한 세 산출물로 끝내지 않는다. 세 전문 작업을 하나의 승격 경로로 통합하여
최소 한 시나리오가 다음 전체 경로를 0콜로 통과하게 한다.

```text
candidate material
→ canonical decision
→ DetectionSpec
→ independent calibration
→ prior state
→ registry manifest
→ console gate
→ /api/meta visibility
→ /api/run preflight
→ 0-call dry run
```

## 2. 팀 역할

| 역할 | 담당 | 입력 | 출력 |
|---|---|---|---|
| Team Lead / Orchestrator | Hermes | 모든 A/B/C artifact | 충돌 조정, 실제 파일 재검증, 다음 assignment |
| A Gate Engineer | task-0 | console + promotion handoff | registry/gate/tests |
| B Award Semantic Engineer | task-1 | frozen award_v2 + audits | award spec/calibration/tests |
| C Material Reviewer | task-2 | polar/exile audits/drafts | owner decision packet |
| Integration Engineer | 2차 에이전트 | A+B+C 결과 | award_v2 manifest 연결, 전체 0콜 통합 테스트 |
| Independent Auditor | 3차 에이전트 | 통합된 checkout | mutation audit, blocker report |

A/B/C는 전문 구현자다. 어느 한 명도 자신의 부분 결과만 보고 전체 승격 성공을 주장하지 않는다.
전체 성공 주장은 Integration Engineer의 실제 통합 테스트와 Independent Auditor의 재검증 뒤에만 가능하다.

## 3. 1차 실행 규칙

현재 실행 중인 A/B/C는 취소하지 않는다. 각자 맡은 파일 범위를 유지하고 기존 공동 handoff 상태를
갱신한다. 병렬 작업 중 같은 파일을 편집한 경우 Team Lead가 실제 diff를 읽고 append-only 기록을
보존한 채 조정한다.

### A가 B에서 받아야 하는 정보

- `issue_award_v2` spec ID/version/hash
- calibration version/hash
- outcome policy
- prior pending 상태

A는 이 값들을 임의로 추측하지 않는다. B 산출물 완료 후 registry manifest에 연결한다.

### B가 A에 제공해야 하는 정보

- registry가 검증할 정확한 material/spec/calibration 좌표
- fail-closed 오류 조건
- award chain completion 요구 사항

### C가 후속 spec 작업자에게 제공해야 하는 정보

- owner가 선택해야 할 문면
- 승인 전 blocked 항목
- 새 issue/fact identity가 필요한 변경
- polar/exile outcome policy

C의 결정 패킷은 owner 승인 전 console registry의 `console_approved` 근거가 될 수 없다.

## 4. 2차 Integration Engineer 작업

A/B/C 완료 후에만 시작한다.

### 허용 작업

- A의 registry schema에 B의 award_v2 package를 candidate로 등록
- prior 상태를 `pending`으로 명시
- candidate 비노출과 prior pending 실행 차단 확인
- prior를 가짜 완료로 바꾸지 않고 fixture에서만 approved happy path 검증
- A/B 테스트를 함께 실행
- 공동 handoff에 통합 결과 append

### 금지 작업

- 실 prior probe 또는 기타 LLM 호출
- polar/exile owner 결정을 대신 승인
- award material/spec/calibration 의미 변경
- 기존 pilot artifact 수정
- commit/push

### 통합 수용 기준

1. 실제 `issue_award_v2`는 candidate/prior pending이라 콘솔 비노출 또는 명확한 blocked 표시.
2. 임시 data root의 완전한 approved fixture는 `/api/meta`에 노출.
3. 같은 fixture의 hash/spec/calibration/prior 하나를 변조하면 `/api/run` 전에 차단.
4. award DetectionSpec과 calibration loader 검증 PASS.
5. partial award chain은 winner 없음.
6. 기존 console 및 award tests 회귀 없음.
7. 모든 검증은 실호출 0.

## 5. 3차 Independent Auditor 작업

Integration Engineer와 다른 에이전트가 수행한다.

- registry 없음
- candidate
- issue/facts/assignment 누락
- filename/content ID 불일치
- material hash mismatch
- spec/calibration version mismatch
- prior pending
- descriptive issue accuracy 요청
- partial award chain
- old pilot hash mutation

을 각각 독립적으로 변조해 기대대로 차단되는지 확인한다. 구현 파일을 직접 고치지 않고 감사 보고서만 남긴다.

## 6. 팀 실행 순서

```text
현재: A/B/C 병렬 실행
          ↓
Team Lead가 실제 파일·테스트·handoff 재검증
          ↓
Integration Engineer 1명 실행
          ↓
A/B 중 필요한 담당자가 finding 수정
          ↓
Independent Auditor 1명 실행
          ↓
owner 승인 및 prior 계획
          ↓
실호출 전 freeze
```

## 7. 상태

### Wave 1 — A/B/C

- delegation: `deleg_c57236e3`
- 상태: 실행 중
- 완료 증거: 세 task 결과 + 실제 repository artifact 재검증 필요

### Wave 2 — Integration Engineer

- 상태: Wave 1 대기
- 시작 조건: A/B/C 산출물 및 공동 handoff 업데이트 확인

### Wave 3 — Independent Auditor

- 상태: Wave 2 대기
- 시작 조건: 통합 테스트 PASS 및 checkout 안정화

## 8. 실제 운용 자원: Claude Code + Hermes 두 도구

사용자가 별도의 5인 에이전트 팀을 구성하는 것을 전제로 하지 않는다. 위 A/B/C와
Integration/Audit는 **물리적 제품 수가 아니라 역할과 격리된 작업 단위**다.

- Hermes: Team Lead, 입력 bundle 생성, 순서·identity·hash 검증, 테스트 재실행, 집계
- Claude Code: 코딩 구현자 및 격리된 judge 실행기
- 공유 Markdown/JSON: 두 도구 사이의 durable handoff와 상태 원장

사용자는 에이전트 설정·메시지 라우팅·팀 서버를 구성하지 않는다. Hermes가 Claude Code CLI를
호출하고 산출물을 읽어 검증한다. Claude Code를 사용할 수 없는 동안에는 shared handoff를
완성해 두고 실행을 blocked로 기록하며, Claude를 실행했다고 주장하지 않는다.

### A/B/C 평가 조건은 물리적 에이전트가 아니다

```text
A = common judge protocol only
B = common protocol + scenario DetectionSpec
C = common protocol + DetectionSpec + independent calibration
```

동일한 Claude judge 버전·모델 설정을 사용하되 각 조건을 **새 세션과 별도 입력 bundle**로
실행한다. B/C가 A의 출력이나 서로의 출력을 읽지 못하게 한다. Hermes는 세 조건의 입력
허용목록을 검사하고, 출력 schema·provenance·hash를 검증한 뒤 조건 라벨을 가린 상태에서
집계한다.

### 최소 실행 형태

```text
Hermes orchestrator
  ├─ bundle_A/common-only.json ──> fresh Claude session A ──> record_A.jsonl
  ├─ bundle_B/common+spec.json ──> fresh Claude session B ──> record_B.jsonl
  └─ bundle_C/common+spec+cal.json ─> fresh Claude session C ─> record_C.jsonl
                                      ↓
                        Hermes schema/hash validator + aggregator
                                      ↓
                        별도 Claude fresh session의 blind review
```

세 Claude 세션은 한 번에 병렬로 돌릴 필요가 없다. 순차 실행해도 session ID, 입력 manifest,
허용 파일 목록을 분리하면 평가 조건 격리는 유지된다.

### 현재 Claude 실행 상태

- 2026-08-20 확인: Claude Code CLI `2.1.217` 설치됨
- 인증 상태: `Expired — log in again`
- 위 상태는 **Hermes가 subprocess로 호출하는 로컬 CLI에만 해당**한다.
- 사용자는 별도의 Claude 앱을 실행 중이라고 확인했다. 앱 세션의 인증·사용 가능 상태를 CLI의
  `Expired`에서 추론하지 않는다.
- 앱이 저장소 파일에 직접 접근할 수 있으면 shared handoff를 읽어 두 번째 코딩 에이전트로
  작업할 수 있다. 직접 접근할 수 없으면 사용자가 handoff와 결과를 전달하는 수동 relay를 쓴다.
- Hermes 자동 호출이 필요한 단계만 CLI 재로그인 전 `blocked_auth_cli`로 기록한다. Claude 앱에서
  실제로 수행한 작업은 앱의 세션/산출물 증거가 있을 때 별도로 기록한다.
