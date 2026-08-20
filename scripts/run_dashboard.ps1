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
    # Do not make the dashboard wait for a potentially long first-run refresh.
    # SQLite WAL mode lets the server read the existing data while this process
    # adds fresh rows in the background.
    $logDir = Join-Path $root "logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $refreshScript = Join-Path $root "src\ETF_screener\main.py"
    $refreshOutLog = Join-Path $logDir "dashboard-refresh.out.log"
    $refreshErrLog = Join-Path $logDir "dashboard-refresh.err.log"
    $refreshProcess = Start-Process `
        -FilePath $python `
        -ArgumentList @($refreshScript, "refresh", "--depth", "365") `
        -WorkingDirectory $root `
        -RedirectStandardOutput $refreshOutLog `
        -RedirectStandardError $refreshErrLog `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "Refreshing ETF data in the background (PID: $($refreshProcess.Id))." -ForegroundColor Green
    Write-Host "The dashboard is available immediately; refresh logs are in logs\dashboard-refresh.*.log." -ForegroundColor Gray

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
