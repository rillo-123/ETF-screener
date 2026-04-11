Write-Host "--- Full Churn (All Tickers x All Strategies) ---" -ForegroundColor Cyan
Write-Host "Mode: no filters, all strategies in strategies/, no lookback limit" -ForegroundColor Gray
Write-Host "-------------------------------------------------"

scripts/run_discovery.ps1 -StrategyPath "strategies/" -Plot 0 -Lookback -1 -Clean
