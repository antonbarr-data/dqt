$repoRoot = Split-Path $PSScriptRoot -Parent

# --- Frontend (port 3000) ---
Write-Host "Looking for processes on port 3000..."
$connFe = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($connFe) {
    foreach ($c in $connFe) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "  killing PID $($c.OwningProcess) ($($proc.Name))"
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  (nothing found on port 3000)"
}

Write-Host "Clearing .next cache..."
$nextDir = "$repoRoot\apps\web\.next"
if (Test-Path $nextDir) {
    Remove-Item -Recurse -Force $nextDir
    Write-Host "  .next removed"
} else {
    Write-Host "  (.next not present)"
}

Write-Host "Starting frontend in new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot\apps\web'; pnpm dev"

# --- Backend (port 8000) ---
Write-Host "Looking for processes on port 8000..."
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        $pid8k = $c.OwningProcess
        $proc = Get-Process -Id $pid8k -ErrorAction SilentlyContinue
        Write-Host "  killing PID $pid8k ($($proc.Name))"
        Stop-Process -Id $pid8k -Force -ErrorAction SilentlyContinue
        # Also kill any Python child processes whose parent_pid matches (uvicorn spawn workers)
        $children = Get-CimInstance Win32_Process | Where-Object {
            $_.CommandLine -like "*parent_pid=$pid8k*"
        }
        foreach ($child in $children) {
            Write-Host "  killing child PID $($child.ProcessId)"
            Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "  (nothing found on port 8000)"
}

# Kill any remaining uvicorn-related Python processes
$uvicornProcs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*uvicorn*dqt_server*" -or $_.CommandLine -like "*dqt_server.main*"
}
foreach ($p in $uvicornProcs) {
    Write-Host "  killing stale uvicorn PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

# Wait until port is actually free
$waited = 0
while ($waited -lt 10) {
    Start-Sleep -Seconds 1
    $still = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if (-not $still) { break }
    $waited++
}
if ($waited -ge 10) {
    Write-Host "ERROR: port 8000 still in use after 10s - aborting"
    exit 1
}
Write-Host "Port 8000 is free. Starting server..."

Set-Location "$repoRoot\apps\server"
uv run uvicorn dqt_server.main:app --reload --reload-dir src --reload-dir "$repoRoot\packages\dqt\src" --host 0.0.0.0 --port 8000
