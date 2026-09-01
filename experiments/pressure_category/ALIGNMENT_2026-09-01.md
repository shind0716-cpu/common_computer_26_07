# 정렬 대장 — 지금 원자료로 무엇을 말할 수 있나 (2026-09-01, 기계 생성물)

> `align_audit.py` 가 찍는다. **기준은 지금 `runs/` 에 있는 판**이고, 재료·판독·세트가
> 그 판과 맞는지를 본다. 밑줄 폴더(드라이런·정찰·격리)는 원자료 대조에서 뺐다.

## ① 원자료 — 판의 재료 지문이 현행 재료와 같은가

| 폴더 | 일치 | 어긋남 | 재료 없음 |
|---|---:|---:|---:|
| `_collision_belief1_20260831` | 2 | 0 | 0 |
| `_dry` | 1024 | 84 | 47 |
| `_scout` | 0 | 120 | 18 |
| `_stale_hash` | 0 | 20 | 0 |
| `claude-haiku` | 879 | 0 | 0 |
| `gemini-flash` | 1064 | 0 | 6 |
| `glm` | 2 | 14 | 0 |
| `gpt` | 753 | 4 | 2 |

밑줄 폴더 밖에서 어긋난 판 **18개**:

| 폴더 | 재료 | 조건 | 판의 지문 | 현행 지문 | 실행일 |
|---|---|---|---|---|---|
| `glm` | cat_feeding_evenweight | C0/A | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `glm` | cat_feeding_evenweight | C0/B | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `glm` | cat_feeding_evenweight | c2r0/A | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `glm` | cat_feeding_evenweight | c2r0/B | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `glm` | cat_feeding_party | C0/A | `aba5675b00ac` | `e64beb9f44e7` | 2026-08-25 |
| `glm` | cat_feeding_party | C0/B | `aba5675b00ac` | `e64beb9f44e7` | 2026-08-25 |
| `glm` | cat_feeding_plainvalue | C0/A | `19e2d8f33484` | `dd584f366467` | 2026-08-25 |
| `glm` | cat_feeding_plainvalue | C0/B | `19e2d8f33484` | `dd584f366467` | 2026-08-25 |
| `glm` | cat_feeding_plainvalue | c2r0/A | `19e2d8f33484` | `dd584f366467` | 2026-08-25 |
| `glm` | cat_feeding_plainvalue | c2r0/B | `19e2d8f33484` | `dd584f366467` | 2026-08-25 |
| `glm` | community_cat_feeding | C0/A | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |
| `glm` | community_cat_feeding | C0/B | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |
| `glm` | community_cat_feeding | c2r0/A | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |
| `glm` | community_cat_feeding | c2r0/B | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |
| `gpt` | cat_feeding_evenweight | c2r0/A | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `gpt` | cat_feeding_evenweight | c2r0/B | `b88402f6b2a1` | `bdc190a4f80b` | 2026-08-25 |
| `gpt` | community_cat_feeding | c2r0/A | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |
| `gpt` | community_cat_feeding | c2r0/B | `6840d0ae3e08` | `7d3f036fd62b` | 2026-08-25 |

## ② 판독 — READ60 이 현행 재료를 가리키는가

판독이 붙은 재료 **30벌** 가운데 현행 재료와 정렬 **22벌** · 어긋남 **8벌**.

어긋난 벌: ambulance, caregiverprotect, childcare, elderdrive, eol, euthanasia, remotewatch, workmind

이 여덟 벌은 판정 뒤에 재료가 개정되어 새 재료로 다시 돌았다. **원자료는 정렬돼 있고**
판독만 옛 재료 기준이다. 다만 **옛 판이 통째로 남아 있다** — `runs/_stale_hash/` 에
여덟 벌 × A·B = **16판이 전부 8/27 로 온전하다**(재료마다 지문 하나씩, 확인함).

**그래서 쓸 수 있는 온전한 기준이 둘이다.**

| 기준 | 판을 어디서 | 판독 | 벌 |
|---|---|---|---:|
| §23 그대로 | 8벌은 `runs/_stale_hash/` · 22벌은 `runs/gpt/` | READ60 그대로 | 30 |
| 이 문서 §④ | 전부 `runs/gpt/` (현행 경로) | READ60 중 정렬분 | 22 |

