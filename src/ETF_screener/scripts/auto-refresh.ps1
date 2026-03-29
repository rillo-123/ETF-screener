# Auto-refresh ETF database on logon
# This script runs etfs refresh with a shallow depth (30 days) to keep data fresh
# Then generates a hotlist of swing trading prospects
# Designed to run once per day at logon via Windows Task Scheduler

$ErrorActionPreference = "SilentlyContinue"

# Get project paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\..\.."))
$logDir = Join-Path $projectRoot "logs"
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "auto-refresh.log"
$runLogFile = Join-Path $logDir "auto-refresh_$runStamp.log"

# Create logs directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-LogLine {
    param([string]$Message)
    $Message | Out-File -FilePath $logFile -Append -Encoding utf8
    $Message | Out-File -FilePath $runLogFile -Append -Encoding utf8
}

function Invoke-LoggedCommand {
    param(
        [scriptblock]$Command,
        [string]$Prefix = $null
    )

    & $Command 2>&1 | ForEach-Object {
        $line = $_.ToString()
        if ($Prefix) {
            $line = "$Prefix$line"
        }
        Write-Host $line
        Write-LogLine $line
    }

    return $LASTEXITCODE
}

# Initialize log
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Starting auto-refresh..." | Out-File -FilePath $logFile -Encoding utf8
"[$timestamp] Starting auto-refresh..." | Out-File -FilePath $runLogFile -Encoding utf8

try {
    # Activate venv
    $venvScript = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvScript) {
        $env:VIRTUAL_ENV_DISABLE_PROMPT = $true
        & $venvScript
        Write-LogLine "[$timestamp] Venv activated"
        Write-LogLine "[$timestamp] Run log: $runLogFile"
    } else {
        throw "Virtual environment not found at $venvScript"
    }

    # Run refresh with shallow depth (30 days - quick update)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-LogLine "[$timestamp] Running: etfs refresh --depth 30 --force"
    
    # Run refresh and capture output to both the latest log and the per-run log.
    # Line-by-line logging avoids the encoding/control-character corruption that
    # made previous appended logs hard to read.
    $refreshExitCode = Invoke-LoggedCommand -Command { etfs refresh --depth 30 --force }
    
    if ($refreshExitCode -eq 0) {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-LogLine "[$timestamp] [OK] Refresh completed successfully"
        
        # Generate hotlist of swing trading prospects
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-LogLine "[$timestamp] Generating swing trading hotlist..."
        
        $hotlistExitCode = Invoke-LoggedCommand -Command { etfs hotlist --aVol 50K --days 10 --swing-pull 2.0 --ema-distance 5.0 }
        
        if ($hotlistExitCode -eq 0) {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Write-LogLine "[$timestamp] [OK] Hotlist generated successfully"
            exit 0
        } else {
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Write-LogLine "[$timestamp] [WARNING] Hotlist generation failed"
            exit 0  # Don't fail the script if hotlist fails
        }
    } else {
        throw "Refresh command failed"
    }

} catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-LogLine "[$timestamp] [ERROR] Error: $_"
    exit 1
}
