# 세션 컨텍스트 — 2026-07-29 (요한 측)

> 새 세션 핸드오프용. docs/CLAUDE.md 리추얼(보드 확인) → 이 문서 → WORKLOG.md 끝부분 순서로.
> 브랜치: feat/p3-transmission-layer1 (origin 대비 **12커밋 미푸시** — 이 세션 환경에 네트워크가
> 없어 미집행. 코드 세션에서 push 예정).
> 앞 문서: docs/SESSION_CONTEXT_0728_NIGHT.md (그대로 유효, 아래 §2가 그 미결 1건을 닫음)

## 1. 오늘(7/29)의 궤적 한 단락

세션 시작 리추얼(보드·색인 확인) → 보드에 요한 앞 미회신 없음 확인, 동기화 커닝페이퍼 작성 →
ts1 사전등록 검토 중 **ρ = D_B/D_A의 분모 폭발 위험** 발견, 이어 "새 발견이 약함"(프롬프트 원문이
이미 답이고 팔 B는 담화 전진과 겹침)으로 **ts1 보류 결정** → 정보 취합 과녁으로 재조준안(ka1
결핍 인식 프로브) 작성 → **연역 사슬 해부로 ka1 자체를 적대 검증, 지표 1건 기각**(trap 조건엔
정답 근거가 없어 정답률을 잴 수 없음 → 주지표를 "확신 철회"로 교체) → 민옥 통화 내용(발화⟹컨텍스트
존재) 공유받고 **resurgence 3건 원문 대조 착수** → carkey·esa 양쪽에서 **작화 0건 / 판정기
비일관성 실물 확인** → WORKLOG 정정 + 팀 메모리 전문·색인 게시(보드는 통화로 다뤄 생략).

## 2. 오늘의 핵심 발견 — 판정기 비일관성 (두 이슈 복제)

접근 없는 발화 **5건(carkey 3 + esa 2) 전부 판정기 산물, 작화 0건.** 민옥 명제(발화⟹컨텍스트
존재)를 **지지**한다. 대신 그 명제가 참일수록 "창이 0인데 발화 있음 = 창 계산이 틀림"이 되고,
우리 창은 판정 결과에서 재구성된다(`window_source: reconstructed`, `n_from_assembly: 0`).

- **carkey `fact_car_03`**: stage 1~3 unmentioned인데 그 3라운드 내내 3~4명이 "보행자 근접" 발화.
  동일 화자 agent_3의 거의 동일 문장이 stage 3=unmentioned / stage 4=mentioned.
- **esa `fact_esa_11`**: agent_8이 stage2 mentioned → stage3 **unmentioned** → stage4 mentioned
  (샌드위치). stage3엔 agent_4·8·6·2 네 명 전부 "갱신 임박" 발화.
- **esa `fact_esa_03` ★ 결정적**: stage2 "집주인 허락 없이 반입"(**원문에 더 가까움**)=unmentioned /
  stage3 "무단 반입"(더 축약)=mentioned. → **"판정기가 축약에 엄격하다"는 설명이 성립하지 않는다.**
  엄격도 문제가 아니라 비일관성.
- 같은 라운드 안에서도 화자 간 누락 확인(esa_03 stage1: agent_7만 계상, agent_1 누락).
- 양방향 오류: stance_support는 **과다** 계상(7/28 RADAR_V2_ML_MEMO R1 기처리), 축약 구체 팩트는
  **과소** 계상(오늘 신규). **방향이 반대라 총 FAR에서 상쇄되어 안 보인다.**

**파생 (제기 수준, 방향·크기 미상)**: 축약은 라운드가 갈수록 심해지고 판정 누락도 축약에 비례
→ **시간축에 걸린 편향**(표본 확대로 안 사라짐). 논문의 추상도 상승과 소실이 판정 층에서 하나가
다른 하나를 만들 수 있음. 그리고 **장부 on은 원문 재주입으로 발화가 원문에 근접 → 판정 용이성
상승** → 팔 간 차분에서도 상쇄 안 될 수 있음(앵무새 비판의 판정층 판본). 담화 전진 A′도 같은 노출.

