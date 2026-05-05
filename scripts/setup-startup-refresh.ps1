# Install a quiet ETF refresh launcher into the current user's Windows Startup folder.

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir ".."))
$launchScript = Join-Path $projectRoot "scripts\startup-refresh.ps1"

if (-not (Test-Path $launchScript)) {
    throw "startup-refresh.ps1 not found at $launchScript"
}

$startupFolder = [Environment]::GetFolderPath("Startup")
if (-not $startupFolder) {
    throw "Could not resolve the current user's Startup folder"
}

$shortcutPath = Join-Path $startupFolder "ETF Screener - Refresh.lnk"
$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path $powershellExe)) {
    $powershellExe = "powershell.exe"
}

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $launchScript
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$powershellExe,0"
$shortcut.Save()

Write-Host "Installed startup launcher:" -ForegroundColor Green
Write-Host "  $shortcutPath" -ForegroundColor White
Write-Host "It will run at logon with below-normal priority and low concurrency." -ForegroundColor Gray
