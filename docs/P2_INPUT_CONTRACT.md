# P2(조건부 소실률) 입력 계약 — judgment 구조 확정용 근거 자료

> **목적**: 동범 님이 judge 실호출 산출물(judgment)의 **최종 구조를 확정**할 때(SCHEMA.md
> 「⚠ 통합 전 확인 필요」·docs/INTEGRATION_ledger.md §3-3), 주지표 **P2(조건부 소실률,
> `modules/survival.py`)** 가 실제로 무엇을 입력으로 기대하는지 코드 근거와 함께 제시한다.
> **이 문서는 근거 자료이지 결정문이 아니다.** 스키마·코드를 바꾸지 않으며, 결정은 §4의
> 열린 질문에 대한 동범 님/팀 회신으로 이뤄진다.
>
> 근거 커밋: `survival.py`(563e563), `ledger.py`/`judge.py`/`SCHEMA.md`(a6cf8c0 통합본).

---

## 0. 한 줄 요약

P2는 judgment에서 **`stages[].facts[].{fact_id, status}` 두 필드만** 실제로 읽는다(프로토콜
준수, fact 레벨 위반 없음 — §2). 다만 그 두 필드를 담는 **봉투(envelope) 3요소**
(`stages` 리스트 · 각 stage의 정렬 가능한 `stage` 키 · 각 stage의 `facts` 리스트)에는
구조적으로 의존하며, 이 봉투에 대해 스키마가 **명시적으로 보장하지 않은 가정 2개**
(① stage가 실시간 라운드 순서로 정렬됨 ② 각 stage.facts[]가 전체 팩트의 **완전 스냅샷**)를
깔고 있다. 이 두 가정이 P2의 유효성을 좌우하므로 §4에서 확인을 요청한다.

---

## 1. P2가 요구하는 최소 계약

### 1-1. 필수 필드 (코드 근거)

survival.py가 judgment에서 접근하는 필드는 아래가 전부다. `critical`은 judgment이 아니라
**facts 파일**(`facts_by_id`)에서 오므로 judgment 입력 계약에는 포함되지 않는다(§1-4).

| 경로 | 접근 방식 | survival.py 줄 | 용도 |
|---|---|---|---|
| `stages` (최상위 리스트) | `judgment.get("stages", [])` — soft(없으면 `[]`) | `survival.py:39, :69, :112` | 전이/누적 집계의 모수 원천 |
| `stages[].stage` | `s.get("stage")` — soft 접근이나 **정렬 시 사실상 hard** | `survival.py:39`(정렬 키), `:90–91`(from/to_stage 출력), `:116`(`*prior, last`), `:138` | 라운드 **순서**와 전이 k→k+1 식별 |
| `stages[].facts` | `stage_record.get("facts", [])` — soft(없으면 `[]`) | `survival.py:44, :139` | 팩트 상태 목록 |
| `stages[].facts[].fact_id` | `f["fact_id"]` — **hard(없으면 KeyError)** | `survival.py:44` | 팩트 동일성 추적(전이 매칭 키) |
| `stages[].facts[].status` | `f.get("status")` — soft(없으면 `None`) | `survival.py:44` | 생존/소실 판정 |

접근 방식 주석:
- **`fact_id`는 진짜 hard**다. `_status_map`이 `f["fact_id"]`로 직접 인덱싱하므로(`:44`) 팩트
  레코드 하나라도 `fact_id`가 없으면 즉시 KeyError.
- **`stage`는 soft처럼 보이나 런타임상 hard**다. `_sorted_stages`가 `key=lambda s: s.get("stage")`
  로 정렬(`:39`)하는데, 일부 stage에 키가 없어 `None`과 정수가 섞이면 Python3에서 정렬 자체가
  TypeError로 터진다. 즉 **모든 stage 레코드에 `stage` 키가 있어야** 한다.
- **`status`가 없거나(`None`) 값이 예상 밖이어도 죽지 않는다.** `None`은 SURVIVING에 없으니
  '소실'로 집계될 뿐이다(`:78, :124`).

### 1-2. 값 어휘 (status)

