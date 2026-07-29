# P3 전달 관문 설계 — 새 세션 컨텍스트 (2026-07-27, 요한 측)

> 이 문서는 세션 핸드오프용이다. 목표: **설계 모드**로 `docs/P3_TRANSMISSION_DESIGN.md`(전달 관문 측정 설계 + 사전고정 판별표) 초안을 작성한다.
> **코드 0줄 원칙**: §F 규율 + 요한의 보드 약속(7/27 입장 정리 — "미니 H2 전에는 계약·설계 문서까지만"). 이 세션의 산출물은 문서뿐이다.

## 1. 임무와 경계

- 요한은 보드(7/27 입장 정리)에서 **전달 관문의 도달 프로브 설계 초안 담당을 확정**했다.
- 넘버링: P2(입력 계약, docs/P2_INPUT_CONTRACT.md)의 후속 = P3.
- 경계: judge 확정 사양(Sonnet 단일·temp 0·n=3 다수결·votes 원본 보존) 불가침. 스키마 v0.2 불가침 — 계약 변경 필요 사항은 보드 안건으로만. 관측 트랙 동결(회사 데이터 walkerhill·mystery 사용 금지 — ESA 픽스처만). recall.py는 민옥 파일(협의 사안, 설계에서 "확장 요청"으로만 다룸).

## 2. 배경 (한 단락)

민옥 7/24 "소실 4관문": 보유(회고 프로브)→발화(FAR·팩트시계)→**전달(계기 공백 ← 이 설계의 대상)**→사용(결정 과제). 동범 7/24 재정의안: 앵커 논문(DelibTrace, arXiv:2606.03032)의 최대 비약 FOL-8 = "말함(saying)을 재고 앎(knowing)을 결론". 전달 관문 정의: "원래 모르던 에이전트가 획득했는가".

## 3. 확정된 설계 골격 (이번 세션에서 재논의 불필요 — 문서화 대상)

**핵심 통찰**: 전달을 한 겹으로 재면 FOL-8을 반복한다 → **2층 설계**.
- 층 1 **전달-발화**: 로그 전수, LLM 0. 비보유자 언급 = assignment `assigned_fact_ids` × judgment `agents_mentioning` 교차.
- 층 2 **전달-보유**: 회고 프로브(recall) 확장을 비보유자에게 — 표본 조사.

**(비보유자 a, 팩트 f) 2×2 분할표**: 언급×회고 → 확증 전달 / 에코(말했으나 안 남음, 층1 거짓양성) / 침묵 획득(층1 사각) / 미전달.

**보정식 (지표 연결의 핵심)**: α=P(회고실패|언급, 비보유), β=P(회고성공|비언급, 비보유)
> **TR̂ = TSR·(1−α) + (1−TSR)·β** — 층 2가 층 1의 보정 계수를 공급 (오분류 보정 구조).

**층 1 지표**: 전달 폭 B(f)=비보유 언급자 수 · TSR(f)=B/|N(f)| · 획득 hazard h_acq(t)=FACTCLOCK_PREREG의 검열 형식화를 획득 방향으로 이식(t₀=도입, 우측 검열 동일) · **경로 분해** T_organic vs T_ledger(`ledger_inject` 이후 언급 분리 — H2 기전 분해: 장부 효과가 재발화인가 실전달인가) · **prior 층화**(facts.prior — low-prior만 추적자 정본).

## 4. 결정 포인트 D1~D5 (문서의 뼈대, 기울기 포함)

| # | 결정 | 요한 기울기 |
|---|---|---|
| D1 | 전달의 조작적 정의 | 층1(발화) 주지표 + 층2(보유) 검증층 — 2층 고정 |
| D2 | prior 조건화 | low-prior 추적자 주보고, 밴드별 병기 |
| D3 | 재주입 처리 | organic/ledger-mediated 분리 집계 |
| D4 | 좌표계 | 팩트 시계 t=0 정렬 + 검열 규칙 이식 |
| D5 | 잣대 | judge_fact·agents_mentioning 재사용, 사람 대조=패키지 B 프레임(같은 30표본으로 귀속 kappa 무료 획득) |

**필수 조항**: "귀속 kappa 하한 미달 시 B·TSR은 탐색적 지위로 강등". 사전고정 판별표는 FACTCLOCK_PREREG(커밋 ff9f7de)·U자 재해석(b4ebf50)과 동일 절차 — 데이터 확인 전 커밋, 사후 변경은 append 전용.

