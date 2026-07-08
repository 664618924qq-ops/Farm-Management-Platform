[CmdletBinding()]
param(
    [string]$Root = "",
    [int]$BackendPort = 8000,
    [int]$TcpPort = 9100,
    [int]$WebPort = 5173,
    [switch]$SkipMysqlInit,
    [switch]$StartPcClient
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

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$LogsDir = Join-Path $Root "logs"
$RunDir = Join-Path $LogsDir "run"

foreach ($dir in @("check", "mysql", "backend", "tcp", "web", "acceptance", "pc-client", "run")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $LogsDir $dir) | Out-Null
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

function Write-Step {
    param(
        [string]$Level,
        [string]$Message
    )

    Write-Host ("[{0}] {1}" -f $Level, $Message)
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

function Wait-Port {
    param(
        [string]$Name,
        [int]$Port,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName "127.0.0.1" -Port $Port -TimeoutMs 500) {
            Write-Step "OK" "$Name is listening on 127.0.0.1:$Port"
            return $true
        }
        Start-Sleep -Seconds 1
    }

    Write-Step "WARN" "$Name did not become reachable on 127.0.0.1:$Port within $TimeoutSeconds seconds."
    return $false
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogName
    )

    $stdout = Join-Path $LogsDir "$LogName\$LogName-$Stamp.out.log"
    $stderr = Join-Path $LogsDir "$LogName\$LogName-$Stamp.err.log"

    Write-Step "INFO" "Starting $Name. stdout=$stdout stderr=$stderr"
    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    Set-Content -Path (Join-Path $RunDir "$LogName.pid") -Value $process.Id -Encoding ASCII
    Write-Step "OK" "$Name process started, pid=$($process.Id)"
}

Write-Step "INFO" "Acceptance startup started at $(Get-Date -Format s)."
Write-Step "INFO" "Root: $Root"

Write-Step "INFO" "Running environment check..."
& (Join-Path $Root "check-env.ps1") -Root $Root -BackendPort $BackendPort -TcpPort $TcpPort -WebPort $WebPort
if ($LASTEXITCODE -ne 0) {
    Write-Step "FAIL" "Environment check failed. See logs\check for details."
    exit 1
}

Write-Step "INFO" "Running port report..."
& (Join-Path $Root "check-ports.ps1") -BackendPort $BackendPort -TcpPort $TcpPort -WebPort $WebPort
if ($LASTEXITCODE -ne 0) {
    Write-Step "FAIL" "Port check failed. MySQL must be reachable before startup."
    exit 1
}

if (-not $SkipMysqlInit) {
    $mysqlOut = Join-Path $LogsDir "mysql\mysql-init-$Stamp.out.log"
    $mysqlErr = Join-Path $LogsDir "mysql\mysql-init-$Stamp.err.log"
    Write-Step "INFO" "Initializing MySQL database. stdout=$mysqlOut stderr=$mysqlErr"
    $mysqlProcess = Start-Process `
        -FilePath $VenvPython `
        -ArgumentList @("scripts\init_mysql.py") `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $mysqlOut `
        -RedirectStandardError $mysqlErr `
        -Wait `
        -PassThru

    if ($mysqlProcess.ExitCode -ne 0) {
        Write-Step "FAIL" "MySQL initialization failed with exit code $($mysqlProcess.ExitCode)."
        exit 1
    }
    Write-Step "OK" "MySQL database initialization completed."
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $BackendPort) {
    Write-Step "WARN" "Backend port $BackendPort is already listening. Existing service will be reused."
} else {
    Start-ServiceProcess `
        -Name "Backend" `
        -FilePath $VenvPython `
        -Arguments @("-m", "uvicorn", "app.main:app", "--app-dir", ".", "--host", "127.0.0.1", "--port", "$BackendPort", "--reload", "--reload-dir", "app") `
        -WorkingDirectory $BackendDir `
        -LogName "backend"
    Wait-Port -Name "Backend" -Port $BackendPort | Out-Null
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $TcpPort) {
    Write-Step "WARN" "TCP receiver port $TcpPort is already listening. Existing service will be reused."
} else {
    Start-ServiceProcess `
        -Name "TCP receiver" `
        -FilePath $VenvPython `
        -Arguments @("-m", "app.tcp.server") `
        -WorkingDirectory $BackendDir `
        -LogName "tcp"
    Wait-Port -Name "TCP receiver" -Port $TcpPort | Out-Null
}

$npmCommand = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
if (-not $npmCommand) {
    $npmCommand = Get-Command "npm" -ErrorAction Stop
}

if (Test-TcpPort -HostName "127.0.0.1" -Port $WebPort) {
    Write-Step "WARN" "Web port $WebPort is already listening. Existing service will be reused."
} else {
    Start-ServiceProcess `
        -Name "Web frontend" `
        -FilePath $npmCommand.Source `
        -Arguments @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$WebPort") `
        -WorkingDirectory $FrontendDir `
        -LogName "web"
    Wait-Port -Name "Web frontend" -Port $WebPort | Out-Null
}

if ($StartPcClient) {
    $pcCandidates = @(
        (Join-Path $Root "pc-client\start.ps1"),
        (Join-Path $Root "pc\start.ps1"),
        (Join-Path $Root "pc-client\start.bat"),
        (Join-Path $Root "pc\start.bat")
    )
    $pcEntry = $pcCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($pcEntry) {
        Write-Step "INFO" "Starting PC client entry: $pcEntry"
        Start-Process -FilePath $pcEntry -WorkingDirectory (Split-Path $pcEntry -Parent) -WindowStyle Hidden | Out-Null
    } else {
        Write-Step "WARN" "PC client entry was requested, but no PC start script was found."
        Write-Step "INFO" "Expected one of: pc-client\start.ps1, pc\start.ps1, pc-client\start.bat, pc\start.bat"
        Write-Step "INFO" "Place PC client logs under logs\pc-client or pc-client\logs for acceptance collection."
    }
} else {
    Write-Step "INFO" "PC client is not started by default. Use -StartPcClient after adding pc-client\start.ps1/.bat or pc\start.ps1/.bat."
}

Write-Host ""
Write-Step "INFO" "Startup flow finished."
Write-Host "Backend: http://127.0.0.1:$BackendPort/health"
Write-Host "Swagger: http://127.0.0.1:$BackendPort/docs"
Write-Host "TCP receiver: 127.0.0.1:$TcpPort"
Write-Host "Web: http://127.0.0.1:$WebPort"
Write-Host "Logs: $LogsDir"
Write-Host ""
Write-Host "Acceptance check: send HJ212 to 127.0.0.1:$TcpPort and confirm CN=9014 ACK plus Web protocol logs."
