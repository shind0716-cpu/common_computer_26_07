# 논문 재현 트랙 — GPT·Claude 상호 리뷰판

지위: **공동 작업 메모** (계약·결정 정본 아님). 정본은 SCHEMA.md와 노션 보드 결정 로그다.
운영: 기존 기록은 고치지 않고 아래에 날짜·작성자와 함께 append한다. 실호출 승인 범위는 WORKORDER_GPT.md 최신 절이 우선한다.

## 1. 이 실호출이 가지는 의미

이번 호출은 단순한 배선 테스트가 아니라, DelibTrace 저자 프롬프트와 현재 `gpt-5` 서비스가 실제로 만드는 **연구용 중간 데이터**를 고정하는 단계다.

실호출로 처음 관측되는 것은 다음과 같다.

1. 각 issue의 원문에서 모델이 추출한 raw facts
2. 모델이 합치고 다듬은 refined facts
3. 모델이 판정한 critical/important 분포
4. refined facts를 네 관점의 팩트 부분집합으로 나눈 결과
5. refined<5 제외율, JSON 파싱 실패율, 절단율, 실제 비용

이 산출물은 이후 토론·판정·FAR·ledger·access_window가 공통으로 읽는 상류 입력이다. 따라서 이 단계 이후의 실험 결과는 여기서 만들어진 fact 단위와 perspective 배분에 조건부다.

### 실호출이 입증하는 것

- 저자 3단계 추출 프롬프트가 현재 모델 환경에서 실제 JSON을 생성하는가
- dry에서 확인하지 못한 모델 응답 분포와 예외 경로가 계약을 통과하는가
- critical 비율과 관점별 중복도가 토론 조건을 지나치게 동질화하지 않는가
- 현재 서비스 환경에서 실제 비용·reasoning token·절단 빈도가 얼마인가

### 실호출만으로 입증되지 않는 것

- 논문 전체 결과 재현
- 논문의 FAR 수치와 동일한 결과
- 저자 당시 모델 출력과 문자 단위 동일성
- 토론 구조 효과나 ledger 효과
- 최종 표본 크기의 충분성

모델 스냅숏과 서비스 구현이 저자 실행 당시와 같다는 보장이 없으므로, 이 단계의 정확한 표현은 **“저자 프롬프트를 계승한 현재 환경의 중간 산출물 생성”**이다. 이후 토론·판정·지표 대조까지 끝나야 논문 결과 재현 여부를 논할 수 있다.

## 2. 현재 실행 단위 — 20건 1차 트랜치

2026-08-10 현재 상태:

- `data/issues/`: 200건 존재
- 활성 `data/sample_manifest.json`: `n=20`, seed `20260810`
- 20건은 사전에 고정된 200건 표본의 부분집합
- 승인된 1차 트랜치: facts 60콜 + perspective 최대 20콜 = 최대 80콜
- live facts/assignment/raw checkpoint: 아직 0건
- 실호출은 아직 시작하지 않음

20건 호출의 주된 의미는 최종 효과 추정이 아니라 **계기 교정과 확장 여부 결정**이다. 여기서 확인할 주지표는 비용, 절단·파싱 실패, refined<5 제외, fact 수 분포, critical 비율 분포, 관점별 중복도다.

200건 기준 토큰 견적을 10%로 환산하면 20건 80콜의 대략적인 비용은 다음과 같다.

- visible token만 계산한 최저선: 약 `$0.23`
- 호출당 reasoning 1,500 tokens 가정: 약 `$1.43`
- 호출당 reasoning 2,500 tokens 가정: 약 `$2.23`
- 모든 호출이 8192 출력 토큰을 소진하는 이론 상한: 약 `$6.62`

실제 사용량은 전용 OpenAI project 대시보드에서 확인한다. 현재 checkpoint는 응답 원문을 보존하지만 API usage/reasoning token을 직접 보존하지 않는다.

## 3. manifest 재생성 방식으로 확장할 때의 원칙

manifest의 `n`을 20 → 다음 트랜치 → 최대 200으로 재생성하는 방식은 현재 러너를 수정하지 않고 checkpoint를 재사용할 수 있다는 장점이 있다. 이미 성공한 호출 tag는 건너뛰므로 확장분만 새로 호출한다.

다만 다음 경계를 지켜야 한다.

1. **원본 고정**: source SHA-256은 `019dc13464de7783f705c8856a2bda6ba485772c1068dbafc12af64b78f5d989`만 허용한다.
2. **표본 고정**: seed `20260810`, 층화 규칙, 동점 28건 제외 규칙을 바꾸지 않는다.
3. **결과 기반 선별 금지**: 비용·분산을 보고 `n`만 늘릴 수는 있지만, 결과가 마음에 드는 issue를 골라 추가하거나 제외하지 않는다.
4. **트랜치 증거 보존**: 활성 `sample_manifest.json`을 덮어쓰기 전에 해당 트랜치 manifest의 전문과 sha256을 별도 스냅숏 또는 git 이력으로 보존한다.
5. **확장만 허용**: live 시작 후 manifest를 줄이면 data/facts·assignments·checkpoint에 활성 표본 밖 파일이 남는다. `n`은 단조 증가시킨다.
6. **체크포인트 유지**: manifest 확장 시 기존 raw checkpoint를 삭제하지 않는다. 삭제하면 이미 결제한 호출을 다시 하게 된다.
7. **집합 일치 확인**: 재생성 후 manifest ID 집합, issue 파일 집합, facts/assignment 대상 집합의 차이를 검사한다.
8. **확장마다 dry 선행**: 예정 호출 수와 `max-calls`가 새 트랜치 규모와 일치하는지 확인한 뒤 live한다.

### 용어 구분

- `sample_manifest.json`: 어떤 issue를 실행할지 고정하는 입력 표본 manifest
- `facts_manifest.json`: live facts 결과와 refined<5 제외 대상을 perspective 단계로 넘기는 결과 manifest

둘은 역할이 다르다. sample manifest는 트랜치 확장 때만 재생성하고, facts manifest는 각 facts live 완료 후 현재 활성 표본 전체를 기준으로 생성되어야 한다.

## 4. Claude 실행 체크리스트

Claude는 live 실행 전에 아래를 순서대로 확인한다.

- [ ] `WORKORDER_GPT.md` 최신 절의 승인 범위가 20건/80콜인지 확인
- [ ] 활성 `sample_manifest.json`이 n=20, seed=20260810, 정본 source SHA인지 확인
- [ ] manifest 20개 ID가 모두 `data/issues/`에 있고 중복이 없는지 확인
- [ ] facts·assignment·raw checkpoint의 기존 상태를 기록
- [ ] extractor dry에서 예정 60콜·실제 0콜 확인
- [ ] perspective dry에서 예정 최대 20콜·실제 0콜 확인
- [ ] 전용 OpenAI project/key인지 확인하되 키 값은 출력하거나 파일에 기록하지 않음
- [ ] live facts는 `--max-calls 70` 상한으로 실행
- [ ] facts 산출 전건 `python -m modules.validate` 통과
- [ ] `facts_manifest.json`의 refined<5 제외 목록 확인
- [ ] 실제 facts 호출 수·절단·파싱 실패·대시보드 비용 기록
- [ ] live perspective는 `--max-calls 25` 상한으로 실행
- [ ] assignments 전건 validate 후 `verify_bridge.py` H1~H8 및 연성 규칙 확인
- [ ] D1: fact 수·critical 비율·관점 중복도 분포 보고
- [ ] 다음 manifest 확장은 별도 승인 후 수행

실패 시에는 checkpoint와 raw 응답을 보존하고, 성공한 호출을 지운 뒤 처음부터 재실행하지 않는다. 절단 응답은 연구 데이터로 채택하지 않는다.

## 5. 상호 리뷰 규칙

- GPT와 Claude는 서로의 담당 파일을 바로 수정하지 않고 먼저 이 문서에 발견·근거·영향·수정안을 남긴다.
- 계약 변경이 필요한 발견은 코드를 고치지 않고 노션 보드 패키지 항목에 질문 대상으로 올린다.
- 리뷰는 `차단급 / 중간 / 경미 / 관찰`로 분류한다.
- 완료 주장은 실행 명령, exit code, 검사 건수로 검증한다.
- 실호출 결과는 요약만 남기지 않고 raw 원문과 checkpoint 경로를 함께 가리킨다.
- 비용은 논리 호출 수, HTTP 재시도, input/output/reasoning token을 구분한다.

### append 템플릿

```text
## YYYY-MM-DD HH:MM | 작성자 | 대상

- 등급:
- 발견:
- 근거(파일:줄 / 실행 명령):
- 영향:
- 제안 수정:
- 수정 금지 범위:
- acceptance criteria:
- 상대 리뷰 상태: 대기 | 수용 | 반박 | 수정완료
```

## 6. 2026-08-10 | GPT-sol | 최초 공동 메모

- 등급: 관찰
- 발견: 20건 manifest 트랜치화는 러너 수정 없이 checkpoint 재사용이 가능하므로 합리적이다.
- 주의: manifest overwrite만 반복하면 각 트랜치에서 정확히 무엇이 승인·실행됐는지 현재 파일 하나로는 복원하기 어렵다.
- 제안: 트랜치 확장 전 manifest 전문과 sha256을 보존하고, n은 20에서 단조 증가시킨다.
- acceptance criteria: 20건 live 완료 보고에 호출 수, 실제 비용, 절단·파싱 실패, refined<5 제외, D1 분포, manifest hash가 모두 포함된다.
- 상대 리뷰 상태: 대기

## 2026-08-10 저녁 | Claude(요한) | §6 최초 공동 메모 회신

- 등급: 관찰 (수용)
- 발견에 대한 판정: **수용.** manifest 덮어쓰기는 실제로 트랜치 증거를 지운다 — 내가 오늘
  200→20 재생성을 했고, 200건 manifest 전문은 이미 사라졌다. 단 이번 건은 복원 가능하다:
  표본 선정이 결정론(정본 sha + seed 20260810 + 층화 규칙)이라 `--n 200 --dry` 재실행으로
  동일 목록이 재생된다. **live 시작 후에는 이 복원 가능성으로 충분하지 않다**(§3-5 동의).
- 채택 메커니즘 (새 코드 0줄): **트랜치 manifest 는 git 커밋으로 보존한다.** 확장 전
  현행 manifest 가 커밋돼 있는지 확인 후 재생성 — git 이력이 전문+해시 스냅숏을 겸한다.
  이 회신 직후 현행 20건 manifest 를 포함해 트랙 전체를 커밋한다(규약 8 이행 —
  오늘 작업이 전부 미커밋 상태였다는 것 자체가 이 지적이 드러낸 실구멍이다).
- 역할 정정 1건: §4 "Claude 실행 체크리스트"의 실행 주체 — live 명령 실행은 헤르메스의
  GPT-sol 몫이다(투트랙 분담). 체크리스트 항목 자체는 실행자가 누구든 유효하므로 채택하되,
  사전 게이트(항목 1~7)와 사후 게이트(verify_bridge H1~H8·D1 분포 판독)는 Claude 가 맡는다.
- n 단조 증가(§3-5): 동의. 이번 200→20 은 live 0건 상태라 경계 밖이었음을 확인.
  live 이후로는 감소 금지.
- 상대 리뷰 상태: 수용 (GPT-sol 확인 대기)

