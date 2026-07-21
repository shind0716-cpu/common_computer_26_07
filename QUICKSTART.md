# 퀵스타트 (Windows)

처음 온 팀원이 이 파이프라인을 자기 컴퓨터에서 돌려보는 가장 빠른 길.
명령어를 칠 필요 없이 **`.bat` 파일을 더블클릭**하면 됩니다.

## 0. 준비 (한 번만)

1. 이 리포를 clone 하거나 ZIP으로 받아 압축을 풉니다.
2. [Python 3.10 이상](https://www.python.org/downloads/) 설치 —
   설치 화면에서 **"Add Python to PATH"** 를 꼭 체크하세요.

## 1. `quickstart.bat` — 파이프라인이 도는지 확인 (API 키 불필요, 비용 0원)

`quickstart.bat` 을 더블클릭하세요. 자동으로:

- 파이썬·패키지를 확인·설치하고
- 파일 계약(validate) → 단위 테스트 17종 → Ledger 소실팩트 점검을 돌리고
- 끝에 **모든 검사 통과 / 실패 지점**을 요약해 보여줍니다.

여기까지 통과하면 "이 파이프라인이 내 컴퓨터에서 정상 작동한다"가 증명된 것입니다.
대부분의 팀원은 이거면 충분합니다.

> 검은 창이 뜨자마자 닫히면, 리포 폴더 **안에서** 실행했는지 확인하세요
> (`quickstart.bat` 이 `modules\`·`data\` 폴더와 같은 자리에 있어야 합니다).

## 2. `run_debate.bat` — 실제 토론까지 (API 키 필요, 비용 발생)

실제 LLM 토론 1회 → 채점 → FAR 산출까지 보고 싶을 때 씁니다.

1. `.env.example` 을 복사해 `.env` 로 만들기: 명령 프롬프트에서 `copy .env.example .env`
2. `.env` 를 메모장으로 열어 예시값 `sk-ant-...` 를 **본인의 실제 키로 바꿔** 저장
3. 저자 코드(토론 엔진이 프롬프트를 여기서 읽음)를 이 리포의 **부모 폴더**에 받기:
   `git clone https://github.com/whr000001/DelibTrace.git DelibTrace-main`
4. `run_debate.bat` 더블클릭

키나 저자 코드가 없으면 `.bat` 이 각 경우를 **친절히 안내하고 멈춥니다**(에러로 죽지 않음).
안내대로 준비한 뒤 같은 파일을 다시 실행하면 됩니다.

키가 아직 없으면 `.bat` 이 **친절히 안내하고 멈춥니다**(에러로 죽지 않음).
키를 넣은 뒤 같은 파일을 다시 실행하면 됩니다.

## 3. 클로드 코드 세션으로 돌리기 (API 키·비용 없이 — 재현/데모용)

각자 쓰는 클로드 코드/Cowork 세션에서 클로드가 토론·채점을 **대행**해 파이프라인을 돌리는 경로입니다.
API 키도 비용도 없지만, 모델·temperature가 고정되지 않아 **정식 실험 수치는 아닙니다**(정식은 위 `run_debate.bat`).
절차는 **`RUN_WITH_CLAUDE.md`** 를 여세요 — 세션에 붙여넣을 지시 블록이 통째로 들어 있습니다.

## 자세한 구조가 궁금하면

`README.md → DESIGN.md → SCHEMA.md → WORKLOG.md` 순서로 읽으세요.
모듈 하나를 직접 돌려보려면 (예):

```
python -m modules.ledger --issue issue_esa --run dryrun --stage 3
python -m modules.validate data/facts/facts_issue_esa.json
```

## 다음 단계 (로드맵 메모)

- **팀 전원이 API 비용 없이 실측**: 팀원 각자 Claude Code / Cowork 세션에서
  judge를 하위 에이전트로 돌리는 경로를 검토 중(스프린트 2일차 관찰 트랙 시연에서 가능성 확인).
  현재 `.bat` 자동화에는 아직 미포함 — API 키 경로가 표준입니다.
- **관찰 트랙**(회사 A2A 로그 → FAR): loader 시연 완료, 리포 정식 반영은 팀 논의 후.
