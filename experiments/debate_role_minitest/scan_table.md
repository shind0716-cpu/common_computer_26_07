# 앵커 스캔 생존 표 — 토론 배역 미니테스트

> 탐색 · 사전등록 없음 · n=1/셀 · **수치 인용 금지** (WORKORDER 2026-08-19).
> 개인 = 그 라운드 발화의 앵커 적중 팩트 수(/12) · 채널 = 양측 합집합.
> r3 의 상대(O) 칸은 설계상 없음(O3 생략) — 채널 r3 = S3 단독.

| 팔 | 모델 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | 상대 신규(자기 대비) r0→r2 |
|---|---|---|---|---|---|
| advance | gemini-flash | 6→5→4→6 | 1→4→3 | 7→8→6→6 | 1→3→2 |
| advance | gpt-mini | 8→8→7→8 | 6→5→4 | 11→11→9→8 | 6→1→1 |
| natural | gemini-flash | 3→1→3→3 | 2→1→0 | 5→1→3→3 | 2→0→0 |
| natural | gpt-mini | 9→9→9→9 | 5→5→4 | 9→9→9→9 | 5→1→0 |
| stubborn | gemini-flash | 4→3→2→4 | 1→1→1 | 5→4→3→4 | 1→0→0 |
| stubborn | gpt-mini | 8→6→6→8 | 3→3→3 | 9→8→8→8 | 3→0→0 |

## MT2 추가분 (WORKORDER2 2026-08-19) — 기존 행 무수정, 아래 덧붙임

> 탐색 · 사전등록 없음 · n=1~2/셀 · **수치 인용 금지**.
> revision = 수정형 장르(첫 발화만 성명서형) · nostance = 성명서형·양측 입장 없음.
> 신규 컬럼 — S/O 신규 = 그 화자의 자기 이전 발화 대비 신규 앵커 수 ·
> 탈락 = 직전 자기 발화 대비 빠진 앵커 수 (fact_id 목록은 scan_result.json).

| 런 | 모델 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | O 신규 r0→r2 | S 신규 r0→r3 | S 탈락 r1→r3 | O 탈락 r1→r2 |
|---|---|---|---|---|---|---|---|---|
| nostance_geminiflash | gemini-flash | 2→3→3→3 | 3→3→3 | 3→5→3→3 | 3→0→0 | 2→3→0→0 | 2→2→0 | 0→0 |
| nostance_gptmini | gpt-mini | 8→5→5→5 | 3→5→5 | 8→5→5→5 | 3→2→0 | 8→0→0→0 | 3→0→0 | 0→0 |
| revision_geminiflash_run1 | gemini-flash | 4→6→6→5 | 1→1→2 | 5→6→6→5 | 1→1→1 | 4→2→0→0 | 0→0→1 | 1→0 |
| revision_geminiflash_run2 | gemini-flash | 5→5→5→4 | 1→3→2 | 6→6→6→4 | 1→2→0 | 5→0→0→0 | 0→0→1 | 0→1 |
| revision_gptmini_run1 | gpt-mini | 3→7→8→7 | 4→7→7 | 6→9→9→7 | 4→3→0 | 3→4→1→0 | 0→0→1 | 0→0 |
| revision_gptmini_run2 | gpt-mini | 9→9→9→9 | 6→7→6 | 9→9→9→9 | 6→2→0 | 9→0→0→0 | 0→0→0 | 1→1 |

## MT3 추가분 (WORKORDER3 2026-08-19) — 기존 행 무수정, 아래 덧붙임

> 탐색 · 사전등록 없음 · n=2/셀 · **수치 인용 금지**.
> note = 수첩 500자+상대 직전 글 · prev = 자기 직전 글+상대 직전 글 —
> r0 이후 사실 12개·토론 전문 화면 소멸. 수첩 = 라운드별 수첩(adopted) 내
> 앵커 수(S r0→r3 · O r0→r2, prev 팔은 —) · 복귀 = 복귀 사건 수(내 보유
> 소멸→상대 발화 등장→내 재등장) · 오염 = 상대 우호 사실의 내 수첩 등장 자리
> 수. fact_id·favors·critical 상세는 scan_result.json.

| 런 | 기억 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | 수첩 S r0→r3 | 수첩 O r0→r2 | 복귀 | 오염 |
|---|---|---|---|---|---|---|---|---|
| note_geminiflash_run1 | note | 4→7→2→2 | 1→1→1 | 5→8→3→2 | 7→3→2→1 | 3→1→1 | 0 | 1 |
| note_geminiflash_run2 | note | 3→3→4→4 | 1→2→1 | 4→3→4→4 | 5→4→4→3 | 2→1→1 | 0 | 4 |
| note_gptmini_run1 | note | 10→7→6→5 | 4→5→5 | 10→9→8→5 | 8→6→5→5 | 4→5→5 | 0 | 5 |
| note_gptmini_run2 | note | 5→5→5→5 | 10→6→6 | 10→7→7→5 | 5→5→5→5 | 6→6→6 | 0 | 7 |
| prev_geminiflash_run1 | prev | 4→4→3→3 | 0→1→1 | 4→4→3→3 | — | — | 0 | 0 |
| prev_geminiflash_run2 | prev | 6→5→1→0 | 1→0→1 | 7→5→1→0 | — | — | 0 | 0 |
| prev_gptmini_run1 | prev | 9→10→10→10 | 5→8→9 | 10→10→10→10 | — | — | 0 | 0 |
| prev_gptmini_run2 | prev | 8→8→8→9 | 5→8→9 | 9→9→9→9 | — | — | 0 | 0 |