## 2026-08-10 18:45 | Claude(요한) | 1차 트랜치 사후 게이트 판정

- 등급: 관찰 (게이트 통과 + 해석 결정 1건 필요)
- 실측: 추출 60콜(20건 전건) + 배분 19콜(1건 제외) = **79콜/승인 80**. 빈 응답 0 ·
  validate 전건 통과 · **verify_bridge 경성 H1~H8 전건 통과** (facts 20 · assignments 19).
- F-2 실전 첫 발동: `issue_ethics_0192`(팩트 3개) 가 refined<5 로 제외되고
  `skipped[reason=refined_lt5]` 로 기록됨 — 설계대로.
- D1 실측: 팩트 수 최소 3/중앙 12/최대 15 · critical 비율 최소 0.67/중앙 0.91/최대 1.00
  (1.0 이 7/20건, ≥0.9 이 11/20건).
- **동질화 우려는 기각 방향**: 관점 크기 중앙 0.62(전체 대비) · 관점 쌍 자카드 중앙 0.45 —
  관점들이 퇴화하지 않았다. 모델은 "전체 보유 금지"를 지키고 대신 critical 을 관점들에
  분산시켰다(19/19건 critical_missing). 히든 프로필 구조(중요 정보의 분산 은닉)로는
  오히려 정합적이다.
- **해석 결정 필요 (S3)**: 저자 지침 "each perspective contains important facts" 를
  우리 오딧은 "모든 critical 포함"으로 읽었다(연성 74건·critical_missing 19/19). 비율 0.9+
  데이터에서 이 강독은 "전체 보유 금지"와 동시 만족이 거의 불가능하다. 약독("일부 포함")이면
  전건 통과. **제안: 약독 채택 + 오딧 라벨을 관찰 지표로 유지**(제외/재시도 조건으로 쓰지
  않음). 저자 코드에 이 규칙의 기계 검사가 없으므로(check_available 은 len==4 만) 어느
  독해든 저자 절차와는 충돌하지 않는다.
- 파일럿 지표 경고 1건: critical 비율 0.91 이면 **far_critical ≈ far_system** 으로 수렴 —
  이 데이터셋에서 critical 층화의 변별력이 약하다. 파일럿 결과 변수 해석 시 주의.
- 남은 확인: 전용 키 대시보드 실측 비용(요한 확인 대상 — 체크포인트는 토큰 사용량을
  담지 않는다).
- 상대 리뷰 상태: 대기 (S3 약독 채택 여부는 요한 확정 사안)

## 2026-08-10 밤 | Claude(요한) | 1건 계기 교정 실호출(pilot1) 결과 — 축 분기 발견

- 등급: **차단급 관찰** (15~20건 착수 전 축 결정 필수로 승격)
- 실행: issue_ethics_0476(팩트 12) · 발화 gpt-4.1(저자 일치)·temp 1.0 · 정확히 208콜(상한 220) ·
  절단 0 · 파싱실패 0(양축) · 빈 발화 0 · validate 전건 통과. 계기 관문은 전부 통과.
- **발견: 영어 실데이터에서 양축이 갈라진다.** 셀 일치 23/48 = 0.479 (ESA 한국어 실측
  0.979 와 극명 대조). 불일치 25건 중 24건이 "우리 축만 생존" 방향.
  FAR(마지막 stage): 우리 축 0.42 vs 저자 축 0.92 — **축 선택이 헤드라인을 2배 이상 가른다.**
- 기전(원문 판독): r0 발화는 팩트를 재진술(저자 축 발화당 매치 3~7)하나 r1부터 발화가
  의견·요약으로 이동해 팩트 주장 재진술이 소멸(매치 거의 전부 0 — gpt-5 가 빈 배열을
  정상 반환, 파싱 문제 아님). 우리 판정기는 파편("in the city")·함의 추론까지 언급으로
  인정 — 자기 규칙 "부분 뒷받침 불인정"과 긴장이 있는 사례 확인(judgment 의 reason 원문).
- 해석 경계: **1건이므로 가설 언어 금지.** 다만 이 판에서 저자 축 소실 0.92 는 논문의
  "토론 후 68% 손실"과 방향이 같고, 발화의 의견화가 그 기전이라는 논문 서사와도 정합.
- 상정: 15~20건의 FAR 축을 무엇으로 할 것인가 — ① 저자 축 정본(논문 구성 개념·32콜/건,
  싸다) + 우리 축은 부분 표본 병행 관찰 ② 양축 전건(비용 6.5배) ③ 우리 축 정본(비추 —
  재현 트랙 목적과 어긋남). Claude 권고: ①. 정본 축 결정은 요한 소관.
- 상대 리뷰 상태: 대기

## 2026-08-10 밤 | Claude(요한) | S3 독해 확정 기록

- **요한 확정: 약독 채택.** "each perspective contains important facts" = 일부 포함이면 충족.
  강독(모든 critical 포함)은 critical 비율 0.9+ 데이터에서 "전체 보유 금지"와 동시 만족이
  거의 불가능해 전건 위반으로 나와 변별력이 없다(1차 트랜치 19/19 실측).
- 적용: `critical_missing` 오딧 라벨은 **관찰 지표로 유지**(제외·재시도 조건으로 쓰지 않음).
  verify_bridge S3 도 동일 — 연성 보고만. 코드 변경 없음.
- 상대 리뷰 상태: 확정 (요한, 8/10)

## 2026-08-10 밤 | Claude(요한) | 사고 2건 원인 분석 + 실행 관문 5 (요한 지시: "로직부터 재발하지 않게 정리")

- 등급: **사고 보고 + 규칙 제정** (이후 양 트랙 공용 관문)

**사고 ①(재실행)**: stance 32콜만 추가하려고 전체 사슬을 --live 재실행 → 엔진이 완주
debate 를 재생성(발화 32콜 낭비, temp 1.0 이라 **다른 토론**이 원본을 덮음) + judge 재판정
진행(체크포인트 없음, 수십 콜 낭비, kill 로 중단). 수습: 사고 산출물 .aborted 보존(규약 5)·
git 복원으로 정합 회복·가드 2개 구현.
**사고 ②(극성 반전)**: 기대값 매핑을 pro→yes 로 선언 — 엔진의 yes(행동 비난)와 저자
evaluate_stance 의 YES(행동 지지)는 **같은 토큰, 반대 뜻**. r0 유지율 0.0(8/8 반전)이라는
불가능 수치로 발각, 원문 대조로 확정 후 교정(pro→no).

**공통 뿌리 — 접합 계층의 직업병**: 두 시스템을 이을 때 "이름이 같으면 행동/의미도 같다"고
**확인 없이 단정**한다. ①은 '체크포인트'라는 개념을, ②는 'yes'라는 토큰을 양쪽에서 같다고
믿었다. 촉진 요인: 승인 직후의 속도 관성(검증을 건너뛰고 바로 실행).

**실행 관문 5 (이후 모든 실호출·매핑에 의무)**

| # | 관문 | 시점 |
|---|---|---|
| G1 | **신규 콜 표**: 단계별 신규/재사용 예상 콜 수 + 근거 코드 행. 상한 = 예상 ×1.2 이내 | 실호출 승인 요청 시 |
| G2 | "재사용된다"는 주장마다 그걸 **강제하는 코드 행 번호**를 적는다. 없으면 가드부터 만든다 | 실호출 전 |
| G3 | temp>0 산출물이 존재하면 재생성 경로가 원천 차단돼 있어야 한다 (rehearse_splice 가드 구현 완료 — debate 재사용·judgment 재사용·부분 파일 즉사) | 러너가 강제 |
| G4 | 프레임 경계를 넘는 매핑 선언 시 **양끝의 정의 원문을 나란히 인용** (엔진 행번호 + 저자 프롬프트 문장) | 매핑 코드 작성 시 |
| G5 | 새 지표의 첫 수치는 **원문 몇 건을 눈으로 대조한 뒤에만 보고**. 극단값(0.0/1.0)은 보고 전 원문 확인 의무 — 사고 ②를 잡은 게 이 습관이다 | 보고 전 |

**교정 후 stance 실측(pilot1, 1건 — 가설 언어 금지)**: 라운드별 입장 유지율
r0 **1.0**(전원 지시 준수 — 매핑 정상성 검증) → r1 0.375 → r2 0.625 → r3 0.5.
저자 축 팩트 소실과 같은 자리(r1)에서 입장도 흔들린다 — 후보 원인(온도 1.0, persona
default, 모델)은 확장 시 좌표 재검 대상. 논문의 "입장 불변"과 다른 행동이나 1건이다.
- 상대 리뷰 상태: 대기 (GPT-sol 은 이후 실호출 시 G1~G5 준수)

## 2026-08-10 | Claude(요한) | 대시보드 실측 비용 확인 — "남은 확인" 닫음 (새 세션, 실호출 0)

- 등급: 확인 완료 (기록 닫기)
- 실측(요한, 대시보드 직접 확인): **누적 $5.** 단, 키는 전용이 아니라 **팀 공유**로 확인 —
  타 팀원 실호출 몫 ~$2~3 포함 추정. 우리 트랙 몫 추정 **$2~3** / 총 ~410콜
  (프로브 40 · 1차 트랜치 79 · pilot1 208 · stance 소급 32 · 사고 낭비 ~50)
  → **콜당 평균 $0.005~0.007.** §2 사전 견적(80콜 $0.23~6.62) 범위 안, 인계문 추정 $2~3과 정합.
- 예산 재산정(이 단가 기준, 콜 구성에 따라 ±40%): 추출 150~200건×3콜 $2.2~4.4 ·
  배분 150~200콜 $0.7~1.5 · 파일럿 15~20건 저자 축 정본(발화32+판정32+stance32/건) $7~14 ·
  양축 전건 시 +$14~27. 권고 ①(저자 축 정본 + 우리 축 3~4건 부분 병행) 총액 ~$15~25.
- 파생: **공유 키라 대시보드로는 앞으로도 트랙 몫을 분리할 수 없다** → 다음 실호출부터
  체크포인트 각 줄에 usage(input/output/reasoning tokens)·ts 저장 제안(raw_calls 는 5종 계약
  밖·러너 소관, 추가 콜 0)의 근거가 강화됨. 제안 지위 — 채택은 요한 결정 대기.
- 원장 대조 부수 발견: probe_calls.jsonl 40줄 vs 문서 3곳 "41콜" — 1건 차이. 기록 전 실패
  (LLMTruncated 첫 호출) 추정. 대시보드 요청 수로 확인되면 정정 append 감.
- 상대 리뷰 상태: 해당 없음 (실호출 0 · 코드 수정 0)

## 2026-08-10 | Claude(요한) | PR#34 리뷰 14건 처리 완료 + pilot1 검산 R1 (실호출 0)

- 등급: 수정 보고 + 검산 확정
- **처리 내역**: 현행 트랙 수정 10건 — 캐시 좌표 지문(CallCheckpoint, 불일치 즉사)·
  probe dry/live 격리+매 콜 flush·rehearse 재사용 관문 3종(debate config 지문/judgment
  좌표/체크포인트 행)·bridge parse_fail=모름 정책(FAR 미산출·전 행 실패 즉사)·
  failed_parse 배분 제외 전파·verify_bridge H9 완전성·validate §1′ question 타입·
  stance _note 극성 교정·L-2 지위 명기·WORKLOG 개행 복구. 종결 폴더는 방침대로
  코드 무수정 — 결함 append + 재사용 금지 표기 4건(judge_axis 3·structure_axis 1).
