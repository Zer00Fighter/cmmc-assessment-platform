@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Omni's Python environment was not found.
  echo Run setup before using the Word SSP launcher.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "generate_ssp_gui.py"
