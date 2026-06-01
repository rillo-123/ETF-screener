[CmdletBinding(PositionalBinding = $false)]
param(
    [switch]$Dashboard,
    [switch]$Screener,
    [switch]$Tests,
    [switch]$Discovery,
    [switch]$MovieScan,
    [switch]$Backtest,
    [switch]$Churn,
    [switch]$ChurnAll,
    [switch]$FilteredPlots,
    [switch]$Vulture,
    [switch]$Help,

    [Alias('All')]
    [switch]$Full,
    [switch]$QualityGate,
    [switch]$Parallel,
    [switch]$RandomOrder,
    [int]$TimeoutSec = 0,
    [int]$LogRetentionDays = 7,
    [int]$LogRetentionMaxFiles = 20,
    [int]$LogRetentionMaxPerType = 5,
    [switch]$Ruff,
    [switch]$Mypy,
    [switch]$Coverage,
    [switch]$Black,
    [switch]$Bandit,

    [string]$StrategyPath = "strategies/",
    [string]$TickerFilter = "",
    [int]$Plot = 0,
    [int]$Lookback = -1,
    [switch]$Show,
    [switch]$PlotDash,
    [switch]$Clean = $true,

    [string]$Format = "html",
    [int]$MaxTickers = 10,
    [switch]$Quiet = $false,

    [string]$Entry = "(ema_10 -gt ema_30)",
    [string]$Exit = "(rsi_14 -gt 75)",
    [string]$Filter = "",
    [switch]$OpenResult,
    [switch]$NoBrowser,

    [int]$MinConfidence = 70,
    [string]$OutFile = "logs/vulture_report.txt",
    [switch]$Open,
    [string]$ExtraArgs = "",
    [string]$Exclude = ".venv,.git",
    [switch]$RunTests,

    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$ManualSymbols
)

$repoRoot = $PSScriptRoot
$scriptsRoot = Join-Path $repoRoot "scripts"

function Invoke-Launcher {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [string[]]$Arguments = @()
    )

    $scriptPath = Join-Path $repoRoot $RelativePath
    if (-not (Test-Path $scriptPath)) {
        throw "Could not find launcher script at $scriptPath"
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath @Arguments
    exit $LASTEXITCODE
}

if ($Help) {
    Write-Host @"
run.ps1

Single root launcher for the ETF Screener repo.

Usage:
  .\run.ps1                 # Start the dashboard server
  .\run.ps1 -Screener       # Start the dashboard server; use your existing browser at /?tab=screener
  .\run.ps1 -Tests -Parallel
  .\run.ps1 -Discovery -StrategyPath strategies/ -Plot 1
  .\run.ps1 -MovieScan -TickerFilter '%ETF%'
  .\run.ps1 -Backtest -Entry "(ema_10 -gt ema_30)" -Exit "(rsi_14 -gt 75)"
  .\run.ps1 -FilteredPlots EXS1.DE EUNG.DE -Lookback 20

The implementation scripts live in scripts/; this file is the user-facing
frontend only.
"@
    exit 0
}

$launcherModes = @()
if ($Dashboard -or $Screener) { $launcherModes += 'dashboard' }
if ($Tests) { $launcherModes += 'tests' }
if ($Discovery) { $launcherModes += 'discovery' }
if ($MovieScan) { $launcherModes += 'moviescan' }
if ($Backtest) { $launcherModes += 'backtest' }
if ($Churn) { $launcherModes += 'churn' }
if ($ChurnAll) { $launcherModes += 'churnall' }
if ($FilteredPlots) { $launcherModes += 'filteredplots' }
if ($Vulture) { $launcherModes += 'vulture' }

if ($launcherModes.Count -eq 0) {
    $launcherModes = @('dashboard')
}

if ($launcherModes.Count -gt 1) {
    throw "Choose only one launcher mode at a time."
}