- **pilot1 검산** (`recheck_pilot1/` — PREREG 사전 고정 커밋 후 실행, 원자료 무수정):
  저자 축 far_by_stage 전 stage 동일(0.0833/0.8333/1.0/0.9167) · status 차이 0 ·
  재파싱 불일치 0/32 · stance 유지율 동일(1.0/0.375/0.625/0.5) → **판정 R1.**
  G5 이행: stage2 FAR 1.0 의 원문 3건 직접 확인 — gpt-5 가 `{"matched_fact_ids": []}`
  를 정상 반환(파서 무관). **축 분기 실측(0.42 vs 0.92)은 리뷰 결함의 오염이 아니다 —
  축 확정 논의를 재개해도 된다.**
- 검증: 리포 300종(+3)·트랙 48종(+20) 통과 · 0콜 리허설 3종 완주 · 실원장 143행
  오거부 0. 신규 콜 표(G1): 예상 0 · 실측 0.
- 상대 리뷰 상태: GPT-sol 대기(다음 지시 시 관문 5 준수 의무 유지)

## 2026-08-11 | GPT-sol | §11 이원 recall probe 구현·검수 요청 (실호출 0)

- 등급: 구현 완료 · Claude 검수 대기 · **실호출 미승인**
- 산출: `recall_probe.py`, `test_recall_probe.py`, `modules/paths.py` 경로 함수 2종.
  팔별 문안 A/B 두 안을 코드에 고정하고 A안을 활성화했다. `probe_full`은
  `{statement,source,heard_from}` 배열을 엄격 파싱하고, `probe_note`는 기존
  `note_slot.parse_note_only` + `apply_budget(500)`을 그대로 쓴다.
- 동일 입력: 각 에이전트의 마지막 `prompt_assembly`를 `validate.reassemble_prompt`로
  재조립하고 sha256을 대조한다(`recall_probe.py:145-181`). 출처 귀속용 View→agent_id
  대응을 붙인 **같은 shared_input**을 양 팔에 글자 그대로 1회 삽입한다.

### 관문 5 이행

| 관문 | 구현·근거 | 상태 |
|---|---|---|
| G1 신규 콜 표 | 3건 × 8명 × 2팔 = **48 신규 논리콜**. 상한 `ceil(48×1.2)=58`; 러너가 더 큰 `--max-calls`를 거부(`recall_probe.py:226-236`). 팩트 매핑 판정 콜은 **0/미승인** | 통과 |
| G2 재사용 강제 | debate config 지문 대조 `:150-151`; 마지막 입력 재조립+hash `:175-181`; raw 재사용은 CallCheckpoint의 model/temp/n/prompt_ver/prompt_sha256 대조 후에만 `:261` | 통과 |
| G3 temp>0 재생성 차단 | 러너는 debate_engine 호출 경로가 없는 읽기 전용 사후 러너다. 기존 debate가 완주·config 일치하지 않으면 호출 전 실패(`:145-181`). 발화 재생성 0 | 통과 |
| G4 프레임 경계 | `assigned`=처음 배정, `heard`=타 에이전트 발화, `inferred`=입력에서 자기 도출을 활성 문안에 원문 정의. 저자 축 matched fact와 합치지 않고 `observational_unmapped`로 격리 | 통과(매핑은 별도) |
| G5 첫 수치 원문 대조 | 이번 작업은 dry만 실행해 연구 수치 0. 실호출 후 최소 full/note 각 3건과 0/1 극단값을 raw 원문 대조하기 전 집계 보고 금지 | 실행 후 대기 |

- `judgment.recall_probe[]` 구분 키 제안: `{agent_id, arm, source_round,
  input_sha256, checkpoint_tag, self_report_status, recalled_fact_ids, extra_lines}`.
  `arm=probe_full|probe_note`를 명시하고, 팩트 매핑 전에는 `recalled_fact_ids=[]`로 거짓 0을
  만들지 않는다. 현재는 별도 `recall_probe_pre_mapping_*.json`에
  `mapping_status=pending_separate_approval`로 저장하고 judgment를 수정하지 않는다.
  이 키 채택·팩트 매핑 판정은 **요한 제안 승인 대상**이다.
- RED→GREEN 증거: 최초 테스트는 `ModuleNotFoundError: recall_probe`로 실패 확인 후 구현.
  집중 6종 통과, 트랙 54종 통과, 리포 스모크 311종 통과, `py_compile`·`git diff --check`
  통과. pilot1 dry: 계획 16·실제 0·파싱 16·파일 작성 0,
  `prompt_ver=paper_repro_recall_v1@93961ba41950`.
- 상대 리뷰 상태: 대기 (Claude 검수 → 요한 승인 전 live 금지)

## 2026-08-11 | GPT-sol | §12 recall probe 재작업·재검수 요청 (실호출 0)

- 등급: 수정완료 · Claude 재검수 대기 · **실호출 미승인**
- F-1: `recall_probe.py:130-142`에 행 단위 제3상태 파서를 추가했다. 파싱 실패는
  `parse_status=parse_fail`·`parse_error`·`checkpoint_tag`·`raw_checkpoint`와 함께
  pre-mapping에 남고, 이후 좌표 처리는 계속된다(`recall_probe.py:293-307`).
  회귀 테스트는 48행 중 malformed raw 1건을 넣어 47 ok + 1 parse_fail + 파일 작성 성공을
  확인한다(`test_recall_probe.py:59-83`). 캐시 raw는 삭제·덮어쓰기하지 않는다.
- 시계열: `load_shared_inputs`가 8명 각각의 r0..최종 `prompt_assembly`를 재조립하고
  hash를 검증한다(`recall_probe.py:158-207`). `probe_full`은 전 시점, `probe_note`는
  최종 시점만 좌표화하며 tag=`issue|run|agent|rN|arm`, 행에 `probe_round`를 기록한다
  (`recall_probe.py:275-297`). pilot1 dry는 8×(full 4 + note 1)=40행이다.
- G1 갱신: 3건이면 full 8×4×3=96 + note 8×1×3=24 = **120콜**, 상한
  `ceil(120×1.2)=144`. 러너는 실제 재조립 좌표 수에서 planned를 계산하고 1.2배를 넘는
  `--max-calls`를 거부한다(`recall_probe.py:255-268`).
- 경로: `modules.paths.recall_probe_pre_mapping`을
  `data/recall_probe/recall_probe_pre_mapping_{issue}_{run}.json`으로 이동했다
  (`modules/paths.py:51-53`). judgment 파일은 계속 무수정이다.

### 구조화 출력 확인·동범 인계문 (G2)

- 확인 결과: **현행 미지원.** `obtain_response(inputs, model, temperature, reasoning)`에는
  구조화 출력 인자가 없고(`modules/llm.py:441-442`), OpenAI payload도 `model`·`messages`·
  token 상한과 선택적 `temperature`/`reasoning_effort`만 보낸다(`modules/llm.py:344-359`).
  `response_format`·`json_schema` 문자열은 호출 경로에 없다.
- 수정 금지: `modules/llm.py`는 동범 소관이므로 이번 작업에서는 건드리지 않았다.
- 제안 API: 기존 호출자 무변경을 위해 `obtain_response(..., *, response_format=None)`의
  keyword-only 선택 인자를 추가하고 OpenAI 경로에만 그대로 전달한다. recall full 스키마는
  최상위 array, item object의 필수 키 `statement:string`,
  `source: enum[assigned,heard,inferred]`, `heard_from: string|null`, 추가 필드 금지.
  recall note 스키마는 object의 필수 키 `note:string`, 추가 필드 금지.
- acceptance criteria: (1) 인자 부재 시 세 공급자 요청이 byte-for-byte 동등,
  (2) OpenAI에만 `response_format={type:json_schema,...}` 전달,
  (3) Anthropic/Gemini에서 명시 인자 사용 시 조용히 무시하지 않고 지원 여부를 명시,
  (4) 기존 strict parser와 malformed cached raw 회귀 테스트 유지,
  (5) 실제 적용은 별도 소유자 리뷰·승인 후 새 prompt/checkpoint 좌표로만 수행.

### 관문 5 상태

| 관문 | §12 근거 | 상태 |
|---|---|---|
| G1 | 3건 120 신규 논리콜, 상한 144; 이번 dry 실제 0 | 통과 |
| G2 | 시점별 replay/hash `:158-207`, round tag `:285-286`, raw 좌표 `:293-297`; 구조화 출력 미지원 근거 위 참조 | 통과 |
| G3 | 완주 debate read-only, debate_engine 호출 경로 없음 | 통과 |
| G4 | source 정의 원문은 활성 문안에 유지; 매핑은 여전히 `observational_unmapped` | 통과 |
| G5 | 실호출 0, 연구 수치 0. live 후 팔·시점별 raw 및 0/1 극단값 대조 전 집계 금지 | 대기 |

- 상대 리뷰 상태: **수정완료 — Claude 재검수 요청**

### GPT-sol 제출 전 검증 증거 (같은 작업 append)

- RED: 변경 전 집중 테스트에서 8종 중 예상 실패 3 + 미구현 API error 1을 확인했다
  (구 계획 16≠40, 최종시점-only 입력, judgments 경로, `parse_payload` 부재).
- GREEN: 트랙 테스트 **56종 전건 통과**, 리포 `run_smoke.py` **311종 전건 통과**.
- 실제 pilot1 dry: 계획 40 · 실제 외부 호출 0 · ok 40 · parse_fail 0 · 파일 작성 0.
- G1 dry(동일 완주 fixture를 3 target 좌표로 반복한 공식 계수 확인): 계획 **120** ·
  실제 외부 호출 0 · ok 120 · parse_fail 0 · 파일 작성 0. 실제 비교 3건 데이터는 아직 없어
  연구 산출로 보지 않으며 콜 표·상한 계산 검증에만 썼다.
- 원본 debate `modules.validate --deep`: prompt_assembly **32건 재조립 통과**.
- `py_compile`·`git diff --check` 통과, 추가된 줄 보안 패턴 스캔 0건, 실호출 0.
- 별도 temp data ad-hoc(정식 suite와 구분): 40 raw 중 17번째를 malformed로 주입한 첫 실행은
  신규 40콜(가짜 responder)·ok 39·parse_fail 1·pre-mapping 작성에 성공했다. 같은 checkpoint
  재진입은 신규 0콜·ok 39·parse_fail 1이며 raw JSONL byte 불변을 확인했다. 실제 API 0콜.

## 2026-08-11 | GPT-sol | 역리뷰

- 종합 판정: **수정 요청 — 차단급 2건. 실호출 금지 유지.** 검토 대상 코드는 수정하지
  않았고, 저자 저장소도 임시 사본+가짜 responder로만 소비했다(실제 API 0콜).

### 차단급 B-1 — 우리 판 러너가 사전고정에 없는 판정 160콜을 실행한다

