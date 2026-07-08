@echo off
setlocal

set "ROOT=C:\Users\DELL\Documents\Codex project"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"

echo [1/4] Init MySQL database...
cd /d "%BACKEND%"
call "%BACKEND%\.venv\Scripts\activate.bat"
python scripts\init_mysql.py
if errorlevel 1 (
  echo Failed to initialize MySQL.
  pause
  exit /b 1
)

echo [2/4] Check backend service...
netstat -ano | findstr ":8000" >nul
if %errorlevel%==0 (
  echo Backend already running on http://127.0.0.1:8000
) else (
  start "Livestock Backend" cmd /k "cd /d ""%BACKEND%"" && call .\.venv\Scripts\activate.bat && python -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000 --reload --reload-dir app"
)

echo [3/4] Check TCP receiver...
netstat -ano | findstr ":9100" >nul
if %errorlevel%==0 (
  echo TCP receiver already running on 127.0.0.1:9100
) else (
  start "Livestock TCP Receiver" cmd /k "cd /d ""%BACKEND%"" && call .\.venv\Scripts\activate.bat && python -m app.tcp.server"
)

echo [4/4] Check frontend service...
netstat -ano | findstr ":5173" >nul
if %errorlevel%==0 (
  echo Frontend already running on http://127.0.0.1:5173
) else (
  start "Livestock Frontend" cmd /k "cd /d ""%FRONTEND%"" && npm run dev"
)

echo.
echo Platform start flow triggered.
echo Backend docs: http://127.0.0.1:8000/docs
echo TCP receiver: 127.0.0.1:9100
echo Frontend app: http://127.0.0.1:5173
pause