둘 다 **판독과 판이 같은 시점을 가리킨다.** 없는 것은 세 번째 — 「현행 판 + 새 판독」이고,
그건 **여덟 벌을 다시 읽어야 존재한다.** §23 을 인용할 때는 여덟 벌의 판이 지금
`runs/gpt/` 가 아니라 `_stale_hash/` 에 있다는 것만 적으면 된다.

### ②-2. §23 을 돌려보려면 — 재료 판본이 어디 있나

세 겹이 8/27 판본이어야 하는데 **재료만 트리에 없다.** 지문에서 역추적한 좌표다 —
커밋을 믿지 말고 지문으로 확인하면 된다.

| 재료 | `_stale_hash` 판이 적은 지문 | 그 판본이 있는 커밋 |
|---|---|---|
| ambulance | `e1f08f1e6780` | `41b00cd` (2026-08-27) |
| caregiverprotect | `5d52af973265` | `41b00cd` (2026-08-27) |
| childcare | `8edd71acb639` | `41b00cd` (2026-08-27) |
| elderdrive | `49e6ee9e74f1` | `41b00cd` (2026-08-27) |
| eol | `67aa60670810` | `41b00cd` (2026-08-27) |
| euthanasia | `6f69e5b27adb` | `abfb629` (2026-08-26) |
| remotewatch | `11bf523fb35c` | `41b00cd` (2026-08-27) |
| workmind | `8d6b1aed3ea0` | `41b00cd` (2026-08-27) |

**커밋 하나로 안 묶인다.** `issue_euthanasia` 는 `a17936e` 에서 지워졌다가 `8d8fcaa` 에서
다시 생겨 `8d8fcaa^` 에 없다 — 그 판본은 `abfb629` 에 있다. 나머지 일곱은 `8d8fcaa^` 다.

판독은 `READ60_*` 그대로, 판은 `runs/_stale_hash/gpt/` 다. 셋을 맞추면 §23 이 돌아간다.

## ③ 가치 세트 — 세트의 카테고리가 현행 재료와 같은가

카테고리를 지목하는 세트 **40개** 중 정렬 **31** · 어긋남 **9**.

어긋남: `all_ambulance`, `all_caregiverprotect`, `all_childcare`, `all_elderdrive`, `all_eol`, `all_euthanasia`, `all_remotewatch`, `all_shelter`, `all_workmind`

전부 재료 개정 전에 만든 옛 올세트다. 지우지 않고 두되 **기준선으로 쓰지 않는다** —
지목하는 낱말이 현행 재료의 카테고리와 한 개도 안 겹친다.

### ③-2. 지문 — 세트·각본이 적어 둔 재료 지문

위 카테고리 대조는 **재료 카테고리를 지목하는 세트에만** 걸린다. 신념 세트와 서열 세트는
카드 이름을 `items[].category` 에 두는데 그건 일부러 재료 밖 낱말이라 대조 상대가 아니다.
그런 세트도 `materials_hash` 는 갖고 있으므로 지문으로 잰다. 각본도 같다.

| 무엇 | 지문 일치 | 지문 없음 | 어긋남 |
|---|---:|---:|---:|
| 가치 세트 | 78 | 31 | 0 |
| 압박 각본 | 46 | 3 | 0 |

지문 없는 것은 지문 칸이 생기기 전에 만든 옛 세트다(카테고리 대조로만 잰다).

## ④ 주 판정 재계산 — 현행 경로의 22쌍

눈금은 `analyze_stage1.py` 머리말 그대로다. 살았다 = 보 ∪ 부 ∪ 변, 짝 단위 `d = p안 − p밖`.
**이건 §23 을 대체하는 값이 아니라 부분집합 값이다** — §23 의 30쌍도 (②의 표대로) 유효하다.

| 코더 | 층 | 쌍 | 양수 | 음수 | 동점 | 중앙 d | 부호검정 p |
|---|---|---:|---:|---:|---:|---:|---:|
| 코더 A | (i) 첫 수첩 진입 | 22 | **22** | 0 | 0 | +0.333 | 4.8e-07 |
| 코더 A | (ii) 이후 생존 | 21 | **6** | 3 | 12 | +0.000 | 0.51 |
| 헤르메스 | (i) 첫 수첩 진입 | 22 | **21** | 0 | 1 | +0.333 | 9.5e-07 |
| 헤르메스 | (ii) 이후 생존 | 21 | **8** | 3 | 10 | +0.000 | 0.23 |

