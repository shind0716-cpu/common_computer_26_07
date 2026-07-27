# 미니 H2 파일럿 — OpenAI 별도 환경 (탐색적/데모 지위)

> 작성: 요한 (2026-07-28). 팀 예산이 OpenAI 키라 본 파이프라인(Anthropic 전용)을 못 태워,
> 민옥 담화 전진·요한 tp1 전례에 따라 **파일럿 지위**로 집행한다.
> **모든 수치는 탐색적 — 정식 H1/H2 판정(판정 프로토콜 v0.1 + 숫자 3개 합의)은
> Anthropic 실호출분에서.** 파일럿 결과로 판별 기준을 적용하지 않는다.

## 무엇이 정본이고 무엇이 편차인가

**정본 그대로 재사용 (tp1보다 계승 폭 큼):**
- 토론 루프 = `modules.debate_engine.run()` 무수정 — utterance_fn/judge_vote_fn 주입
  슬롯 사용(테스트 98종이 검증한 ledger v0 결합부·호출상한·체크포인트 전부 정본).
- 저자 프롬프트 원문(authors_prompts → DelibTrace-main), temp 1.2 논문 상수 그대로
  (OpenAI 0~2 허용 — Anthropic 선결 ①에 해당 없음).
- judge 잣대 문구 = `judge.JUDGE_SYSTEM`·`_user_prompt`·`_parse_vote` 정본.
  n=3 다수결·votes 원본 보존·동점 보수 규칙(judge_fact) 정본.

**편차 (전부 기록):**
- D-p1: debate_model = gpt-5.4-mini (팀 정본 claude-haiku — 예산 사유)
- D-p2: judge 모델 = gpt-5.4-mini (확정 사양 Sonnet과 **모델만** 다름; temp0·n=3 유지)
- D-p3: issue_esa에 question 필드 로컬 주입("룸메이트를 집주인에게 신고해야 할까요?")
  — title이 팩트 요지 누출(tp1 발견). 파일럿 사본에만 주입, 팀 data/ 무수정.

## 사전 등록

실행 **전에** `QUESTIONS.md`(Q0~Q5)를 커밋했다 — v1/v2 설계가 이 데이터에 물을
질문의 사전 고정. analyze가 Q0~Q5를 자동 집계해 `data/h2_report.json`에 쓴다.

## 실행 절차 (내일)

```
# 0. .env에 OPENAI_API_KEY (선택: OPENAI_MODEL, 기본 gpt-5.4-mini)
# 1. 리허설이 남긴 data/ 산출물이 없는지 확인 (있으면 스킵됨)
python experiments/mini_h2_pilot/run_h2.py --phase all
# 또는 단계별: --phase debate|judge --arm off|v0, --phase analyze
# 2. 자가 검사
python -m modules.validate experiments/mini_h2_pilot/data/debates/*.jsonl \
  experiments/mini_h2_pilot/data/judgments/*.json
# 3. 원자료 즉시 커밋 (CLAUDE.md 규칙 8)
```

예상 호출: off 32 + v0 140(발화 32+루프 내 판정 108) + 사후 judge 288 = **460콜**
(전역 상한 600, 엔진 내장 상한 별도). gpt-5.4-mini 기준 수 달러 이내.

중단·재개: debate는 엔진 라운드 체크포인트(단, 완료 파일 존재 시 스킵이므로 부분
파일은 삭제 후 재실행), judge는 stage별 체크포인트(자동 재개).

## 리허설 (2026-07-28 완료)

`--phase all --dry` (API 0원, 가짜 발화 + 문자열 대조 판정)로 전 구간 완주 검증:
off·v0 토론(v0에서 ledger_inject 2건 발생 확인) → 판정 4-stage × 12팩트 × 3표 →
Q0~Q5 집계 → validate 4파일 전부 통과. 리허설 산출물은 실행 스킵 방지를 위해 삭제.
