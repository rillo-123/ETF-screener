param(
    [Parameter(Position=0)]
    [string[]]$ManualSymbols,
    
    [string]$TickerFilter = "",
    [string]$Format = "svg",
    [int]$Lookback = 30,
    [int]$MaxTickers = 0,
    [switch]$Clean = $true,
    [switch]$MovieScan = $true,
    [switch]$Quiet = $true
)

# 1. Clean old plots if requested
if ($Clean) {
    Write-Host "--- Cleaning old plots ---" -ForegroundColor Yellow
    Remove-Item "plots/*.svg" -ErrorAction SilentlyContinue
    Remove-Item "plots/*.png" -ErrorAction SilentlyContinue
}

# 2. Extract tickers
$symbolsArg = ""
if ($MovieScan) {
    Write-Host "--- Using tickers from most recent movie scan ---" -ForegroundColor Yellow
    $latestScan = Get-ChildItem "data/movie_scan_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($latestScan) {
        Write-Host "File: $($latestScan.Name)" -ForegroundColor Gray
        $csvData = Import-Csv $latestScan.FullName
        
        # Apply ticker filter at the CSV level if provided (handles SQL-style %)
        $tickers = if ($TickerFilter) {
            $regex = "^" + ($TickerFilter -replace "%", ".*") + "$"
            $csvData.Ticker | Where-Object { $_ -match $regex } | Select-Object -Unique
        } else {
            $csvData.Ticker | Select-Object -Unique
        }
        
        if ($tickers) {
            # Apply MaxTickers cap if specified
            if ($MaxTickers -gt 0 -and $tickers.Count -gt $MaxTickers) {
                Write-Host "Capping results to first $MaxTickers tickers (found $($tickers.Count))." -ForegroundColor Gray
                $tickers = $tickers | Select-Object -First $MaxTickers
            }

            $symbolsArg = ($tickers -join " ")
            Write-Host "Found $($tickers.Count) unique tickers matching filter."
        } else {
            Write-Warning "No symbols found matching filter in $($latestScan.Name)"
            exit 0
        }
    } else {
        Write-Error "No movie scan files found in 'data/'"
        exit 1
    }
} else {
    # This captures positional symbols like "E960.DE"
    $symbolsArg = ($ManualSymbols -join " ")
    if ($symbolsArg) {
        Write-Host "Using manual symbols: $symbolsArg" -ForegroundColor Yellow
    }
}

Write-Host "--- Discovery-Style Plotter (from Movie Scan) ---" -ForegroundColor Cyan
if ($TickerFilter) { Write-Host "Ticker Filter: $TickerFilter" }
Write-Host "Lookback:      $Lookback days"
Write-Host "-----------------------------"

# 3. Build the 'fetch' command (Discovery style)
if (-not $symbolsArg) {
    Write-Error "No symbols provided. Use -MovieScan to pull from the latest results."
    exit 1
}

# '--plot' is implicit in the 'fetch' command as it generates charts by default
$quietArg = if ($Quiet) { "--quiet" } else { "" }
$cmd = "python -m ETF_screener.main fetch --days $Lookback --plot-format $Format $quietArg $symbolsArg"

Invoke-Expression $cmd
