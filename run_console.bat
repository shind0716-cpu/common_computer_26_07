@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   실험 콘솔 - 내 컴퓨터에서 켜는 웹앱
echo   압박 실험 실행 / 결과 / 집계 - 처음이면 화면의 안내 탭부터
echo ============================================================
echo.

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD where python >nul 2>nul && set "PYCMD=python"
if not defined PYCMD goto :nopython

echo [1/3] 필요한 파이썬 패키지 설치 - fastapi, uvicorn 등
%PYCMD% -m pip install --quiet -r tools\console\requirements.txt
if errorlevel 1 echo     경고: 설치에 문제가 있었지만 일단 계속 켭니다
echo     완료
echo.

REM 키 점검 - 엔진은 호출 실패를 5회 재시도 후 공백 발화로 넘긴다.
REM 키가 죽어 있으면 전 발화가 빈 로그가 조용히 완주하고, 호출을 다 태운
REM 뒤에야 폴백 카운터로 알게 된다. 그래서 돌리기 전에 사람에게 알린다.
echo [2/3] API 키 점검 - 어떤 AI 모델을 실제로 쓸 수 있는지
if not exist ".env" goto :nodotenv
%PYCMD% -X utf8 -m tools.console.keycheck
goto :serve

:nodotenv
echo     경고: .env 파일이 없습니다 - API 키가 없다는 뜻입니다
echo     결과를 보는 탭은 되지만 실험을 새로 돌리지는 못합니다
echo     .env.example 을 .env 로 복사한 뒤 키를 넣으세요

:serve
echo.
echo [3/3] 서버 시작 - 브라우저가 곧 열립니다. 주소는 127.0.0.1:8021
echo     이 검은 창을 닫으면 서버가 꺼집니다
echo.
echo   [!] 이 콘솔은 인증이 없습니다. 내 컴퓨터 전용입니다.
echo   [!] app.py 를 고치면 이 창을 닫고 다시 실행해야 반영됩니다.
echo   [!] 화면 파일 index.html 은 브라우저 새로고침이면 됩니다.
echo   [!] 켜는 법과 오류 대처는 tools/console/README.md
echo.
start "" "http://127.0.0.1:8021"
%PYCMD% -m uvicorn tools.console.app:app --port 8021
goto :done

:nopython
echo [X] 파이썬을 찾지 못했습니다
echo     파이썬을 설치하거나 quickstart.bat 을 먼저 실행해 보세요
pause

:done
endlocal
