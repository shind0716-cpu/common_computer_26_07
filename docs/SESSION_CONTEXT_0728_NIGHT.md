# 세션 컨텍스트 — 2026-07-28 밤 기준 (요한 측)

> 새 세션 핸드오프용. 먼저 docs/CLAUDE.md 리추얼(보드 확인) → 이 문서 → WORKLOG.md 끝부분 순서로.
> 브랜치: feat/p3-transmission-layer1 (master 머지 완료, 원격 push는 미실행 — 요한 결정 대기).

## 1. 오늘(7/28)의 궤적 한 단락

ChatGPT 외부 리뷰("우리 비판에도 역방향 비약 있음" + FOI 사슬 해부)를 소화 →
접근 창 계기(modules/access_window.py) 신설·tp1 실데이터 적용(resurgence 실물·stance 동형
오염 발견) → 접근 창 자기비판(판정 매개 — 발화만 근거) → 보드에서 채널 제어 축 승격 왕복
확인(P3 = 측정 대상 → 제어 플랫폼, config 표면 channel/summary_budget/window/rounds) →
"엄밀한 질문" 요구에서 **ts1 참수 실험 설계**(저자 프롬프트 원문 확인: "Ensure your post
mentions all facts" 실물) → PREREG v0.1 초안 커밋. 저녁에 민옥 측 히든 프로필 미니 테스트가
master 도착(시나리오 작동, 배분 결함 발견 — 배분 v2 필요).

## 2. 요한 결정 대기 (이게 최우선)

1. **ts1 PREREG [요한 확인] 4건** (experiments/task_structure/PREREG.md 맨 끝):
   P1 임계값(0.8/0.3)·시드 수(3)·ESA 보조 포함·팔 B others 문자열. 승인 → 그 커밋이 고정
   커밋 → 러너 구현.
2. **원격 push 여부** — 로컬 커밋 2건(세션 산출물 + master 머지) 미푸시.
3. **ANTHROPIC_API_KEY** — .env가 자리표시자(민옥 측도 401 독립 확인, D-h1). 키가 오면
   tp2(Sonnet 4.6·judge n=1, 러너 완성 상태) 즉시 실행 가능.

## 3. 바로 집을 수 있는 작업 후보

- **ts1 러너 구현** (PREREG 승인 후) — run_tp1 계승, 3팔×3시드, ~720콜/이슈, OpenAI 키로 가능.
- **resurgence 6건 원문 대조** (비용 0) — tp1 접근 원장의 접근 없는 발화(작화 vs judge 오탐
  판별). 좌표는 access_report_*_tp1.json에.
- **접근 창 근거 한정 반영** (요한이 동의한 방향, 미실행): 독스트링 "물리"→"판정 매개" 정정,
  원장에 evidence 등급(literal|judged) 필드, resurgence율 = 자기 진단 지표 격상.
- **동기화 커닝페이퍼** (일어난 일/정할 것/화젯거리) — 재료 전부 준비됨: 관측 창 4종
  (docs/proposals/OBSERVATION_WINDOWS.md), 매개 노출 강제 지점, 히든 프로필 접속 제안
  (토론 러너가 v0.2+prompt_assembly 모양이면 P3 층1·접근 창 무수정 접속, ⓖ 팩트-입장
  동형성 회피).

## 4. 지위·경계 주의 (실수 방지)

- ts1·tp1·tp2 전부 **탐색적 파일럿 레인**(개인 키·experiments/ 분리·정본 무접촉). 파일럿
  1회에 가설 언어 금지 — "계기가 생겨 보이게 됐다" 톤(7/28 요한 교정, 메모리
  no-overclaiming-single-runs).
- 저자 프롬프트(DelibTrace-main@afce3595)는 라이선스 미표기 — **리포·팀 문서에 전문 복사
  금지**, 로컬 참조만.
- recall.py·debate_engine 구조 변형·히든 프로필·배분 생성기 = 민옥 소관. 과녁 전환 전체
  확정 = 동기화 안건 1번.
- 알려진 기존 버그: test_viewmodel 크래시(별도 칩 발행됨, 우리 변경 무관).

## 5. 재료 위치 요약

| 것 | 위치 |
|---|---|
| 접근 창 계기·테스트 | modules/access_window.py · tests/test_access_window.py |
| tp1 접근 원장 실측 | experiments/transmission_pilot/data/access_report_*_tp1.json |
| ts1 참수 PREREG | experiments/task_structure/PREREG.md |
| tp2 Sonnet 러너(대기) | experiments/transmission_pilot/run_tp2_sonnet.py |
| 관측 창 인벤토리 | docs/proposals/OBSERVATION_WINDOWS.md |
| P3 해석 한정 append | docs/P3_TRANSMISSION_DESIGN.md 맨 끝 2건 |
| 히든 프로필(민옥) | experiments/hidden_profile/REPORT_v0.md |
| 저자 프롬프트 | ../DelibTrace-main/prompts/ (로컬 클론) |
