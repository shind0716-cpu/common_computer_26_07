# 논문 재현 트랙 — 러너·데이터 (사양: docs/proposals/PAPER_REPRO_HANDOFF.md)

지위: **확정** (사양 §12 결정 반영분의 구현. 계약 변경 없음 — SCHEMA §1′ 은 이미 등재됨)

## 모듈 3개 현황 (사양 §5)

| 모듈 | 담당 트랙 | 상태 |
|---|---|---|
| 1. loader (`load_issues.py`, LLM 0콜) | 접합 계층 (클로드) | **완료** — 200건 + manifest, 전건 validate 통과 |
| 2. extractor (저자 facts.py 3단계 계승) | 저자 충실 계층 (GPT) | 미착수 — 프로브(`probe_extract.py`)가 선행 검증 |
| 3. perspective 배분기 (저자 perspective.py 계승) | 저자 충실 계층 (GPT) | 미착수 |

## 투트랙 경계 (2026-08-10 요한 확정)

- **저자 충실 계층(GPT)**: extractor·perspective 배분기. 산출 = `data/facts/`·`data/assignments/`.
- **접합 계층(클로드)**: loader·인덱스↔ID 브리지·ledger/access_window 접합·validate·뷰어.
- 두 계층은 **파일 계약으로만** 만난다. 병렬 작업의 의존은 `fixtures/` 가 끊는다 —
  하류는 픽스처 위에서 먼저 완성하고, 실데이터가 오면 갈아 끼운다.

### 브리지 계약 (픽스처가 시연하는 것)

1. **`facts[]` 배열 순서 = 저자 위치 인덱스.** 각 팩트에 `origin_index`(0-based)를 병기한다.
   저자 파이프라인(perspective·evaluate)은 전부 위치로 말하므로, 이 대응이 끊기면
   ledger·access_window 로 이어지는 회수 경로가 끊긴다.
2. **관점은 정확히 4개** (저자 `check_available`: `len(pers) == 4`).
3. **같은 관점의 yes/no 쌍은 `assigned_fact_ids` 완전 동일** (저자 `obtain_discussion_initial`:
   관점당 fact_text 1회 조립 후 yes/no 공유). 저자 관점 산출(인덱스 배열)은
   `assignment.perspective_sets.sets` 에 원형 보존한다.
4. `issue_id` 는 **원본 710건 파일 내 위치(1-based) 순번** `issue_ethics_NNNN` — 표본을
   다시 뽑아도 같은 항목은 같은 id. 원본 id 는 `source_meta.origin_id`.

## 실행

```
PYTHONUTF8=1 python experiments/paper_repro/load_issues.py --n 20 --dry   # 리허설 (0콜·파일 미작성)
PYTHONUTF8=1 python experiments/paper_repro/load_issues.py                # 본 실행 (기본 n=200)
PYTHONUTF8=1 python experiments/paper_repro/probe_extract.py --dry        # 프로브 리허설
python -m modules.validate experiments/paper_repro/data/issues/issue_ethics_0036.json
```

## 편차 대장 (사양 §10-6 의무 기재 · 상세는 HANDOFF §12-3)

| # | 내용 |
|---|---|
| P-1 | 출력 상한: 저자는 `max_tokens` 미전송, 우리는 러너에서만 `llm.MAX_TOKENS=8192` 완화 (`llm.py` 무수정 확정) |
| P-2 | 표본 출처: 710건은 논문 선별 기준의 역추정 — 논문과 동일 집합 아님 |
| P-3 | 동점 28건 제외 (`RIGHT==WRONG` 인데 `gold_label` 전건 YES 강제) → 풀 682건 |
| P-4 | 추출 모델 gpt-5 — 저자 시점과 같은 스냅숏 보장 없음 |
| P-5 | `facts_select` 질문 = 항목별 영어 제목 (일치율 0.938 실측 — 영향 없음) |
| — | 라이선스 미확인: `usage_approved` 전건 `null` (Scruples/RealNews 확인 별도 항목) |

계약 밖 필드 2건(`gold`·`origin_question` 보존, `tags: []`)은 사양 §7 임시 처리 — 계약 변경 아님.

## 데이터

- `data/issues/` — loader 산출 200건 (seed 20260810, 층화 NO 116/YES 84)
- `data/sample_manifest.json` — 원본 sha256 · 시드 · 뽑힌 id 전량 · 편차
- `fixtures/data/` — 계약 픽스처 3종 (issue·facts·assignment). **측정에 넣지 말 것**
- `probe/` — 착수 전 검증 41콜 (응답 원문 전량)

---

## 브리지 (접합 계층 · 2026-08-10 플랜 승인분 — append)

