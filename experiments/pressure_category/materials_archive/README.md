# materials_archive — 실험 도구가 안 보는 재료 보관함 (2026-09-03, 민옥 트랙)

> 지위: 정리 작업 (민옥 지시). 러너·검사기·콘솔·정렬 대장은 `materials/*.json` 한 층만 훑으므로,
> 여기 있는 재료는 **실험 도구 전체에서 보이지 않는다.** 내용은 한 글자도 안 고쳤다(이동만).
> 되돌리기: 파일을 `materials/`로 다시 옮기면 끝(파일 안 issue_id로 등록되므로 이름 그대로).

## 왜 옮겼나
9/3 기준 `materials/`에 67벌이 있었는데, 발표·보고서에 들어간 것은 정독 세트 11벌 + 단어 찾기 40 세트뿐이었다.
콘솔 드롭다운에 67벌이 떠서 처음 보는 사람이 어느 재료가 "쓰는 재료"인지 알 수 없었다.
`materials/`에는 **보고서에 들어간 40 세트(A+B, 37벌 — 3벌은 재료 파일이 이미 없음)만** 남긴다.

## 층 (판 수는 9/3 runs/ 실측: 3모델 가치 A/B × C0·C1·C2 × rep3 = 모델당 18판 기준)

| 폴더 | 벌 | 무엇 | 왜 여기 |
|---|---:|---|---|
| `C_gemini_only/` | 13 | gemini-flash 18판만 있고 claude-haiku·gpt 0. `issue_book_room` 등 12벌(요한 9/1 재료) + `cat_feeding_entry_party` | 보고서 어디에도 안 들어감. 3모델 비교 불가 |
| `D_unrun/` | 5 | 판 0 (`community_room_party`·`floor_noise_party`·`garden_plot_party`·`restaurant_family`·`restaurant_team_dinner`) | 한 번도 안 돌음 |
| `S_source/` | 12 | `src_*` — 요한이 9/1 식당 원문에서 다시 쓴 개발용 재료(파일 안 status: "development_only, 사람 검토 전, 실호출 전") | 실험 재료가 아니라 원천 |

`materials/`에 남긴 37벌 = 정독 세트 11 + 단어 찾기 세트 26. 단어 찾기 40 세트 중 `issue_community_room`·`issue_floor_noise`·`issue_garden_plot` 3벌은 판(runs/)은 있으나 재료 파일이 이전에 이름이 바뀌어 `materials/`에 없다(정렬 대장 9/1 「재료 없음」과 같은 항목) — 이 정리와 무관.

## 소유
C·S층 25벌은 요한이 만든 파일이다. 옮긴 사람은 민옥(SilenceBreaker)이고, 요한 쪽 작업에 필요하면 그냥 되돌려도 된다(보드에 한 줄).

## 마지막 실험 세트
마지막 실험(라벨 또는 신념)의 재료는 폴더가 아니라 목록으로 정한다 — `sets/FINAL_SET_11_2026-09-03.json`. 이유: 러너는 파일 안 issue_id로 등록하므로 목록이 폴더보다 안전하고, 옛 판 집계가 안 깨진다.

---

## 정정 1 (2026-09-04, 요한+클로드) — `D_unrun` 세 벌은 안 돈 게 아니었다

`community_room_party.json` · `floor_noise_party.json` · `garden_plot_party.json` 을
**`materials/` 로 되돌렸다.** 파일 내용은 안 건드렸고 이동만 했다.

**왜.** 이 셋은 「판 0」이 아니라 **각각 63판씩, 합 189판이 돌아 있다.**
파일 안 `issue_id` 가 `issue_community_room` · `issue_floor_noise` · `issue_garden_plot` 이고,
그 id 로 돈 판이 적어 둔 `materials_hash` 가 **이 파일들의 지문과 정확히 같다**
(`b9a22d30ebc5` · `953e800c0ca1` · `c018b6d7605e`, 63/63 일치). 다른 재료가 아니라
**바로 이 재료로 돈 판**이다.

파일 이름이 `*_party` 라 「안 돈 파티 변형」으로 보였을 것이다. 위 §「왜 옮겼나」가
이 셋을 「재료 파일이 이전에 이름이 바뀌어 `materials/` 에 없다 … 이 정리와 무관」이라
적었는데, 실은 **여기 D_unrun 에 있었다.**

**무엇이 달라지나.** 되돌리기 전에 `scan_pressure.py` 를 돌리면 새 판 759 가 들어오면서
**414 판이 조용히 빠졌다**(스캐너는 `materials/` 한 층만 읽는다). 되돌린 뒤에는
**들어옴 768 · 빠짐 234** 이고, 빠지는 234 는 `C_gemini_only` 13벌로 **의도한 정리 그대로**다.

`D_unrun` 에는 진짜 판 0 인 `restaurant_family` · `restaurant_team_dinner` 만 남겼다.
