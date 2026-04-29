
# Set the project root to ensure imports work correctly
$env:PYTHONPATH = "src"

# Define python path early so it's available for all commands
$python = "c:/Users/carlr/OneDrive/Documents/GitHub/ETF-screener/.venv/Scripts/python.exe"

Write-Host "--- ETF Discovery Lab Server ---" -ForegroundColor Cyan
Write-Host "Framework: FastAPI + Uvicorn"
Write-Host "URL:       http://127.0.0.1:5000"
Write-Host "Docs:      http://127.0.0.1:5000/docs"

Write-Host "-----------------------------"

# Refresh ETF data (backfill up to 1 year, only missing data)
Write-Host "Refreshing ETF data (backfilling up to 1 year, only missing data)..." -ForegroundColor Green
& $python src/ETF_screener/main.py refresh --depth 365
Write-Host "Data refresh complete." -ForegroundColor Green

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
    # Use triple quotes for uvicorn options to force literal passing in PowerShell
    & $python -m uvicorn "ETF_screener.dashboard.app_fast:app" --host 127.0.0.1 --port 5000 --reload --reload-dir src --reload-dir strategies --reload-include '"*.py"' --reload-include '"*.html"' --reload-include '"*.js"' --reload-include '"*.dsl"'
} else {
    Write-Error "Could not find Python executable at $python. Please ensure the venv is setup."
}
