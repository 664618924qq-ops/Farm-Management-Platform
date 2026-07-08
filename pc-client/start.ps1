$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$EnvPath = Join-Path $ProjectRoot ".env"
$EnvExamplePath = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path -LiteralPath $EnvPath)) {
    if (Test-Path -LiteralPath $EnvExamplePath) {
        Copy-Item -LiteralPath $EnvExamplePath -Destination $EnvPath
    } else {
        New-Item -Path $EnvPath -ItemType File | Out-Null
    }
}

$script:EnvContent = Get-Content -LiteralPath $EnvPath -Raw -Encoding UTF8

function Set-EnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $line = "$Name='$Value'"
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"
    if ($script:EnvContent -match $pattern) {
        $script:EnvContent = [regex]::Replace($script:EnvContent, $pattern, $line)
    } else {
        if ($script:EnvContent.Length -gt 0 -and -not $script:EnvContent.EndsWith("`n")) {
            $script:EnvContent += "`r`n"
        }
        $script:EnvContent += "$line`r`n"
    }
}

Set-EnvValue -Name "PLATFORM_HOST" -Value "127.0.0.1"
Set-EnvValue -Name "PLATFORM_PORT" -Value "9100"
Set-EnvValue -Name "PLATFORM_ACK_TIMEOUT_SECONDS" -Value "3.0"

Set-Content -LiteralPath $EnvPath -Value $script:EnvContent -Encoding UTF8

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Host "Creating local Python virtual environment..."
    python -m venv .venv
}

Write-Host "Checking desktop runtime dependencies..."
& $PythonExe ".\scripts\check_runtime_env.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies from requirements.txt..."
    & $PythonExe -m pip install -r ".\requirements.txt"
    & $PythonExe ".\scripts\check_runtime_env.py"
}

Write-Host "Starting shrimp monitoring PC client..."
Write-Host "Platform TCP: 127.0.0.1:9100, ACK required, ACK timeout: 3.0s"
& $PythonExe -m desktop_app.main