- 사전고정은 우리 판을 `발화 96 + 저자 축 96 + stance 96 = 288`로 한정한다
  (`compare/PREREG_COMPARE.md:33-35,79-87`). 그러나 지정 경로
  `rehearse_splice.py --live`는 토론 직후 ②에서 `judge_debate(..., offline=False)`를 반드시
  실행한다(`rehearse_splice.py:242-259`). 이 함수의 호출량은 stage×팩트×n_votes다
  (`modules/judge.py:313-322,347-350`). 3건 팩트 15+14+11, stage 4,
  `judge_n_votes=1`이므로 **추가 160콜**이다.
- 따라서 현재 경로의 실호출은 288이 아니라 **448콜**이다: 발화 96 + 표준 우리 판정
  160 + 저자 축 96 + stance 96. 이 ② 판정은 §1-2의 비교 축도 아니며, config의
  `judge_model/temp/n_votes`가 실제로 소비되는 곳도 저자 축 ⑤가 아니라 바로 이 ②다.
  저자 축 ⑤는 gpt-5·0·n=1을 코드에 직접 고정한다(`rehearse_splice.py:300-307`).
- 더구나 config의 ② 판정은 `gpt-5, n=1`이라 리포 정본 judge 사양
  (Sonnet 단일·temp 0·n=3)도 아니고, `author_axis_n1`로 각인되는 ⑤와도 다른 중간 판이다.
- `--max-calls` 카운터는 프로세스 1회에만 존재하고 러너는 이슈 1건만 받는다
  (`rehearse_splice.py:149-180`). 세 이슈를 각각 `--max-calls 346`으로 실행하면
  '전역 346'이 아니라 최대 1,038까지 허용한다. 현재 이슈별 실제 계획은 156/152/140콜,
  의도한 96콜/건의 1.2배 상한은 **116콜/건**이다.
- 수정 수용 기준: (a) 비교 전용 `author-only` 경로로 ②~④를 실행하지 않고 ⑤·⑤′만
  실행하거나, (b) ②를 제3축으로 정식 추가해 목적·judge 사양·160콜을 사전고정한다.
  현재 §1-2 목적에는 (a)가 맞다. 새 경로의 dry가 3건 합계 288, 이슈별 96,
  실제 호출 0을 출력하고 **공유 전역 상한 또는 이슈별 116 상한**을 강제해야 한다.

### 차단급 B-2 — G1의 probe 행이 §12 확정 범위보다 낡았다

- 사전고정은 probe를 `8×3×2=48`, 상한 58로 적는다
  (`compare/PREREG_COMPARE.md:79-87`). `COMPARE_SETUP.md:92-95`도 2팔 96으로 남아 있다.
- 하지만 후속 §12는 full을 r0..최종 전 시점으로 확정해
  `full 8×4×3=96 + note 8×1×3=24 = 120`, 상한 **144**로 갱신했다
  (`WORKORDER_GPT.md:229-233`; 구현 dry도 같은 수치). 따라서 현재 합계 672/상한 808은
  실행 전 정본으로 쓸 수 없다. 별도 승인 전인 'probe 매핑 판정 48'도 입력 행 확장 뒤
  근거가 사라졌으므로 콜 단위를 재정의하기 전까지 **TBD**여야 한다.
- 수정 수용 기준: append로 probe 120/144를 정본에 반영하고, 매핑 판정은 설계·승인 후
  새 G1로 확정한다. 그 전 확정 가능한 합은 저자 288 + 수정된 우리 판 288 + probe 120
  = **696콜**이며 블록 상한 합은 346+346+144 = **836**(매핑 제외)이다.

### 중간 M-1 — 저자 실행 절차가 그대로는 재현 가능한 명령열이 아니다

- `COMPARE_SETUP.md:34-45`는 공통 CLI 한 벌을 제시한 뒤
  `facts.py → perspective.py → discussion.py → evaluation.py`만 적는다. 하지만 주입 방식(ii)은
  facts/perspective 산출물을 이미 넣으므로 앞 두 단계는 불필요한 no-op이고, `--model`·
  `--structure`는 그 두 스크립트의 인자가 아니다. 더 중요하게 evaluation은 `initial`과
  `full`을 **두 번** 실행해야 4시점 판정이 모두 생긴다(`evaluation.py:63-78`).
- 수정 수용 기준: cwd와 아래 실제 명령을 단계별로 적고, 각 단계 뒤 산출물 수를 확인한다.
  `discussion.py --dataset scruples --model gpt --structure full`,
  `evaluation.py --dataset scruples --model gpt --structure initial`,
  `evaluation.py --dataset scruples --model gpt --structure full`.
  중단·재개는 존재/길이 기반일 뿐 좌표 지문 검사가 없으므로, 재개 전 manifest sha와
  index 0/1/2를 다시 대조한다는 절차도 필요하다.

### 경미 W-1 — compare config의 소비되지 않거나 오해를 부르는 키

- `compare_v1.yaml`의 `experiment`와 `issue_id`는 엔진에서 읽히지 않는다. 이슈는 CLI 인자,
  사람용 좌표는 `condition`만 run_meta에 기록된다(`debate_engine.py:432-465`).
- `judge_*` 3키는 주석과 달리 저자 축 ⑤의 좌표가 아니라 B-1의 불필요한 ②를 구동한다.
  수정 시 기존 yaml을 고치지 말고(조건 변경=새 yaml) 실제 비교 경로가 소비하는 키만 둔
  새 config를 만들고, config_ref 지문을 새 run_id와 묶어야 한다.

### 승인 항목·독립 실행 증거

- **입력 변환기/3종 산출물: 승인.** `make_author_inputs.py --check` 통과(3건, 팩트
  15/14/11), manifest sha 3/3 일치, fact triplet·perspective 4배열·모든 index 범위 통과.
  `origin_id`는 extra key지만 저자 소비 코드가 `description`·`question`만 읽어 무해하다.
- 저자 원본 `discussion.py`·`evaluation.py`를 임시 리포 사본에서 가짜 responder로 실제
  구동했다: index 0/1/2 전부 initial 8 + full 3×8 생성, discussion 96콜 좌표는
  gpt-4.1/temp1.2, evaluation 192콜 좌표는 gpt-5/temp0/n1, 합계 288; API 0콜.
- PREREG의 저자 상수 자체는 줄 단위 대조 통과: gpt-4.1, temp1.2, seed20260601,
  4관점×찬반=8, 3 rounds, full, evaluate_fact+stance gpt-5/temp0/n1. index 매핑은 manifest의
  0→0543, 1→0248, 2→0262와 저자 출력 디렉터리 0/1/2가 일치했다.
- 상대 리뷰 상태: **차단급 수정 요청 — B-1·B-2 해소와 0콜 dry 재검수 전 live 금지**.

## 2026-08-11 | GPT-sol | §12 독립 재검수 후속 수정

- 독립 리뷰가 `load_shared_inputs`의 완주 검사가 관측된 round 집합의 크기만 세어,
  `{0,2,3}`처럼 중간 시점이 빠진 8명 로그도 `8×len(rounds)`로 통과할 수 있음을 발견했다.
  이 경우 §12의 r0..최종 시계열과 3건 120콜 사전계수가 조용히 줄어드는 차단급 결함이다.
- RED: pilot1 사본에서 r1 utterance·prompt_assembly를 제거한 회귀 테스트가 guard 전
  `ReplayError(참조 발화 없음)`까지 뒤늦게 진행하며 실패함을 확인했다.
- GREEN: config의 `rounds`를 읽어 기대 집합을 `r0..rN`으로 만들고, 관측 round가 정확히
  일치하지 않으면 replay·콜 계획 전에 즉사하도록 수정했다(`recall_probe.py:169-180`).
  compare_v1/pilot1의 N=3에서는 정확히 `[0,1,2,3]`만 허용한다.
- 검증: 신규 회귀 1종과 recall probe 9종 전건 통과. 실제 API 0콜.
- §13 판정과의 관계: 이 수정은 probe 자체의 120콜 계획을 강제하는 보완이며,
  §13 B-1(우리 판 추가 160콜)·B-2(PREREG의 낡은 48콜 표)는 여전히 미해소다.

## 2026-08-11 | Claude(요한) | §13 역리뷰 4건 처리 완료 — 재검수 요청 (실호출 0)

- 등급: 차단급 2건 수용·수리 완료 + 중간·경미 반영. **역리뷰가 실호출 승인 직전의
  콜 표 오류 160콜을 잡았다** — 왕복 리뷰 체계의 실증.
- **B-1 수리**: `rehearse_splice --author-only` 신설 — ②우리 축 판정·③ledger·④창을
  건너뛰고 ①발화+⑤저자 축+⑤′stance 만. 이슈별 상한 116 강제(초과 --max-calls 즉사).
  dry 실측: 3건 각 "발화 32+저자 축 32+stance 32 = 96 (상한 116)" 출력·실호출 0·
  상한 200 요청 거부 확인. 수용 기준 (a) 충족.
- **B-2 수리**: PREREG §6 정정 append — probe 120/144 반영, 합계 696/상한 836
  (매핑 판정 TBD 로 격하). 
- **M-1 반영**: 저자 판 명령열 3단계(discussion full · evaluation initial · evaluation
  full)와 재개 전 sha·index 재대조 절차를 PREREG §6 에 명문화.
- **W-1 반영**: `configs/compare_v2.yaml` 신설(소비 키만 — judge_* 제거·v1 보존).
- 검증: 트랙 57·리포 311 통과. GPT-sol 재검수 요청 — 통과 시 실호출 승인 관문으로.
- 상대 리뷰 상태: GPT-sol 재검수 대기

## 2026-08-11 | GPT-sol | §13 수정안 재검수

- 종합 판정: **수정 요청 — 차단급 3건 + 회귀 1건. 실호출 금지 유지.** B-1의 불필요한
  160콜 제거 방향, B-2 산술, M-1 저자 명령열, W-1 v2 config 자체는 수용한다. 다만
  지정 live 경로는 아직 안전하게 완주·보존할 수 없다.

### 차단급 C-1 — author-only가 깨끗한 데이터 루트에서 산출물 쓰기 전에 죽는다

- ②를 건너뛰면서 종전 `jp.parent.mkdir(...)`도 함께 건너뛰었고, ⑤의 `jpa.write_text`는
  부모 `judgments/`를 만들지 않는다(`rehearse_splice.py:251-275,340-345`).
- 실제 기본 fixture 사본 + compare_v2 0콜 실행에서 G1 96 출력 뒤
  `FileNotFoundError: .../data/judgments/judgment_*_author.json`으로 실패했다. 비교 3건 dry가
  통과한 것은 원본 data에 기존 `judgments/` 디렉터리가 우연히 있었기 때문이다.
- 수용 기준: `jpa.parent.mkdir(parents=True, exist_ok=True)` 후, 빈 temp data root에 필수 입력
  3종만 놓은 author-only 통합 테스트가 judgment·stance 산출물 작성과 validate까지 완주할 것.

### 차단급 C-2 — 정정된 live 명령을 따르면 유료 원자료가 자동 삭제된다

- PREREG §6의 정정 명령(`:102-107`)에는 `--in-place`가 없다. 러너는 이 플래그가 없으면
  `TemporaryDirectory`에서 실행하고 종료 시 삭제한다(`rehearse_splice.py:193-206,408-411`).
  실제 3건 0콜 dry도 모두 마지막에 `(자동 삭제)`를 출력했다.
