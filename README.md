# fact-ledger-pipeline

멀티에이전트 토론에서 사실(fact)이 사라지는 현상을 측정하고, Fact Ledger로 완화하는 실험 파이프라인.
(AIFFEL 365 커먼컴퓨터 팀 · DelibTrace 기반 · 노션 협업 보드가 의사결정 원본)

## 처음 온 사람 / 새 세션이 읽는 순서
1. 이 README — 구조와 실행법
2. `CLAUDE.md` — AI로 작업한다면 여기가 먼저. 「무엇이 현행인지 판별하는 법」 절 필독
3. DESIGN.md — 왜 이렇게 설계했는가 (파이프라인 7모듈, 사다리, 진단 실험)
4. SCHEMA.md — 파일 계약 (모듈 간 유일한 약속). **끝까지 읽을 것** — 이 리포는
   append-only라 제목은 v0.2지만 문서 뒤쪽에 **v0.3 확정분**(`prompt_assembly`·`note_update`)이 있다
5. WORKLOG.md — 지금까지 무슨 일이 있었는가 (append-only, **아래가 최신**)

> 문서의 **지위**(확정/제안/사전고정/근거자료/데모)는 각 문서 첫 3줄에 적혀 있다.
> 확정 여부의 정본은 리포가 아니라 **노션 보드 결정 로그**다.

## 구조 지도
- `configs/` 실험 조건 정의 — 조건을 바꿀 땐 코드가 아니라 여기를 바꾼다.
  조건 변경 = 새 yaml (기존 파일 수정 아님). `configs/console/` 은 콘솔이 자동 생성한 것
- `data/` 파일 계약의 실체 — 모듈은 여기서 읽고 여기에 쓴다 (issues/facts/assignments/debates/judgments)
- `modules/` 파이프라인 모듈 — 각자 독립 실행 가능
  - `paths.py` 경로 유도 규칙의 단일 소스 (경로 하드코딩 금지)
  - `validate.py` 산출물 스키마 검사기 = 완료 기준 판정기 (`--deep` 는 프롬프트 재조립까지 검증)
- `docs/` 설계·계약 문서. `proposals/` 안에도 **확정된 계약이 있다** — 폴더 이름이 아니라
  문서 첫 줄의 지위를 볼 것. `docs/CLAUDE.md` 는 팀 공통 지침(리포 규칙인 루트 CLAUDE.md와 별개)
- `tools/` 사람이 쓰는 화면 2종 — **읽기 전용 뷰어**(`viewer/`, 요한)와
  **실행·개입 콘솔**(`console/`, 민옥). 둘은 파일로만 연결된다(같은 `data/` 를 본다)
- `experiments/` **코드가 아니라 기록이다.** 각 폴더는 사전고정 → 실행 → 결과 한 벌이며,
  러너를 나중에 리팩터하면 "이 코드가 이 결과를 냈다"는 대응이 끊긴다. 손대지 말 것
- `viewers/` 뷰어가 **뽑아낸 산출물** HTML (앱은 `tools/viewer/`)

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
- **2026-08-21 갱신(요한 결정)**: 신동범 타 팀 이적. 구 패키지 A(debate_engine·judge·llm·authors_prompts·gen_dryrun2)는
  **공용 코어**로 전환 — 개인 소유자 없음. 변경은 전체 테스트 통과 + WORKLOG 기록 + 보드 결정 로그 한 줄(계약 변경 시). 소유자 표기는 각 모듈 독스트링 첫 줄이 정본.

## 호환성 (OS 불문 동작 원칙)
- Python 3.10 이상. 가상환경 권장: `python -m venv .venv`
- 모든 파일 I/O는 UTF-8 (`encoding="utf-8"` 명시 — validate.py 참조), 경로는 pathlib만 사용 (슬래시 하드코딩 금지)
- .env 만들기 — Windows: `copy .env.example .env` / Mac·Linux: `cp .env.example .env`
- 데이터 파일 안 한국어가 깨져 보이면 코드가 아니라 편집기 인코딩 설정 문제 (UTF-8로 열 것)
- 줄바꿈은 .gitattributes가 LF로 통일 — CRLF 관련 diff 노이즈는 무시하고 pull 우선

## 실험 콘솔 켜는 법 (2026-09-03 추가)

리포 루트의 `run_console.bat`을 더블클릭하면 `http://127.0.0.1:8021`에 콘솔이 뜬다. 설치·API 키·흔한 오류·탭 설명은 `tools/console/README.md`.
