@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
  echo.
  echo PC client failed to start. Please check the messages above.
  pause
)
