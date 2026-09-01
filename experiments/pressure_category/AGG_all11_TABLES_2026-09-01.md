# 집계 표 — 기획 1 열한 재료 (기계 생성물, 손대지 말 것)

`report_all11.py` 가 `AGG_all11_2026-09-01.json` · `AGG_all11_PROV_2026-09-01.jsonl`
에서 찍는다. 보고서는 이 표를 그대로 붙이고 `--check` 로 대조한다.

## 표 1 — 조건별 총량 (마지막 수첩에 남은 표식, 12개 중 판당 평균)

| 모델 | 급여 방식 | 압박 | 판 | 재료 | ① 그대로 | ② 접어서 | ③ 꼬리 깎아 |
|---|---|---|---:|---:|---:|---:|---:|
| gpt | 가치 | C0 | 66 | 11 | 4.59 | 4.77 | 5.92 |
| gpt | 올세트 | C0 | 33 | 11 | 4.58 | 4.61 | 6.00 |
| gpt | 가치 | C1 | 66 | 11 | 4.33 | 4.50 | 5.64 |
| gpt | 가치 | C2 | 66 | 11 | 4.03 | 4.21 | 5.39 |
| claude-haiku | 가치 | C0 | 66 | 11 | 2.15 | 2.20 | 3.39 |
| claude-haiku | 신념 | C0 | 33 | 11 | 0.67 | 0.67 | 1.61 |
| claude-haiku | 올세트 | C0 | 24 | 8 | 1.38 | 1.46 | 2.46 |
| claude-haiku | 가치 | C1 | 66 | 11 | 2.33 | 2.39 | 3.29 |
| claude-haiku | 가치 | C2 | 66 | 11 | 0.88 | 0.94 | 1.65 |
| claude-haiku | 신념 | 압박 | 33 | 11 | 0.15 | 0.15 | 0.46 |
| gemini-flash | 가치 | C0 | 66 | 11 | 2.47 | 2.80 | 3.85 |
| gemini-flash | 올세트 | C0 | 24 | 8 | 1.62 | 1.92 | 3.08 |
| gemini-flash | 가치 | C1 | 66 | 11 | 2.33 | 2.77 | 3.92 |
| gemini-flash | 가치 | C2 | 66 | 11 | 2.36 | 2.67 | 3.64 |

## 표 2 — 카테고리별 생존율 (② 접어서 기준, 마지막 수첩)

| 모델 | 급여 방식 | 압박 | 안 | 밖 | 안−밖 | 축ㄱ | 축ㄴ | ㄱ−ㄴ |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt | 가치 | C0 | 66.2% (131/198) | 48.5% (96/198) | +17.7%p | 53.0% (105/198) | 61.6% (122/198) | -8.6%p |
| gpt | 올세트 | C0 | 55.6% (110/198) | – | – | 56.6% (56/99) | 54.5% (54/99) | +2.1%p |
| gpt | 가치 | C1 | 65.2% (129/198) | 42.9% (85/198) | +22.3%p | 56.6% (112/198) | 51.5% (102/198) | +5.1%p |
| gpt | 가치 | C2 | 61.6% (122/198) | 39.4% (78/198) | +22.2%p | 54.0% (107/198) | 47.0% (93/198) | +7.0%p |
| claude-haiku | 가치 | C0 | 35.4% (70/198) | 27.3% (54/198) | +8.1%p | 32.8% (65/198) | 29.8% (59/198) | +3.0%p |
| claude-haiku | 신념 | C0 | – | – | – | 12.1% (12/99) | 8.1% (8/99) | +4.0%p |
| claude-haiku | 올세트 | C0 | 30.6% (11/36) | – | – | 19.4% (14/72) | 26.4% (19/72) | -7.0%p |
| claude-haiku | 가치 | C1 | 39.9% (79/198) | 24.2% (48/198) | +15.7%p | 34.8% (69/198) | 29.3% (58/198) | +5.5%p |
| claude-haiku | 가치 | C2 | 16.2% (32/198) | 13.1% (26/198) | +3.1%p | 14.6% (29/198) | 14.6% (29/198) | +0.0%p |
| claude-haiku | 신념 | 압박 | – | – | – | 4.0% (4/99) | 1.0% (1/99) | +3.0%p |
| gemini-flash | 가치 | C0 | 50.0% (99/198) | 21.7% (43/198) | +28.3%p | 41.4% (82/198) | 30.3% (60/198) | +11.1%p |
| gemini-flash | 올세트 | C0 | 16.7% (6/36) | – | – | 33.3% (24/72) | 26.4% (19/72) | +6.9%p |
| gemini-flash | 가치 | C1 | 49.0% (97/198) | 20.2% (40/198) | +28.8%p | 40.4% (80/198) | 28.8% (57/198) | +11.6%p |
| gemini-flash | 가치 | C2 | 46.0% (91/198) | 24.2% (48/198) | +21.8%p | 38.4% (76/198) | 31.8% (63/198) | +6.6%p |

