@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   팩트 생존 뷰어 (라이브 서버) 실행기
echo   (tools/viewer — 요한 님 FastAPI 어댑터를 실행만 합니다)
echo ============================================================
echo.

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD (
  where python >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo [X] 파이썬을 찾지 못했습니다. quickstart.bat 을 먼저 실행해 보세요.
  pause
  exit /b 1
)

echo [1/2] 뷰어 서버 패키지 설치 (fastapi·uvicorn) ...
%PYCMD% -m pip install --quiet -r tools\viewer\requirements.txt
if errorlevel 1 (
  echo     ^(경고^) 설치에 문제가 있었지만 계속 시도합니다.
)
echo     완료.
echo.

echo [2/2] 서버 시작 — 브라우저가 곧 열립니다. 이 창을 닫으면 서버가 꺼집니다.
start "" "http://localhost:8011"
%PYCMD% -m uvicorn tools.viewer.app:app --port 8011

endlocal