switch ($launcherModes[0]) {
    'dashboard' {
        Invoke-Launcher -RelativePath 'scripts/run_dashboard.ps1'
    }
    'tests' {
        $args = @()
        if ($Full) { $args += '-Full' }
        if ($QualityGate) { $args += '-Full' }
        if ($Parallel) { $args += '-Parallel' }
        if ($RandomOrder) { $args += '-RandomOrder' }
        if ($TimeoutSec -gt 0) { $args += @('-TimeoutSec', "$TimeoutSec") }
        if ($LogRetentionDays -ne 7) { $args += @('-LogRetentionDays', "$LogRetentionDays") }
        if ($LogRetentionMaxFiles -ne 20) { $args += @('-LogRetentionMaxFiles', "$LogRetentionMaxFiles") }
        if ($LogRetentionMaxPerType -ne 5) { $args += @('-LogRetentionMaxPerType', "$LogRetentionMaxPerType") }
        if ($Ruff) { $args += '-Ruff' }
        if ($Mypy) { $args += '-Mypy' }
        if ($Coverage) { $args += '-Coverage' }
        if ($Black) { $args += '-Black' }
        if ($Bandit) { $args += '-Bandit' }
        Invoke-Launcher -RelativePath 'scripts/run_all_tests.ps1' -Arguments $args
    }
    'discovery' {
        $args = @('-StrategyPath', $StrategyPath, '-TickerFilter', $TickerFilter, '-Plot', "$Plot", '-Lookback', "$Lookback")
        if ($Show) { $args += '-Show' }
        if ($PlotDash) { $args += '-PlotDash' }
        if ($PSBoundParameters.ContainsKey('Clean')) {
            if ($Clean) { $args += '-Clean' } else { $args += '-Clean:$false' }
        }
        Invoke-Launcher -RelativePath 'scripts/run_discovery.ps1' -Arguments $args
    }
    'moviescan' {
        $args = @()
        if ($PSBoundParameters.ContainsKey('StrategyPath') -and $StrategyPath) { $args += @('-StrategyPath', $StrategyPath) }
        if ($TickerFilter) { $args += @('-TickerFilter', $TickerFilter) }
        if ($Lookback -ge 0) { $args += @('-Lookback', "$Lookback") }
        if ($Show) { $args += '-Show' }
        if ($Plot -ne 0) { $args += @('-Plot', "$Plot") }
        Invoke-Launcher -RelativePath 'scripts/run_movie_scan.ps1' -Arguments $args
    }
    'backtest' {
        $args = @('-Entry', $Entry, '-Exit', $Exit)
        if ($Filter) { $args += @('-Filter', $Filter) }
        if ($OpenResult) { $args += '-OpenResult' }
        Invoke-Launcher -RelativePath 'scripts/run_custom_backtest.ps1' -Arguments $args
    }
    'churn' {
        $args = @('-StrategyPath', $StrategyPath, '-TickerFilter', $TickerFilter, '-Plot', "$Plot", '-Lookback', "$Lookback")
        if ($Show) { $args += '-Show' }
        if ($PlotDash) { $args += '-PlotDash' }
        if ($PSBoundParameters.ContainsKey('Clean')) {
            if ($Clean) { $args += '-Clean' } else { $args += '-Clean:$false' }
        }
        Invoke-Launcher -RelativePath 'scripts/run_churn.ps1' -Arguments $args
    }
    'churnall' {
        Invoke-Launcher -RelativePath 'scripts/run_churn_all.ps1'
    }
    'filteredplots' {
        $args = @()
        if ($ManualSymbols) {
            $args += $ManualSymbols
            $args += '-MovieScan:$false'
        } else {
            $args += '-MovieScan'
        }
        if ($TickerFilter) { $args += @('-TickerFilter', $TickerFilter) }
        if ($Format) { $args += @('-Format', $Format) }
        if ($Lookback -ge 0) { $args += @('-Lookback', "$Lookback") }
        if ($MaxTickers -gt 0) { $args += @('-MaxTickers', "$MaxTickers") }
        if ($Quiet) { $args += '-Quiet' }
        if ($PSBoundParameters.ContainsKey('Clean')) {
            if ($Clean) { $args += '-Clean' } else { $args += '-Clean:$false' }
        }
        Invoke-Launcher -RelativePath 'scripts/run_filtered_plots.ps1' -Arguments $args
    }
    'vulture' {
        $args = @('-MinConfidence', "$MinConfidence", '-OutFile', $OutFile)
        if ($Open) { $args += '-Open' }
        if ($ExtraArgs) { $args += @('-ExtraArgs', $ExtraArgs) }
        if ($Exclude) { $args += @('-Exclude', $Exclude) }
        if ($RunTests) { $args += '-RunTests' }
        Invoke-Launcher -RelativePath 'scripts/run_vulture.ps1' -Arguments $args
    }
}
