@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   커먼컴퓨터 fact-ledger-pipeline · 퀵스타트
echo   (API 키 없이 파이프라인이 이 컴퓨터에서 도는지 확인합니다)
echo ============================================================
echo.

REM --- 파이썬 확인 --------------------------------------------------------
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo [X] 파이썬을 찾지 못했습니다.
  echo     https://www.python.org/downloads/ 에서 Python 3.10 이상을 설치하고,
  echo     설치 시 "Add Python to PATH" 를 체크한 뒤 이 파일을 다시 실행하세요.
  echo.
  pause
  exit /b 1
)
echo [1/4] 파이썬 확인 ...
%PYCMD% --version
echo.

REM --- 패키지 설치 --------------------------------------------------------
echo [2/4] 필요한 패키지 설치 (pyyaml) ...
%PYCMD% -m pip install --quiet pyyaml
if errorlevel 1 (
  echo     ^(경고^) 패키지 설치에 문제가 있었지만 계속 진행합니다.
)
echo     완료.
echo.

REM --- 스모크 검증 --------------------------------------------------------
echo [3/4] 스모크 검증 실행 ...
echo.
%PYCMD% run_smoke.py
set "RC=%errorlevel%"
echo.

REM --- 관측 데모: 뷰어 생성 + 열기 ---------------------------------------
REM dryrun2 = 현행 구조 정본 픽스처(결정론적 소실 모의, 커밋됨). 재생성하지 않고
REM 그대로 소비한다 — 정본 덮어쓰기 금지(재현성 보호, 7/22 dryrun 교훈).
if "%RC%"=="0" (
  if exist "data\judgments\judgment_issue_esa_dryrun2.json" (
    echo [4/4] 관측 데모: 팩트 생존 뷰어 생성 ...
    %PYCMD% scripts\make_viewer.py --issue issue_esa --run dryrun2
    if exist "viewers\viewer_issue_esa_dryrun2.html" (
      echo     브라우저에서 뷰어를 엽니다 — 팩트가 라운드를 지나며 살고 죽는 과정을 보세요.
      start "" "viewers\viewer_issue_esa_dryrun2.html"
    )
  ) else (
    echo [4/4] ^(건너뜀^) 데모 데이터^(dryrun2^)가 없어 뷰어 생성을 생략합니다.
  )
)

echo.
if "%RC%"=="0" (
  echo ------------------------------------------------------------
  echo   [OK] 완료: 파이프라인이 정상 작동하고, 뷰어가 열렸습니다.
  echo   방금 본 것: 오프라인 데모 런^(dryrun2^)의 팩트 생존 매트릭스.
  echo   다음 단계:
  echo     - 실제 토론^(API 실호출^)은 run_debate.bat ^(.env 키 필요^)
  echo     - 라이브 뷰어^(서버^)는 run_viewer.bat ^(새 run이 목록에 자동 등장^)
  echo ------------------------------------------------------------
) else (
  echo ------------------------------------------------------------
  echo   [FAIL] 일부 검사가 실패했습니다. 위 로그를 확인하세요.
  echo   가장 흔한 원인: 이 .bat 을 리포 폴더 안에서 실행하지 않은 경우입니다.
  echo   ^(이 파일은 fact-ledger-pipeline 폴더 안에 있어야 합니다^)
  echo ------------------------------------------------------------
)
echo.
pause
endlocal
