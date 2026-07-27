# 담화 전진 가설 — 정식 검증 (별개 실험 폴더)

파이프라인(modules/)과 분리된 독립 실험. debate_engine 불필요 — 단독 에이전트
3조건(A 반복 / A′ 전진 / B 자기숙의)을 실 API로 돌려 데모(7/24)를 정식 승격한다.

## 빠른 시작 (Windows)

```bat
pip install requests
:: 리포 루트의 .env에 키 채우기 (.env.example 참고 — 파이프라인과 같은 파일 하나로 관리)
cd experiments\discourse_progression
python run_experiment.py all
```

키는 **리포 루트의 `.env` 하나**로 관리한다 — ANTHROPIC(파이프라인)·OPENAI·GEMINI
전부 같은 파일. 루트 `.gitignore`가 `.env`를 막고 있어 커밋되지 않는다.
환경변수를 직접 set 하면 .env보다 우선한다.

끝나면 `results/analysis.json`에 P1~P5 + 복제 판정(R1)이 담긴다.
콘솔에도 생존 곡선 수치와 판정이 출력된다.

## 모델 ID 바꾸기 (키 받고 사용 가능 모델 확인 후)

```bat
set OPENAI_MODEL=gpt-5          ← 실제 쓸 모델명으로
set GEMINI_MODEL=gemini-2.5-pro
set JUDGE_MODEL=gpt-5           ← 생략 시 OPENAI_MODEL과 동일
```

기본값은 자리표시자일 수 있음 — 반드시 발급받은 키로 쓸 수 있는 모델명 확인.

## 순서 규율

1. **PREREG_v0.2.md 먼저 읽고 승인** (승인 = 기준 커밋, 이후 변경 금지)
2. `python run_experiment.py all`
3. `results/analysis.json` 확인 → 보고서 v1 승격 여부는 R1 규칙대로

## 구조

```
run_experiment.py   생성(gen) → 채점(judge) → 분석(analyze) — 부분 실행 가능
PREREG_v0.2.md      사전고정 (판별 기준 P1~P5 + 복제 기준 R1)
fixtures/           ESA 이슈·12팩트 정본 (data/에서 복사 — 원본 불변)
results/            산출물 (모델별 텍스트·judgments.json·stability.json·analysis.json)
```

- 중단돼도 재실행하면 완료분은 스킵하고 이어서 돌아간다.
- 판단 = LLM(생성·채점), 집계 = 순수 계산(analyze) — 파이프라인과 같은 경계 원칙.
- git 커밋은 사람이 터미널에서. API 키는 절대 커밋하지 말 것 (환경변수만 사용).
