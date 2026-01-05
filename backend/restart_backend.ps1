# Restart SlotFit Backend Server
# This script stops any existing backend process and starts a new one

Write-Host "Stopping existing backend processes..." -ForegroundColor Yellow

# Find and stop process using port 8000
$procs = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($procs) {
    foreach ($proc in $procs) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Stopped process(es) on port 8000" -ForegroundColor Green
} else {
    Write-Host "No process found on port 8000" -ForegroundColor Gray
}

# Also stop any Python processes that might be running uvicorn
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
        if ($cmdLine -like "*uvicorn*" -or $cmdLine -like "*app.main*") {
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # Ignore errors getting command line
    }
}

Start-Sleep -Seconds 1

Write-Host "Starting backend server..." -ForegroundColor Yellow
Write-Host "Server will be available at http://localhost:8000" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Change to backend directory and start server
Set-Location $PSScriptRoot

# Create logs directory if it doesn't exist
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "backend.log"
$errorLogFile = Join-Path $logDir "backend_error.log"

Write-Host "Logs will be written to:" -ForegroundColor Cyan
Write-Host "  Output: $logFile" -ForegroundColor Gray
Write-Host "  Errors: $errorLogFile" -ForegroundColor Gray
Write-Host ""

# Start server with output redirection
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 *> $logFile
