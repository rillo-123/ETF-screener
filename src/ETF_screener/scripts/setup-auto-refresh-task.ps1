# Setup automated ETF database refresh at logon
# This script creates a Windows Task Scheduler task to run auto-refresh.ps1 at logon
# Run this script with admin privileges: powershell -ExecutionPolicy Bypass -File setup-auto-refresh-task.ps1

$ErrorActionPreference = "Stop"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script must run as Administrator. Please right-click PowerShell and select 'Run as administrator'"
    exit 1
}

# Get project root
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$refreshScript = Join-Path $projectRoot "auto-refresh.ps1"

if (-not (Test-Path $refreshScript)) {
    Write-Error "auto-refresh.ps1 not found at $refreshScript"
    exit 1
}

Write-Host "📋 Setting up auto-refresh scheduled task..." -ForegroundColor Cyan

# Task details
$taskName = "ETF Screener Auto-Refresh"
$taskDescription = "Automatically refresh ETF database on logon"
$taskPath = "\ETF Screener\"
$fullTaskPath = "{0}{1}" -f $taskPath, $taskName

# Get current user
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task: $fullTaskPath" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false | Out-Null
}

# Create task folder
$taskFolder = Get-ScheduledTaskFolder -Path "\" -ErrorAction SilentlyContinue
if (-not (Test-Path "Microsoft.PowerShell.Core\FileSystem::\\?$\SYSTEM\CurrentControlSet\Services\Schedule\TaskScheduler\Tree$taskPath")) {
    $taskFolder.CreateFolder($taskPath.Trim("\")) | Out-Null
    Write-Host "✓ Created task folder: $taskPath" -ForegroundColor Green
}

# Create task trigger (at logon)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Create task action (run PowerShell script)
$psArgs = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"{0}`"" -f $refreshScript
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArgs

# Create task settings
$settings = New-ScheduledTaskSettingsSet -MultipleInstances Parallel -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -TaskPath $taskPath `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Description $taskDescription `
        -User $currentUser `
        -RunLevel Highest `
        -Force | Out-Null
    
    Write-Host "✓ Task created successfully" -ForegroundColor Green
    Write-Host "  Task Name: $fullTaskPath" -ForegroundColor White
    Write-Host "  Trigger: At logon for user $currentUser" -ForegroundColor White
    Write-Host "  Action: Run auto-refresh.ps1" -ForegroundColor White
    
} catch {
    Write-Error "Failed to create scheduled task: $_"
    exit 1
}

Write-Host ""
Write-Host "📊 Auto-refresh is now enabled!" -ForegroundColor Green
Write-Host ""
Write-Host "Details:" -ForegroundColor Cyan
Write-Host "  ✓ Runs every time you log on to Windows"
Write-Host "  ✓ Keeps 30 days of history (shallow refresh - 2-3 min)"
Write-Host "  ✓ Logs to: logs\auto-refresh.log"
Write-Host ""
Write-Host "To view the log:" -ForegroundColor Cyan
Write-Host "  Get-Content .\logs\auto-refresh.log -Tail 20"
Write-Host ""
Write-Host "To disable:" -ForegroundColor Cyan
Write-Host "  Unregister-ScheduledTask -TaskPath '\ETF Screener\' -TaskName 'ETF Screener Auto-Refresh' -Confirm:`$false"
Write-Host ""
