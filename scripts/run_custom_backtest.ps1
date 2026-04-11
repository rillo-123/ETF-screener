param(
    # --- PRESET EXAMPLES (Comment/Uncomment One Pair) ---
    
    # Example 1: Strict Trend Following (EMA + ADX Trend)
    #[string]$Entry = "(ema_10 -gt ema_30)",
    #[string]$Entry = "(ema_10 -gt ema_30) and (ADX -gt 20)",
    [string]$Exit = "(rsi_14 -gt 75)",

    # Example 2: Conservative Recovery (RSI Oversold + EMA Cross)
    # [string]$Entry = "(rsi_14 -lt 40) and (ema_10 -gt ema_20)",
    # [string]$Exit = "(rsi_14 -gt 70) or (ema_10 -lt ema_30)",

    # Example 3: Supertrend Core (Pure ST Play)
    # [string]$Entry = "(close -gt Supertrend) and (ADX -gt 20)",
    # [string]$Exit = "(close -lt Supertrend)",

    # Example 4: Sharp EMA Crossover (Momentum Entry)
     [string]$Entry = "cross_up(ema_10, ema_30) and ema_100_slope -gt 0",
    # [string]$Exit = "cross_down(ema_10, ema_30) or (rsi_14 -gt 75)",

    # Example 5: Confirmed Trend (2-Day Post-Cross Stability)
    # [string]$Entry = "was_true(cross_up(ema_10, ema_30), 2) and (ema_10 -gt ema_30)",
    # [string]$Exit = "cross_down(ema_10, ema_30) or (rsi_14 -gt 80)",

    # Example 6: Mean Reversion Recovery (Oversold Bounce)
    # [string]$Entry = "was_true(rsi_14 -lt 30, 1) and (rsi_14 -gt rsi_14_d1)",
    # [string]$Exit = "(rsi_14 -gt 70) or cross_down(ema_10, ema_30)",

    # Example 7: MACD Momentum (Signal Line Cross)
    # [string]$Entry = "cross_up(macd, macd_signal)",
    # [string]$Exit = "cross_down(macd, macd_signal) or (rsi_14 -gt 80)",

    # Example 8: Stochastic Overbought/Oversold
    # [string]$Entry = "cross_up(stoch_k, stoch_d) and (stoch_k -lt 20)",
    # [string]$Exit = "cross_down(stoch_k, stoch_d) and (stoch_k -gt 80)",

    # Example 9: Trend Intensity (Price above EMA AND EMA is sloping up)
    # [string]$Entry = "(close -gt ema_50) and (ema_50_slope -gt 0)",
    # [string]$Exit = "(close -lt ema_50) or (ema_50_slope -lt 0)",

    [string]$Filter = "",
    [switch]$OpenResult
)

function Normalize-DslExpr {
    param([string]$Expr)
    if (-not $Expr) { return $Expr }

    $normalized = $Expr
    $normalized = $normalized -replace '(?i)\s+-ge\s+', ' >= '
    $normalized = $normalized -replace '(?i)\s+-le\s+', ' <= '
    $normalized = $normalized -replace '(?i)\s+-gt\s+', ' > '
    $normalized = $normalized -replace '(?i)\s+-lt\s+', ' < '
    $normalized = $normalized -replace '(?i)\s+-eq\s+', ' == '
    $normalized = $normalized -replace '(?i)\s+-ne\s+', ' != '
    $normalized = $normalized -replace '(?i)\s+-and\s+', ' and '
    $normalized = $normalized -replace '(?i)\s+-or\s+', ' or '
    return $normalized
}

$Entry = Normalize-DslExpr -Expr $Entry
$Exit = Normalize-DslExpr -Expr $Exit
$Filter = Normalize-DslExpr -Expr $Filter

# Function to create a clean mnemonic from the script string
function Get-Mnemonic($scriptText) {
    if (-not $scriptText) { return "none" }
    # Remove operators and leave keywords/numbers, join with underscores
    $clean = $scriptText -replace '[-()\[\]]',' ' -replace '\s+','_'
    # Remove characters invalid in Windows file names
    $clean = $clean -replace '[<>:"/\\|\?\*]', '_'
    $clean = $clean -replace 'and|or',''
    $clean = $clean -replace ',','_'
    $clean = $clean -replace '__+','_'
    # Truncate to avoid path length issues
    if ($clean.Length -gt 40) { $clean = $clean.Substring(0, 40) }
    return $clean.Trim('_').ToLower()
}

$entryMnemonic = Get-Mnemonic -scriptText $Entry
$exitMnemonic = Get-Mnemonic -scriptText $Exit
$filterMnemonic = if ($Filter) { "filter_$Filter" } else { "all" }

$timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$outputFile = "data/backtest_${entryMnemonic}_vs_${exitMnemonic}_${filterMnemonic}_${timestamp}.csv"

Write-Host "--- ETF Screener DSL Backtest ---" -ForegroundColor Cyan
Write-Host "Entry: $Entry"
Write-Host "Exit:  $Exit"
Write-Host "Target Output: $outputFile"
Write-Host "---------------------------------"

# Build the python command
$env:PYTHONPATH = "src"
$python = "c:/Users/carlr/OneDrive/Documents/GitHub/ETF-screener/.venv/Scripts/python.exe"
$args = @("src/ETF_screener/scripts/churn_strategies.py", "--entry", "$Entry", "--exit", "$Exit")

if ($Filter) {
    $args += "--filter"; $args += "$Filter"
}

Write-Host "Executing: $python $($args -join ' ')" -ForegroundColor Gray
& $python $args

# The python script currently saves to data/custom_script_results.csv
if (Test-Path "data/custom_script_results.csv") {
    Move-Item -Path "data/custom_script_results.csv" -Destination $outputFile -Force
    Write-Host "Results archived to: $outputFile" -ForegroundColor Green
    
    if ($OpenResult) {
        # Check for LibreOffice Calc specifically, otherwise fallback to default CSV handler
        $libreOfficePath = "C:\Program Files\LibreOffice\program\scalc.exe"
        if (Test-Path $libreOfficePath) {
            Write-Host "Opening in LibreOffice Calc..." -ForegroundColor Gray
            Start-Process $libreOfficePath -ArgumentList "`"$outputFile`""
        } else {
            Write-Host "LibreOffice not found in default path, opening with system default..." -ForegroundColor Yellow
            Invoke-Item $outputFile
        }
    }
} else {
    Write-Warning "Backtest failed to produce results or no trades found."
}
