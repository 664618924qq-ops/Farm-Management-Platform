$root = "C:\Users\DELL\Documents\Codex project"
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "[1/4] Init MySQL database..." -ForegroundColor Cyan
Set-Location $backend
& ".\.venv\Scripts\python.exe" "scripts\init_mysql.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to initialize MySQL." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[2/4] Check backend service..." -ForegroundColor Cyan
$backendRunning = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($backendRunning) {
    Write-Host "Backend already running on http://127.0.0.1:8000" -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000 --reload --reload-dir app"
    )
}

Write-Host "[3/4] Check TCP receiver..." -ForegroundColor Cyan
$tcpRunning = Get-NetTCPConnection -LocalPort 9100 -State Listen -ErrorAction SilentlyContinue
if ($tcpRunning) {
    Write-Host "TCP receiver already running on 127.0.0.1:9100" -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$backend'; & '.\.venv\Scripts\python.exe' -m app.tcp.server"
    )
}

Write-Host "[4/4] Check frontend service..." -ForegroundColor Cyan
$frontendRunning = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontendRunning) {
    Write-Host "Frontend already running on http://127.0.0.1:5173" -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$frontend'; npm run dev"
    )
}

Write-Host ""
Write-Host "Platform start flow triggered." -ForegroundColor Green
Write-Host "Backend docs: http://127.0.0.1:8000/docs"
Write-Host "TCP receiver: 127.0.0.1:9100"
Write-Host "Frontend app: http://127.0.0.1:5173"
Read-Host "Press Enter to close"
