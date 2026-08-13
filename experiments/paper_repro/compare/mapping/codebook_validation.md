# codebook_validation — Step 1 게이트 판정 (codebook_ver: v1)

> **상태: 미완. E0 판정 불가 — coder_b 미도착.**
> 규약: append-only. coder_b 결과가 오면 아래 §5에 append하고 본문 판정을 갱신하지 않는다.

2026-08-13 · 콜 0 · 셔플 시드 20260813 · 20셀

---

## 1. 게이트 3개

| 게이트 | 기준 | 판정 |
|---|---|---|
| **E0** | 2인 코딩 κ ≥ 0.60 | **판정 불가** — coder_b 미도착. 1인 코딩으로 κ를 만들지 않았다(TASK N5) |
| G2 | `ambiguous` ≤ 20% | **잠정 미달** — coder_a 6/20 = 30% |
| G3 | 실제 관측 등급 4단 이상 | **잠정 통과** — coder_a 5단 전부 관측 |

G2·G3은 coder_a 단독 수치라 확정이 아니다. **E0이 판정되지 않았으므로 Step 2(전처리·판정기)로
넘어가지 않는다**(PREREG §11 N2).

### 왜 1인으로 끝내지 않았나

E0은 "등급이 맞았나"가 아니라 "판별 규칙이 두 번째 사람에게도 같은 결과를 주나"를 재는
관문이다. 한 사람이 두 번 매기면 그 값은 규칙의 재현성이 아니라 그 사람의 일관성이라,
κ 자리에 넣는 순간 게이트가 통과 절차로 바뀐다.

---

## 2. coder_a 결과 (단독, 잠정)

등급 분포 — L0=9 · L1=5 · L2=3 · L3=1 · L4=2 (n=20)

### 2.1 대응표 — 원판독 범주 × 새 등급

| | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| 판정 경계 (15셀) | 9 | 4 | 2 | 0 | 0 |
| 발화 부재 (5셀) | 0 | 1 | 1 | 1 | 2 |

**예상(TASK 절차 4)**: 판정 경계 → L1~L3, 발화 부재 → L3~L4.

### 2.2 예상과 어긋난 칸 — 11셀

등급 정의는 고치지 않는다(TASK N4). 사실만 적는다.

**판정 경계 → L0 (9셀).** 예상 상한을 넘었다.

| blind | 좌표 | 근거 |
|---|---|---|
| U04 | 0543 initial fact_09 | 미언급 판에 `two-night, three-day "date"`·`equate it to cheating` 이 문면 그대로 |
| U01 | 0248 R2 fact_13 | `if I started dating HR right now, yeah, I probably would be the asshole` |
| U02 | 0248 R3 fact_04 | `no overlap or secretive scheming` |
| U06 | 0248 R2 fact_04 | `waited until after her breakup with GB and there was no cheating` |
| U17 | 0248 R3 fact_06 | `the news was shared (or not shared) with the group`·`private breakup` |
| U19 | 0248 R1 fact_03 | `previously had feelings for HR, even if I never acted on them before` |
| U08 | 0262 R1 fact_06 | `religious beliefs around not touching women's hair`·`differing haircut techniques` |
| U07 | 0262 R3 fact_05 | `seeing the female stylist by appointment` |
| U18 | 0262 R2 fact_05 | `women needing appointments for both religious and skill-based reasons` |

**발화 부재 → L1·L2 (2셀).** 예상 하한을 넘었다. 이쪽이 더 무겁다.

| blind | 좌표 | 무슨 일 |
|---|---|---|
| **U15** | 0543 R1 fact_13 | 원판독은 "이전에 없었다는 명제를 담은 발화 없음"으로 `발화 부재`. 그러나 미언급 판 S6에 `make immediate ultimatums about my friendships **when there was little precedent for such jealousy**`, S1에 `even if it wasn't obvious before` 가 있다. coder_a는 이를 사실 진술로 보고 L1 |
| U09 | 0262 R2 fact_09 | `same price`·`couple of hours' notice` 는 실제로 없으나, `an alternative was offered (wait for the female stylist)` 로 방향이 남아 L2 |

U15는 **원판독 자체를 다시 볼 대상**이다. 코드북 문제가 아니라 8/12 판독이 해당 구절을
놓쳤을 가능성이 있다. 원자료·원판독은 고치지 않았고(TASK N2), 여기에 기록만 한다.
coder_b가 같은 셀을 어떻게 읽는지가 판별 근거가 된다.

