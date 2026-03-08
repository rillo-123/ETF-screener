# Auto-refresh ETF database on logon
# This script runs etfs refresh with a shallow depth (30 days) to keep data fresh
# Then generates a hotlist of swing trading prospects
# Designed to run once per day at logon via Windows Task Scheduler

$ErrorActionPreference = "SilentlyContinue"

# Get project paths
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$logFile = Join-Path $projectRoot "logs\auto-refresh.log"
$logDir = Split-Path -Parent $logFile

# Create logs directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Initialize log
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Starting auto-refresh..." | Out-File -FilePath $logFile -Append

try {
    # Activate venv
    $venvScript = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvScript) {
        $env:VIRTUAL_ENV_DISABLE_PROMPT = $true
        & $venvScript
        "[$timestamp] Venv activated" | Out-File -FilePath $logFile -Append
    } else {
        throw "Virtual environment not found at $venvScript"
    }

    # Run refresh with shallow depth (30 days - quick update)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] Running: etfs refresh --depth 30 --force" | Out-File -FilePath $logFile -Append
    
    # Run refresh and capture output to log while also showing it in the console
    # Using Tee-Object to show output (including progress bars) to user
    etfs refresh --depth 30 --force 2>&1 | Tee-Object -FilePath $logFile -Append
    
    if ($LASTEXITCODE -eq 0) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$timestamp] [OK] Refresh completed successfully" | Out-File -FilePath $logFile -Append
        
        # Generate hotlist of swing trading prospects
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$timestamp] Generating swing trading hotlist..." | Out-File -FilePath $logFile -Append
        
        etfs hotlist --aVol 50K --days 10 --swing-pull 2.0 --ema-distance 5.0 2>&1 | Tee-Object -FilePath $logFile -Append
        
        if ($LASTEXITCODE -eq 0) {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "[$timestamp] [OK] Hotlist generated successfully" | Out-File -FilePath $logFile -Append
            exit 0
        } else {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "[$timestamp] [WARNING] Hotlist generation failed" | Out-File -FilePath $logFile -Append
            exit 0  # Don't fail the script if hotlist fails
        }
    } else {
        throw "Refresh command failed"
    }

} catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timestamp] [ERROR] Error: $_" | Out-File -FilePath $logFile -Append
    exit 1
}
