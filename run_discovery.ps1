param(
    [string]$Path = "strategies/",
    [string]$Filter = "",
    [switch]$OpenResult
)

Write-Host "--- Strategy Discovery Lab ---" -ForegroundColor Cyan
Write-Host "Path:   $Path"
Write-Host "Filter: $(if($Filter){$Filter}else{'None'})"
Write-Host "-----------------------------"

# Ensure output path exists
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" }

# Execute the churner
$cmd = "set PYTHONPATH=src; python src/ETF_screener/scripts/churn_strategies.py --strat_path `"$Path`""
if ($Filter) { $cmd += " --filter `"$Filter`"" }

Write-Host "Running Discovery Engine..." -ForegroundColor Gray
Invoke-Expression $cmd

$resultFile = "data/multi_strategy_results.csv"

if (Test-Path $resultFile) {
    if ($OpenResult) {
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