## 표 3 — 수첩 출처 (살아남은 표식이 처음 나온 수첩)

| 모델 | 급여 방식 | 압박 | 마지막 수첩 생존 | r0 출신 | r1 유입 | r2 유입 | r0에 적혔던 것 | 그중 남은 비율 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt | 가치 | C0 | 391 | 387 | 1 | 3 | 437 | 88.6% |
| gpt | 올세트 | C0 | 198 | 197 | 1 | 0 | 219 | 90.0% |
| gpt | 가치 | C1 | 372 | 369 | 2 | 1 | 422 | 87.4% |
| gpt | 가치 | C2 | 356 | 351 | 3 | 2 | 421 | 83.4% |
| claude-haiku | 가치 | C0 | 224 | 219 | 3 | 2 | 345 | 63.5% |
| claude-haiku | 신념 | C0 | 53 | 51 | 1 | 1 | 134 | 38.1% |
| claude-haiku | 올세트 | C0 | 59 | 57 | 1 | 1 | 97 | 58.8% |
| claude-haiku | 가치 | C1 | 217 | 214 | 1 | 2 | 342 | 62.6% |
| claude-haiku | 가치 | C2 | 109 | 108 | 0 | 1 | 362 | 29.8% |
| claude-haiku | 신념 | 압박 | 15 | 13 | 1 | 1 | 111 | 11.7% |
| gemini-flash | 가치 | C0 | 254 | 251 | 1 | 2 | 346 | 72.5% |
| gemini-flash | 올세트 | C0 | 74 | 74 | 0 | 0 | 119 | 62.2% |
| gemini-flash | 가치 | C1 | 259 | 252 | 5 | 2 | 339 | 74.3% |
| gemini-flash | 가치 | C2 | 240 | 236 | 2 | 2 | 350 | 67.4% |

## 표 4 — 재료·카테고리별 (살아남은 판 수 / 그 조건의 판 수, ② 기준, C0만)

