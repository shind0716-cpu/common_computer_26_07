# P3 전달 레이더 파일럿 (tp1) — 탐색적/데모 지위

> **지위**: 탐색적 — 정식 판정(H-T1·H-T2)은 미니 H2 실호출분에서. 브랜치 시제품(§F "브랜치는
> 자유") · 개인 키 별도 환경 집행(민옥 담화 전진 전례 계승). P3 팀 확정은 동기화 대기 중이며
> 이 파일럿은 그 확정과 무관하다(레이더 계기의 실가동 검증 + 첫 실측).
> 측정 정의의 정본: docs/P3_TRANSMISSION_DESIGN.md v1.0 (사전고정 커밋 a70470d — 실행 전 고정).

## 무엇을 했나

롤링 창 토론(자기·이웃 직전 발화만 — modules/debate_engine 정보 생태 재현)을 외부 모델로
2개 이슈에 대해 돌리고, v0.2 모양 산출물을 `modules/transmission.py`(레이더)에 그대로 물렸다.

| 런 | 이슈 | 재료 |
|---|---|---|
| tp1/esa | ESA(팀 정본 픽스처) | data/ 의 issue·facts·assignment 재사용(읽기 전용) |
| tp1/carkey | **안현수 7/27 둘째 이슈 후보 2** (「아버지 몰래 차 키를 숨겨야 할까요?」) | fixtures/ 수기 변환 — **후보 지위(팀 검수 전), 정본 승격과 무관. 검수에서 팩트가 바뀌면 본 수치는 이 버전 기준** |

변환 시 현수 님 원표의 "불리한 입장"→`harm_stance`, "critical 근거 한 줄"→`critical_rationale`,
"관점"→`perspective` 를 추가 필드로 보존했다(v0.2 소비자에 무해 — 라벨 증발 방지 실증).

## 설정 (민옥 담화 전진 정식 검증의 검증된 스택 계승)

- 생성: gpt-5.4-mini · temp 0.7(민옥 N1) · max 1024(N2) · seed 기록(N3 best-effort)
- 판정: gpt-5.4-mini · temp 0 · **n=1 단일 표** — **파일럿 판정기이며 팀 확정 judge
  (Sonnet·temp0·n3)가 아니다.** 의역 매칭(앵커 논문 B.5 관례).
- 프라이어 프로브: 민옥 확정 방식 v0(맥락 없이 팩트 지식 질의) — carkey 12/12 known=False
  (허구 팩트 = 천연 low-prior 추적자 실측 확인), ESA 는 일부 known=True(일반상식형).
- question 영점 스캔(v1.0 §3-2): 양쪽 모두 question_exposed 0건.
- 안전장치: 호출 상한 300/phase · 라운드 체크포인트 · **출력 절단 시 즉시 에러**(민옥 D1 교훈)
  · judge 파싱실패 카운트(양 런 모두 0).

## 편차 (전부 의도적·기록)

1. **rounds=4** (논문 상수 3): 엄격 u≥1 지표의 관측창 확보 목적.
2. **ESA question 오버라이드**: ESA issue 에 question 필드가 없고 title("…ESA 개 무단 반입
   신고…")이 팩트 요지를 누출 → 파일럿에서 "룸메이트를 집주인에게 신고해야 할까요?"로 지정
   (팀 파일 무수정). 둘째 이슈 채택 시 question 필드 지정 요청의 실증 근거.
3. 파일럿 판정기 n=1 (비용 — 확정 사양은 Anthropic judge 트랙 사안).

## 결과 (tp1, 탐색적 — 해석은 팀 메모리 전문/보드 보고 참조)

| 지표 | ESA | carkey |
|---|---|---|
| 쌍(비보유×팩트) | 72 | 72 |
| 획득(엄격 u≥1 / u0 즉답) | 17 / 13 | 6 / 6 |
| TSR_system 엄격 (상한) | 0.2361 (0.4167) | 0.0952 (0.1905) |
| low-prior 한정 TSR | 0.1818 | 0.0952 (전 팩트 low) |
| prior_suspect | 0 | 3 (전부 fact_car_12 — stance_support 팩트, round 0) |
| 음영(never_exposed) | 0 | 6 (fact_car_04 — 보유자가 발화 관문에서 이미 침묵) |
| judge 파싱실패 | 0 | 0 |

관측 하이라이트: ① carkey 엄격 획득 6건은 전부 **critical counter_evidence 2종**
(fact_car_03 위험 증거·fact_car_10 어머니 투석)에 몰렸고 전부 τ=r4(수렴 국면) —
h_acq 가 age 3 에서만 발화(0.1053). ② prior_suspect 방어선이 stance_support 팩트의
의역 거짓양성(발화 입장≈"형의 입장" 진술)을 정확히 걸러냄 — stance_support 태그는 추적자
부적합 후보(v2 개선 재료). ③ fact_car_04 음영 = "발화 관문에서 죽은 팩트는 전달 관문에
도달조차 못한다"의 첫 실측(4관문 연쇄). ④ ESA low-prior 층화가 TSR 을 0.236→0.182 로
끌어내림 — 일반상식형 팩트가 전달을 부풀린다는 D2 가정 실측.

## 비용·재현

총 248 LLM 호출(생성 80·판정 120·프로브 24·스캔 24), gpt-5.4-mini — 수 달러 수준.
재실행: 이 폴더의 run_pilot.py 를 phase 별로(파일 존재 시 스킵 — 체크포인트).
키는 리포 루트 .env(.gitignore 차단).

## 산출물 (data/ — 원자료 전부 커밋, CLAUDE.md 규칙 8)

debate_{issue}_{tp1}.jsonl · judgment_{issue}_{tp1}.json · prior_·question_scan_·
transmission_report_{issue}_{tp1}.json (레이더 사건 원장 + 집계 뷰 전문).

## 지위 갱신 (2026-08-13 append — 결과 표를 읽기 전에 볼 것)

이 README의 결과 표(TSR·음영·생명표)는 tp1 judgment(판정기 n=1) 위에 서 있다.
그 판정은 7/29 계기 점검에서 경계면 불안정이 실측됐고(fact_car_04 s0 재판정
n=5에서 5:0 뒤집힘 — WORKLOG 7/29), **`data/STATUS.md`가 `access_report_*`를
인용 금지, `transmission_report_*`를 재검토 대상으로 강등**했다. 뒤집힘이
사실이면 TSR 분모가 달라지고, 위 표의 "fact_car_04 음영 첫 실측"은 바로 그
뒤집힌 셀에 걸려 있다. 결과 표 원문은 append-only 규칙상 남겨 두며, 수치를
인용하려면 `data/STATUS.md`의 지위를 먼저 확인하라.
