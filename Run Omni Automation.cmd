@echo off
setlocal
cd /d "%~dp0"
if exist "Omni.local.cmd" call "Omni.local.cmd"
if not exist ".venv\Scripts\python.exe" (
  echo Omni's Python environment was not found.
  exit /b 1
)
".venv\Scripts\python.exe" manage.py run_compliance_automation
exit /b %errorlevel%
