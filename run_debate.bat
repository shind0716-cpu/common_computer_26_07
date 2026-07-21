@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   커먼컴퓨터 fact-ledger-pipeline · 실제 토론 1회 실행
echo   (Anthropic API 를 호출합니다 — 비용이 발생합니다)
echo ============================================================
echo.

REM --- 파이썬 확인 --------------------------------------------------------
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo [X] 파이썬을 찾지 못했습니다. 먼저 quickstart.bat 을 실행해 환경을 확인하세요.
  echo.
  pause
  exit /b 1
)

REM --- .env 키 확인 -------------------------------------------------------
if not exist ".env" (
  echo [안내] .env 파일이 없습니다. 실제 토론에는 API 키가 필요합니다.
  echo.
  echo   1^) 이 폴더에서 .env.example 을 복사해 .env 로 만드세요:
  echo        copy .env.example .env
  echo   2^) .env 를 메모장으로 열고 ANTHROPIC_API_KEY 값에 본인 키를 넣으세요.
  echo   3^) 저장한 뒤 이 파일^(run_debate.bat^)을 다시 실행하세요.
  echo.
  echo   ^(키 없이 파이프라인만 확인하려면 quickstart.bat 을 쓰세요 — 비용 0원^)
  echo.
  pause
  exit /b 0
)

REM .env 안에 실제 키가 들어있는지 확인.
REM 먼저 sk- 로 시작하는 키가 있는지 보고, 그게 예시값(sk-ant-...)이면 아직 안 채운 것으로 본다.
findstr /C:"ANTHROPIC_API_KEY=sk-" .env >nul 2>nul
if errorlevel 1 goto :nokey
findstr /C:"ANTHROPIC_API_KEY=sk-ant-..." .env >nul 2>nul
if not errorlevel 1 goto :nokey
goto :haskey

:nokey
echo [안내] .env 는 있으나 ANTHROPIC_API_KEY 가 아직 실제 키로 채워지지 않았습니다.
echo        .env 를 열어 예시값^(sk-ant-...^)을 본인의 실제 키로 바꾸고 저장한 뒤 다시 실행하세요.
echo.
pause
exit /b 0

:haskey

echo [확인] .env 키 감지됨.
echo.

REM --- 저자 코드(DelibTrace) 확인 — 토론 엔진이 프롬프트를 여기서 읽음 ------
if not exist "..\DelibTrace-main\prompts" (
  echo [안내] 토론 엔진은 저자 코드^(DelibTrace^)의 프롬프트를 사용합니다.
  echo        이 리포의 부모 폴더에 DelibTrace-main 이 필요합니다.
  echo.
  echo   받는 법 ^(이 리포의 부모 폴더에서 실행^):
  echo        git clone https://github.com/whr000001/DelibTrace.git DelibTrace-main
  echo.
  echo   ^(quickstart.bat 의 테스트·Ledger 점검은 저자 코드 없이도 됩니다^)
  echo.
  pause
  exit /b 0
)

echo 이번 실행은 config: configs\sprint_mini.yaml (ledger_mode=off, 대조군) 기준입니다.
echo 에이전트 8 x 라운드 3 의 실제 호출이 일어납니다.
echo.
set /p GO="계속하려면 y 를 입력하고 Enter (취소는 그냥 Enter): "
if /I not "%GO%"=="y" (
  echo 취소했습니다.
  echo.
  pause
  exit /b 0
)

echo.
echo [1/2] 토론 엔진 실행 (debate_engine) ...
%PYCMD% -m modules.debate_engine --issue issue_esa --run run001 --config configs\sprint_mini.yaml
if errorlevel 1 goto :failed

echo.
echo [2/2] 채점기 실행 (judge) -> FAR 산출 ...
%PYCMD% -m modules.judge --issue issue_esa --run run001 --config configs\sprint_mini.yaml
if errorlevel 1 goto :failed

echo.
echo [검사] 산출물 스키마 확인 ...
%PYCMD% -m modules.validate data\debates\debate_issue_esa_run001.jsonl data\judgments\judgment_issue_esa_run001.json

echo.
echo ------------------------------------------------------------
echo   [OK] 완료: 실제 토론 1회 + 채점 + FAR 산출까지 끝났습니다.
echo   결과 파일:
echo     data\debates\debate_issue_esa_run001.jsonl   ^(토론 로그^)
echo     data\judgments\judgment_issue_esa_run001.json ^(판정 + FAR^)
echo ------------------------------------------------------------
echo.
pause
endlocal
exit /b 0

:failed
echo.
echo [X] 실행 중 문제가 발생했습니다. 위 로그를 확인하세요.
echo     흔한 원인: API 키 오류/한도, 네트워크, 또는 리포 폴더 밖에서 실행.
echo.
pause
endlocal
exit /b 1
