@echo off
setlocal
cd /d "%~dp0"
if exist "Omni.local.cmd" call "Omni.local.cmd"
if not exist ".venv\Scripts\python.exe" (
  echo Omni's Python environment was not found.
  echo Run setup before starting the web application.
  pause
  exit /b 1
)
start "Omni Web" /min ".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/"
