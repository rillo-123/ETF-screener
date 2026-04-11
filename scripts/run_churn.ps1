param(
    [string]$StrategyPath = "strategies/",
    [string]$TickerFilter = "",
    [int]$Plot = 0,
    [int]$Lookback = -1,
    [switch]$Show,
    [switch]$PlotDash,
    [switch]$Clean = $true
)

scripts/run_discovery.ps1 @PSBoundParameters