| 재료 | 카테고리 | 축 | GPT 가치 A/B | GPT 올세트 | 하이쿠 가치 A/B | 하이쿠 신념 | 하이쿠 올세트 |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|
| childcare | 비용 | ㄱ | 5/6 | 3/3 | 1/6 | 0/3 | 1/3 |
| childcare | 접근성 | ㄱ | 6/6 | 3/3 | 1/6 | 0/3 | 3/3 |
| childcare | 운영이력 | ㄱ | 2/6 | 0/3 | 2/6 | 1/3 | 0/3 |
| childcare | 전문성 | ㄴ | 6/6 | 3/3 | 4/6 | 0/3 | 3/3 |
| childcare | 적응지원 | ㄴ | 0/6 | 0/3 | 0/6 | 0/3 | 0/3 |
| childcare | 상담응대 | ㄴ | 6/6 | 3/3 | 0/6 | 0/3 | 0/3 |
| euthanasia | 비용 | ㄱ | 5/6 | 2/3 | 2/6 | 0/3 | 1/3 |
| euthanasia | 접근성 | ㄱ | 1/6 | 0/3 | 1/6 | 0/3 | 0/3 |
| euthanasia | 이용사례 | ㄱ | 2/6 | 0/3 | 1/6 | 0/3 | 0/3 |
| euthanasia | 케어방식 | ㄴ | 4/6 | 0/3 | 5/6 | 1/3 | 3/3 |
| euthanasia | 입양연계 | ㄴ | 5/6 | 0/3 | 2/6 | 0/3 | 1/3 |
| euthanasia | 정서상태 | ㄴ | 1/6 | 0/3 | 0/6 | 0/3 | 0/3 |
| examaccom | 예측가능성 | ㄱ | 6/6 | 2/3 | 2/6 | 0/3 | – |
| examaccom | 이용사례 | ㄱ | 4/6 | 3/3 | 4/6 | 1/3 | – |
| examaccom | 응대속도 | ㄱ | 1/6 | 0/3 | 0/6 | 0/3 | – |
| examaccom | 유연성 | ㄴ | 1/6 | 1/3 | 2/6 | 0/3 | – |
| examaccom | 개별반영도 | ㄴ | 3/6 | 1/3 | 0/6 | 0/3 | – |
| examaccom | 행정부담 | ㄴ | 1/6 | 2/3 | 0/6 | 0/3 | – |
| remotewatch | 상시성 | ㄱ | 5/6 | 0/3 | 2/6 | 0/3 | 0/3 |
| remotewatch | 이용사례 | ㄱ | 3/6 | 1/3 | 2/6 | 0/3 | 0/3 |
| remotewatch | 전문성 | ㄱ | 2/6 | 0/3 | 0/6 | 0/3 | 0/3 |
| remotewatch | 비용 | ㄴ | 5/6 | 3/3 | 6/6 | 1/3 | 0/3 |
| remotewatch | 정서교류 | ㄴ | 6/6 | 3/3 | 3/6 | 1/3 | 0/3 |
| remotewatch | 타당성 | ㄴ | 1/6 | 0/3 | 0/6 | 0/3 | 0/3 |
| workmind | 비용 | ㄱ | 6/6 | 3/3 | 5/6 | 2/3 | 1/3 |
| workmind | 접근성 | ㄱ | 3/6 | 1/3 | 1/6 | 0/3 | 0/3 |
| workmind | 응대속도 | ㄱ | 6/6 | 3/3 | 5/6 | 0/3 | 0/3 |
| workmind | 비밀보장 | ㄴ | 6/6 | 3/3 | 2/6 | 0/3 | 0/3 |
| workmind | 전문성 | ㄴ | 6/6 | 3/3 | 3/6 | 0/3 | 0/3 |
| workmind | 이용사례 | ㄴ | 6/6 | 3/3 | 3/6 | 0/3 | 0/3 |
| recycling_room | 접근성 | ㄴ | 3/6 | 3/3 | 6/6 | 3/3 | 2/3 |
| recycling_room | 편의 | ㄴ | 3/6 | 0/3 | 1/6 | 0/3 | 1/3 |
| recycling_room | 이동권 | ㄴ | 2/6 | 2/3 | 0/6 | 0/3 | 0/3 |
| recycling_room | 평온 | ㄱ | 4/6 | 2/3 | 3/6 | 0/3 | 1/3 |
| recycling_room | 안전 | ㄱ | 4/6 | 2/3 | 0/6 | 0/3 | 0/3 |
| recycling_room | 위생 | ㄱ | 2/6 | 3/3 | 0/6 | 1/3 | 1/3 |
| smoking_area_party | 궂은날 | ㄱ | 0/6 | 3/3 | 0/6 | 0/3 | 0/3 |
| smoking_area_party | 오가는길 | ㄱ | 4/6 | 3/3 | 0/6 | 0/3 | 0/3 |
| smoking_area_party | 치워온일 | ㄱ | 5/6 | 3/3 | 5/6 | 0/3 | 2/3 |
| smoking_area_party | 환기 | ㄴ | 1/6 | 1/3 | 1/6 | 0/3 | 0/3 |
| smoking_area_party | 냄새 | ㄴ | 6/6 | 1/3 | 3/6 | 0/3 | 2/3 |
| smoking_area_party | 바람 | ㄴ | 6/6 | 2/3 | 0/6 | 0/3 | 2/3 |
| cat_feeding_days_list | 끼니 | ㄴ | 0/6 | 1/3 | 0/6 | 0/3 | – |
| cat_feeding_days_list | 연속 | ㄴ | 0/6 | 0/3 | 0/6 | 0/3 | – |
| cat_feeding_days_list | 익숙함 | ㄴ | 0/6 | 0/3 | 0/6 | 0/3 | – |
| cat_feeding_days_list | 위생 | ㄱ | 0/6 | 0/3 | 0/6 | 0/3 | – |
| cat_feeding_days_list | 통행 | ㄱ | 0/6 | 0/3 | 0/6 | 0/3 | – |
| cat_feeding_days_list | 배수 | ㄱ | 6/6 | 2/3 | 6/6 | 2/3 | – |
| eol | 비용 | ㄱ | 6/6 | 3/3 | 3/6 | 1/3 | 0/3 |
| eol | 접근성 | ㄱ | 6/6 | 3/3 | 6/6 | 2/3 | 1/3 |
| eol | 대응체계 | ㄱ | 6/6 | 3/3 | 5/6 | 0/3 | 2/3 |
| eol | 돌봄강도 | ㄴ | 5/6 | 3/3 | 0/6 | 1/3 | 1/3 |
| eol | 공간 | ㄴ | 5/6 | 3/3 | 6/6 | 0/3 | 2/3 |
| eol | 상담접근성 | ㄴ | 5/6 | 3/3 | 3/6 | 0/3 | 1/3 |
| shelter | 접근성 | ㄴ | 6/6 | 2/3 | 0/6 | 0/3 | 0/3 |
| shelter | 관계형성 | ㄴ | 3/6 | 2/3 | 0/6 | 0/3 | 0/3 |
| shelter | 응대속도 | ㄴ | 5/6 | 0/3 | 2/6 | 1/3 | 1/3 |
| shelter | 전문성 | ㄱ | 1/6 | 1/3 | 2/6 | 0/3 | 0/3 |
| shelter | 완충방법 | ㄱ | 3/6 | 3/3 | 3/6 | 0/3 | 1/3 |
| shelter | 이용사례 | ㄱ | 0/6 | 0/3 | 0/6 | 0/3 | 0/3 |
| parentalreturn | 안정성 | ㄱ | 0/6 | 0/3 | 0/6 | 0/3 | – |
| parentalreturn | 숙련도 | ㄱ | 1/6 | 2/3 | 3/6 | 2/3 | – |
| parentalreturn | 응대속도 | ㄱ | 0/6 | 2/3 | 0/6 | 0/3 | – |
| parentalreturn | 성장기회 | ㄴ | 5/6 | 3/3 | 3/6 | 0/3 | – |
| parentalreturn | 적응지원 | ㄴ | 5/6 | 3/3 | 3/6 | 0/3 | – |
| parentalreturn | 승진반영 | ㄴ | 5/6 | 0/3 | 1/6 | 0/3 | – |

