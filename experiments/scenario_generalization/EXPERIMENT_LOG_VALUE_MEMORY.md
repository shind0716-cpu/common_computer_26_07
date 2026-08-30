# 가치관–외부화 수첩 실험일지

> 문서 성격: append-only 개발 일지
> 트랙: 중간보고서 이후 신규 실험
> 최초 작성: 2026-08-24
> 실호출: 0

## 2026-08-24 — 문제 정의와 설계 경계

### 작성 주체

- 사용자: 연구 방향과 실험 재료의 소유자
- Hermes: 설계 정리 및 인계 문서 작성
- 후속 시나리오 작성자: 아직 배정되지 않음

### 새 실험의 목적

고정된 라운드 수와 외부화 수첩 구조 아래에서, 3개 가치관으로 구성된 페르소나 프로필이 카테고리별 시나리오의 사실과 주장을 어떻게 기록·유지·수정·제외하고 후속 발화에 사용하는지 관찰한다.

이 실험은 종료 단계의 담화 전진 실험을 다시 실행하거나 재작성하는 작업이 아니다. 담화 전진 실험은 배경 연구이며, 이번 트랙의 직접 조작 대상은 가치관 프로필과 시나리오 재료다.

### 현재 연구 질문

> 동일한 시나리오 정보와 수첩 구조에서도 초점 가치관이 다른 프로필 사이에 외부화된 수첩의 의미 보존·수정·제외 분포가 달라지는가? 그 차이가 다음 발화와 행동 제안에서도 관찰되는가?

### 고정하기로 한 요소

- 모델 및 모델 버전
- 생성 설정과 출력 한도
- 라운드 수
- 라운드별 정보 공개 시점
- 외부화 수첩의 필드·길이·갱신 규칙
- 발화 프롬프트와 출력 형식
- 컨텍스트 예산
- 에이전트당 가치관 수 3개
- 가치관 제시문의 형식과 길이
- 사실 수와 제시 형식
- 채점 및 사람 검토 절차

### 변화시키려는 요소

- 카테고리
- 카테고리 안의 시나리오
- 세 가치관으로 구성된 프로필
- 같은 시나리오 골격 안에서 바뀌는 핵심 사실

### 중요한 설계 결정

1. 첫 파일럿부터 모든 카테고리를 한꺼번에 섞지 않는다.
2. 카테고리 하나에서 비교 가능성과 코딩 가능성을 먼저 점검한다.
3. 특정 가치관 차이를 보려면 초점 가치만 바꾸고 보조 가치 두 개는 공유한다.
4. 세 가치관을 모두 바꾸면 결과를 `단일 가치관 효과`가 아니라 `프로필 묶음 차이`라고 부른다.
5. 가치관은 특정 찬성·반대 선택지에 고정하지 않는다.
6. 같은 가치관이 사실 조건에 따라 서로 다른 결론을 지지할 수 있어야 한다.
7. 시나리오는 정답을 유도하는 문제가 아니라 가치 충돌과 양보 경계를 드러내는 자극으로 작성한다.
8. 수첩 출력은 모델 내부 기억이나 실제 신념으로 간주하지 않는다.
9. 발화 누락만으로 억제·은폐·방어적 삭제 의도를 추정하지 않는다.
10. 수첩 변화가 발화보다 먼저 나타나도 곧바로 인과 매개라고 부르지 않는다.

### 현재 1차 관찰값

- 정합·충돌·중립 사실의 의미 보존율
- 반대 근거의 의미·출처 무결성
- 수첩 추가·수정 항목의 다음 발화 사용률
- 조건·예외·최소선 형태의 주장 재구성
- 사실 왜곡, 출처 변경, 추적 불가능한 신규 사실

초기 단계에서는 종합점수를 만들지 않는다.

### 작성된 설계 자료

- `VALUE_MEMORY_EXPERIMENT_DRAFT_2026-08-24.md`
- `VALUE_DESIGN_EVIDENCE_TEMPLATE.yaml`
- `README_VALUE_DESIGN_TEMPLATE.md`

### 현재 미결정 사항

- [ ] 첫 파일럿 카테고리
- [ ] 카테고리의 포함·제외 경계
- [ ] 해당 카테고리의 가치관 후보와 근거
- [ ] 세 프로필의 초점 가치 및 공통 보조 가치
- [ ] 공통 사실 골격
- [ ] 시나리오 사례 수
- [ ] 라운드 수의 정확한 값
- [ ] 라운드별 정보 공개 규칙
- [ ] 수첩의 정확한 스키마와 길이 한도
- [ ] 사람 코딩 담당과 검토 방식
- [ ] 개발용 호출 예산과 실행 승인