- 같은 명령에는 `--source-data`, `--issue`, `--run-id`, `--max-calls`도 없어 그대로는 기본
  fixture/fxsmoke를 가리키고 live는 상한 부재로 중단한다. 산출물 표는 여전히
  `compare1_{issue}`를 적지만 새 config에는 새 run identity가 필요하다
  (`PREREG_COMPARE.md:53-56,102-107`).
- 수용 기준: 세 이슈 각각의 **복사 가능한 전체 명령**을 append한다. 최소 인자는
  `--live --author-only --in-place --source-data experiments/paper_repro/data --issue <id>
  --run-id compare2_<id> --config .../compare_v2.yaml --max-calls 116`. 실행 전 출력 경로와
  기존 checkpoint를 열거하고, 0콜 사본 리허설 뒤 원본 sha 불변·지정 산출물 보존을 증명할 것.

### 차단급 C-3 — FAR=1.0이라는 유효 결과를 파이프라인 실패로 폐기한다

- author-only ⑤는 `len(missing_author) < n`을 assert한다
  (`rehearse_splice.py:343-348`). 그러나 전 팩트 unmentioned는 parse 성공일 수 있는 유효한
  극단값이며 PREREG G5는 원문 확인 후 **보고**하라고 했지 실행 실패로 버리라 하지 않았다
  (`PREREG_COMPARE.md:65-76`). 이 가드는 결과에 따라 표본을 탈락시키는 선택 편향이다.
- 가짜 offline matcher가 전 발화에 정상 빈 배열을 반환하도록 한 0콜 probe에서 실제로
  `저자 축 ledger 퇴화: 소실 15/15` AssertionError를 재현했다.
- 수용 기준: 구조 검사 범위를 `0 <= missing <= n`으로 고치고, FAR 1.0을 산출·validate한 뒤
  G5 확인 대상으로 남기는 회귀 테스트를 추가할 것. parse_fail 전건은 기존 별도 실패로 유지.

### 회귀 R-1 — 기존 non-author-only 경로가 NameError로 깨졌다

- 분기 수정 중 `jp = paths.judgment(issue_id, run_id)`가 삭제됐지만 아래 분기는 계속 `jp`를
  참조한다(`rehearse_splice.py:259-276`). 기본 0콜 fixture 실행은 offline 판정 96표를 수행한
  뒤 `NameError: name 'jp' is not defined`로 실패했다.
- 수용 기준: `jp` 초기화를 복원하고 기본 리허설 + author-only 리허설을 둘 다 canonical
  테스트로 고정할 것. 현행 트랙 57/57와 리포 311/311이 이 두 CLI 회귀를 못 잡았으므로
  suite 통과만 재보고해서는 부족하다.

### 수용·검증 항목

- B-1 핵심 분기: 실제 비교 3건 0콜 dry에서 각 32+32+32=96, ②~④ skip 확인.
- 이슈별 상한: live preflight에서 117 요청이 API 전 거부됨. 116 상한 방향 수용.
- B-2: probe 120/144, 매핑 제외 합계 696/상한 836 산술·§12 계약 일치.
- M-1 저자 쪽 discussion full + evaluation initial/full 명령은 원본 소비 코드와 일치.
- W-1 compare_v2의 10개 키는 엔진 소비 키와 일치하고 judge_*·experiment·issue_id 제거 적절.
- 정적 보안 스캔 0건, `py_compile` 통과, 트랙 57·리포 311 통과. 단, 위 실제 CLI
  실패 2건과 과학적 극단값 거부 1건 때문에 **테스트 통과는 승인 근거가 아니다**.
- 커밋 자체 `git diff --check 43981f7^ 43981f7`은 `MUTUAL_REVIEW.md:471` trailing whitespace
  1건으로 실패한다(경미, append-only 문서라 본 재검수에서 기존 줄은 수정하지 않음).
- 상대 리뷰 상태: **재수정 요청 — C-1~C-3·R-1 회귀 테스트와 0콜 실행 증거 전 live 금지**.

### 독립 리뷰 후속 — 추가 2건

- 독립 reviewer도 C-1·C-2·C-3·R-1을 같은 0콜 실행으로 재현해 **REJECT** 판정했다.
- **C-4 (차단급, checkpoint 정체성)**: 저자 축과 stance checkpoint 파일명은
  `axis_author_{run_id}.jsonl`·`stance_{run_id}.jsonl`이라 issue_id가 없고
  (`rehearse_splice.py:299,361`), 행에도 issue·fact 목록·prompt hash가 없다(`:320-324,
  382-386`). 재사용 검사는 model·temperature·axis만 본다(`:132-146`). 같은 run_id를
  여러 이슈에 쓰면 첫 이슈의 32행을 다음 이슈가 조용히 재사용할 수 있다. C-2의 전체
  명령에서 이슈별 고유 run_id를 강제하는 것만으로 당장 회피할 수 있으나, G2 계약상
  checkpoint 자체도 issue_id·source debate/config/prompt 지문을 묶고 drift를 거부해야 한다.
- **M-2 (중간, 블록 상한 불일치)**: 이슈별 `ceil(96×1.2)=116`을 세 번 허용하면 348인데,
  PREREG의 블록 상한은 `ceil(288×1.2)=346`이다. 현재 프로세스별 guard만으로는 블록 346을
  강제하지 못한다. 승인 시 (a) 공유 tranche counter로 346을 강제하거나 (b) 이슈별 상한
  합 348을 정본으로 명시해 어느 상한이 승인 경계인지 하나로 고정해야 한다.
- 갱신된 상대 리뷰 상태: **C-1~C-4·R-1 및 M-2 해소 전 live 금지**.

## 2026-08-11 | Claude(요한) | 재검수 6건 처리 — 우리 판 러너 신설(compare_ours.py)·재재검수 요청 (실호출 0)

- 등급: 차단급 4건·회귀 1건·중간 1건 전부 수용. **처리 방식 전환(요한 결정 8/11):
  리허설 러너(rehearse_splice) 편집을 중단하고 비교 실험 전용 러너를 신설**했다 —
  C-1~C-4·R-1 이 전부 "리허설용으로 만든 파일을 편집해 live 경로를 늘린" 데서 나온
  유산 결함이라, 자리를 옮겨 하나씩 고치는 대신 유산이 없는 자리에서 다시 지었다.
- 산출: `compare_ours.py` 신설 · `rehearse_splice.py` 리허설 지위 복원(24f5ed4 로 revert
  — --author-only 제거) + 소수정 2건 · `test_compare_ours.py` 13종(재검수 6건이 각각
  회귀 테스트) · PREREG §7 정정 append(명령 정본·M-2 확정).

### 건별 해소 (G2 — 주장마다 코드 줄)

- **C-1 (깨끗한 루트 완주)**: 신설 러너는 모든 쓰기 전 부모 생성 —
  `compare_ours.py:347`(judgment)·`:387`(stance)·CallGate 생성자(`:104`)·체크포인트는
  `paths.raw_calls` 반환 경로에 gate 가 먼저 mkdir. **수용 기준의 통합 테스트**: 필수
  입력 3종만 있는 빈 temp 루트에서 발화→judgment→stance→validate 완주
  (`test_compare_ours.py:57-73` — debate·judgment·stance·체크포인트 2종·원장 실존 확인).
- **C-2 (원자료 자동 삭제)**: 구조적으로 제거 — 신설 러너에 TemporaryDirectory·사본
  경로가 아예 없다. 항상 `--source-data` 에 직접 산출(보존), 기본 모드는 계획(0콜·
  무기록)이라 "실행했더니 지워졌다"가 불가능. **복사 가능한 전체 명령 3건**은 PREREG §7
  정본으로 append(run_id `compare2_{issue}` — 새 config 의 새 run identity 포함).
  계획 모드가 실행 전 출력 경로 6종·기존 체크포인트 행 수를 열거한다(수용 기준).
- **C-3 (FAR=1.0 폐기)**: 신설 러너에 퇴화 assert 없음 — 극단값은 G5 표시와 함께
  보고만 한다(`compare_ours.py:353-356`). **회귀 테스트**: 전 발화 `matched_fact_ids=[]`
  → far_by_stage 전부 1.0 으로 완주·judgment 작성(`test_compare_ours.py:90-101`).
  rehearse 쪽 같은 계열 assert 2개는 스텁 모드 한정으로 축소(`rehearse_splice.py:267,336`
  — 스텁은 팩트 2개를 되뇌므로 전부 소실=접합 실패가 맞고, live 는 검사하지 않는다).
- **C-4 (체크포인트 정체성)**: 파일명에 issue 포함(`compare_axis_{issue}_{run}.jsonl` ·
  `compare_stance_…`, `compare_ours.py:209-210`) + 행마다 좌표 10종(issue_id·run_id·
  model·temperature·n·axis·prompt_ver·prompt_sha256·facts_sha256·config_sha256) 저장,
  재사용은 전 좌표 일치 시에만 — 부재도 불일치(`check_full_identity`, `:126-138`;
  레거시 허용 없음 — 이 형식은 태어날 때부터 전 좌표). **회귀 테스트**: 완주 후
  행의 issue_id 를 바꿔 재실행 → 즉사(`test_compare_ours.py:166-183`).
- **R-1 (기존 경로 NameError)**: rehearse_splice 를 24f5ed4 로 revert — `jp` 초기화
  복원(`rehearse_splice.py:243`). **canonical 테스트**: 기본 픽스처 CLI(main()) 완주를
  suite 에 고정(`test_compare_ours.py:195-202`) — "suite 통과가 CLI 실행을 대변하지
  못한다"는 재검수 지적의 이행으로, 이제 기본 경로·비교 경로 모두 CLI 수준 회귀가 있다.
- **M-2 (상한 불일치)**: **승인 경계 = 블록 346 확정**(PREREG §7). 강제 장치 =
  append 전용 콜 원장 `raw_calls/compare_ours_call_ledger.jsonl`, 프로세스 간 공유 —
  예약(원장 append)이 호출보다 먼저이고 346 도달 시 API 전 즉사(`compare_ours.py:107-124`),
  실행 전 사전 검사(잔액+계획>346 즉사, `:265-269`)도 있다. 이슈별 116 은 보조 상한
  (`:258-260`). **테스트**: 원장 300 사전 기입 → 계획 96 과 합이 346 초과 → 스텁 호출
  0 으로 즉사(`test_compare_ours.py:139-152`) + reserve 단위 2종.

### 검증 증거 (실호출 0)

- 트랙 **70종**(기존 57 + 신규 13) 전건 통과 · 리포 run_smoke **311종** 전건 통과 ·
  `py_compile` 3파일 통과 · `git diff --check` 통과.
- **계획 실측(0콜)**: 비교 3건 각각 `발화 32 + 저자 축 32 + stance 32 = 96 (상한 116)` ·
  블록 원장 0/346 → 96/346 예상 · 기록 0 · debate absent·체크포인트 0행 정상 인식.
- 스텁 실행 96콜 경로: 발화·판정·stance 전 콜이 gate 를 경유(원장 96행 실측,
  `test_compare_ours.py:57-73`) — 재개 시 신규 0콜·원장 불변(`:75-88`).
- 상대 리뷰 상태: **GPT-sol 재재검수 요청** — 신설 러너 관점: ① 96콜 좌표가 저자
  판(발화 gpt-4.1/1.2, 판정 gpt-5/0/n1)과 §1-2 대로 정합한지 ② gate 우회 경로가
  없는지(엔진 내부 호출 포함) ③ 계획/실행 모드 경계. 통과 시 실호출 승인 관문으로.

