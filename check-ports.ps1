[CmdletBinding()]
param(
    [int]$MySqlPort = 3306,
    [int]$BackendPort = 8000,
    [int]$TcpPort = 9100,
    [int]$WebPort = 5173
)

$ErrorActionPreference = "Continue"

function Get-PortListeners {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        $processName = "unknown"
        try {
            $processName = (Get-Process -Id $connection.OwningProcess -ErrorAction Stop).ProcessName
        } catch {
            $processName = "pid-$($connection.OwningProcess)"
        }

        [pscustomobject]@{
            Port = $Port
            Address = $connection.LocalAddress
            Pid = $connection.OwningProcess
            Process = $processName
        }
    }

    if (-not $connections) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1000, $false)) {
                $client.EndConnect($async)
                [pscustomobject]@{
                    Port = $Port
                    Address = "127.0.0.1"
                    Pid = "n/a"
                    Process = "reachable; listener not enumerable by Get-NetTCPConnection"
                }
            }
        } catch {
            # No listener reachable on 127.0.0.1.
        } finally {
            $client.Close()
        }
    }
}

function Write-PortReport {
    param(
        [string]$Name,
        [int]$Port,
        [string]$Expected
    )

    $listeners = @(Get-PortListeners -Port $Port)
    if ($listeners.Count -eq 0) {
        if ($Expected -eq "listening") {
            Write-Host "[FAIL] $Name port $Port is not listening."
            return 1
        }

        Write-Host "[OK]   $Name port $Port is free."
        return 0
    }

    foreach ($listener in $listeners) {
        $line = "$Name port $Port listening on $($listener.Address), pid=$($listener.Pid), process=$($listener.Process)"
        if ($Expected -eq "free") {
            Write-Host "[WARN] $line"
        } else {
            Write-Host "[OK]   $line"
        }
    }

    return 0
}

$failures = 0
$failures += Write-PortReport -Name "MySQL" -Port $MySqlPort -Expected "listening"
$failures += Write-PortReport -Name "Backend" -Port $BackendPort -Expected "free"
$failures += Write-PortReport -Name "TCP receiver" -Port $TcpPort -Expected "free"
$failures += Write-PortReport -Name "Web" -Port $WebPort -Expected "free"

Write-Host ""
Write-Host "Note: Backend/TCP/Web listeners are warnings before startup. Confirm the PID is expected before acceptance."

if ($failures -gt 0) {
    exit 1
}

exit 0
