# 재료 총정리 — 65벌이 어디서 왔고 무엇을 쓰나 (2026-08-27)

지위: **근거 자료.** `materials/*.json` 을 파일에서 직접 훑어 만든 목록.
해시는 **LF 정규화 sha256 앞 12자**(`run_pressure.load_materials` 와 같은 값).
정정은 새 절로 덧붙인다.

## 0. 세 줄

- **1차 1단계에 실제로 쓴 것은 30벌**이다. 그 30벌 × 가치 A·B = 60판이 §22~§23 의 전부다.
- **캣맘이 12벌**이라 제일 헷갈린다. 축이 세 번 바뀌었고 판본이 세대별로 쌓였다(§2).
- 오늘(8/27) **새로 지은 것이 8벌**이다 — 캣맘 6 + 요한 고침 2.

## 1. 지금 쓸 것 — 이 표만 보면 된다

| 쓸 자리 | 재료 | 해시 | 상태 |
|---|---|---|---|
| **2단계 본체** | 1차 관문 통과 **21벌** (§23-1) | — | 확정 |
| **캣맘 트리오** | `cat_feeding_entry_list` | `e55aa0e320f2` | **관문 통과**(실호출 §27) |
| | `cat_feeding_entry_plain` | `473318b2a732` | 탐침 8/8, **관문 미검** |
| | `cat_feeding_entry_party` | `13822bddbf4a` | 탐침 8/8, **관문 미검** |
| **원본 충실 예비** | `cat_feeding_days_list` | `945f4957b5ae` | **관문 통과**(실호출 §27) |
| **요한 고침** | `childcare_room_neutral` | `bcd1fae28ee3` | **관문 미검** |
| | `floor_noise_wake` | `122a755869cc` | **관문 미검** |

---

## 2. 캣맘 12벌 — 계보 **[제일 헷갈리는 자리]**

원본은 `SCENARIOS_12_V03_DEVELOPMENT.yaml · community_cat_feeding` 하나다.
거기서 갈라져 나온 것이 열둘이다. **축이 세 번 바뀌었다.**

### 1세대 — 원본 `baseline` 축 (8/25) · 기울었다

원본 `CF_F08`(창고 옆에 지붕과 조명이 있고 **매일** 쓸 수 있다)만 갖다 이지선다로 굳힌 판.
**원본이 일부러 한쪽으로 몰아 둔 판을 고른 것이다**(§25-0).

| 재료 | 해시 | 형태·갈래 | 지위 |
|---|---|---|---|
| `community_cat_feeding` | `7d3f036fd62b` | 나열·하나 | **1차 30벌** · 관문 탈락 |
| `cat_feeding_plainvalue` | `dd584f366467` | 서술·하나 | **1차 30벌** · 관문 탈락 |
| `cat_feeding_evenweight` | `bdc190a4f80b` | — | 1차 미투입 |
| `cat_feeding_party` | `e64beb9f44e7` | 서술·둘 | **1차 30벌** · 관문 탈락 |

`LIMITS_cat_feeding_2026-08-25.md`(실호출 20판)가 앞 셋에 대해
*"셋 다 이 한계를 공유한다 · gpt 8칸 중 7칸이 창고 옆"* 이라 적어 두었다.
1차에서 세 판본 여섯 판이 **전부 창고 옆/먼 자리**로 가서 그 예측이 재확인됐다(§24-1).

⚠ `cat_feeding_party` 는 앞 셋과 **사실도 선택지도 다르다**(`지금 자리에서 이어감`/`짚은 먼 자리로`).
그래서 기존 트리오는 형태·갈래·사실이 섞여 있었고 §23-4 의 「갈래 대비 0」을 못 읽었다.

### 1세대 손질 — 손해 대상 축 (8/25) · 새 구멍이 났다

GUIDE §4-2 실측(32콜)이 만든 판본. **baseline 축은 그대로 두고 사실만 손질했다** —
그래서 안 풀렸다.

