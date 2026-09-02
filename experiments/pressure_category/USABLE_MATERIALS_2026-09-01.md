# 쓸 수 있는 재료 — 표식 기반 수치를 인용할 수 있는가 (2026-09-01, 기계 생성물)
> 지위: **근거 자료** (기계 생성물 — 손으로 고치지 마라. `usable_materials.py` 를 고친다).


> `usable_materials.py` 가 찍는다. 판정은 **죽은 카테고리 수** 하나로 한다 —
> 실호출 전 판에서 한 번도 안 잡힌 카테고리는 사실이 없어서인지 잣대가 못 본
> 것인지 못 가르므로, 그 축으로는 아무 말도 할 수 없다.
> 잣대는 `aggregate_all11.py` 와 같은 ② 접어서(= 기존 스캐너 판정).
> **C 등급도 최종 선택과 사람 판독에는 그대로 쓸 수 있다** — 못 쓰는 것은 표식 수치뿐이다.

실호출 판이 있는 재료 53벌 · A 32 · B 10 · C 11

| 등급 | 재료 | 판 | 카테고리 생존율 | 죽은 카테고리 | 와/과 표식 | 어긋난 가치 세트 |
|:-:|---|---:|---:|---|---|---|
| **A** | drift | 71 | 75.8% | — | — | — |
| **A** | restaurant_anniversary | 63 | 74.6% | — | — | — |
| **A** | childcare_room | 63 | 73.5% | — | — | — |
| **A** | restaurant_sogaeting | 63 | 73.5% | — | — | — |
| **A** | restaurant_sanggyeollye | 63 | 72.5% | — | — | — |
| **A** | eol | 87 | 68.6% | — | — | all_eol |
| **A** | cat_feeding_shared | 56 | 66.1% | — | 「새와 벌레」 | — |
| **A** | restaurant_biz_meeting | 63 | 63.8% | — | — | — |
| **A** | restaurant_date | 63 | 61.6% | — | — | — |
| **A** | cat_feeding_evenweight | 60 | 60.6% | — | 「새와 벌레」 | — |
| **A** | childcare_party | 63 | 60.1% | — | — | — |
| **A** | restaurant_elders | 63 | 60.1% | — | — | — |
| **A** | cat_feeding_plainvalue | 67 | 58.0% | — | 「새와 벌레」 | — |
| **A** | community_cat_feeding | 69 | 57.2% | — | 「새와 벌레」 | — |
| **A** | restaurant_brunch | 63 | 55.6% | — | — | — |
| **A** | smoking_area | 63 | 54.0% | — | — | — |
| **A** | elderdrive | 69 | 53.4% | — | — | all_elderdrive |
| **A** | restaurant_kids | 63 | 52.6% | — | — | — |
| **A** | workmind | 87 | 52.3% | — | — | all_workmind |
| **A** | restaurant_office_lunch | 63 | 46.0% | — | — | — |
| **A** | cat_feeding_party | 65 | 44.9% | — | 「사료와 물」 | — |
| **A** | childcare | 87 | 43.3% | — | — | all_childcare |
| **A** | cat_feeding_harm | 54 | 43.2% | — | 「새와 벌레」 | — |
| **A** | remotewatch | 87 | 40.6% | — | — | all_remotewatch |
| **A** | caregiverprotect | 69 | 38.2% | — | — | all_caregiverprotect |
| **A** | garden_plot | 63 | 38.1% | — | — | — |
| **A** | floor_noise | 63 | 37.3% | — | — | — |
| **A** | restaurant_solo | 63 | 31.5% | — | — | — |
| **A** | examaccom | 81 | 29.8% | — | — | — |
| **A** | smoking_area_party | 81 | 29.2% | — | — | — |
| **A** | euthanasia | 87 | 28.5% | — | — | all_euthanasia |
| **A** | recycling_room | 81 | 25.3% | — | — | — |
| **B** | recycling_room_party | 63 | 40.2% | 돌아오는시각 | — | — |
| **B** | community_room | 63 | 24.9% | 인원수용 | — | — |
| **B** | parentalreturn | 81 | 23.7% | 안정성 | — | — |
| **B** | shelter | 87 | 21.8% | 이용사례 | — | all_shelter |
| **B** | notice_vote | 18 | 19.4% | 때 | — | — |
| **B** | ambulance | 69 | 16.7% | 응대속도 | — | all_ambulance |
| **B** | study_seat | 18 | 14.8% | 혼자있기 · 조용함 | — | — |
| **B** | book_room | 18 | 13.0% | 돈 | — | — |
| **B** | rehab_exercise | 18 | 8.3% | 지원맞춤 · 깨끗함 | — | — |
| **B** | summer_pool | 18 | 8.3% | 돈 · 자리 | — | — |
| **C** | carebalance | 54 | 34.3% | 관계친밀도 · 응대속도 · 지속가능성 | — | — |
| **C** | cat_feeding_days_list | 81 | 14.0% | 연속 · 익숙함 · 위생 · 통행 | 「매일 저녁 사료와 물」 · 「목요일과 토요일」 · 「새와 벌레」 | — |
| **C** | paint_care | 18 | 13.9% | 전문성 · 이용사례 · 자리 · 깨끗함 | — | — |
| **C** | playground_floor | 18 | 10.2% | 이용사례 · 몸다침 · 마음 | — | — |
| **C** | festival_yard | 18 | 9.3% | 때 · 돈 · 혼자있기 | — | — |
| **C** | song_class | 18 | 7.4% | 때 · 닿기 · 조용함 · 지원맞춤 | — | — |
| **C** | tool_lending | 18 | 5.6% | 닿기 · 지원맞춤 · 전문성 · 해온일 | — | — |
| **C** | hospital_escort | 18 | 3.7% | 혼자있기 · 몸다침 · 마음 · 이용사례 | — | — |
| **C** | cat_feeding_entry_list | 54 | 2.2% | 날씨 · 통행 · 위생 · 마주침 | 「비와 눈을 맞지 않는다」 · 「담장과 담장 사이」 · 「유모차와 짐수레」 · 「새와 벌레」 | — |
| **C** | kimjang_share | 18 | 0.9% | 깨끗함 · 이용사례 · 마음 · 규범 · 닿기 | — | — |
| **C** | cat_feeding_entry_party | 18 | 0.0% | 끼니 · 날씨 · 길목 · 통행 · 위생 · 마주침 | 「비와 눈을 맞지 않는다」 · 「담장과 담장 사이」 · 「유모차와 짐수레」 · 「새와 벌레」 | — |

## 지문이 여럿인 재료 (판마다 다른 재료를 가리킨다 — 섞어 세면 안 된다)

- issue_cat_feeding_evenweight — 지문 ['b88402f6b2a1', 'bdc190a4f80b']
- issue_cat_feeding_plainvalue — 지문 ['19e2d8f33484', 'dd584f366467']
- issue_community_cat_feeding — 지문 ['6840d0ae3e08', '7d3f036fd62b']
- issue_cat_feeding_party — 지문 ['aba5675b00ac', 'e64beb9f44e7']