**§23 의 30쌍과 견주면 방향이 같고 부분집합이 더 선명하다** — 30쌍에서 (i) 25/30 · 중앙 +0.250 이던 것이
22쌍에서 22/22 · 중앙 +0.333 이 된다. 빠진 여덟 벌은 §23-6 이 이미 「격차가 0에 가깝다」고
적어 둔 현수 재료라, 선명해진 것은 새 발견이 아니라 **약한 무대를 뺀 결과**다.
(ii) 는 두 기준 모두 기각이고 동점이 절반이라는 천장도 그대로다.

⚠ **관문 수도 기준에 따라 다르다** (2026-09-01 피어 감사). 관문은 `run_C0_{A,B}_rep1.json` 의
`final_poll` 둘만 보는데, 개정된 여덟 벌은 8/31 판으로 갈렸다. **8/27 판 기준 21/30 ·
현행 판 기준 23/30** 이다(childcare 가 8/27 에는 같은 답이라 탈락, 8/31 에는 갈려 통과).
판을 바꾼 커밋은 `8d8fcaa`(재료 재업로드) 뿐 아니라 **`6466eb3`**(8/31, 옛 판 18개를
`_stale_hash` 로 옮기고 같은 경로를 새 판으로 채움)이다. §23 의 21/30 은 8/27 기준이고,
위 22쌍 재판정은 **판독과 판이 둘 다 8/27 인 22벌**만 쓰므로 안이 맞는다(확인함).

## 그래서 무엇을 쓸 수 있나

| 산출물 | 근거 | 판정 |
|---|---|---|
| `SELECTION_live30` §23 (H0·H3′·H6 판정) | 8/27 60판 + 판독 1,424칸 | **유효** — 판독과 판이 같은 시점이다. 인용할 때 여덟 벌의 판이 `_stale_hash/` 에 있다고만 적는다 |
| READ60 판독 원장 (30벌 κ 0.817 · 정렬 22벌 부분집합 κ 0.832) | 같음 | **유효** — 옛 판과 짝지으면 30벌, 현행 경로만 쓰면 22벌 |
| `analyze_stage1.py` | 결과 보기 전 커밋 | **안 돈다** — 여덟 벌에서 사실 id 대조에 걸린다. 고치지 않고 둔다(사전고정 코드) |
| `READOUT_belief1` (신념 66판) | 8/31 하이쿠 | **유효** — 지문 전건 일치 |
| `ALL11_*` receipt·manifest (올세트 33판) | 9/1 gpt | **유효** |
| `AGG_all11_*` · `READOUT_all11` · `USABLE_MATERIALS` | 9/1 전수 741판, 지문 대조 통과 | **유효** — 다만 표식 기준이라 탐색 등급 |
| 옛 올세트 `values/all_*.json` 9개 | 재료 개정 전 | **못 쓴다** (③) |

## 보고서를 쓸 때 여는 것 · 안 여는 것

잣대는 하나다 — **1차 보고서가 인용할 근거인가.** 「닫음」은 폐기가 아니라
*이번 보고서를 쓰는 동안 열지 않아도 된다*는 뜻이다. 파일은 그대로 둔다.

트랙 문서 **53편** — 연다 **13** · 원장이라 안 연다 **20** · 이번 보고서와 무관 **20**.

### 연다

| 문서 | 왜 |
|---|---|
| `STOCK_2026-09-01.md` | **보고서 재료.** 인용할 수치가 전부 여기 있다 — 여기부터 연다 |
| `ALIGNMENT_2026-09-01.md` | 입구. 무엇을 쓸 수 있는지가 여기 있다 |
| `SELECTION_live30_2026-08-27.md` | §23 주 판정. 156KB 중 이 절만 연다 |
| `PREREG_v0.md` | 1차 사전고정 — 예측과 판정선 |
| `READ60_kappa_all.md` | 판독 신뢰도 κ 0.817 |
| `PREREG_belief1_2026-08-31.md` | 신념 트랙 사전고정 |
| `READOUT_belief1_2026-08-31.md` | 신념 66판 판독 — 수첩이 신조문이 된다 |
| `READOUT_all11_2026-09-01.md` | 올세트·전수 741판 집계 |
| `AGG_all11_TABLES_2026-09-01.md` | 위 보고서의 표 원본 |
| `USABLE_MATERIALS_2026-09-01.md` | 재료 등급 — 표식 수치를 인용해도 되는 벌 |
| `GUIDE_scenario_writing_2026-08-25.md` | §2 표식 한계 — 한계 절의 근거 |
| `READPLAN_ab_2026-09-01.md` | A/B 를 belief1 방식으로 물을 문항 초안 |
| `PREREG_packW_2026-09-01.md` | 팩 가 사전고정 — 판독 전에 걸어 둔 예측과 판정선 |

