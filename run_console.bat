@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   실험 콘솔 v0 - 로컬 웹앱 실행기
echo   시나리오 / 설정+실행 / 수첩 매트릭스 / 개입 모드
echo ============================================================
echo.

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD where python >nul 2>nul && set "PYCMD=python"
if not defined PYCMD goto :nopython

echo [1/3] 콘솔 패키지 설치 - fastapi, uvicorn, requests
%PYCMD% -m pip install --quiet -r tools\console\requirements.txt
if errorlevel 1 echo     경고: 설치에 문제가 있었지만 계속 시도합니다
echo     완료
echo.

REM 키 점검 - 엔진은 호출 실패를 5회 재시도 후 공백 발화로 넘긴다.
REM 키가 죽어 있으면 전 발화가 빈 로그가 조용히 완주하고, 호출을 다 태운
REM 뒤에야 폴백 카운터로 알게 된다. 그래서 돌리기 전에 사람에게 알린다.
echo [2/3] API 키 점검 - 어떤 모델을 실제로 쓸 수 있는지
if not exist ".env" goto :nodotenv
%PYCMD% -X utf8 -m tools.console.keycheck
goto :serve

:nodotenv
echo     경고: .env 파일이 없습니다
echo     실호출은 안 되고 화면만 볼 수 있습니다
echo     .env.example 을 .env 로 복사한 뒤 키를 넣으세요

:serve
echo.
echo [3/3] 서버 시작 - 브라우저가 곧 열립니다
echo     이 창을 닫으면 서버가 꺼집니다
echo.
echo   [!] 이 콘솔은 인증이 없습니다. 내 컴퓨터 전용입니다.
echo   [!] 코드를 수정하면 이 창을 닫고 다시 실행해야 반영됩니다.
echo.
start "" "http://127.0.0.1:8021"
%PYCMD% -m uvicorn tools.console.app:app --port 8021
goto :done

:nopython
echo [X] 파이썬을 찾지 못했습니다
echo     quickstart.bat 을 먼저 실행해 보세요
pause

:done
endlocal