### 다음 작업 순서

1. 사용자가 카테고리와 가치관 후보를 입력한다.
2. 시나리오 작성자는 입력 근거와 카테고리 경계를 먼저 점검한다.
3. 공통 사실 골격을 작성한다.
4. 최소 두 개의 비교 가능한 시나리오를 작성한다.
5. 각 시나리오에서 제한된 핵심 사실만 바꾼 변형을 만든다.
6. 사실 단위와 가치관 관계 라벨 초안을 별도 표로 작성한다.
7. 독립 검토자가 문면 유도·입장 고정·사실 비대칭을 검토한다.
8. 수정 후에만 개발용 파일럿 실행 여부를 결정한다.

### 현재 상태

`SCENARIO_INPUT_REQUIRED`

카테고리와 가치관 입력이 없으므로 실제 시나리오 내용을 임의로 확정하지 않는다. 후속 작성자는 빈칸을 그럴듯한 연구 사실이나 가치관 목록으로 채우지 않는다.

---

## 후속 append 형식

```markdown
## YYYY-MM-DD HH:MM — <작업명>

- 작성자/세션:
- 사용한 입력 파일과 버전:
- 수행한 작업:
- 생성·수정한 파일:
- 확인한 사실:
- 추론 또는 제안:
- 검증 결과:
- 남은 위험:
- 상태: `수용 | 수정완료 | 대기 | 차단`
- 다음 담당자와 인수 조건:
```

---

## 2026-08-24 17:28 — community_living 첫 실제 시나리오 패킷

- 작성자/세션: 후속 시나리오 작성자(Hermes Agent), 단독·순차 문서 작업
- 사용한 입력 파일과 버전: 사용자 승인 입력 2026-08-24; `README.md`; `DESIGN.md`; `SCHEMA.md` 전체; `WORKLOG.md` 전체; `EXPERIMENT_LOG_VALUE_MEMORY.md`; `VALUE_MEMORY_EXPERIMENT_DRAFT_2026-08-24.md`; `README_VALUE_DESIGN_TEMPLATE.md`; `VALUE_DESIGN_EVIDENCE_TEMPLATE.yaml`; `HANDOFF_VALUE_MEMORY_SCENARIO_AUTHORING_2026-08-24.md`
- 수행한 작업: `community_living` 카테고리 계약, 사용자 승인 가치관 provenance, 공통 가치 세트에서 focal 순서만 바꾼 P1–P3, 두 허구 시나리오와 각 3개 변형, 사실–가치 관계 사전 코딩, 작성자 자체 검토를 작성했다.
- 생성·수정한 파일: `values/VALUE_DESIGN_EVIDENCE_COMMUNITY_LIVING_v0.yaml`; `scenarios/community_living/CATEGORY_CONTRACT.md`; `SCENARIOS_DRAFT.yaml`; `VALUE_RELATION_DRAFT.yaml`; `SCENARIO_REVIEW.md`; 본 실험일지; 시나리오 작성자 인계 문서
- 확인한 사실: 사용자 입력은 카테고리 정의·포함·제외, V1–V3 정의와 양보 조건, P1–P3 focal 우선순위, 두 시나리오와 변형 요구를 모두 포함해 입력 게이트를 통과했다. 외부 이론 근거는 제공되지 않아 evidence 상태를 `pending`으로 유지했다. 모델/API 실호출은 0회다.
- 추론 또는 제안: 변형 축을 생활소음 사례는 `대체 활동 공간의 실제 이용 가능성`, 주차 사례는 `차량 구성 변화가 만드는 일반 주차면 대체 가능성`으로 제한했다. 이 축 선택은 설계자의 개발용 제안이며 검증된 효과가 아니다.
- 자체 수정: quiet-hours boundary 초안의 actor 불일치와 정서 비대칭을 제거했고, parking focal-change에서 공통 차량 사실과 교체 사실이 충돌하던 문면을 차량 방향별 통로 필요로 일반화했다. 상세는 `SCENARIO_REVIEW.md` §6에 기록했다.
- 검증 결과: YAML 실제 파싱, 전역 fact_id 중복, 라운드 참조, profile value ID, variant replaces/with_fact_id, active/release 집합, 가치 관계 라벨·review_status 검사를 실행해 통과했다. `git diff --check`도 통과했다. 검증 명령과 최종 수치는 완료 보고에 기록한다.
- 남은 위험: 독립 검토 미실시; 복합 fact 단위의 원자성; baseline 중립 오독; 아동·교대근무·승하차판·보행 부담의 사전 태도; 주차 사례의 실제 법률·의학·장애 우선권 추론; 실제 프롬프트 서식의 순서 외 차이.
- 상태: `수정완료`
- 다음 담당자와 인수 조건: 독립 검토자가 6개 변형의 문면 유도·단일 축·가치–입장 비고착·법률/의학 경계를 반례 중심으로 검토한다. 승인·확증 사용·실호출은 별도 결정 전 금지한다.

