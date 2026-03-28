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

$args = @("src/ETF_screener/scripts/movie_scanner.py")
if ($StrategyPath) { $args += "--strat_path"; $args += "$StrategyPath" }
if ($TickerFilter) { $args += "--filter"; $args += "$TickerFilter" }
if ($Lookback -gt 0) { $args += "--lookback"; $args += "$Lookback" }
if ($Show) { $args += "--open" }
if ($Plot -ne 0) { 
    $args += "--plot"; $args += "$Plot"
}

$env:PYTHONPATH = "src"
$python = "c:/Users/carlr/OneDrive/Documents/GitHub/ETF-screener/.venv/Scripts/python.exe"
& $python $args