- P2는 status 문자열을 **판정 잣대 `judge.SURVIVING`에 그대로 위임**한다(import `survival.py:31`).
  현재 `SURVIVING = {"mentioned", "accepted"}`(`judge.py:37`). **생존 = 이 집합에 속함, 소실 =
  그 밖 전부**(`survival.py:76, :78, :120, :124`).
- 따라서 P2는 특정 status 어휘를 **강제하지 않는다.** SURVIVING 집합만 유효하면 나머지 값은
  무엇이든 '소실'로 떨어진다. SCHEMA 5종(`unmentioned|mentioned|accepted|refuted|ignored`)이든,
  현행 judge v0의 2종(`mentioned|unmentioned`, 동범.md 설계노트·드라이런 픽스처 확인)이든
  P2 계산은 동작한다.
- **단, 감사용 분해(`lost_by_status`)는 어휘에 민감하다.** `survival.py:81`은 소실 내역을
  `{"unmentioned", "refuted", "ignored", "absent"}` 버킷으로 나눈다(레코드 부재 = `absent`).
  새 status 값이 와도 `by_status.get(key, 0) + 1`(`:84`)로 버킷이 동적 추가되어 죽지는 않지만,
  현행 judge가 `mentioned/unmentioned`만 내는 한 이 분해표는 **사실상 `unmentioned`/`absent`
  두 칸만** 채워진다. `refuted/ignored` 칸은 v1 상태추적이 붙어야 값이 생긴다.

### 1-3. 라운드 표현

- P2의 주지표는 **전이 hazard**(`conditional_attrition`, `survival.py:51`)로, 본질적으로
  **정렬된 라운드 k→k+1 인접쌍**을 필요로 한다(`zip(stages, stages[1:])`, `:71`).
- 요구사항: `stage` 값이 **① 존재하고 ② 서로 비교(정렬) 가능하며 ③ 실제 토론 진행 순서와
  단조 일치**해야 한다. 절대값(0-기반이든 1-기반이든)이나 연속성은 **무관**하다 — P2는
  정렬 후 인접쌍만 쓰므로 `[0,1,2,3]`이든 `[1,2,3]`이든 `[2,5,9]`든 순서만 맞으면 동일하게 돈다.
- 누적 지표(`post_intro_final_loss`, `:99`)는 정렬 결과의 **마지막 stage를 '최종'으로 간주**
  한다(`*prior, last = stages`, `:116`). 따라서 "가장 크게 정렬되는 stage = 토론의 최종 라운드"
  가 성립해야 한다.

### 1-4. 결측 라운드·스냅샷 요건 (결정 2)

survival.py는 소실을 **보수적**으로 본다(judge 관례와 일치, docstring `:18–19`):

- **"k+1(또는 마지막 stage)에서 SURVIVING으로 재확인된 것만 생존."** 어떤 팩트가 stage k에서
  생존이었는데 stage k+1의 `facts[]`에 **레코드가 아예 없으면** → `map_k1.get(fid)`가 `None` →
  SURVIVING 아님 → **소실(`absent`)로 집계**(`:78, :83, :124`).
- 이는 **각 stage의 `facts[]`가 추적 대상 팩트 전체의 완전 스냅샷**이라는 것을 전제로 한다.
  만약 judgment이 "이번 라운드에 변한 팩트만" 담는 **델타/변경분 기록**이라면, 변화 없이
  생존 중인 팩트가 스냅샷에서 빠져 **거짓 소실(absent)** 로 잡혀 P2가 부풀어 오른다.
- 현행 judge.py는 이 전제를 **구현으로 충족**한다: `judge_debate`가 stage마다 `judge_stage(utts,
  facts, ...)`를 **전체 facts** 대상으로 호출(`judge.py:250`)하므로 모든 stage가 전 팩트를 담는다.
  그러나 이는 **코드의 우연한 보장이지 SCHEMA가 명문화한 계약이 아니다**(§4-C).

### 1-5. 전이 hazard에 필요한 "직전 라운드 생존" 복원 가능성

- P2가 k→k+1 hazard를 재려면, 각 팩트의 **stage k 상태**와 **stage k+1 상태**를 동시에 알아야
  한다(`map_k`, `map_k1`, `survival.py:72–78`).