## 3. 요한 결정 대기

1. **원격 push** — feat/p3-transmission-layer1 12커밋. untracked 4건(docs/SESSION_CONTEXT_0728_NIGHT.md ·
   docs/P3_SESSION_CONTEXT.md · configs/mini_h2_off.yaml · configs/mini_h2_v0.yaml) 동반 여부.
2. **ka1 착수 여부** — 재조준안 + 사슬 해부는 세션 산출물로만 있고 리포 미커밋. 착수 시
   `experiments/knowledge_absence/PREREG.md`부터.
3. **ANTHROPIC_API_KEY** — 여전히 자리표시자. tp2(Sonnet) 러너는 대기 상태.

## 4. 바로 집을 수 있는 작업

- **접근 창 근거 한정 집행** (요한 동의·미실행, 오늘 필요성 확정) — 독스트링 "물리"→"판정 매개",
  원장에 evidence 등급(literal|judged) 필드, resurgence율을 자기 진단 지표로 격상.
- **축약 판정 기준 사전 명시** — 패키지 B 사람 라벨 지침. esa `fact_esa_03` 사례가 예시 문항으로
  그대로 사용 가능("집주인 허락 없이 반입 = 6주 전 허락 없이 개를 데려왔다인가").
- **ka1 PREREG** — 사슬 해부 반영판(주지표 = 확신 철회율, 대조 팔 K1′ 포함, 결론 사거리는
  "정밀 pull 불가 → 설계 분기"까지).

## 5. 지위·경계 주의 (실수 방지)

- 판정기는 tp1 파일럿용(gpt-5.4-mini·temp0·**n=1**), 팀 확정 judge 아님. 다만 **다수결은 호출
  비결정성만 누르고 판정 기준의 모호함은 못 누른다** — n=3이라 괜찮다고 덮지 말 것.
- 이슈 2종·run 1회. **일반화 금지.** 파일럿 1회에 가설 언어 금지(7/28 요한 교정).
- **tp1 접근 창 수치(사망 9/12·부활 3·유예 1라운드)는 재검토 전까지 인용 금지.**
  dryrun2(모의)는 판정 결정론적이라 영향 없음.
- **ts1 보류.** 저자 프롬프트 원문 확인(r0=낭독 / r1+=요약)은 실험 없이 성립하는 사실이라 유효 —
  정량화는 Track R 본재현에 팔 C로 편입.
- 저자 프롬프트(DelibTrace-main@afce3595) 라이선스 미표기 — **리포·팀 문서에 전문 복사 금지.**
- 보드 게시는 통화로 다룬 건이면 생략(7/29 요한 방침). 단 **기록층(팀 메모리·WORKLOG)은 통화가
  대체하지 않음.**
- 팀 메모리에 올리는 글은 강한 워딩 금지("참수 실험" → "과제 구조 분해 실험").

## 6. 재료 위치

| 것 | 위치 |
|---|---|
| 오늘 대조 원자료 | experiments/transmission_pilot/data/{judgment,debate}_issue_{carkey,esa}_tp1.* |
| 접근 원장 | experiments/transmission_pilot/data/access_report_*_tp1.json |
| 팀 메모리 전문(오늘분) | notion 3ac0261412b0815c90f8c60e9e226b49 (esa 복제분 append 포함) |
| 색인 | notion 39e0261412b08051bb6bd6178e7aeac3 · W3 맨 아래 |
| 관측 창 인벤토리 | docs/proposals/OBSERVATION_WINDOWS.md |
| 레이더 v2 메모(R1 = 과다 계상 기처리) | docs/proposals/RADAR_V2_ML_MEMO.md |
| ts1 PREREG(보류) | experiments/task_structure/PREREG.md |
| 히든 프로필(민옥) | experiments/hidden_profile/REPORT_v0.md |
| ka1 재조준안·사슬 해부 | **리포 밖 — 세션 산출물** (필요 시 재작성) |
