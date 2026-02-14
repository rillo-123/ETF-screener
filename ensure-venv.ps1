# Idempotent venv activation and requirements check
# This script safely activates the virtual environment and ensures dependencies match requirements.txt
# 
# USAGE: Either of these two methods:
#   1. ensure-venv        (function from profile.ps1 - requires terminal restart to load)
#   2. . .\ensure-venv.ps1 (dot-source - works immediately)

$ErrorActionPreference = "Stop"

# Get the script directory and project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = $scriptDir
$venvDir = Join-Path $projectRoot ".venv"
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
$requirementsFile = Join-Path $projectRoot "requirements.txt"
$profileScript = Join-Path $projectRoot "profile.ps1"

# Load profile if not already loaded (check for git prompt functions)
if (-not (Get-Command Get-GitBranch -ErrorAction SilentlyContinue)) {
    if (Test-Path $profileScript) {
        . $profileScript 2>$null | Out-Null
    }
}

# Check if venv exists, create if not
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment at $venvDir..." -ForegroundColor Cyan
    python -m venv $venvDir
    if (-not $?) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Check if requirements.txt exists
if (-not (Test-Path $requirementsFile)) {
    Write-Error "requirements.txt not found at $requirementsFile"
    exit 1
}

# Activate venv if not already activated
if (-not $env:VIRTUAL_ENV) {
    # Disable prompt modification from Activate.ps1 (profile.ps1 handles it)
    $env:VIRTUAL_ENV_DISABLE_PROMPT = $true
    & $activateScript
}

# Clear the git prompt cache so it updates on next prompt
if (Get-Variable -Name GitPromptCache -Scope Global -ErrorAction SilentlyContinue) {
    Set-Variable -Name GitPromptCache -Value @{ 
        Path = $null
        Branch = $null
        Dirty = $null
        Timestamp = [datetime]::MinValue 
    } -Scope Global -Force
}

# Check if pip is available
try {
    $pipVersion = pip --version 2>$null
    if (-not $?) {
        Write-Error "pip not found in virtual environment"
        exit 1
    }
} catch {
    Write-Error "Failed to run pip"
    exit 1
}

# Get current installed packages and their versions
$currentPackages = @{}
pip freeze | ForEach-Object {
    $parts = $_ -split '=='
    if ($parts.Count -eq 2) {
        $currentPackages[$parts[0].ToLower()] = $parts[1]
    }
}

# Parse requirements.txt
$requiredPackages = @{}
Get-Content $requirementsFile | Where-Object { $_ -match '^\w' -and $_ -notmatch '^\s*#' } | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '([a-zA-Z0-9\-_.]+)\s*==\s*(.+)') {
        $requiredPackages[$matches[1].ToLower()] = $matches[2]
    }
}

# Check for mismatches
$mismatches = @()
$requiredPackages.GetEnumerator() | ForEach-Object {
    $pkgName = $_.Key
    $requiredVersion = $_.Value
    $currentVersion = $currentPackages[$pkgName]
    
    if ($null -eq $currentVersion) {
        $mismatches += "$pkgName==$requiredVersion (not installed)"
    } elseif ($currentVersion -ne $requiredVersion) {
        $mismatches += "$pkgName (installed: $currentVersion, required: $requiredVersion)"
    }
}

# Install/upgrade if needed
if ($mismatches.Count -gt 0) {
    Write-Host "Installing/updating packages..." -ForegroundColor Cyan
    pip install -r $requirementsFile
    
    if (-not $?) {
        Write-Error "Failed to install packages from requirements.txt"
        exit 1
    }
    Write-Host "✓ Packages updated" -ForegroundColor Green
} else {
    Write-Host "✓ All packages up to date" -ForegroundColor Green
}

# Install the package in editable mode (activates entry points)
Write-Host "Installing package in editable mode..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    pip install -e . --quiet 2>$null | Out-Null
    if (-not $?) {
        Write-Error "Failed to install package in editable mode"
        exit 1
    }
    Write-Host "✓ Package entry points registered" -ForegroundColor Green
} finally {
    Pop-Location
}
