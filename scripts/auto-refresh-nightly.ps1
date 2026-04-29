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
    @'
from ETF_screener.config_loader import get_paths
from ETF_screener.market_data_service import MarketDataRefresher

db_path = get_paths()["data"]["etf_db"]
refresher = MarketDataRefresher(db_path=db_path)
status = refresher.refresh_market_data(
    depth=730,
    stale_after_days=0,
    force=True,
    max_workers=8,
    rebuild_shortlist=True,
)
print(status)
'@ | python -
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
