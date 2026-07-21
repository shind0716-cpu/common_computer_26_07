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
echo [1/3] 파이썬 확인 ...
%PYCMD% --version
echo.

REM --- 패키지 설치 --------------------------------------------------------
echo [2/3] 필요한 패키지 설치 (pyyaml) ...
%PYCMD% -m pip install --quiet pyyaml
if errorlevel 1 (
  echo     ^(경고^) 패키지 설치에 문제가 있었지만 계속 진행합니다.
)
echo     완료.
echo.

REM --- 스모크 검증 --------------------------------------------------------
echo [3/3] 스모크 검증 실행 ...
echo.
%PYCMD% run_smoke.py
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" (
  echo ------------------------------------------------------------
  echo   [OK] 완료: 파이프라인이 정상 작동합니다.
  echo   다음 단계: 실제 토론까지 보려면 run_debate.bat 실행 ^(.env 키 필요^)
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
