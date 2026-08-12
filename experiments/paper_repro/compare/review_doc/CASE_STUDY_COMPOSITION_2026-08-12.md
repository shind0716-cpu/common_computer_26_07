# 정성 사례 보고 — 발화 구성이 급격히 바뀐 두 사례 (2026-08-12)

지위: 탐색적 정성 분석 (근거 자료). 추가 API 콜 없음 — 커밋·저장된 compare2 원자료만
다시 읽었다. 단일 실행(temp 1.2)에 판정 n=1이므로 사례 기술이고, 엔진 효과나 판정기
오류를 확정하지 않는다. 수치 정본은 RESULT.md와 커밋된 원자료다.

## 0. 배경

RESULT §3에 "발화 길이는 완만히 주는데(약 20%) 재진술은 급락한다(약 90%)"는 집계 관찰이
있다. 이게 발화자 한 명 수준에서 실제로 어떤 모습인지 보려고, 낙폭이 가장 큰 발화자
둘을 골라 원문을 읽었다.

- 0248 agent_2: 첫 발화에 13팩트 → 다음 라운드 2팩트. 낙폭 최대.
- 0262 agent_1: 8팩트 → 0팩트, r3까지 판정상 복귀 없음. 그런데 원문을 읽어보면 팩트가
  아주 없는 게 아니다. 아래 §3.

## 1. 데이터 좌표

| 자료 | 경로 |
|---|---|
| 우리 판 발화 원장 | `experiments/paper_repro/data/debates/debate_issue_ethics_{0248,0262}_compare2_*.jsonl` (`event: utterance`, `response_text` 원문 전량 보존) |
| 판정 원장 (저자 축 gpt-5 n=1) | `experiments/paper_repro/data/judgments/judgment_issue_ethics_{0248,0262}_compare2_*_author.json` (`agents_mentioning`) |
| 배분표 | `experiments/paper_repro/compare/author_inputs/perspective_scruples.json` |

셈법: 발화자×라운드의 언급 팩트 수 = 판정 원장에서 그 발화자가 `agents_mentioning`에
등장한 fact 수. 길이 = `response_text` 문자 수.

## 2. 사례 A — 0248 agent_2 (관점1 · con)

| | r0 | r1 | r2 | r3 |
|---|---|---|---|---|
| 언급 판정 팩트 | 13 (01–08, 10–14) | 2 (01, 06) | 2 (01, 06) | 4 (01, 02, 06, 12) |
| 발화 길이(자) | 1,701 | 1,070 | 1,374 | 1,804 |

r0는 사건을 시간순으로 다시 쓰는 글이다. 14팩트 중 13개가 이 한 발화에 들어 있다.

> "Let's lay out the facts: GB and HR broke up, and you, GB, and HR are all in the same
> friend group. While HR and GB were dating, you became close friends with HR and had some
> romantic feelings, but you didn't act on those feelings out of respect. […] Three weeks
> ago, you started talking to HR and only then learned about the breakup because the group
> kept it quiet."

r1은 사건이 아니라 앞사람들 말에 답하는 글이 된다. 팩트 자리에는 요약 한 구절이 남고,
나머지는 자기 입장을 다듬는 데 쓴다.

> "After really considering everyone's perspectives, I can see why there's such a strong
> reaction. Several people pointed out that […] the optics, timing, and context matter a
> lot […] So, while my view hasn't entirely flipped (I don't think you're *the* asshole),
> I'm more uncertain now."

r2도 같은 틀인데, 자기 논거(NTA)를 받치는 팩트 01(이별 사실)·06(교제 중 무행동)은
매 라운드 살아남는다. r3에서 02·12가 다시 나와 4개가 되고 길이도 1,804자로 돌아오지만
재진술은 r0의 1/3이다.

정리하면, 이 발화자에게 팩트는 r1부터 전달할 정보가 아니라 논거 재료다. 입장을 받치는
최소한만 반복되고, 입장과 무관한 11개는 발화에서 빠진다. 어디까지나 이 발화자 한 명의
단일 실행 관찰이다.

## 3. 사례 B — 0262 agent_1 (관점1 · pro)

| | r0 | r1 | r2 | r3 |
|---|---|---|---|---|
| 언급 판정 팩트 | 8 (01–05, 07, 08, 11) | 0 | 0 | 0 |
| 발화 길이(자) | 2,383 | 1,768 | 1,674 | 1,520 |

r0는 바버샵 정황(99% 남성 고객, 여성은 예약제, 게시된 정책, 무슬림 직원의 종교적 제약,
교육·도구 차이, 같은 가격)을 직접 서술한다. r1부터 판정상 0인데, 원문에는 팩트 내용이
남아 있다.

> "Several people argued that the policies were clearly posted and rooted in religious
> practices/training […] It's true the female stylist system is meant to respect everyone's
> comfort and that you offered her the same price and an option to wait, not an outright
> denial."