## MT4 추가분 (WORKORDER4 2026-08-20) — 기존 행 무수정, 아래 덧붙임

> 탐색 · 사전등록 없음 · n=2/셀 · **수치 인용 금지**.
> 비대칭 기억(승인 기본안): S = 수첩 500자+상대 직전 글(MT3 note 축자) ·
> O = 전체 기억+배역(stubborn = 대조분석 §3-1 수정 문안 · advance = 1호
> 축자). 드롭 S(기회) = S 드롭 사건 수(괄호 = 그중 상대가 이후 말해준
> 사건 수 — §2-2 복귀율의 분모) · 복귀 = 복귀 사건 수 · 오염 = 상대 우호
> 사실의 S 수첩 등장 자리 수 · O 신규 = 자기 이전 발화 대비 신규 앵커
> (1호 방식 배역 이행 점검). 상세는 scan_result.json 의 drop_events.

| 런 | 배역 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | 수첩 S r0→r3 | 드롭 S(기회) | 복귀 | 오염 | O 신규 r0→r2 |
|---|---|---|---|---|---|---|---|---|---|
| advancenote_geminiflash_run1 | advance | 3→4→5→4 | 2→3→0 | 5→7→5→4 | 6→5→5→5 | 1(0) | 0 | 4 | 2→1→0 |
| advancenote_geminiflash_run2 | advance | 5→1→2→2 | 1→3→1 | 6→4→3→2 | 5→2→2→2 | 4(1) | 1 | 1 | 1→2→1 |
| advancenote_gptmini_run1 | advance | 5→4→5→5 | 4→4→3 | 8→7→8→5 | 6→5→5→5 | 3(0) | 0 | 4 | 4→1→0 |
| advancenote_gptmini_run2 | advance | 7→5→6→5 | 4→5→4 | 9→9→8→5 | 7→6→6→5 | 3(1) | 0 | 3 | 4→2→1 |
| stubbornnote_geminiflash_run1 | stubborn | 4→4→5→5 | 4→4→4 | 8→8→8→5 | 5→5→6→4 | 1(0) | 0 | 4 | 4→0→0 |
| stubbornnote_geminiflash_run2 | stubborn | 5→5→4→3 | 2→2→2 | 7→7→6→3 | 6→4→4→3 | 3(0) | 0 | 4 | 2→0→0 |
| stubbornnote_gptmini_run1 | stubborn | 8→8→7→7 | 6→6→6 | 11→11→11→7 | 8→8→8→8 | 0(0) | 0 | 4 | 6→0→0 |
| stubbornnote_gptmini_run2 | stubborn | 5→6→5→6 | 3→3→3 | 7→8→7→6 | 6→6→6→6 | 0(0) | 0 | 4 | 3→0→0 |

## MT5 추가분 (WORKORDER5 2026-08-20) — 기존 행 무수정, 아래 덧붙임

> 탐색 · 사전등록 없음 · n=2/셀 · **수치 인용 금지**.
> 직전 글 × 상대 성격(비대칭 유지): S = 자기 직전 글+상대 직전 글(MT3
> prev 축자, 수첩 콜 없음) · O = 전체 기억+배역(MT4와 축자 동일).
> 드롭 S(기회) = S 드롭 사건 수(괄호 = 그중 상대가 이후 말해준 사건 수) ·
> 복귀 = 복귀 사건 수 · O 신규 = 자기 이전 발화 대비 신규 앵커(배역 이행
> 점검). 상세는 scan_result.json 의 drop_events.

| 런 | 배역 | 개인 S r0→r3 | 개인 O r0→r2 | 채널 r0→r3 | 드롭 S(기회) | 복귀 | O 신규 r0→r2 |
|---|---|---|---|---|---|---|---|
| advanceprev_geminiflash_run1 | advance | 3→2→3→1 | 1→2→2 | 4→4→4→1 | 3(0) | 0 | 1→1→2 |
| advanceprev_geminiflash_run2 | advance | 6→1→3→1 | 2→4→2 | 7→5→5→1 | 7(0) | 0 | 2→3→0 |
| advanceprev_gptmini_run1 | advance | 7→9→8→8 | 7→4→4 | 11→10→9→8 | 1(0) | 0 | 7→0→1 |
| advanceprev_gptmini_run2 | advance | 6→7→6→7 | 7→4→5 | 10→10→9→7 | 1(1) | 0 | 7→1→1 |
| stubbornprev_geminiflash_run1 | stubborn | 3→3→4→5 | 4→4→4 | 7→7→7→5 | 0(0) | 0 | 4→0→0 |
| stubbornprev_geminiflash_run2 | stubborn | 3→1→1→1 | 1→1→1 | 4→2→2→1 | 3(0) | 0 | 1→0→0 |
| stubbornprev_gptmini_run1 | stubborn | 9→9→9→9 | 5→5→5 | 10→10→10→9 | 0(0) | 0 | 5→0→0 |
| stubbornprev_gptmini_run2 | stubborn | 7→7→7→7 | 4→4→4 | 9→9→9→7 | 0(0) | 0 | 4→0→0 |
