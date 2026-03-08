# auto-refresh-nightly.ps1
# This script waits until 3 AM, runs the ETF refresh, and prevents sleep during execution.

$targetTime = "03:00:00"
$today = Get-Date -Format "yyyy-MM-dd"
$targetDate = Get-Date ("$today $targetTime")

# If it's already past 3 AM, set for tomorrow
if ((Get-Date) -gt $targetDate) {
    $targetDate = $targetDate.AddDays(1)
}

Write-Host "[NIGHTLY] Waiting until $targetDate to start refresh..." -ForegroundColor Cyan
while ((Get-Date) -lt $targetDate) {
    $remaining = $targetDate - (Get-Date)
    Write-Progress -Activity "Waiting for Nightly Refresh" -Status "Starting in $($remaining.Hours)h $($remaining.Minutes)m"
    Start-Sleep -Seconds 60
}

Write-Host "[NIGHTLY] 3:00 AM reached! Starting refresh..." -ForegroundColor Green

# Prevent sleep while this process is running
$execution = Start-Job -ScriptBlock {
    $env:PYTHONPATH = "src"
    # Using python -m to ensure package discovery
    python -m ETF_screener.main refresh --depth 730
}

# Keep the terminal busy so Windows sees activity
while ($execution.State -eq "Running") {
    Write-Host "Refreshing... $(Get-Date -Format "HH:mm:ss")"
    Start-Sleep -Seconds 30
}

$output = Receive-Job -Job $execution
Write-Host "[NIGHTLY] Refresh Complete!" -ForegroundColor Green
Write-Host $output

# Now Windows is free to go back to sleep normally.
