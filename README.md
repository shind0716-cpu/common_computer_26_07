# fact-ledger-pipeline

멀티에이전트 토론에서 사실(fact)이 사라지는 현상을 측정하고, Fact Ledger로 완화하는 실험 파이프라인.
(AIFFEL 365 커먼컴퓨터 팀 · DelibTrace 기반 · 노션 협업 보드가 의사결정 원본)

## 처음 온 사람 / 새 세션이 읽는 순서
1. 이 README — 구조와 실행법
2. DESIGN.md — 왜 이렇게 설계했는가 (파이프라인 7모듈, 사다리, 진단 실험)
3. SCHEMA.md — 파일 계약 v0.2 (모듈 간 유일한 약속)
4. WORKLOG.md — 지금까지 무슨 일이 있었는가 (append-only)

## 구조 지도
- `configs/` 실험 조건 정의 — 조건을 바꿀 땐 코드가 아니라 여기를 바꾼다
- `data/` 파일 계약의 실체 — 모듈은 여기서 읽고 여기에 쓴다 (issues/facts/assignments/debates/judgments)
- `modules/` 파이프라인 모듈 — 각자 독립 실행 가능
  - `paths.py` 경로 유도 규칙의 단일 소스 (경로 하드코딩 금지)
  - `validate.py` 산출물 스키마 검사기 = 완료 기준 판정기

## 퀵스타트
```
pip install -r requirements.txt
copy .env.example .env      # API 키 입력 (커밋 금지)
python -m modules.validate data/facts/facts_issue_esa.json   # 계약 검사 동작 확인
```

## 모듈 실행 규약
모든 모듈은 같은 방식으로 부른다:
```
python -m modules.<모듈명> --issue issue_esa --run run001 --config configs/sprint_mini.yaml
```
출력을 만들면 반드시 validate로 자기 검사:
```
python -m modules.validate data/judgments/judgment_issue_esa_run001.json
```

## 동기화 규칙 (깃허브)
1. 의사결정은 노션 협업 보드에서, 코드·데이터 동기화는 이 리포에서
2. data/의 로그(debates, judgments)도 커밋한다 — 로그가 최우선 산출물이며, 로그만 있으면 토론 재실행 없이 분석 재현 가능
3. .env(API 키)만 커밋 금지
4. 작업을 마치면 WORKLOG.md에 한 줄 추가 후 커밋 (append-only, 남의 줄 수정 금지)

## 담당 (3일 스프린트, 상세: 노션 작업 지시서 #1)
- 신동범: modules/debate_engine.py + modules/judge.py (수 20시)
- 민옥(리더): 픽스처·ledger.py·게이트·통합·분석
- 이론조 3인: judge 수동 검증 표본 30개 (금 오전)

## 호환성 (OS 불문 동작 원칙)
- Python 3.10 이상. 가상환경 권장: `python -m venv .venv`
- 모든 파일 I/O는 UTF-8 (`encoding="utf-8"` 명시 — validate.py 참조), 경로는 pathlib만 사용 (슬래시 하드코딩 금지)
- .env 만들기 — Windows: `copy .env.example .env` / Mac·Linux: `cp .env.example .env`
- 데이터 파일 안 한국어가 깨져 보이면 코드가 아니라 편집기 인코딩 설정 문제 (UTF-8로 열 것)
- 줄바꿈은 .gitattributes가 LF로 통일 — CRLF 관련 diff 노이즈는 무시하고 pull 우선
