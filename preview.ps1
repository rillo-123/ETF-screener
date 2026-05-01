param(
    [Parameter(Position=0)]
    [string[]]$Symbols = @("EXS1.DE"),

    [Parameter(Position=1)]
    [string]$StrategyPath = "",
    [int]$Days = 60,
    [string]$PlotDir = "plots",
    [string]$DataDir = "data",
    [switch]$NoOpen = $false
)

$env:PYTHONPATH = "src"
$python = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Could not find Python executable at $python. Please ensure the venv is set up."
    exit 1
}

if (-not $Symbols -or $Symbols.Count -eq 0) {
    $Symbols = @("EXS1.DE")
}

$env:PREVIEW_SYMBOLS = ($Symbols -join ",")
$env:PREVIEW_DAYS = "$Days"
$env:PREVIEW_PLOT_DIR = $PlotDir
$env:PREVIEW_DATA_DIR = $DataDir
$env:PREVIEW_STRATEGY_PATH = $StrategyPath

Write-Host "--- Quick Preview ---" -ForegroundColor Cyan
Write-Host "Symbols:     $($Symbols -join ', ')" -ForegroundColor Gray
Write-Host "Days:        $Days" -ForegroundColor Gray
if ($StrategyPath) {
    Write-Host "Strategy:    $StrategyPath" -ForegroundColor Gray
}
Write-Host "---------------------"

$pythonScript = @'
import os
from pathlib import Path

import pandas as pd

from ETF_screener.indicators import add_indicators
from ETF_screener.plotter_plotly import InteractivePlotter
from ETF_screener.storage import ParquetStorage
from ETF_screener.yfinance_fetcher import YFinanceFetcher


def load_strategy(strategy_path: str) -> str | None:
    if not strategy_path:
        return None
    path = Path(strategy_path)
    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")
    return path.read_text(encoding="utf-8")


symbols = [s.strip() for s in os.environ.get("PREVIEW_SYMBOLS", "").split(",") if s.strip()]
days = int(os.environ.get("PREVIEW_DAYS", "60"))
plot_dir = os.environ.get("PREVIEW_PLOT_DIR", "plots")
data_dir = os.environ.get("PREVIEW_DATA_DIR", "data")
strategy_content = load_strategy(os.environ.get("PREVIEW_STRATEGY_PATH", ""))

storage = ParquetStorage(data_dir=data_dir)
fetcher = YFinanceFetcher()
plotter = InteractivePlotter(output_dir=plot_dir)
written_paths: list[str] = []

for symbol in symbols:
    df = storage.load_etf_data(symbol)
    if df is None or df.empty:
        print(f"Cache miss for {symbol}; fetching {days} days from Yahoo Finance...")
        fetched = fetcher.fetch_multiple_etfs([symbol], days=days, quiet=False)
        df = fetched.get(symbol, pd.DataFrame())
        if df.empty:
            raise RuntimeError(f"No data available for {symbol}")
        df = add_indicators(df)
        storage.save_etf_data(df, symbol)
    else:
        df = df.tail(days).copy()
        df = add_indicators(df)

    fig = plotter.create_plot(df, symbol, strategy_content=strategy_content)
    output_path = Path(plot_dir) / f"{symbol.lower()}_interactive.html"
    post_script = (
        "var s=document.createElement('style');"
        "s.textContent='.modebar-container{"
        "border:1px solid #d1d5db;"
        "border-radius:4px;"
        "padding:2px;"
        "}';"
        "document.head.appendChild(s);"
    )
    fig.write_html(
        str(output_path),
        post_script=post_script,
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "scrollZoom": True,
        },
    )
    written_paths.append(str(output_path))
    print(f"Preview written: {output_path}")
'@

$result = & $python -c $pythonScript 2>&1
$exitCode = $LASTEXITCODE
if ($result) {
    Write-Host ($result -join [Environment]::NewLine)
}
if ($exitCode -ne 0) {
    exit $exitCode
}

if (-not $NoOpen) {
    $firstSymbol = $Symbols[0].ToLower()
    $plotPath = Join-Path $PlotDir ("{0}_interactive.html" -f $firstSymbol)
    if (Test-Path $plotPath) {
        Start-Process $plotPath
    } else {
        Write-Warning "Preview file not found: $plotPath"
    }
}
