[CmdletBinding()]
param(
    [string]$Root = "",
    [int]$MySqlPort = 3306,
    [int]$BackendPort = 8000,
    [int]$TcpPort = 9100,
    [int]$WebPort = 5173
)

$ErrorActionPreference = "Continue"

if ([string]::IsNullOrWhiteSpace($Root)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $Root = $PSScriptRoot
    } else {
        $Root = (Get-Location).Path
    }
}
$Root = (Resolve-Path $Root).Path

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$LogsDir = Join-Path $Root "logs"

$RequiredLogDirs = @(
    "check",
    "mysql",
    "backend",
    "tcp",
    "web",
    "pc-client"
)

foreach ($dir in $RequiredLogDirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $LogsDir $dir) | Out-Null
}

$CheckLog = Join-Path $LogsDir ("check\check-env-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

function Write-Check {
    param(
        [string]$Level,
        [string]$Message
    )

    $line = "[{0}] {1}" -f $Level, $Message
    Write-Host $line
    Add-Content -Path $CheckLog -Value $line -Encoding UTF8
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMs = 1000
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

$failures = 0
$warnings = 0

Write-Check "INFO" "Acceptance environment check started at $(Get-Date -Format s)."
Write-Check "INFO" "Root: $Root"

if (Test-Path $BackendDir) {
    Write-Check "OK" "Backend directory exists: $BackendDir"
} else {
    Write-Check "FAIL" "Backend directory missing: $BackendDir"
    $failures++
}

if (Test-Path $FrontendDir) {
    Write-Check "OK" "Frontend directory exists: $FrontendDir"
} else {
    Write-Check "FAIL" "Frontend directory missing: $FrontendDir"
    $failures++
}

if (Test-Path $VenvPython) {
    $pythonVersion = & $VenvPython --version 2>&1
    Write-Check "OK" "Python venv found: $VenvPython ($pythonVersion)"
} else {
    Write-Check "FAIL" "Python venv missing: $VenvPython"
    Write-Check "INFO" "Expected setup: cd backend; py -3.12 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e .[dev]"
    $failures++
}

if (Test-CommandExists "node") {
    $nodeVersion = node --version 2>&1
    Write-Check "OK" "Node found: $nodeVersion"
} else {
    Write-Check "FAIL" "Node command not found."
    $failures++
}

if (Test-CommandExists "npm") {
    $npmVersion = npm --version 2>&1
    Write-Check "OK" "npm found: $npmVersion"
} else {
    Write-Check "FAIL" "npm command not found."
    $failures++
}

if (Test-Path (Join-Path $FrontendDir "node_modules")) {
    Write-Check "OK" "Frontend node_modules exists."
} else {
    Write-Check "FAIL" "Frontend node_modules missing. Run: cd frontend; npm install"
    $failures++
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $MySqlPort) {
    Write-Check "OK" "MySQL is reachable on 127.0.0.1:$MySqlPort"
} else {
    Write-Check "FAIL" "MySQL is not reachable on 127.0.0.1:$MySqlPort"
    $failures++
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $BackendPort) {
    try {
        $health = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/health" -UseBasicParsing -TimeoutSec 3
        Write-Check "OK" "Backend port $BackendPort is listening; /health returned HTTP $($health.StatusCode)."
    } catch {
        Write-Check "WARN" "Backend port $BackendPort is listening but /health failed: $($_.Exception.Message)"
        $warnings++
    }
} else {
    Write-Check "WARN" "Backend is not listening on 127.0.0.1:$BackendPort yet."
    $warnings++
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $TcpPort) {
    Write-Check "OK" "TCP receiver is listening on 127.0.0.1:$TcpPort"
} else {
    Write-Check "WARN" "TCP receiver is not listening on 127.0.0.1:$TcpPort yet."
    $warnings++
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $WebPort) {
    Write-Check "OK" "Web frontend is listening on 127.0.0.1:$WebPort"
} else {
    Write-Check "WARN" "Web frontend is not listening on 127.0.0.1:$WebPort yet."
    $warnings++
}

Write-Check "INFO" "Log directories ready under: $LogsDir"
Write-Check "INFO" "Summary: failures=$failures warnings=$warnings"

if ($failures -gt 0) {
    exit 1
}

exit 0
