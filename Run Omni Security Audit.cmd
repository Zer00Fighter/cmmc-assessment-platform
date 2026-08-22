@echo off
setlocal
cd /d "%~dp0"
if exist "Omni.local.cmd" call "Omni.local.cmd"
if not exist ".venv\Scripts\python.exe" (
  echo Omni's Python environment was not found.
  pause
  exit /b 1
)
echo Running Django configuration checks...
".venv\Scripts\python.exe" manage.py check
if errorlevel 1 goto :failed
echo.
echo Running Omni security gates...
".venv\Scripts\python.exe" manage.py security_audit
if errorlevel 1 goto :failed
echo.
echo Auditing pinned dependencies...
".venv\Scripts\python.exe" -m pip_audit -r requirements.txt --progress-spinner off
if errorlevel 1 goto :failed
echo.
echo Omni security audit completed successfully.
pause
exit /b 0
:failed
echo.
echo Omni security audit failed. Review the output above.
pause
exit /b 1
