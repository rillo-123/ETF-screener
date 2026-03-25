param(
    [string]$StrategyPath = "",
    [string]$TickerFilter = "",
    [int]$Lookback = 0,
    [switch]$Show = $false,
    [int]$Plot = 0
)

Write-Host "--- Strategy Movie Scanner (Reverse) ---" -ForegroundColor Cyan
Write-Host "Path:     $($StrategyPath -or 'Default from settings')"
if ($Lookback -gt 0) { Write-Host "Lookback: $Lookback" }
if ($Show) { Write-Host "Show:     Yes" }
if ($Plot -gt 0) { Write-Host "Plot:     Limit to $Plot" }
elseif ($Plot -eq -1) { Write-Host "Plot:     Yes (All)" }
Write-Host "-----------------------------"

$cmd = "set PYTHONPATH=src; python src/ETF_screener/scripts/movie_scanner.py"
if ($StrategyPath) { $cmd += " --strat_path `"$StrategyPath`"" }
if ($TickerFilter) { $cmd += " --filter `"$TickerFilter`"" }
if ($Lookback -gt 0) { $cmd += " --lookback $Lookback" }
if ($Show) { $cmd += " --open" }
if ($Plot -ne 0) { 
    $cmd += " --plot $Plot"
}

Invoke-Expression $cmd