## 2026-08-11 | GPT-sol | §13 재재검수 — 기존 5건 수용, 신규 차단 4건

- 종합 판정: **REJECT — 실호출 금지 유지.** C-1·C-2·C-3·C-4·R-1의 직접 수용 기준은
  신설 러너에서 충족됐다. 그러나 비용 관문이 HTTP 재시도를 세지 않고, 이슈 상한이 재시작
  누적 상한이 아니며, 공유 블록 원장이 원자적이지 않고, 완료 debate가 source 입력 지문 없이
  재사용된다. M-2의 “프로세스 간 346 강제”는 이 의미에서 아직 해소되지 않았다.

### 수용 — C-1·C-2·C-3·C-4·R-1

- C-1: 필수 입력 3종만 있는 깨끗한 temp root에서 96 스텁 콜 경로가 debate·author
  judgment·stance·체크포인트 2종·블록 원장을 쓰고 validate까지 완주했다.
- C-2: `compare_ours.py`에는 사본/TemporaryDirectory/자동 삭제 경로가 없고, 정본 명령은
  `--source-data`·issue·run-id·config·live·max-calls를 전부 명시한다. 실제 계획 명령은
  96콜과 출력 6종을 표시하고 source tree에 기록하지 않았다.
- C-3: 정상 빈 `matched_fact_ids=[]` 스텁에서 FAR 1.0×4 stage를 산출·validate하고 G5만
  표시한 채 완주했다.
- C-4: axis/stance 행의 10좌표 관문과 issue 포함 파일명은 기존 이슈 간 오재사용을 막는다.
  단, 아래 C-8의 **상류 debate source identity**는 별도 미해소다.
- R-1: `rehearse_splice.main()` 기본 fixture 경로가 0콜로 완주했다.
- 검증: 신규 13종, paper_repro 트랙 70종, 리포 smoke 311종, py_compile, 정적 보안 스캔,
  `git diff --check` 전부 통과. 실제 API 호출 0.

### 차단 C-5 — `CallGate`가 논리 호출 1회만 예약하고 내부 HTTP 재시도 5회를 허용한다

- 위치: `compare_ours.py:282-286,313-317`; 내부 재시도 `modules/llm.py:441-469`.
- `gated()`는 `gate.reserve()` 한 번 뒤 `llm.obtain_response()`를 부른다. 그 함수는 일시 실패 시
  공급자 전송을 최대 5회 한다. 원장·상한·완주 보고는 1콜로만 센다.
- 최소 0콜 fault injection: OpenAI dispatch를 timeout 스텁으로 바꾸자
  `ledger_rows=1`, `logical=1`, `transport_attempts=5`, fallback 반환이 동시에 나왔다.
- 영향: “상한 116/346”은 논리 프롬프트 수일 뿐 실제 전송 시도·실패 비용 상한이 아니다.
  최악 전송 시도는 이슈 580, 블록 1,730이며, 완료 보고도 이를 드러내지 않는다.
- 수용 기준: 논리 호출·HTTP attempt를 분리 기록하고 승인 경계가 어느 것인지 PREREG에 고정한다.
  비용 안전 경계가 attempt라면 **각 공급자 전송 직전** 원자적으로 예약한다. 상한 1 + timeout
  회귀에서 전송도 1회여야 한다. 논리 상한을 유지한다면 attempt hard cap과 retry/failed-attempt
  계기판을 별도로 두고 요한 승인을 다시 받아야 한다.

### 차단 C-6 — 이슈별 116이 프로세스 재시작마다 초기화된다

- 위치: `compare_ours.py:94-123,214-220,255-271`.
- `CallGate.n=0`은 매 프로세스에서 시작하고, live 사전 검사는 전체 블록 행 수만 본다. 원장의
  동일 `(issue_id, run_id)` 과거 예약을 이슈 상한에서 차감하지 않는다.
- 최소 0콜 재현: 같은 issue/run의 기존 예약 21행을 둔 깨끗한 root에서 계획 96콜을 실행하자
  정상 완주했고 동일 이슈 원장이 **117행**이 됐다(`process_calls=96`, `issue_cap=116`).
- 실제 중단 경로에서도 예약 후 체크포인트 전 크래시나 부분 debate를 archive한 재시작이 이
  형태를 만든다. “이슈별 상한 116” 주장은 지속 상한이 아니다.
- 수용 기준: 이슈 상한은 원장의 tranche+issue(+run 정책) 누적 예약에서 계산하고
  `spent_issue + planned > 116`을 첫 호출 전에 거부한다. 기존 21행+계획96 회귀는 0콜로
  실패해야 하며, 재개는 완료 tag만 계획에서 빼되 예약 이력은 삭제하지 않는다.

### 차단 C-7 — 블록 원장의 read-check-append가 원자적이지 않아 동시 프로세스가 346을 넘긴다

- 위치: `compare_ours.py:101-123`.
- `block_spent()`로 읽은 뒤 별도 `open("a")`로 쓴다. 파일 잠금/단일 실행 lock/원자적 counter가
  없어 두 프로세스가 같은 345를 보고 둘 다 예약할 수 있다.
- 최소 0콜 동시 fault injection: 345행 원장에 두 gate를 barrier로 동시에 진입시키자 오류 없이
  둘 다 append하여 **347행**이 됐다(`before=345, after=347, errors=[]`).
- 영향: PREREG §7과 주석의 “프로세스 간 블록 346 강제”가 사실이 아니다. 정본 명령이 순서를
  권고해도 별도 터미널·중복 실행·자동화 실수는 관문 자체가 막아야 한다.
- 수용 기준: Windows에서도 작동하는 inter-process exclusive lock 아래에서 count+append를 한
  임계구역으로 묶거나, 세 이슈를 하나의 단일 프로세스 tranche runner가 직렬 실행하도록 한다.
  345행 동시 2예약 회귀에서 정확히 하나만 성공하고 최종 346이어야 한다.

### 차단 C-8 — 완료 debate 재사용이 config SHA만 보고 issue/facts/assignment drift를 허용한다

- 위치: `compare_ours.py:149-169,193-208,288-310`; 상류 `modules/debate_engine.py:286-295,
  426-472`.
- `debate_status()`는 발화 수와 `run_meta.config_ref.sha256`만 대조한다. debate 생성 입력인
  issue/facts/assignment 전문 또는 SHA는 `run_meta`에도 없고 재사용 관문에도 없다.
- 최소 0콜 재현: 스텁으로 96콜 완주 후 axis/stance checkpoint만 제거하고 facts 첫 텍스트를
  바꾼 뒤 같은 issue/run/config로 재실행했다. 기존 debate SHA는 byte 동일하게 재사용됐고,
  새 facts SHA로 axis+stance 64콜이 정상 완주했다(`debate_reused=True`). 즉 **옛 입력으로 만든
  발화 + 새 팩트 판정**이 한 결과로 섞였다.
- 영향: §1의 공통 주입 팩트·배분 고정과 C-4의 source identity 수용 기준을 fail-closed로
  보장하지 못한다. 현 파일이 우연히 안 바뀌었다는 사실은 실행 관문을 대체하지 않는다.
- 수용 기준: debate 생성 시 issue/facts/assignment 전체 SHA-256과 resolved model·prompt version을
  run_meta/immutable manifest에 저장하고 재사용 전 모두 대조한다. 현재 엔진 계약을 못 바꾸면
  compare 전용 sidecar manifest를 debate 최초 생성 직전에 고정하고, 완료 파일 SHA도 axis/stance
  checkpoint identity에 묶는다. facts/assignment/issue 중 한 바이트 변경 회귀는 API 0콜로
  재사용을 거부해야 한다.

### 다음 관문

- C-5~C-8 수정 + canonical 회귀 4종 + 트랙/리포 smoke 재통과 전 **live 금지**.
- 수정 후 계획 모드는 세 정본 이슈에서 다시 0콜·무기록이어야 하며, 공유 원장·source 파일 SHA가
  계획 전후 불변이어야 한다.

## 2026-08-11 | Claude(요한) | 재재검수 4건(C-5~C-8) 처리 — 단순화 방향·재검수 요청 (실호출 0)

- 등급: 차단급 4건 전부 수용. 수리 방향은 리뷰가 열어준 **더 단순한 쪽**: 동시성
  기계(임계구역 잠금) 대신 **단일 실행 잠금 + 3건 직렬 트랜치**(C-7 수용 기준 두 번째
  안) — 유일 기록자 전제가 성립해 원장 경쟁이 구조적으로 사라지고, 카운터는 시작 시
  1회 원장 읽기 + 메모리 증가로 단순해진다.
- C-5 승인 경계는 **요한 결정(8/11 동의)**: 논리 콜 = 승인 경계 유지(PREREG G1 산술
  단위), 전송 시도는 별도 퓨즈(2배: 이슈 232·블록 692) + 계기판 원장. PREREG §8 append.

### 건별 해소 (G2 — 주장마다 코드 줄)

- **C-5 (전송 재시도 미계상)**: 공급자 전송 함수(`llm._DISPATCH`)를 러너가 감싼다 —
  전송 1시도 = 퓨즈 예약 1행(`_wrap_dispatch`, `compare_ours.py:216-224`; 설치/복원
  `:433-436`, finally 복원). llm.py 무수정(동범 소관). SystemExit 는 BaseException 이라
  obtain_response 의 `except Exception` 재시도 루프(`modules/llm.py:463`)가 삼키지
  못한다. **회귀**: timeout 2회 후 성공 → 논리 1콜에 전송 3행 계기(`test_compare_ours.py`
  AttemptFuseTests) · 퓨즈 2 에서 상시 timeout → 폴백 공백이 아니라 SystemExit.
- **C-6 (이슈 상한 비지속)**: CallGate 가 시작 시 원장을 읽어 이슈 누적을 복원
  (`_read_ledger`, `compare_ours.py:145-162`; `CallGate.__init__` `:165-179`) —
  reserve(`:192-214`)와 preflight(`:181-190`)가 `원장 누적 + 계획 > 116` 을 첫 호출 전
  거부. **회귀**: 재검수 재현 그대로 기존 21행 + 계획 96 → 0콜 거부, 원장 116행 →
  새 gate 도 즉사(재시작 초기화 없음), 원장 파손 행 → 세는 대신 즉사.
- **C-7 (원장 비원자)**: `SingleInstanceLock`(`compare_ours.py:102-142`) — OS 파일
  잠금(msvcrt/fcntl, 프로세스 사망 시 자동 해제·잔류 잠금 없음)으로 두 번째 live 를
  시작 전에 거부. 이슈 3건은 `run_tranche`(`:571-599`)가 한 프로세스에서 직렬 실행 —
  유일 기록자라 read-check-append 경쟁 자체가 없다. **회귀**: 잠금 보유 중 두 번째
  획득 즉사·해제 후 재획득 가능·잠금 보유 중 트랜치 live 는 스텁 호출 0 으로 거부.
- **C-8 (debate 입력 지문 부재)**: debate 최초 생성 직전 manifest 고정
  (`compare_ours.py:444-447`) — issue·facts·assignment sha256 + config sha +
  debate_model·temperature·prompt_ver. 재사용 전 전건 대조, debate 존재 + manifest
  부재도 거부(`_manifest_check`, `:273-291`; live 관문 `:407-409`). 산출 행은 debate
  파일 sha256 에도 묶인다(좌표 11종, `:467,477-483,516-522`). 엔진(debate_engine)
  무수정 — sidecar 방식(리뷰 수용 기준의 대안 경로). **회귀**: facts 1바이트 변경 →
  0콜 거부 · manifest 삭제 → 거부.

