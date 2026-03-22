param(
    [string]$StrategyPath = "",
    [string]$TickerFilter = "",
    [int]$Lookback = 0,
    [switch]$Show = $false
)

Write-Host "--- Strategy Movie Scanner (Reverse) ---" -ForegroundColor Cyan
Write-Host "Path:     $($StrategyPath -or 'Default from settings')"
if ($Lookback -gt 0) { Write-Host "Lookback: $Lookback" }
if ($Show) { Write-Host "Show:     Yes" }
Write-Host "-----------------------------"

$cmd = "set PYTHONPATH=src; python src/ETF_screener/scripts/movie_scanner.py"
if ($StrategyPath) { $cmd += " --strat_path `"$StrategyPath`"" }
if ($TickerFilter) { $cmd += " --filter `"$TickerFilter`"" }
if ($Lookback -gt 0) { $cmd += " --days $Lookback" }
if ($Show) { $cmd += " --open" }

Invoke-Expression $cmd