---

## 2026-08-24 — 부모 오케스트레이터의 산출물 재검토와 균형 수정

- 작성자/세션: Hermes 부모 오케스트레이터, 하위 작성 완료 후 실제 파일 재열람
- 사용한 입력 파일과 버전: 하위 작성자가 생성한 가치관 YAML 1개, 시나리오 YAML 2개, 카테고리 계약, 자체 검토서, 본 일지와 인계 답변
- 수행한 작업: 하위 에이전트의 완료 요약을 증거로 간주하지 않고 YAML 3개를 다시 파싱했다. 프로필–가치 ID, 2개 시나리오, 6개 변형, 전역 fact ID, 라운드 공개와 active 집합, replacement 양끝, 6개 관계 블록과 54개 관계 코딩을 독립 재계산했다.
- 확인한 사실: 구조 검증은 오류 0건으로 통과했다. 다만 주차 baseline에서 `SP_F03`은 35m 초과 보행 부담을 말하고 가장 가까운 일반 면은 24m·31m라서, 307호의 넓은 면 필요가 105호보다 지나치게 약해질 수 있었다.
- 수정: 허구 생활조건의 보행 부담 기준을 35m 초과에서 20m 초과로 변경했다. `SCENARIOS_DRAFT.yaml`의 중복 본문 두 곳, `VALUE_RELATION_DRAFT.yaml`의 요약·대안 읽기, `SCENARIO_REVIEW.md`의 검토 문면과 수정 이력을 함께 동기화했다.
- 검증 결과: 독립 구조 검사 `PASS`; scenarios=2, variants=6, facts=20, relation_blocks=6, relation_rows=54, errors=0. 수정 후 YAML 파싱과 참조 무결성 재검증 및 `git diff --check`를 다시 수행한다.
- 남은 위험: 복합 fact 원자성, baseline 명칭의 중립 오독, 아동·교대근무·승하차판·보행 부담의 사전 태도, 실제 장애인 전용면·법률·의학 우선권 오독, 실제 프롬프트 조립에서 focal 순서 외 서식 차이.
- 상태: `수정완료`
- 다음 담당자와 인수 조건: 독립 문면 검토자는 특히 수정된 주차 baseline에서 두 필요가 모두 실질적이면서도 특정 배정이 자동 정답이 되지 않는지 반례를 작성한다. 실호출은 별도 승인 전 금지한다.

### 수정 후 집중 임시 검증

- 검증 성격: 정식 프로젝트 테스트 스위트가 아닌 `focused ad-hoc verification`
- 임시 스크립트: `C:\Users\u\AppData\Local\Temp\hermes-verify-eg67cdvb.py`
- 검증 범위: YAML 3개 파싱, 3프로필–3가치 ID, 2시나리오·6변형, 20 fact 전역 고유성, 4 replacement 양끝·활성 상태, 라운드 공개–active 집합 일치, 6 관계 블록·54 관계 코딩, 수정된 주차 20m/9m/24m/31m 조건, 시나리오 본문의 낡은 35m 문면 부재
- 결과: `AD_HOC_VERIFICATION=PASS`, `ERRORS=none`, `PARKING_BALANCE_ASSERTION=PASS`, exit code 0
- 정리: 임시 스크립트 삭제 확인 `TEMP_CLEANUP=PASS`
- 해석 경계: 위 결과는 변경 YAML의 구조·참조·수정 조건을 검증한다. 정식 스위트 green이나 독립 문면 타당성 승인을 뜻하지 않는다.

---

## 2026-08-24 — 교수 본문 평가와 v0.2 개정

