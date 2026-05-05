# Quiet ETF database refresh that runs at logon.
# Intended to be launched from the Windows Startup folder.

$ErrorActionPreference = "SilentlyContinue"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".."))
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "startup-refresh.log"
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runLogFile = Join-Path $logDir "startup-refresh_$runStamp.log"
$venvActivate = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

try {
    [System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = "BelowNormal"
} catch {
    # If priority adjustment is not available, keep going quietly.
}

$mutexName = "Local\ETF_Screener_Startup_Refresh"
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, $mutexName, [ref]$createdNew)
if (-not $createdNew) {
    if ($logFile) {
        try {
            Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Another startup refresh is already running; exiting"
        } catch {
            # Ignore logging failures during duplicate start-up.
        }
    }
    $mutex.Dispose()
    return
}

function Write-LogLine {
    param([string]$Message)
    $Message | Out-File -FilePath $logFile -Append -Encoding utf8
    $Message | Out-File -FilePath $runLogFile -Append -Encoding utf8
}

function Invoke-LoggedCommand {
    param(
        [scriptblock]$Command
    )

    & $Command 2>&1 | ForEach-Object {
        $line = $_.ToString()
        Write-LogLine $line
    }

    return $LASTEXITCODE
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Starting startup refresh..." | Out-File -FilePath $logFile -Encoding utf8
"[$timestamp] Starting startup refresh..." | Out-File -FilePath $runLogFile -Encoding utf8
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-LogLine "[$timestamp] Startup worker launched"
Write-LogLine "[$timestamp] Log file: $runLogFile"

$exitCode = 0
try {
    if (-not (Test-Path $venvActivate)) {
        throw "Virtual environment not found at $venvActivate"
    }

    Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Activating virtual environment"
    $env:VIRTUAL_ENV_DISABLE_PROMPT = $true
    & $venvActivate
    Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Virtual environment activated"

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-LogLine "[$timestamp] Preparing market refresh"
    Write-LogLine "[$timestamp] Refresh parameters: depth=365 stale_after_days=0 force=False max_workers=2 rebuild_shortlist=False"

    $refreshExitCode = Invoke-LoggedCommand -Command {
        $env:PYTHONPATH = "src"
        @'
import json
from ETF_screener.config_loader import get_paths
from ETF_screener.market_data_service import MarketDataRefresher

db_path = get_paths()["data"]["etf_db"]
print(f"[PYTHON] Using database: {db_path}")
refresher = MarketDataRefresher(db_path=db_path)
print("[PYTHON] Starting refresh_market_data(...)")
status = refresher.refresh_market_data(
    depth=365,
    stale_after_days=0,
    force=False,
    max_workers=2,
    rebuild_shortlist=False,
)
print("[PYTHON] Refresh complete")
print(json.dumps(status, sort_keys=True))
'@ | python -
    }

    if ($refreshExitCode -eq 0) {
        Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Market refresh completed successfully"
        Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [OK] Startup refresh completed"
        $exitCode = 0
    } else {
        throw "Refresh command failed"
    }
} catch {
    Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Startup refresh failed"
    Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [ERROR] $_"
    $exitCode = 1
} finally {
    try {
        $mutex.ReleaseMutex() | Out-Null
        $mutex.Dispose()
    } catch {
        # Ignore shutdown cleanup issues.
    }
}

Write-LogLine "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Exiting startup refresh process"
exit $exitCode