| 파일 | 역할 |
|---|---|
| `bridge.py` | 인덱스↔ID 번역 정본(`origin_index` 기준, 불일치 즉사) + 저자 축 판정물(`{round, agent_id, matched_fact_ids}`) → judgment 스키마 5 변환(`aggregation: author_axis_n1` 각인). 이 변환이 없으면 `ledger.missing_facts` 가 저자 축 산출의 전 팩트를 소실로 오판한다 |
| `configs/fx_smoke.yaml` | 접합 리허설 전용 좌표 (파일럿 config 아님) |
| `rehearse_splice.py` | 0콜 통합 리허설 — 픽스처 임시 사본으로 debate→judge→ledger→access_window + 저자 축 변환 전 사슬 완주 실증 |
| `test_bridge.py` | 번역 왕복 항등·H1 방어·변환 정확성·계약 validate (GPT 담당 test_runners.py 와 분리) |
| `verify_bridge.py` **H8** | bridge 실물 왕복을 데이터로 검사 (H5 는 독립 구현 대조, H8 은 번역층 자체) |

### 편차 대장 추가분

| # | 내용 |
|---|---|
| P-6 | **판정기 언어.** 우리 축 `JUDGE_SYSTEM` 은 한국어인데 재현 트랙 팩트·발화는 영어다. 기존 파일럿(한국어)과 잣대 조건이 다름. 비-Anthropic judge 는 `prompt_ver` 에 `+merged_system` 부가 |
| P-7 | **발화 온도 1.0.** 저자 상수는 1.2. 기존 팔들과의 비교 가능성을 위해 1.0 채택(요한 결정 8/10). 논문 좌표와의 불일치로 영구 기재 |

### 결정 대기 (다음 라운드 소관 — 파일럿 착수 전에 박을 것)

- **판정 축 예산 정정**: 사양 §6 "64콜/건"은 저자 축 전제. 우리 축이면 건당 ≈188콜(팩트 13 기준) — 어느 축으로 돌지 사전 고정 필요 (8/10 예고: "둘 다")
- **`evaluate_stance` 파킹 결정문**: 현재 어디에도 파킹돼 있지 않음(§2 는 resurgence 만). 안 재기로 하면 명시 파킹해야 §1 사후 지표 금지와 충돌 안 함
- **`question_exposed_ids` 산정 규칙**: 미정 시 access_window 영점이 조용히 전건 0
- **`prior` 부재**: 재현 트랙 facts 에 prior 없음 → 밴드 전건 unknown. 파일럿 결과 변수에서 밴드 층화 제외 명문화

---

## 역리뷰 반영 (2026-08-10 저녁 — GPT-sol 역리뷰 R-1~R-4, 접합 계층 수정분 append)

**R-1·R-2 (픽스처)** — assignment 픽스처 재작성: 각 관점이 critical 전부{0,1,2,5}를
포함하도록(연성 S3 시연), perspective 라벨을 라이브 배분기와 같은 `관점N` 관례로 통일.
**R-4 (loader)** — 원본 sha256 정본값(`CANONICAL_SHA256`)을 loader 에 박고 불일치 즉사.
issue_id 순번이 원본 파일 순서에 의존하므로, 재정렬/교체된 원본으로 재실행하면 같은
issue_id 가 다른 내용으로 덮어써지는 구멍이 있었다. 정본 교체는 `--expect-sha` 명시로만.

**R-3 — 브리지 계약 전체 목록 (위 「브리지 계약」 4항은 요약이었다. 강제되는 전 조건):**

| # | 조건 | 강제 지점 |
|---|---|---|
| 1 | `facts[]` 배열 순서 == `origin_index` (0-based) | verify_bridge H1 · bridge.fact_ids_in_order 즉사 |
| 2 | `fact_id` = `fact_ethics_NNNN_MM`, MM = origin_index+1 두 자리 | verify_bridge H1 |
| 3 | `critical` 은 bool · `tags` 는 `[]` | verify_bridge H2 · validate |
| 4 | extractor 좌표 gpt-5 / temperature 0 | verify_bridge H3 |
| 5 | 관점 정확히 4개 = 에이전트 8명, pro/con 쌍 `assigned_fact_ids` 완전 동일 | verify_bridge H4 · 저자 check_available |
| 6 | `perspective_sets.sets` 를 순서대로 번역한 결과 == `assigned_fact_ids` (왕복 항등) | verify_bridge H5(독립 구현)·H8(bridge 실물) |
| 7 | `assigned_fact_ids` ⊆ facts 전집합 · `seed` = 20260810 | verify_bridge H6 |
| 8 | `issue.source` = "paper" · `question` 명시(폴백 금지) | verify_bridge H7 · §1′ 경계 1 |

**상태표 갱신** — §「모듈 3개 현황」의 "미착수" 표기는 낡았다(append-only 라 위를 고치지
않는다). 현행: extractor·perspective 배분기 **구현 완료**(F-1~F-3 수정 반영, dry 통과),
실호출 800콜 승인됨(8/10). 실행 예시 추가분:

```
PYTHONUTF8=1 python experiments/paper_repro/extract_facts.py --dry        # 추출 리허설
PYTHONUTF8=1 python experiments/paper_repro/assign_perspective.py --dry   # 배분 리허설
PYTHONUTF8=1 python experiments/paper_repro/rehearse_splice.py            # 접합 0콜 완주
PYTHONUTF8=1 python experiments/paper_repro/verify_bridge.py              # 라이브 산출 게이트
```
