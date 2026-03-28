# Set the project root to ensure imports work correctly
$env:PYTHONPATH = "src"

Write-Host "--- ETF Discovery Lab Server ---" -ForegroundColor Cyan
Write-Host "Framework: FastAPI + Uvicorn"
Write-Host "URL:       http://127.0.0.1:5000"
Write-Host "Docs:      http://127.0.0.1:5000/docs"
Write-Host "-----------------------------"

$python = "c:/Users/carlr/OneDrive/Documents/GitHub/ETF-screener/.venv/Scripts/python.exe"
$appPath = "src/ETF_screener/dashboard/app_fast.py"

# Check if port 5000 is already in use
$portProcess = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($portProcess) {
    $procId = $portProcess[0].OwningProcess
    $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($process -and ($process.ProcessName -match "python|uvicorn")) {
        Write-Host "Server already running (PID: $procId). Stopping it first..." -ForegroundColor Yellow
        Stop-Process -Id $procId -Force
        Start-Sleep -Seconds 1
    }
}

if (Test-Path $python) {
    Write-Host "Starting server..." -ForegroundColor Gray
    # Run with uvicorn --reload to handle source changes automatically
    # Only monitor .py and .html files to avoid unnecessary restarts from log/data files
    & $python -m uvicorn ETF_screener.dashboard.app_fast:app --host 127.0.0.1 --port 5000 --reload --reload-dir src --reload-include "*.py" --reload-include "*.html"
} else {
    Write-Error "Could not find Python executable at $python. Please ensure the venv is setup."
}