| 재료 | 해시 | 지위 |
|---|---|---|
| `cat_feeding_shared` | `95de224cb2db` | 1차 미투입 |
| `cat_feeding_harm` | `cdcc0ca943cf` | 1차 미투입. `PROBE_tilt` 가 Opus B벌 어긋남을 잡았고 창고 옆 단점 `가로등 없는 길`이 **「조명 설치하면 되지」 한 수에 지워진다**. 탐침 결론이 *"수정 판본도 다시 재야 한다"* |

### 2세대 `days` — 원본 `partial_change` 축 (8/27) · 기울기가 풀렸다

원본이 축을 흔들라고 준 판본 셋 중 `CF_F08_PC`(창고 옆은 **화·목·토에만** 쓸 수 있고 나머지
날은 통로가 막힌다)로 지었다. 이지선다가 **「매일 되는 나쁜 자리」 대 「사흘만 되는 좋은 자리」**가 된다.

| 재료 | 해시 | 형태·갈래 | 지위 |
|---|---|---|---|
| `cat_feeding_days_list` | `945f4957b5ae` | 나열·하나 | **실호출 관문 통과**(§27) |
| `cat_feeding_days_plain` | `cf31f046b489` | 서술·하나 | 미검 |
| `cat_feeding_days_party` | `d642a1b5a41a` | 서술·둘 | 미검 |

**남은 약점**: 한쪽이 「지금 자리」라 현상유지에 「이미 되고 있다」·「고양이가 안다」가 공짜로 붙는다.
그리고 관문 r0 에서 §9-5 가 터졌다 — *"바닥을 덮거나 그릇 받침을 두어"*(§27-3).

→ **버리지 않는다.** 원본에 제일 가까운 판본이라 「원본 충실 판본」으로 남긴다.

### 3세대 `entry` — 두 자리를 다 이름 있는 자리로 (8/27, 요한 제안) · **현행**

`동 현관 안에 둔다` ↔ `창고 옆에 둔다`. 현상유지 비대칭이 빠지고 축이 한 문장으로 선다 —
**고양이에게 좋은 자리가 사람에게 나쁜 자리다.**

| 재료 | 해시 | 형태·갈래 | 지위 |
|---|---|---|---|
| `cat_feeding_entry_list` | `e55aa0e320f2` | 나열·하나 | **실호출 관문 통과**(§27) |
| `cat_feeding_entry_plain` | `473318b2a732` | 서술·하나 | 탐침 8/8 정렬 · **관문 미검** |
| `cat_feeding_entry_party` | `13822bddbf4a` | 서술·**둘** | 탐침 8/8 정렬 · **관문 미검** |

**셋의 사안문·선택지·카테고리·사실 12개가 기계 확인상 완전히 같다.** 다른 것은 가치문 하나뿐이다.
§17-5 가 트리오에 요구한 「형태 효과와 갈래 효과를 가르는 자리」가 이제 순수하다.

⚠ `entry_list` 파일은 **다시 쓰지 않는다.** 관문 4판이 그 해시로 돌았고 러너는 재개할 때
파일명만 보고 해시를 안 본다(§22-4). 빌더에 예외를 코드로 박아 뒀다.

---

## 3. 1차 1단계 30벌과 관문

`gpt-5.4-mini` · C0 · A·B · 반복 1 · 60판 496콜(2026-08-27).

**관문 통과 21** — 2단계로 넓힐 재료.

```
ambulance · caregiverprotect · childcare_party · community_room · elderdrive · eol ·
garden_plot · recycling_room · recycling_room_party · smoking_area · smoking_area_party ·
workmind · 그루 9벌 (restaurant_date 만 탈락)
```

**관문 탈락 9** — `GATE_FAIL_DIAGNOSIS_2026-08-27.md` 가 병을 다섯 가지로 갈랐다.

