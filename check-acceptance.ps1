[CmdletBinding()]
param(
    [string]$Root = "",
    [int]$BackendPort = 8000,
    [int]$TcpPort = 9100,
    [int]$WebPort = 5173,
    [switch]$SkipStartup,
    [switch]$SkipMysqlInit
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $Root = $PSScriptRoot
    } else {
        $Root = (Get-Location).Path
    }
}
$Root = (Resolve-Path $Root).Path

$LogsDir = Join-Path $Root "logs"
$AcceptanceLogDir = Join-Path $LogsDir "acceptance"
$BackendPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
$AcceptanceScript = Join-Path $Root "tools\acceptance_smoke.py"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$AcceptanceLog = Join-Path $AcceptanceLogDir "tcp-acceptance-$Stamp.json"

New-Item -ItemType Directory -Force -Path $AcceptanceLogDir | Out-Null

function Write-Step {
    param(
        [string]$Level,
        [string]$Message
    )

    Write-Host ("[{0}] {1}" -f $Level, $Message)
}

Write-Step "INFO" "Acceptance preflight started at $(Get-Date -Format s)."
Write-Step "INFO" "Root: $Root"

& (Join-Path $Root "check-env.ps1") -Root $Root -BackendPort $BackendPort -TcpPort $TcpPort -WebPort $WebPort
if ($LASTEXITCODE -ne 0) {
    Write-Step "FAIL" "Environment check failed. See logs\check."
    exit 1
}

if (-not $SkipStartup) {
    $startupArgs = @("-Root", $Root, "-BackendPort", $BackendPort, "-TcpPort", $TcpPort, "-WebPort", $WebPort)
    if ($SkipMysqlInit) {
        $startupArgs += "-SkipMysqlInit"
    }

    & (Join-Path $Root "start-all.ps1") @startupArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Step "FAIL" "Startup chain failed. See logs\backend, logs\tcp, logs\web, and logs\mysql."
        exit 1
    }
} else {
    Write-Step "INFO" "Startup skipped by request. Existing services will be tested."
}

Write-Step "INFO" "Running QA real TCP acceptance smoke. Output: $AcceptanceLog"
$apiBase = "http://127.0.0.1:$BackendPort/api/v1"
$acceptanceOutput = & $BackendPython $AcceptanceScript --mode tcp --host 127.0.0.1 --port $TcpPort --api-base $apiBase
$acceptanceExit = $LASTEXITCODE
$acceptanceOutput | Set-Content -Path $AcceptanceLog -Encoding UTF8
$acceptanceOutput | Write-Host

if ($acceptanceExit -ne 0) {
    Write-Step "FAIL" "TCP acceptance failed with exit code $acceptanceExit. Collect $AcceptanceLog and service logs."
    exit $acceptanceExit
}

Write-Step "OK" "TCP acceptance passed. CN=9014 ACK and platform evidence were verified."
Write-Step "INFO" "Acceptance log: $AcceptanceLog"
