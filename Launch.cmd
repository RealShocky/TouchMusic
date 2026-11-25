@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Setup.cmd first.
  pause
  exit /b 1
)
start "TouchMusic" ".venv\Scripts\pythonw.exe" -m touchmusic %*