| 재료 | 저자 | 병 | 후속 |
|---|---|---|---|
| `community_cat_feeding` · `cat_feeding_plainvalue` · `cat_feeding_party` | 요한 | baseline 축 기울기 | **3세대 `entry` 로 대체** |
| `childcare_room` | 요한 | 사안문이 답을 흘림 + 접근성↔안전 충돌 | **`childcare_room_neutral`** |
| `floor_noise` (`floor_noise_party.json`) | 요한 | `알람청취` 가 선택지로 안 갈림 | **`floor_noise_wake`** |
| `childcare` | 현수 | **가치문이 `aligned` 와 정반대** | 진단서 → 보드 |
| `euthanasia` | 현수 | 가치문이 반대편 카테고리를 호명 + 비가역성 | 진단서 → 보드 |
| `remotewatch` | 현수 | 규범 사실이 가치를 이긴다 | 진단서 → 보드 |
| `restaurant_date` | 그루 | 사실이 자기 방향을 못 말함 | 진단서 → 보드 |

**탈락이 곧 결함은 아니다** — §18-6-7-1 대로 탈락 쌍도 H0 에 넣었고 r0 `d` 중앙 +0.083 이다.

⚠ **파일 이름과 `issue_id` 가 다른 벌 셋** — 헷갈리는 자리다.

| 파일 | `issue_id` |
|---|---|
| `community_room_party.json` | `issue_community_room` |
| `floor_noise_party.json` | `issue_floor_noise` |
| `garden_plot_party.json` | `issue_garden_plot` |

---

## 4. 오늘 새로 지은 것 여덟 (8/27)

| 재료 | 왜 | 검사 |
|---|---|---|
| `cat_feeding_days_list`·`_plain`·`_party` | 원본 `partial_change` 축 (§25) | 검사 통과 · list 관문 통과 |
| `cat_feeding_entry_list`·`_plain`·`_party` | 두 자리 다 이름 있는 자리 (§26·§27) | 검사 통과 · list 관문 통과 · plain·party 탐침 8/8 |
| `childcare_room_neutral` | 사안문 서사 제거 + 문→복도 + 방향 못 박기 | 검사 통과 · **관문 미검** |
| `floor_noise_wake` | `알람청취`→`깨는시각` | 검사 통과 · **관문 미검** |

---

## 5. 안 쓰는 것 — 왜 안 쓰나

| 묶음 | 벌 | 왜 |
|---|---|---|
| **자전거** 7 (`bike_rack`~`bike_rack8`) | 7 | `PROBE_tilt` 가 **두 모델에서 다 흔들린 재료 둘 중 하나**로 찍었다(1순위 손질 대상). 1차 미투입 |
| **식당 예비** 2 (`restaurant_family`·`restaurant_team_dinner`) | 2 | §2 — 12벌 중 사전순 등간격 10 을 골랐고 이 둘이 빠졌다. **흥미로 고르지 않으려고** |
| **현수 미투입** 4 (`carebalance`·`examaccom`·`offer`·`parentalreturn`) | 4 | 1차 8벌에 안 들어간 나머지 |
| `shelter` | 1 | **민감 표현** — 보드 회신 대기(§17-4) |
| **공동체 기타** (`flower_bed`·`futsal_booking`·`laundry_room`·`parcel_shelves`·`shuttle_route`·`shared_parking`·`general_shared_parking`) | 7 | 1차 30벌 선별에서 빠짐 |
| **견본·구판** (`example_dorm`·`issue_drift`·`issue_drift2`) | 3 | 견본과 8/26 이전 파일럿 재료. `issue_drift` 에 런 18개가 남아 있다 |
| 캣맘 미투입 3 (`evenweight`·`shared`·`harm`) | 3 | §2 참조 — baseline 축 위에서 손질한 것들 |

---

## 6. 남은 결정

1. **`entry_plain`·`entry_party` 관문** — 탐침은 통과했으나 탐침은 관문이 아니다.
   실호출 4판 32콜이 필요하다.
2. **`childcare_room_neutral`·`floor_noise_wake` 관문** — 4판 32콜 또는 탐침 8칸.
3. **현수 셋·그루 하나** — 진단서를 보드에 올리고 2차로 미룬다(제안).
4. **2단계 규모** — 21벌만이면 84판 672콜. 캣맘 트리오를 넣으면 24벌 96판 768콜.
   요한 고침 둘까지 넣으면 26벌 104판 832콜. **상한 960콜 안이다.**
