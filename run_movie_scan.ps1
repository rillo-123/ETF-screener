param(
    [string]$Path = "strategies/",
    [string]$Filter = "",
    [int]$Days = 14
)

Write-Host "--- Strategy Movie Scanner (Reverse) ---" -ForegroundColor Cyan
Write-Host "Path:   $Path"
Write-Host "Days:   $Days"
Write-Host "-----------------------------"

$cmd = "set PYTHONPATH=src; python src/ETF_screener/scripts/movie_scanner.py --strat_path `"$Path`""
if ($Filter) { $cmd += " --filter `"$Filter`"" }
if ($Days) { $cmd += " --days $Days" }

Invoke-Expression $cmd