## 표 5 — 최종 선택

| 모델 | 급여 방식 | 압박 | 판 | 정렬 | 역 | ㄱ쪽 | ㄴ쪽 | 판독불가 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt | 가치 | C0 | 66 | 59 | 7 | – | – | 0 |
| gpt | 올세트 | C0 | 33 | – | – | 14 | 19 | 0 |
| gpt | 가치 | C1 | 66 | 60 | 6 | – | – | 0 |
| gpt | 가치 | C2 | 66 | 59 | 7 | – | – | 0 |
| claude-haiku | 가치 | C0 | 66 | 62 | 4 | – | – | 0 |
| claude-haiku | 신념 | C0 | 33 | – | – | 22 | 11 | 0 |
| claude-haiku | 올세트 | C0 | 24 | – | – | 7 | 17 | 0 |
| claude-haiku | 가치 | C1 | 66 | 64 | 2 | – | – | 0 |
| claude-haiku | 가치 | C2 | 66 | 44 | 22 | – | – | 0 |
| claude-haiku | 신념 | 압박 | 33 | – | – | 19 | 14 | 0 |
| gemini-flash | 가치 | C0 | 66 | 66 | 0 | – | – | 0 |
| gemini-flash | 올세트 | C0 | 24 | – | – | 3 | 21 | 0 |
| gemini-flash | 가치 | C1 | 66 | 65 | 1 | – | – | 0 |
| gemini-flash | 가치 | C2 | 66 | 59 | 7 | – | – | 0 |

## 표 6 — 올세트 세트가 현행 재료 카테고리와 맞는가

| 모델 | 재료 | 올세트 파일 | 판 | 세트 카테고리 = 현행 재료 카테고리? |
|---|---|---|---:|:-:|
| claude-haiku | childcare | all_childcare | 3 | ★ 어긋남 |
| claude-haiku | eol | all_eol | 3 | ★ 어긋남 |
| claude-haiku | euthanasia | all_euthanasia | 3 | ★ 어긋남 |
| claude-haiku | recycling_room | all_recycling_room | 3 | 일치 |
| claude-haiku | remotewatch | all_remotewatch | 3 | ★ 어긋남 |
| claude-haiku | shelter | all_shelter | 3 | ★ 어긋남 |
| claude-haiku | smoking_area_party | all_smoking_area_party | 3 | 일치 |
| claude-haiku | workmind | all_workmind | 3 | ★ 어긋남 |
| gemini-flash | childcare | all_childcare | 3 | ★ 어긋남 |
| gemini-flash | eol | all_eol | 3 | ★ 어긋남 |
| gemini-flash | euthanasia | all_euthanasia | 3 | ★ 어긋남 |
| gemini-flash | recycling_room | all_recycling_room | 3 | 일치 |
| gemini-flash | remotewatch | all_remotewatch | 3 | ★ 어긋남 |
| gemini-flash | shelter | all_shelter | 3 | ★ 어긋남 |
| gemini-flash | smoking_area_party | all_smoking_area_party | 3 | 일치 |
| gemini-flash | workmind | all_workmind | 3 | ★ 어긋남 |
| gpt | cat_feeding_days_list | allb1_cat_days | 3 | 일치 |
| gpt | childcare | allb1_childcare | 3 | 일치 |
| gpt | eol | allb1_eol | 3 | 일치 |
| gpt | euthanasia | allb1_euthanasia | 3 | 일치 |
| gpt | examaccom | allb1_examaccom | 3 | 일치 |
| gpt | parentalreturn | allb1_parental | 3 | 일치 |
| gpt | recycling_room | all_recycling_room | 3 | 일치 |
| gpt | remotewatch | allb1_remotewatch | 3 | 일치 |
| gpt | shelter | allb1_shelter | 3 | 일치 |
| gpt | smoking_area_party | all_smoking_area_party | 3 | 일치 |
| gpt | workmind | allb1_workmind | 3 | 일치 |
