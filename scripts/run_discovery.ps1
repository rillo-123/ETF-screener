param(
    [string]$StrategyPath = "strategies/",
    [string]$TickerFilter = "",
    [int]$Plot = 0,
    [int]$Lookback = -1,
    [switch]$Show,
    [switch]$PlotDash,
    [switch]$Clean = $true
)

Write-Host "--- Strategy Discovery Lab ---" -ForegroundColor Cyan
Write-Host "Path:     $StrategyPath"
Write-Host "Filter:   $(if($TickerFilter){$TickerFilter}else{'None'})"
Write-Host "Plot:     $Plot"
Write-Host "Lookback: $(if($Lookback -ge 0){$Lookback}else{'All Time'})"
Write-Host "Dashboard: $(if($PlotDash){'Yes'}else{'No'})"
Write-Host "-----------------------------"

# Ensure output path exists
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" }

# Execute the churner
$env:PYTHONPATH = "src"
$python = "c:/Users/carlr/OneDrive/Documents/GitHub/ETF-screener/.venv/Scripts/python.exe"
$cmd_args = @("src/ETF_screener/scripts/churn_strategies.py", "--strat_path", "$StrategyPath")

if ($TickerFilter) { $cmd_args += "--filter"; $cmd_args += "$TickerFilter" }
if ($Plot -gt 0) { $cmd_args += "--plot"; $cmd_args += "$Plot" }
if ($Lookback -ge 0) { $cmd_args += "--since"; $cmd_args += "$Lookback" }
if ($Clean) { $cmd_args += "--force" }

# Run the command
Write-Host "Running Discovery: $python $($cmd_args -join ' ')" -ForegroundColor Gray
& $python $cmd_args

# Open the dashboard if requested
if ($PlotDash) {
    if (Test-Path "plots/index.html") {
        $dashboard = Resolve-Path "plots/index.html"
        Write-Host "Opening Dashboard: $dashboard" -ForegroundColor Green
        Start-Process $dashboard
    } else {
        Write-Warning "Dashboard file not found: plots/index.html"
    }
}

$resultFile = "data/multi_strategy_results.csv"

if (Test-Path $resultFile) {
    if ($Show) {
        $libreOfficePath = "C:\Program Files\LibreOffice\program\scalc.exe"
        if (Test-Path $libreOfficePath) {
            Write-Host "Opening results in LibreOffice Calc..." -ForegroundColor Green
            Start-Process $libreOfficePath -ArgumentList "`"$resultFile`""
        } else {
            Invoke-Item $resultFile
        }
    } else {
        Write-Host "Discovery complete. Results saved to: $resultFile" -ForegroundColor Green
    }
} else {
    Write-Warning "Discovery failed to produce results folder or file."
}
