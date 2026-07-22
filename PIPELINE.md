# PIPELINE — 파이프라인 명세 v0 (팀 설계 제안)

> 2026-07-22 민옥. **제안 상태** — 주간 동기화에서 합의되면 v1 승격. append-only:
> 바뀌면 이 문서를 고쳐 쓰지 말고 아래에 새 절을 추가한다.
>
> 문서 분업: **SCHEMA.md** = 파일 계약 원문(무엇을 주고받나) · **DESIGN.md** = 왜 이렇게
> 짰나 · **이 문서** = 내 가설을 어디에 어떻게 끼우나(팀원 진입점).

## 0. 한 문장

팩트가 흘러가는 관(파이프라인)은 하나로 고정하고, 각자의 가설은 **config 변수 또는
모듈 슬롯**으로 끼운다 — **가설 하나 = 변수 하나 = yaml 한 벌**.

## 1. 데이터 흐름 — 파일 계약 6종

```
issue ──▶ facts ──▶ assignment ──▶ debate ──▶ judgment ──▶ 지표(FAR·survival)
(쟁점)   (원자팩트)  (누가뭘아나)     (토론로그)   (생존판정)    (소실률 곡선)
                                    ▲
                        ledger (ledger_mode=v0 이면 루프 안에서
                                주입→발화→즉시판정이 한 바퀴로)
```

- 화살표 하나 = 모듈 하나가 **파일을 읽어 다음 파일을 쓴다**. 경로는 `modules/paths.py`로만 유도.
- 스키마 원문은 `SCHEMA.md`(노션 원본의 리포 미러). 자기 검사: `python -m modules.validate <파일>`.
- **loader = 소스 어댑터**(company_json | paper | synthetic), 뒷단(judge→지표→ledger)은 공용.
  소스가 바뀌어도 loader 하나만 추가하면 측정 인프라는 그대로 재사용.

## 2. 모듈 지도 (지금 리포에 있는 것)

| 단계 | 모듈 | 상태 | LLM |
|---|---|---|---|
| issue / facts / assignment | (수작업 정본 — extractor 자동화는 후속) | ESA 픽스처 v1 | 없음(사람) |
| debate | `modules/debate_engine.py` | 저자 포팅 + ledger 결합(7/22) | ★ |
| judge | `modules/judge.py` | 초안 v0.1 (실호출 미검증) | ★ |
| ledger | `modules/ledger.py` | v0 (전량 재주입) | 없음(순수) |
| 지표 | `judge.far` / `modules/survival.py` | FAR 잠정 / 조건부 소실률 P2 | **금지** |

원칙(설계 노트 §3): **판단 = LLM**(debate·judge), **집계 = 순수 계산**(far·survival·ledger).
FAR·survival에 LLM 개입 절대 금지 — 측정 무결성의 마지노선.

## 3. 가설 슬롯 지도 — "네 가설은 이 줄이다"

실험 규칙: `configs/sprint_mini.yaml`을 **복사**해서 변수 하나만 바꾼다. 코드 수정 금지.

| 가설 / 관심사 | 돌리는 변수 | 끼우는 곳 | 관련 기록 |
|---|---|---|---|
| Ledger 켜면 소실이 주는가 (미니 H2) | 재주입 여부 | `ledger_mode: off → v0` | docs/INTEGRATION_ledger.md |
| 라운드가 늘수록 나빠지는가 (라운드 역효과) | 라운드 수 | `rounds: 3 → 5 …` | 요한 전문 3 |
| 연결 구조의 영향 (토폴로지) | 이웃 구조 | `structure: full \| tree \| line` | 논문 §topology |
| 완고함/아첨 성향 (sycophancy 대조) | 페르소나 | `persona: default \| open-minded \| stubborn` | 안현수 인접연구 |
| 팩트 배분 겹침 (다양성·화자 분리) | 배분표 | `data/assignments/*.json` (seed 명시) | 요한 전문 4·5 |
| judge를 믿을 수 있나 (신뢰도) | 표 수·모델 | `judge_n_votes`, `judge_model` | 7/16 파일럿 |
| 다른 데이터에서도 재현되나 (소스 교체) | loader | `issues[].source` + loader 추가 | 관찰 트랙(7/22) |

새 변수가 필요하면: config 키 추가를 노션 색인에 `question`으로 올리고 동기화에서 합의.

## 4. 실행 경로 3종 (팀원용 — 자세한 건 QUICKSTART.md)

1. `quickstart.bat` — 더블클릭, API 키 불필요, 0원. 스모크(계약 검사 + 테스트 전체 + ledger 점검).
2. `run_debate.bat` — 더블클릭, `.env` 키 필요. 실토론 1회 → judge → FAR.
3. `RUN_WITH_CLAUDE.md` — 클로드 세션 붙여넣기, 키 불필요. 클로드가 debate·judge 대행(데모).

## 5. 실험 무결성 규칙 (요약)

- **본실험 실행 창구는 1곳** (예산·실험 통제, 결정 로그). 각자 실행은 스모크·드라이런까지.
- **같은 잣대**: '소실' 정의의 단일 소스는 `judge.SURVIVING` (ledger·survival이 import).
  정의 교체는 SCHEMA.md + judge.py 두 곳만 — 나머지는 자동 추종.
- 실호출에는 `max_llm_calls` 상한 + 라운드별 체크포인트가 기본 탑재 (debate_engine).
- 결과를 보기 **전에** 성공·반증 기준을 고정한다 (요한 판정 프로토콜 v0.1).

## 6. 확정 대기 — 이 명세의 빈 칸

1. **judgment 최종 구조** (동범) — 목요일 on/off 비교표의 선결 조건.
2. **judge_stage 시그니처·재주입 블록 위치** (동범) — 7/22 통합이 제안 상태로 구현해 둠.
3. **FAR 정의** — 기업 회신 시 SCHEMA 「FAR 정의」절 + judge.SURVIVING/far() 교체.
4. **관찰 트랙 리포 반영 여부** (팀 합의) — 회사 JSON loader·judgment는 현재 리포 밖.
