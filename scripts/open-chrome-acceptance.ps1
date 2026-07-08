$ErrorActionPreference = "Stop"

$urls = @(
  "http://127.0.0.1:5173",
  "http://127.0.0.1:5173/data-query",
  "http://127.0.0.1:5173/protocol",
  "http://127.0.0.1:5173/telemetry",
  "http://127.0.0.1:5173/analysis",
  "http://127.0.0.1:8000/health"
)

foreach ($url in $urls) {
  Start-Process $url
}

Write-Host "Chrome acceptance URLs opened:"
$urls | ForEach-Object { Write-Host "- $_" }