**사전고정 가설 후보 2개**: ① 전달 폭↑ → 소실 hazard↓ (종말부 침묵 3건의 재해석: B=0이라 복구 경로 부재였나) ② 담화 전진(민옥 2-그램 자카드 전진 점수) × 전달의 상호작용.

## 5. ML 개선 부록 (우선순위·거버넌스 구분 확정)

1. **Dawid-Skene를 보존된 votes에 사후 적용** — 비용 0·사양 충돌 0(다수결이 정본, 이건 분석층 재해석). 항목별 confidence + 귀속 신뢰도. 문서에 명세로 포함.
2. **이산시간 hazard 회귀 + run 랜덤효과** — 비용 0. 공변량(B·prior·critical·전진 점수) 동시 투입, run 클러스터(민옥 데모 자인 한계 "전이 27개 9런 비독립") 해결. 문서에 모형식 포함.
3. **임베딩 2단 판정** — 최대 비용 레버(judge가 비용 ~90%), 이미 보드 열린 질문. 임계값은 패키지 B 라벨 ROC로, 절차 사전고정. 측정기 변경 = 보드 확정 필요.
4. **카나리아 팩트**(prior=0 보장 허구 디테일 주입) — β를 준-실측으로 격상. 데이터 변경 = 리더 사안. 현저성 통제 명시 필요.
5. **MC 회고 프로브 + 능동 표본추출**(층1 confidence 낮은 쌍에 예산 집중, TR̂는 구간 보고 + "구간이 판별 기준 걸치면 무승부" 규칙) — 층 2 실행 시점. 민옥 open/pointed AB에 MC 팔 추가 제안.
6. (보류) 전달 그래프·확산 모델 — 토폴로지 실험과 접속, 현 규모(라운드 3~4)에 과잉.

## 6. 재료 확인 완료 (전부 현행 v0.2 계약)

- assignment: `seed`, `agents[].assigned_fact_ids`
- judgment: `stages[].facts[].agents_mentioning`, `votes`(원본 보존), `summary.judge_health`
- debate.jsonl: `utterance`(round·agent_id·response_text), `ledger_inject`(round·injected_fact_ids)
- facts.json: `prior.score`, `critical`, `tags`
- 참조 코드(읽기): modules/survival.py(fact_clock 검열 형식화), modules/recall.py(민옥 — replay+프리필+judge_fact 재사용), FACTCLOCK_PREREG.md

## 7. 주변 상태 (2026-07-27 기준)

- PR #16(뷰어: run 기록/베이스라인 자격 판정 + 쌍 비교 뷰) **머지됨**. 뷰어 우선순위 = 베이스라인 기록 + 가설 검증 생태계(변주 축 ①config ②ledger ③아키텍처 — ③ 라벨 `condition` 필드를 v0.3 안건으로 보드 제안함).
- 실호출 베이스라인 부재: 선결 2건(debate_temperature 1.2 → 400·무음 공백 / judge_model 별칭 Sonnet 5 → temp0 거부) 사람 확정 대기. 미니 H2 미집행 — 그래서 P3도 문서까지만.
- 동기화(민옥·요한) 일정 대기 — 안건: 재정의안·4관문·Track R/S, kappa 프로토콜 개정(요한 채택 선언), §4-3 동결 의존성, 선결 2건, v0.3(+condition).
- master 최신: 담화 전진 실험(`experiments/discourse_progression/` — PREREG_v0.2), debate·judge 진행 계기판.

## 8. 이번 세션의 작업 순서 제안

1. survival.py의 검열 형식화·FACTCLOCK_PREREG·recall.py 독스트링·P2_INPUT_CONTRACT를 읽어 표기·형식을 맞춘다 (기존 문서 계보 계승).
2. `docs/P3_TRANSMISSION_DESIGN.md` 초안: 목적 → 2층 구조 → 지표 정의(형식화) → D1~D5 → 오염원·방어 → 사전고정 판별표(초안, "커밋 = 고정" 명시) → ML 부록(위 1·2는 명세, 3~5는 보드 안건 표기) → 실행 단계(§F 게이트).
3. 사람 검토 포인트를 `[요한 확인]`으로 표기. 보드 공유 글 초안까지 준비(게시는 승인 후).