### 2.3 ambiguous 6건 — 어느 경계인가

| 경계 | 건 | 갈린 이유 |
|---|---|---|
| L0/L2 | U02 · U06 · U12 | 남은 표현이 **형제 팩트**의 술어인지 이 팩트의 술어인지 구별되지 않음 (0248 fact_03↔04, fact_02의 HR 소속) |
| L2/L3 | U09 | 잔존분이 형제 팩트(0262 fact_05·08)만으로도 도출됨 — L3 `entail` 여지 |
| L3/L4 | U03 | 규범문 안의 전제(`past reassurance`)를 간접 잔존으로 셀지 |
| L1/L3 | U11 | 팩트가 **발화 행위**(부인한다)인데 텍스트는 제3자가 대신 단언 |

6건 중 4건이 **팩트끼리 내용이 겹치는 지점**에 몰렸다. 이는 등급 사다리의 결함이라기보다
PREREG §4c(함의 행렬 사전 마킹)가 아직 실행되지 않아서 생긴 것으로 보인다 — 이 판단도
coder_b 결과 전에는 확정하지 않는다.

---

## 3. 이 결과에 붙는 한정

### 3.1 coder_a는 완전 블라인드가 아니다

coder_a(Claude 세션)는 이 20셀의 재료 조립자다. `build_blind_sheet.py`를 작성하며
**각 셀의 원판독 범주(판정 경계/발화 부재)와 방향(저자만/우리만)을 봤다.** 블라인드 시트에서
이슈·stage 좌표를 빼고 셔플했지만, 발화 내용으로 좌표가 짐작되는 셀에서는 노출이 남는다.

영향 방향: 원판독 범주를 아는 코더는 예상 등급 쪽으로 끌리기 쉽다. 그런데 실제 결과는
**예상에서 11셀이 벗어났다.** 그래도 이 노출은 κ 해석의 한정으로 남는다 — coder_b가
완전 블라인드라면 두 코더의 조건이 대칭이 아니다.

### 3.2 codebook_ver v1 의 규칙부는 코딩 전에 고정됐다

`CODEBOOK.md` §1~§4는 coder_a 코딩 착수 전에 쓰였고 이후 수정하지 않았다.
`codes_coder_a.jsonl`은 coder_b 배부 전에 커밋해 순서를 남긴다. coder_b의 블라인드는
그 이후로는 지시 준수에 의존한다 — 기계적으로 막지 않았다.

### 3.3 L3은 상한 추정치다

PREREG §1의 L3 통합 한계가 그대로 적용된다. L3은 **문법 변형 잔존**과 **다른 팩트에서
도출 가능한 것**이 섞인 칸이고 이 설계로는 분리되지 않는다. coder_a의 L3=1건도
실측이 아니라 상한이다.

### 3.4 20셀은 0543만이 아니다

TASK 제목은 "0543 차이 셀 20개"지만 실제 20셀은 0543 8 · 0248 7 · 0262 5로 3이슈에
걸쳐 있다(`MUTUAL_REVIEW.md` 8/12 append 2건 = 2셀 + 18셀). 원판독 범주 합계
15/5는 일치한다. PREREG §8도 "0543 20셀"로 적혀 있어 표기가 같은 방향으로 어긋나 있다.
문서는 고치지 않았다 — 사람 판단 사항이다.

---

## 4. 좌표를 못 찾은 셀

없다. 20/20 모두 `MUTUAL_REVIEW.md` 8/12 append에서 좌표가 확정됐고,
판정 원장(`data/judgments/judgment_*_author.json`)과 교차 검사도 20/20 일치했다
(`저자만` → 우리 판 `unmentioned` 8건, `우리만` → `mentioned` 12건).
`build_blind_sheet.py`의 assert가 이 검사를 매 실행 수행한다.

두 append의 팩트 번호 체계가 다르다는 점만 기록한다. 8/12 첫 append(0543 R1 2셀)의
`[9]`·`[12]`는 **저자 판 0-based 인덱스**이고, 18셀 표의 `…09` 형식은 **fact_id 1-based
끝자리**다. 조립 시 fact_id로 통일했다(`build_blind_sheet.py` CELLS 주석).

---

## 5. coder_b 도착 후 (append 예정)

`codes_coder_b.jsonl`이 들어오면 `python merge_recode.py`를 다시 돌려
κ · 불일치 경계 · G2/G3 확정치를 여기에 append한다. 본문 §1~§4는 고치지 않는다.