게시된 정책, 같은 가격 제안이 문장 안에 있다. 다만 "내가 전하는 사실"이 아니라 "다른
사람들이 주장한 것"의 요약이거나 양보절이고, 판정은 이 발화를 0팩트로 셌다. r2도 같다.

> "I still hold firm to my earlier view that while the policy on women's haircuts at the
> shop was clearly posted and had its justifications — primarily religious beliefs and
> staff training — this rigid application didn't ser[ve]…"

정책 게시(fact 03 계열)의 명제가 그대로 있는데 판정은 0. r3는 타인 논거의 재인용
("those still leaning toward NTA because of the barbershop's transparency…")으로 한 겹
더 멀어진다.

이 사례에서는 두 가지가 겹쳐 있다. 발화 자체가 사건 서술에서 토론 논평으로 넘어가서 새
팩트 진술이 없어진 것이 하나. 간접 인용이나 양보절 속에 남은 팩트 명제를 n=1 판정이
계속 unmentioned로 처리한 것이 다른 하나다. 후자는 20셀 원문 판독에서 나온 `판정 경계`
15건과 같은 종류로 보이는데, 판정기가 직접 진술만 세는 경향이 있는지는 이 데이터로
확정할 수 없다. judge 신뢰도 트랙의 재료다.

## 4. 두 사례에서 같이 보이는 것, 그리고 대조군

두 사례 모두 r0와 r1 사이에 글의 상대가 바뀐다. r0는 사건을 보고 쓰고("Let's lay out
the facts"), r1은 직전 라운드를 보고 쓴다("After considering everyone's perspectives").
rolling window에서 프롬프트에 들어오는 내용이 원사건 자료에서 앞 라운드 발화로 바뀌는
구조와 맞는 방향이다. 그러면서 팩트는 단정 서술에서 간접 인용("several people argued"),
대명사("those boundaries"), 양보절("It's true that… but")로 옮겨 간다. 길이는 r0→r1에서
20% 안팎 주는 데 그치지만(A: 1,701→1,070, B: 2,383→1,768) 재진술은 85–100% 준다.
줄어든 건 분량이 아니라 발화 안에서 팩트가 차지하던 자리다.

대조군으로 0248 패널이 있다. 8인 전원이 r3까지 발화당 2–4팩트를 유지한 유일한
이슈이고(이슈 평균 재진술 r1–r3: 0248 = 2.62/2.38/2.62, 0543 = 0.62/0.75/0.62, 0262 =
0.75/0.25/0.38), FAR 고원도 셋 중 가장 낮다(우리 판 r2·r3 = 0.57). 재진술 유지와 낮은
FAR이 이슈 수준에서 같이 가는 그림인데, 이슈가 3건뿐이라 상관이라고 부를 수는 없다.

부수 관찰 하나. r0 길이의 발화자 간 편차(0248: 881–1,977자)는 배분표의 관점별 할당
팩트 수(6–13개)와 방향이 맞는 데가 있다. 0248 관점3(할당 6개)이 881·933자로 전체
최소다. 0543에서는 이 대응이 약해서, temp 1.2의 확률 편차가 얹혀 있다고 봐야 한다.

## 5. 이 보고서가 말할 수 없는 것

- 단일 실행(temp 1.2), 판정 n=1. 두 사례는 대표 표본이 아니라 극단값을 고른 것이다.
- "판정기가 직접 진술만 세는 경향"은 사람 판독과 판정이 어긋난 데서 나온 후보 기술이다.
  확정은 judge 신뢰도 트랙 몫.
- 0248의 재진술 유지와 낮은 FAR 고원의 동행은 이슈 3건 중 1건이다. 이슈 속성(WIBTA
  프레임, 팩트 수)과의 교락을 이 데이터로 분리할 수 없다.

## 6. 후속 연결

- judge 신뢰도 트랙: 사례 B의 r1·r2 발화를 사람 라벨 30표본에 넣을 후보로 제안.
  간접 인용·양보절 속 팩트를 판정기가 어떻게 처리하는지 보는 경계 표본.
- 팩트 기준 시계열(hazard) 트랙: 사례 A의 "입장 받치는 팩트만 생존(01·06)" 패턴이
  팩트별 생존 곡선으로 일반화되는지.
- 매핑 판정 설계: probe 회고와 발화의 격차(RESULT §3)와 같은 계열. 회고에는 남고
  발화에서는 인용으로 밀려나는 팩트의 추적.

## 변경 이력 (append-only)

| 날짜 | 버전 | 바꾼 것 | 바꾼 사람 |
|---|---|---|---|
| 2026-08-12 | v0 | 초안 작성 (0콜 원자료 재판독) | 요한 측 Claude |
| 2026-08-12 | v1 | 문장 전면 재작성 — 라벨식 병렬 구조·과한 수사 제거, 실험 노트 톤으로. 표·인용·수치 불변 | 요한 측 Claude |
| 2026-08-12 | v1.1 | 범위 물결(~)을 –로 교체 — GFM 취소선 오렌더링 방지 | 요한 측 Claude |