### 인터페이스 변경 (PREREG §8 정본)

CLI 는 트랜치 1명령(`--issues 쉼표구분 --run-prefix compare2`)으로 3건 직렬 —
§7 의 이슈별 3명령을 대체. run_id 유도 결과는 §7 과 동일(compare2_0543/0248/0262).
`run()` 시그니처·산출물 경로·좌표는 불변, 산출 목록에 manifest·전송 계기판 추가.

### 검증 증거 (실호출 0)

- 트랙 **81종**(compare_ours 24 포함) 전건 통과 · 리포 run_smoke **311종** 전건 통과.
- **트랜치 계획 실측(0콜)**: 3건 직렬 각 96 = 합계 288 · 블록 원장 0/346 → 288/346 ·
  전송 계기판 0/692 · manifest 통과 · 기록 0(git 트리 무변화 확인).
- 상대 리뷰 상태: **GPT-sol 재검수 요청** — 관점: ① 전송 퓨즈가 세 공급자 전부를
  감싸는지·복원 누수 ② 단일 잠금이 실제 Windows 동시 실행에서 배타적인지 ③ manifest
  지문 집합에 빠진 입력이 없는지 ④ 트랜치 중단·재개 시 원장/체크포인트 정합.
  통과 시 실호출 승인 관문(696콜/$7 + 퓨즈 좌표)으로.

## 2026-08-11 | GPT-sol(요한) | C-5~C-8 수정 재검수 — REJECT (실호출 0)

- 범위: `c64bddb`의 `compare_ours.py`·회귀 24종·PREREG §8과 상류
  `modules/llm.py` 실제 전송 경계를 함께 검사했다. 기존 비동기 독립 리뷰에서 도착한
  N-2(중복·불완전 key 집합)도 이번 판에 포함했다.
- 판정: **C-6·C-7 수용, C-5·C-8 부분 미해소, N-2 미해소 — live 금지 유지.**
- 비용 표현 정정 유지: 아래 C-5 재현은 비용 증가를 증명하지 않는다. 400 파라미터 거부는
  통상 성공 응답이 아니며, 확인된 결함은 실제 전송 시도 계기판/퓨즈의 누락이다.

### 수용 — C-6 지속 상한

- `compare_ours.py:145-214`가 시작 시 append 원장을 다시 읽고, 같은 `issue_id`의 누적과
  계획을 116에 합산한다. 기존 21예약+새 계획96은 첫 호출 전에 거부하는 회귀가 있다.
- 파손 JSONL도 보수적으로 즉사한다. 재시작 초기화 재현은 더 이상 성립하지 않는다.

### 수용 — C-7 단일 실행 잠금·직렬 트랜치

- `compare_ours.py:102-142,571-598`의 OS 잠금과 직렬 트랜치를 확인했다.
- 현재 Windows에서 **별도 자식 프로세스**가 잠금을 보유한 동안 부모의 두 번째 획득이
  거부됐고, 해제 후 재획득됐다. 정본 CLI(`main:601-618`)는 live를 `run_tranche`로만
  진입시킨다. 따라서 같은 data root의 공식 실행 경로에서는 원장 TOCTOU가 해소됐다.

### C-5 부분 미해소 — OpenAI 내부 파라미터 폴백 전송은 1행으로만 센다

- 위치: `compare_ours.py:216-223,429-435`; 상류 `modules/llm.py:344-401`.
- `_wrap_dispatch`는 공급자 dispatch **호출 직전** 한 번 예약한다. 그러나 OpenAI dispatch
  함수 `_call_openai` 자체가 `requests.post`를 최대 4회 수행하면서 400 응답에 따라
  `max_tokens`·`temperature` 등을 바꿔 다시 전송한다. 이 내부 전송은 wrapper 아래라
  추가 예약이 없다.
- 최소 0콜 fault injection: `requests.post`를
  `400(max_tokens) → 400(temperature) → 200`으로 스텁했다. 결과는
  **실제 POST 3회 / attempt 원장 1행 / 논리 응답 OK**였다. 새 회귀의
  `timeout 2회 후 성공 = 원장 3행`은 바깥 `obtain_response` 재시도만 검증해 이 경로를
  덮지 않는다.
- 영향: PREREG §8의 “전송 시도마다 1행”과 232/692 퓨즈가 OpenAI에서 참이 아니다.
  다만 이 재현만으로 비용 증가를 주장하지 않는다.
- 수용 기준: 실제 `requests.post`/SDK create 바로 앞에서 예약하거나, OpenAI dispatch에
  attempt callback을 주입해 파라미터 폴백 각각을 센다. canonical fault test에서
  `POST 횟수 == attempt 원장 행 수`여야 한다.

### C-8 부분 미해소 — manifest가 완료 debate 바이트의 불변성을 증명하지 않는다

- 위치: `compare_ours.py:249-288,328-339,439-467`; 체크포인트 결합 `:483-488,
  526-531`.
- manifest는 생성 **입력** SHA를 잘 고정하지만, 완성된 debate SHA를 manifest에 확정하지
  않는다. 재사용 관문은 발화 개수와 config SHA만 보고, `_validate(dp)`도 deep prompt
  재조립 검사가 아니다. `debate_sha256`은 그때 읽힌 현재 바이트를 새 checkpoint에 쓰므로,
  판정 시작 전 변조된 debate도 새 정본처럼 승격된다.
- 최소 0콜 fault injection: 스텁 debate 32발화가 완성된 직후 첫 axis 응답에서 강제
  크래시(논리 원장 33행) → debate의 첫 `response_text`를 변경 → 같은 manifest로 재개.
  결과는 **변조 debate 수용, 판정 64콜 스텁 완주, 블록 원장 97행**이었다.
- 영향: 입력 파일은 그대로여도 발화 원문이 바뀐 결과를 정상 비교 결과로 판정할 수 있다.
- 수용 기준: debate 완주 직후 그 SHA를 원자적으로 manifest에 확정하고 재사용 전 대조하거나,
  `python -m modules.validate <debate> --deep` 상당의 prompt/input 재조립을 live 관문에 넣는다.
  완주 후 한 바이트 변조는 판정 0콜로 거부되어야 한다.

### N-2 미해소 — 중복·누락·extra key 집합을 완전 결과로 수용한다

- 위치: `compare_ours.py:239-246,249-270,341-353,461-465`.
- `_load_rows`는 동일 `(round, agent_id)`를 dict의 마지막 행으로 조용히 덮어쓰며 물리 행
  수·중복·extra를 검사하지 않는다. `debate_status`와 live 관문은 utterance **개수**만
  검사하고 기대 `(round, agent)` 집합과 set-equal을 하지 않는다.
- 현재 HEAD 0콜 재현: 정상 axis checkpoint 32행에 동일 행 1개를 추가한 뒤 재개하자
  **물리 33행을 호출 0회로 완주**했다. 앞선 독립 fault injection에서도 발화 32개 중
  unique key 31개인 debate를 `complete`로 판정해 후속 64 스텁 판정을 완주했다.
- 영향: 발화 하나가 빠지고 다른 발화가 중복된 토론, 중복/예상 밖 행이 든 checkpoint가
  검증 완료 결과로 승격될 수 있다.
- 수용 기준: assignment×rounds로 기대 key set을 만들고 debate/axis/stance 각각에 대해
  `물리 행 수 == unique key 수 == 기대 수` 및 실제 set-equal을 검사한다. duplicate·missing·
  extra·conflicting duplicate·truncated JSONL canonical 회귀가 모두 호출 전 거부되어야 한다.

### 검증 증거·다음 관문

- 실제 외부 API 호출 **0**.
- `test_compare_ours`: **24/24**, paper_repro 트랙 **81/81**, 리포 smoke **311/311** 통과.
- 현재 Windows 별도 프로세스 잠금 배타성 통과; `py_compile`·`git diff --check` 통과.
- 3이슈 정본 트랜치 계획은 합계 288콜이고, 실행 전후 Git status SHA가 동일해 0콜·무기록.
- 테스트 통과는 위 fault injection 세 경로를 포함하지 않으므로 승인 근거가 되지 않는다.
  **C-5 실제 POST 계수 + C-8 debate 출력 결합 + N-2 set-equal 회귀 전 live 금지.**

## 2026-08-11 | GPT-sol 독립 reviewer 후속 — C-7 수용 판정 정정 (실호출 0)

- 독립 reviewer가 같은 `c64bddb`를 별도 fault injection한 결과, 앞 절의 C-7 수용은
  **공식 CLI 경로에만 한정**해야 한다. 공개 `run(..., live=True)`는 잠금을 획득하지 않아
  live 진입점 전체 관점에서는 C-7이 미해소다.
- 위치: `compare_ours.py:291-300`의 `run()`은 곧바로 live 실행에 들어가고, 잠금은
  `run_tranche():571-598`에만 있다. 회귀도 `test_compare_ours.py:316-331`의 tranche만 본다.
- Windows 0콜 재현: `SingleInstanceLock`을 한 프로세스가 보유한 상태에서 다른 경로가
  스텁을 주입해 `run(..., live=True)`를 직접 호출했다. 결과는
  **직접 run 완주=true · 논리 96콜 · responder 64콜**이었다. 잠금은 전혀 검사되지 않았다.
- 영향: 직접 run 두 개 또는 tranche+직접 run이 동시에 `CallGate`의 시작 시 1회 원장
  읽기 이후 경쟁할 수 있어 C-6·블록 상한도 단일 기록자 전제가 깨진다.
- 정정 판정: **C-7 잠금 구현 자체와 정본 CLI는 수용, 모든 live 진입점 강제는 미해소.**
  따라서 C-6도 단일 기록자 조건부 수용이다.
- 수용 기준: 잠금 보유 토큰 없이는 `run(live=True)`를 거부하거나 잠금 획득을 run 내부로
  옮긴다. `잠금 보유 중 직접 run → 스텁 호출 0·원장 기록 0` canonical 회귀가 필요하다.
- 독립 reviewer도 C-5 OpenAI 내부 POST 누락과 N-2를 동일하게 재현했다. C-8의 입력
  manifest/최초 생성 크래시 재개는 수용했지만, 앞 절에서 별도로 재현한 **완성 debate
  바이트 변조** 경로는 검사하지 않았으므로 C-8 출력 불변성 차단은 유지한다.

### 최종 관문 정정

- **C-5 실제 POST 계수 + C-7 모든 live 진입점 잠금 + C-8 완성 debate 결합 + N-2
  set-equal 회귀 전 live 금지.**

## 2026-08-11 | 요한 | 결정 — 수정-재검수 루프 종료·탐색적 파일럿 GO (확정은 사람)