- §1-4의 완전 스냅샷 전제가 성립하면, **직전 라운드(k) 생존 여부는 stage k 레코드에서 직접
  읽힌다** — 별도 이력 재구성이 필요 없다. 즉 **복원 가능(로컬 읽기로 충족)**.
- 반대로 judgment이 델타/append-only 이벤트 형태로 바뀌면, 직전 라운드 생존을 **스냅샷으로
  복원하는 로직이 judgment 소비자(P2/ledger) 쪽에 새로 필요**해진다. 현재 survival.py에는
  그런 재구성 로직이 없다(스냅샷을 그대로 신뢰). → §4-C.

---

## 2. `fact_id`·`status` 외 의존 점검 (프로토콜 위반 여부)

프로토콜: "judgment 구조 의존 최소화 — `stages[].facts[].{fact_id, status}` 두 필드만 읽는다"
(survival.py docstring `:13`, ledger.py `:13`와 동일 문구).

**fact 레벨 판정: 위반 없음.** survival.py가 `facts[]` 원소에서 읽는 필드는 `fact_id`(`:44`)와
`status`(`:44`) **둘뿐**이다. judge가 내는 다른 fact 필드(`votes`, `agents_mentioning`, `reason`)는
**전혀 참조하지 않는다.** 이 부분이 동범 님께 드리는 핵심 안심 포인트다 — judgment의 fact 레코드
내부 구조(예: `votes`가 `[{agent_id,votes:[bool×3]}]`이든 `[{status,agents_mentioning,reason}]`이든,
SCHEMA 「통합 전 확인 필요」의 그 드리프트)를 **어떻게 확정하든 P2는 영향받지 않는다.**

**봉투(envelope) 레벨: 프로토콜 문구가 커버하지 않는 추가 의존 3건이 있다**(위반은 아니나 명시
필요). 위 프로토콜 문구는 `facts[]` **원소 내부**를 규정할 뿐, 그 원소를 담는 그릇은 규정하지
않는다. P2는 그릇에 대해 다음을 요구한다:

1. `stages`가 **리스트**로 존재(`:39`).
2. 각 stage에 **정렬 가능한 `stage` 키**가 존재(`:39` 정렬, `:116` 최종 판정) — §1-1·§4-A.
3. 각 stage에 **`facts` 리스트**가 존재하고 **전 팩트 완전 스냅샷**(`:44`) — §1-4·§4-C.

`critical`(critical-only 집계용)은 `_is_critical`이 **facts 파일에서 온 `facts_by_id`**를 읽는
것이지(`survival.py:47–48`) judgment의 fact 레코드를 읽는 게 아니다. 따라서 **judgment 입력
계약과 무관**하며 위반 대상이 아니다.

---

## 3. 현행 문서/코드와의 불일치 목록

| # | 항목 | SCHEMA.md / 문서 | survival.py 기대 | 판정 |
|---|---|---|---|---|
| D1 | **stage 번호 기점** | 드라이런 픽스처는 `stage = [0,1,2,3]`(0-기반). judge 실호출은 debate_engine `range(1, rounds+1)`(1-기반)로 stage `[1..N]` 산출 예상 | 절대값 무관, **순서만** 필요(§1-3) | **P2에 무해.** 단 on/off 비교표·다른 소비자와의 정합을 위해 기점 통일은 별도 확인 권장 |
| D2 | **status 어휘 폭** | SCHEMA #5는 5종(`unmentioned/mentioned/accepted/refuted/ignored`) | 5종 전부 수용. SURVIVING 밖은 소실 | **정합.** 단 현행 judge v0는 2종만 산출(동범.md 설계노트·픽스처) → `lost_by_status`의 `refuted/ignored` 칸은 v1 전까지 항상 0(§1-2) |
| D3 | **stage.facts 완전 스냅샷 보장** | SCHEMA #5는 `stages[].facts[]` 구조만 규정, **"매 stage 전 팩트 재기재"를 명문화하지 않음** | 완전 스냅샷 **전제**(레코드 부재=소실, `:78,:83`) | **문서 공백.** 현행 judge.py `:250`이 구현으로 충족하나 계약화 안 됨 → §4-C |
| D4 | **fact 레코드 내부 드리프트** | SCHEMA 「⚠ 통합 전 확인 필요」·INTEGRATION §3-3: `votes`/summary 구조가 드라이런 vs judge.py 상이 | `votes` 등 **미참조**(§2) | **P2 무관.** 이 드리프트 확정은 P2 유효성에 영향 없음 |
| D5 | **stage_type=summary_layer** | SCHEMA #5: `stage_type: "round" | "summary_layer"`(관찰 트랙) | stage를 **실시간 라운드 순서**로 가정(§1-3) | **미확인.** summary_layer의 stage가 시간순 라운드가 아니면 전이 hazard 의미 붕괴 → §4-B |