- 작성자/세션: Hermes 부모 오케스트레이터(교수 검토 턴)
- 수행한 작업: 에이전트가 실제로 읽는 라운드별 본문을 6개 변형으로 복원해 정답 유도, 프로필 조작 혼입, 일정·영향 빈칸, 비의도적 의학 추론, 복합 fact 채점 가능성을 평가하고 정본 YAML을 개정했다.
- 핵심 수정: F07 해법 목록 제거·round 1 이동; 가치 목록 순서 고정과 별도 focal instruction; 생활소음 화·수·목 일정과 공동 관찰 `AQ_F09`; 주차 대기 공간 조건과 주 평균 3회 저녁 겹침; 복합 fact의 원자 `scoring_claims`; 변형별 분석 역할 명시.
- 수정한 파일: `SCENARIOS_DRAFT.yaml`; `VALUE_RELATION_DRAFT.yaml`; `VALUE_DESIGN_EVIDENCE_COMMUNITY_LIVING_v0.yaml`; `CATEGORY_CONTRACT.md`; `SCENARIO_REVIEW.md`
- 현재 구조 변화: fact는 20개에서 21개로 증가했고, 생활소음 세 관계 블록에 `AQ_F09 × 3가치` 9개 관계 코딩을 추가했다.
- 상태: `REVISED_PENDING_VERIFICATION`
- 다음 조건: OS 임시 스크립트로 YAML·참조·원자 claim·라운드 공개 집합·금지 문면을 검증하고 통과한 뒤에만 `READY_FOR_INDEPENDENT_REVIEW`로 복귀한다.

### v0.2 수정 후 검증

- 검증 성격: 정식 프로젝트 스위트가 아닌 focused ad-hoc verification 두 차례
- 전체 검증: `V02_AD_HOC_VERIFICATION=PASS`; profiles=3, values=3, scenarios=2, variants=6, facts=21, claims=32, replacements=4, blocks=6, rows=63; focal-order separation·F07 hint removal·atomic claims PASS
- 마지막 semantic notes 수정 후 재진입: `V02_POST_EDIT_REENTRY=PASS`; `F07_BODY_AND_NOTES=PASS`; errors=none
- 정리: 두 임시 `hermes-verify-*.py` 파일 모두 삭제 확인 `TEMP_CLEANUP=PASS`
- Git: `git diff --check` PASS
- 상태: `READY_FOR_INDEPENDENT_REVIEW`
- 해석 경계: 구조·참조·금지 문면 검증만 통과했다. 독립 블라인드 문면 검토와 실험 실행 승인은 남아 있다.

---

## 2026-08-25 — 사용자 피드백 1과 공동체 시나리오 12개 v0.3

- 사용자 피드백: `정당한 경계 설정`을 사전 가치로 강조한 결과, 실험 뒤 관찰해야 할 경계 구성이 가치 프롬프트에 투영되는 오염이 발생했다. 경계의 중요성은 실험 후 결과에서 파악하는 편이 낫다.
- 결정: v0.2의 `legitimate_boundary_setting`과 해결 절차를 예고하는 `adaptive_reassessment`를 새 프로필에서 제거했다. v0.2 패킷은 삭제하지 않되 새 실행 후보에서 제외하고 `superseded_for_value-contamination_review`로 표시했다.
- 새 가치 후보: 개인 생활의 자율, 공용 자원의 동등한 접근, 필요에 따른 배려. 세 가치 모두 경계·절충·요일/시간 배분·시험 운영·재검토를 지시하지 않는다.
- 작성한 12주제: 길고양이 급식, 일반 공용 주차, 층간 생활소음, 쓰레기·재활용, 공용 화단, 빈 텃밭, 버스 노선, 임산부 우선 주차석, 공동 흡연 구역, 택배 보관공간, 공용 세탁실, 주민 공용실.
- 산출물: `scenarios/community_living/SCENARIOS_12_V03_DEVELOPMENT.yaml`; `SCENARIOS_12_V03_REVIEW.md`; `verify_scenarios_12_v03.py`.
- 본문 검토: 각 시나리오의 실제 round 1–3 본문을 읽고 충돌 대상, 단일 변형 축, 외삽 위험을 주제별로 기록했다.
- 검증: `V03_12_SCENARIO_VERIFICATION=PASS`; errors none; scenarios 12; unique topics 12; facts 120/120 unique; variants 36; profiles 3; agent hint scan PASS; value contamination scan PASS; governance gate PASS; `git diff --check` PASS.
- 상태: `DEVELOPMENT_ONLY_PENDING_INDEPENDENT_REVIEW`.
- 해석 경계: 기계 검증과 작성자 본문 검토만 완료했다. 가치 프로필 사용자 승인, 독립 블라인드 문면 검토, scoring claim 사전고정, 실행 승인은 남아 있다.