### 원장이라 안 연다 — 인용할 때만

`READ60_pack_b1_r0.md` · `READ60_pack_b1_last.md` · `READ60_pack_b2_r0.md` · `READ60_pack_b2_last.md` · `READ60_pack_b3_r0.md` · `READ60_pack_b3_last.md` · `READ60_judgments_b1_r0.md` · `READ60_judgments_b1_last.md` · `READ60_judgments_b2_r0.md` · `READ60_judgments_b2_last.md` · `READ60_judgments_b3.md` · `READ60_adjudication_b1_r0.md` · `READ60_PROMPT_coder.md` · `READ20_judgments.md` · `READ20_PROTOCOL.md` · `MATERIALS_REGISTRY_2026-08-27.md` · `REFERENCE_source_values_2026-08-25.md` · `scan_table.md` · `DIAG_numword_2026-09-01.md` · `WORKLOG.md`

### 이번 보고서와 무관

| 문서 | 사유 |
|---|---|
| `MATERIALS_JOHAN12_PLAN_2026-08-30.md` | 신작 12벌 제작 계획. 1차 30벌과 다른 재료 |
| `PLAN_restaurant_side_assignment_2026-08-26.md` | 재료 제작 계획 |
| `PLAN_value_once_2026-08-27.md` | 실행자 미정, 안 돌았다 |
| `PROBLEM_care12_2026-08-26.md` | 현수 재료 검토 — 판독이 어긋난 여덟 벌 쪽 |
| `REVIEW_care12_favors_2026-08-26.md` | 같음 |
| `GATE_FAIL_DIAGNOSIS_2026-08-27.md` | 관문 탈락 진단 — 캣맘은 1차에서 전부 탈락해 보고서에 안 든다 |
| `LIMITS_cat_feeding_2026-08-25.md` | 같음 |
| `HANDOFF_CAT_FEEDING_REVIEW_2026-08-25.md` | 같음 |
| `READOUT_track2_2026-08-25.md` | 제안 — 사전고정 전이고 안 돌았다 |
| `기획_신념세트_4안_2026-08-31.md` | 기획 단계 문서. 확정본은 PREREG_belief1 |
| `READOUT_gpt_haikuset_2026-08-31.md` | 다른 배치 집계 — 1차 보고서 범위 밖 |
| `RESEARCH_value_vs_belief_lit_2026-08-31.md` | 문헌 메모. 인용은 노션 카드로 |
| `TRACTION_belief2_2026-09-01.md` | 기획 2(합리주의) — 아직 안 돌았다 |
| `TRACTION_belief1_2026-08-31.md` | 종이 채점 — 판정은 READOUT_belief1 이 한다 |
| `TRACTION_rest6_2026-09-01.md` | 기획 3(식당 서열) — 아직 안 돌았다 |
| `PROBE_belief1_2026-08-31.md` | 탐침 — 관문이 아니다 |
| `PROBE_belief3_2026-09-01.md` | 기획 3 탐침 — 아직 안 돌았다 |
| `WORKORDER_신념트랙_템플릿_2026-09-01.md` | 작업 지시서 |
| `식당_시나리오_12가지.md` | 그루 원문 — 기획 3 재료 |
| `README_팀원용.md` | 트랙 안내 |

## 다음에 이 사고를 안 내려면

재료를 고칠 때 그 재료를 가리키는 것이 셋이다 — **판 · 판독 · 세트**. 지금까지 판은
격리로 챙겼고(`_stale_hash`) 세트는 새로 지었지만 **판독은 챙기는 자리가 없었다.**
재료 개정 절차에 「그 재료의 판독을 무효로 표시한다」를 넣을지가 결정 사항이다.
