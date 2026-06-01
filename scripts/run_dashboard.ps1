param()

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $scriptRoot) -ieq 'scripts') {
    $root = Split-Path -Parent $scriptRoot
} else {
    $root = $scriptRoot
}

$env:PYTHONPATH = "src"
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "--- ETF Discovery Lab Server ---" -ForegroundColor Cyan
Write-Host "Framework: FastAPI + Uvicorn"
Write-Host "URL:       http://127.0.0.1:5000"
Write-Host "Docs:      http://127.0.0.1:5000/docs"
Write-Host "-----------------------------"
Write-Host "Starting with a data refresh first, then launching the dashboard server..." -ForegroundColor Cyan

# Refresh ETF data (backfill up to 1 year, only missing data).
Write-Host "Refreshing ETF data (backfilling up to 1 year, only missing data)..." -ForegroundColor Green
& $python (Join-Path $root "src\ETF_screener\main.py") refresh --depth 365
Write-Host "Data refresh complete." -ForegroundColor Green

# Stop any existing dashboard server before starting a fresh reload-enabled one.
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
    Write-Host "Starting server with auto-reload on port 5000..." -ForegroundColor Gray
    & $python -m uvicorn "ETF_screener.dashboard.app_fast:app" `
        --host 127.0.0.1 `
        --port 5000 `
        --reload `
        --reload-dir src `
        --reload-dir strategies `
        --reload-include '"*.py"' `
        --reload-include '"*.html"' `
        --reload-include '"*.js"' `
        --reload-include '"*.dsl"'
} else {
    Write-Error "Could not find Python executable at $python. Please ensure the venv is setup."
}