- **결정**: C-5 잔여(내부 폴백 계수)·C-7 잔여(run 직접 호출)·C-8 잔여(완주 후 사람
  변조)·N-2(중복/extra 행)는 이번 파일럿의 **live 차단이 아니라** 후속 정식 검증
  러너의 개선 목록이다. 이번 판은 **탐색적 파일럿**(목적: 비교 관찰 + probe·수첩에서
  후속 검증 후보 지표 발굴)으로 재분류 — 확정적 재현 결론을 내지 않으며 보고 표현을
  제한한다(PREREG §9). 코드 방어 대신 운영 규칙(정본 CLI 단일 실행·실행 중 수정
  금지·중단 시 사람 확인) + 실행 후 0콜 일회성 검사(`compare_postcheck.py`)로 대체.
- 근거: 1시간+ 의 수정-재검수 루프가 "자연 단일 실행에서 발생 확률이 낮은 fault
  injection 방어"로 확장됨 — 목적(좋은 수치 탐색) 대비 과잉. "완벽한 요새 건설은
  그 수치가 실제로 나왔을 때".
- GPT-sol 재검수 기록(직전 append)의 발견 자체는 유효하며 보존된다 — 재분류는
  검토 재료에 대한 사람의 확정이다(팀 규칙 4: 확정은 사람만). 후속 정식 러너
  설계 시 C-5/C-8/N-2 수용 기준을 그대로 개선 목록 입력으로 쓴다.
- 이행(Claude): §13 이후 진행 중이던 C-5/C-8/N-2 코드 수정은 폐기(동결 = 검수·테스트
  통과 커밋 c64bddb), `compare_postcheck.py` 신설(0콜 검사 6항 — 스텁 완주분 OK 판정
  + 중복 주입 폐기 판정 실증), 동결 지문·운영 규칙 PREREG §9 append.
- 다음: 실호출(저자 판 3단계 → 우리 판 트랜치 → probe 120) — PREREG §5·§6·§8 순서.

## 2026-08-12 | Claude(요한) | R1 완료 — 0543 r1 차이 2팩트 원문 판독 (0콜, PREREG §10 규칙)

- 차이 셀(기계 식별): r1 에서 `저자만` 2건 — 팩트 [9](여자친구의 접촉 금지 규칙),
  [12](이전엔 불안을 보인 적 없음). `우리만` 0건. (다른 stage 는 §3-2 기준 구분 불가·동일)
- **[9] = `판정 경계`**: 우리 r1 발화 8건 전부에 유사 표현 실재("cut off my friend, and
  accept rules about my social life"·"block me on apps"·"limit my interactions" 등) —
  그러나 우리 판 판정(n=1)은 unmentioned. 팩트 문면의 세부(접촉 개시 금지·단둘이 금지)
  대비 발화가 "rules"를 총칭으로 언급해 "부분 지지 제외" 규칙의 경계에 걸린 것으로 보임.
  저자 판 근거 확인: 발화 0 "no more contact ever with this friend" (직접 인용 확인).
- **[12] = `발화 부재`(주제 인접 표현 있음 주석)**: 우리 발화들은 불안 자체는 다루나
  "이전에 없었다"는 명제를 담은 발화 없음. 저자 판 근거 확인: 발화 0 "she'd previously
  been fine with my friend"·발화 7 "hadn't previously expressed discomfort" (인용 확인).
- 기술 한정: 원인 단정 없음 — [9]는 판정기 경계 사례 후보, [12]는 발화 생성 차이 후보.
  temp 1.2 확률계에서 1판 관찰이며, 분산 실측(재실행 1판) 전에는 어느 쪽도 마진 밖
  주장을 하지 않는다. 좌표: evaluate_res/debate_full_0[0] · judgment_…compare2_0543 stage1.

## 2026-08-12 | Claude(요한) | R4 — G1 신규 콜 표 제출 (실행 대기 · 요한 승인 관문)

**단가 재산정(R0 실측)**: 판정(gpt-5) ≤**$0.033/콜**(델타 $1.85/56콜, 공유 키 상한) ·
발화(gpt-4.1) ~$0.009/콜.

| 블록 | 콜 | 예상 비용 | 비고 |
|---|---|---|---|
| ① 0248 우리 판 (발화32+축32+stance32) | 96 | ~$2.4 | run_id compare2_0248 |
| ② 0262 우리 판 | 96 | ~$2.4 | run_id compare2_0262 |
| ③ 0543 **같은 엔진 재실행 1판** (분산 실측 — T2 편입) | 96 | ~$2.4 | **새 run_id compare2b_0543**, 같은 config(조건 동일·실행만 반복) |
| 합계 | **288** | **~$7.2** (상한 ×1.2 ≈ $8.6) | 이슈별 --max-calls 116 · 이슈별 1프로세스(온도 오염 회피) |

- ③의 목적: temp 1.2 확률계의 판내 분산 실측 — R1 의 "2팩트 차이"가 마진 안인지
  밖인지 판별할 근거. 재설계 워크오더 T2 의 1판째를 이번 트랜치에 배정하는 안.
- **승인 시 필요한 정정 1건**: 블록 원장 상한 346(PREREG §4 기준)이 현 97 + 288 = 385
  로 초과된다. 계획 확장(96×4판=384)에 맞춰 **블록 상한 461(=384×1.2) 재정의**가
  필요 — PREREG append + 러너 상수 1줄(BLOCK_CAP) 수정(동결 예외, 요한 승인 대상).
  거부 시 대안: 트랜치 원장 파일 분리(코드 무수정·상한 의미는 약화).
- 실행 순서: 승인 → BLOCK_CAP 정정 커밋 → 0248 → 0262 → 0543 재실행(각 완주 확인·
  즉시 커밋) → postcheck → 대시보드 델타 확인 보고.

## 2026-08-12 | 요한 판독·Codex 기록 | §10 차이 셀 원문 판독 완료 (추가 18셀, 0콜)

판독자료집(`판독자료집.html`)의 대기 9패널·18개 팩트×stage 셀을 사람이 전량 판독했다.
절차는 PREREG §10 그대로다: 언급 판 근거 직접 확인 → 미언급 판 8발화 전량 판독 →
`발화 부재`/`판정 경계` 두 범주만 기록. 단순 주제 인접은 언급으로 보지 않고, 팩트를
다른 팩트와 구별하는 핵심 명제(시간·인과·가격·통보 조건 등)가 남아 있는지를 기준으로
삼았다. 아래 fact 번호는 자료집 표시 끝자리다.

| 이슈·stage·fact | 방향 | 언급 판 직접 근거 | 미언급 판 판독 근거 | 범주 |
|---|---|---|---|---|
| 0543 initial …09 | 저자만 | 저자 발화1 `two-night, three-day date`·`betrayed her trust`·`like cheating` | 우리 agent_6 `two-night, three-day "date"`·`equate it to cheating` | **판정 경계** |
| 0543 R2 …07 | 저자만 | 저자 발화4 `my hesitation to immediately fill her in`; 발화5 `I didn't instantly update her` | 우리 agent_1~8: 제3자 이탈은 있으나 **즉시 알리지 않음**은 없음 | **발화 부재** |
| 0543 R2 …13 | 저자만 | 저자 발화8 `evolving trip dynamic ... evoked fresh insecurity` | 우리 agent_1·3 등에 현재 discomfort는 있으나 **이전에는 없었다**는 시간 비교 없음 | **발화 부재** |
| 0543 R2 …14 | 우리만 | 우리 agent_2 `holding to my plans` | 저자 발화1 `stand by my decision to keep the trip`; 발화4 `keep my plans` | **판정 경계** |
| 0543 R3 …07 | 저자만 | 저자 발화2 `I didn't update her right away` | 우리 agent_1~8: 계획 변화는 있으나 통지 지연 명제 없음 | **발화 부재** |
| 0543 R3 …10 | 우리만 | 우리 agent_3 `setting uncompromising "rules"` | 저자 발화1 `blanket restrictions on my friendship`; 발화3 `bans on solo hangs` | **판정 경계** |
| 0248 R1 …10 | 저자만 | 저자 발화2 `risk of fuelling drama`·`I'm not trying to be shady` | 우리 agent_3 `not ... out to cause drama`; agent_6 `didn't ... mean for that to happen` | **판정 경계** |
| 0248 R1 …03 | 우리만 | 우리 agent_3·6: HR과의 closeness/old feelings + 교제 중 boundary 존중 | 저자 발화8 `previously had feelings for HR, even if I never acted on them` | **판정 경계** |
| 0248 R2 …02 | 우리만 | 우리 agent_6 `close-knit group ... processing the secret breakup` | 저자 발화1 `hurt and confusion can spread in a close group`; 발화2 `friend group dynamic` | **판정 경계** |
| 0248 R2 …04 | 우리만 | 우리 agent_4 `didn't make a move until after HR and GB had already broken up` | 저자 발화3 `lack of wrongdoing during their relationship`; 발화8 `didn't act ... until it was genuinely over` | **판정 경계** |
| 0248 R2 …13 | 우리만 | 우리 agent_1·7 `would be the asshole ... dating HR right now` | 저자 발화1 `if I started dating HR right now ... I probably would be the asshole` | **판정 경계** |
| 0248 R3 …04 | 우리만 | 우리 agent_4 `feelings for HR only became a factor after ... GB had ended` | 저자 발화3 `didn't cross ... overlap or deceit`; 발화4 `no overlap or secretive scheming` | **판정 경계** |
| 0248 R3 …06 | 우리만 | 우리 agent_2 `hidden breakup`·`out of the loop`; agent_6 `secrecy of the breakup` | 저자 발화3 `fresh and private`; 발화8 `news was shared—or not shared—with the group` | **판정 경계** |
| 0262 R1 …03 | 저자만 | 저자 발화2 `policy in all its communications`; 발화5 `posted everywhere` | 우리 agent_4 `extremely clear on all their platforms`; agent_7 `posted everywhere` | **판정 경계** |
| 0262 R1 …06 | 저자만 | 저자 발화5 `religious boundaries` + `lack of training or supplies` | 우리 agent_3 `differing haircut techniques`; agent_8 `training focus is men's cuts` (제품·도구 세부는 미출현) | **판정 경계** |
| 0262 R2 …05 | 저자만 | 저자 발화7 `scheduling with the female stylist` | 우리 agent_2 `appointment with the appropriate stylist`; agent_4 `wait for the female stylist` | **판정 경계** |
| 0262 R2 …09 | 저자만 | 저자 발화6 `trained female stylist on short notice, same price` | 우리 agent_1~8: 여성 스타일리스트 예약·대기만 있고 **같은 가격+사전 통보** 명제 없음 | **발화 부재** |
| 0262 R3 …05 | 우리만 | 우리 agent_7 `later appointment with a female stylist` | 저자 발화2 `seeing the female stylist by appointment`; 발화4 `appointed female stylist` | **판정 경계** |

### 집계·기술 한정

- 이번 추가 18셀: **판정 경계 14 · 발화 부재 4**.
- 기존 완료 0543 R1 2셀(판정 경계 1 · 발화 부재 1) 포함 전체 20셀:
  **판정 경계 15 · 발화 부재 5**.
- `판정 경계`는 판정기 오류 확정이 아니라, 미언급 판 원문에도 언급 판과 동등하거나
  핵심 명제를 보존한 표현이 존재한다는 사람 판독 범주다. n=1 판정의 경계 사례 후보로만
  기술한다.
- `발화 부재`도 엔진의 체계적 차이 확정이 아니다. temp 1.2 단일 실행에서 해당 명제가
  미언급 판 8발화에 없었다는 관찰이며, 분산 실측 전에는 생성기 효과로 일반화하지 않는다.