---

## 4. 동범 님 확인이 필요한 결정 지점 (열린 질문)

P2가 무너지지 않으려면 judgment 최종 구조가 아래를 만족해야 한다. 각 항목은 **판정 대기**이며,
답에 따라 survival.py의 방어 로직(현재는 픽스처 관례에 맞춰 보수적)을 조정할 수 있다.

- **A. `stage` 키는 항상 존재하고 정렬 가능한 값인가?**
  P2는 `stage` 누락 시 정렬에서 TypeError로 죽는다(§1-1). 최종 judgment에서 모든 stage 레코드가
  `stage`(정수 또는 전순서를 갖는 값)를 반드시 갖도록 확정되는가? 기점은 0/1 어느 쪽으로 고정하나(D1)?

- **B. 관찰 트랙(`stage_type=summary_layer`)에 P2를 돌릴 것인가?** 돌린다면 그때 `stage`는
  **실시간 라운드 순서와 단조 일치**하는가(D5)? summary_layer의 stage가 시간 축이 아니라 요약
  레이어 인덱스라면, 전이 hazard(k→k+1)의 "k 생존자 중 k+1 이탈" 해석이 성립하지 않는다.
  P2는 `stage_type`을 읽지 않으므로(무차별 적용) 이 구분은 **호출 측 계약으로** 정해야 한다.

- **C. 각 stage의 `facts[]`는 전 팩트 완전 스냅샷으로 확정되는가, 아니면 델타/이벤트로 갈 것인가?**
  이것이 **P2 정확도의 최대 급소**다(§1-4·§1-5·D3). 완전 스냅샷이면 현행 survival.py가 그대로
  정확하다. 델타로 가면 "레코드 부재 = 소실"(결정 2) 규칙이 **생존 중인 팩트를 거짓 소실로**
  집계하므로, judgment 스키마에 스냅샷 보장을 명문화하거나 P2에 이력 재구성 로직을 추가해야 한다.

- **D. 소실 판정 잣대(`SURVIVING`)의 최종값 확정 시점.** 현재 `{mentioned, accepted}`는 잠정이며
  (judge.py `:35–37`, SCHEMA 「FAR 정의」 잠정 확정) 기업 확인(패키지 A: FAR 수식 방향) 회신 시
  교체 예정이다. P2·ledger·FAR이 **동일 소스(`judge.SURVIVING`)를 공유**하도록 강제돼 있으므로
  (SCHEMA 「FAR 정의」·survival.py `:9,:12`), 이 값이 바뀌면 P2 결과도 함께 이동한다. judgment
  구조 확정과 **별개 트랙**이지만, 최종 수치를 보고할 땐 두 확정의 선후를 맞출 필요가 있다.

- **E. `lost_by_status` 감사 분해를 최종 산출물에 노출할 것인가?** 노출한다면 judge가 언제부터
  `refuted/ignored`를 실제로 산출하는지(v1 상태추적 도입 시점)에 따라 분해표의 정보량이 달라진다
  (§1-2·D2). v0 구간에서는 `unmentioned/absent` 두 칸만 의미를 가진다는 점을 표에 주석으로 달지 여부.

---

*(이 문서는 신규 추가 전용이다. SCHEMA.md·INTEGRATION_ledger.md·survival.py를 포함한 기존
파일은 본 작업에서 수정하지 않았다.)*
