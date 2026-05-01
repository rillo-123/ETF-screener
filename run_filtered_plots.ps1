param(
    [Parameter(Position=0)]
    [string[]]$ManualSymbols,

    [string]$TickerFilter = "",
    [string]$Format = "html",
    [int]$Lookback = 50,
    [int]$MaxTickers = 10,
    [switch]$Clean = $true,
    [switch]$MovieScan = $true,
    [switch]$Quiet = $false
)

& (Join-Path $PSScriptRoot "scripts/run_filtered_plots.ps1") @PSBoundParameters
exit $LASTEXITCODE
