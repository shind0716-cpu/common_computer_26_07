@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VIEWER_DATA=experiments\mini_h2_pilot\data"
echo [pilot viewer] data=%VIEWER_DATA% port=8012
python -m uvicorn tools.viewer.app:app --port 8012
