<#
run_all_tests.ps1

Comprehensive test and code quality suite for ETF Screener project.

Usage:
  .\run_all_tests.ps1                    # Run pytest only
    .\run_all_tests.ps1 -Parallel          # Run pytest in parallel (-n auto)
    .\run_all_tests.ps1 -RandomOrder       # Randomize pytest order (pytest-randomly)
    .\run_all_tests.ps1 -TimeoutSec 120    # Per-test timeout in seconds
    .\run_all_tests.ps1 -SkipPlaywright    # Skip browser regression tests
    .\run_all_tests.ps1 -Full              # Run all checks (pytest, ruff, mypy, coverage, vulture)
      .\run_all_tests.ps1 -All               # Alias for -Full
      .\run_all_tests.ps1 -QualityGate       # Alias for -Full
  .\run_all_tests.ps1 -Ruff              # Run pytest + ruff linter
  .\run_all_tests.ps1 -Mypy              # Run pytest + mypy type checker
  .\run_all_tests.ps1 -Coverage          # Run pytest with coverage report
  .\run_all_tests.ps1 -Vulture           # Run pytest + vulture dead code detection
  .\run_all_tests.ps1 -Black             # Run black code formatter (check mode)
  .\run_all_tests.ps1 -Bandit            # Run bandit security scanner

Default runs include the Playwright browser regression tests in tests/test_dashboard_playwright.py.
If Chromium is missing, install it once with: python -m playwright install chromium
#>

param(
    [Alias('All', 'QualityGate')]
    [switch]$Full,
    [switch]$Parallel,
    [switch]$RandomOrder,
    [int]$TimeoutSec = 0,
    [int]$LogRetentionDays = 7,
    [int]$LogRetentionMaxFiles = 20,
    [int]$LogRetentionMaxPerType = 5,
    [switch]$Ruff,
    [switch]$Mypy,
    [switch]$Coverage,
    [switch]$Vulture,
    [switch]$Black,
    [switch]$Bandit,
    [switch]$SkipPlaywright,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
run_all_tests.ps1

Comprehensive test and code quality suite for ETF Screener project.

Usage:
  .\scripts\run_all_tests.ps1
  .\scripts\run_all_tests.ps1 -Parallel
  .\scripts\run_all_tests.ps1 -RandomOrder
  .\scripts\run_all_tests.ps1 -TimeoutSec 120
  .\scripts\run_all_tests.ps1 -SkipPlaywright
  .\scripts\run_all_tests.ps1 -Full
  .\scripts\run_all_tests.ps1 -Ruff
  .\scripts\run_all_tests.ps1 -Mypy
  .\scripts\run_all_tests.ps1 -Coverage
  .\scripts\run_all_tests.ps1 -Vulture
  .\scripts\run_all_tests.ps1 -Black
  .\scripts\run_all_tests.ps1 -Bandit

Default runs include tests/test_dashboard_playwright.py as a separate
Playwright browser regression section. If Chromium is missing, install it once:
  python -m playwright install chromium
"@
    exit 0
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptPath
Push-Location $root

# Get venv python or fall back to system
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

# Logging
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir "test_results_$timestamp.log"
Start-Transcript -Path $logFile -Append | Out-Null

$failedTests = @()
$progressActivity = "run_all_tests progress"
$progressCurrent = 0
$progressTotal = 1

$playwrightTest = Join-Path $root 'tests\test_dashboard_playwright.py'
if ((-not $SkipPlaywright) -and (Test-Path $playwrightTest)) { $progressTotal++ }
if ($Full -or $Ruff) { $progressTotal++ }
if ($Full -or $Mypy) { $progressTotal++ }
if ($Full -or $Coverage) { $progressTotal++ }
if ($Full -or $Vulture) { $progressTotal++ }
if ($Full -or $Black) { $progressTotal++ }
if ($Full -or $Bandit) { $progressTotal++ }

function Start-Section {
    param(
        [string]$Name,
        [string]$Label
    )

    $script:progressCurrent++
    $percentComplete = [Math]::Round(($script:progressCurrent / $script:progressTotal) * 100, 0)
    Write-Progress -Activity $script:progressActivity -Status "[$($script:progressCurrent)/$($script:progressTotal)] $Name" -PercentComplete $percentComplete
    Write-Host "`n[$($script:progressCurrent)/$($script:progressTotal)] $Label" -ForegroundColor $Cyan
    Write-Host ("--"*30) -ForegroundColor $Cyan
}

function Remove-OldLogs {
    param(
        [string]$Directory,
        [int]$RetentionDays,
        [int]$MaxFiles
    )

    if (-not (Test-Path $Directory)) {
        return
    }

    $logs = @(Get-ChildItem -Path $Directory -Filter 'test_results_*.log' -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending)

    if ($RetentionDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-$RetentionDays)
        foreach ($log in @($logs | Where-Object { $_.LastWriteTime -lt $cutoff })) {
            Remove-Item -LiteralPath $log.FullName -Force -ErrorAction SilentlyContinue
        }
        $logs = @(Get-ChildItem -Path $Directory -Filter 'test_results_*.log' -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending)
    }

    if ($MaxFiles -gt 0 -and $logs.Count -gt $MaxFiles) {
        foreach ($log in @($logs | Select-Object -Skip $MaxFiles)) {
            Remove-Item -LiteralPath $log.FullName -Force -ErrorAction SilentlyContinue
        }
    }
}

try {
    # Colors
    $Green = 'Green'
    $Red = 'Red'
    $Yellow = 'Yellow'
    $Cyan = 'Cyan'

    Write-Host "`n" + ("="*60) -ForegroundColor $Cyan
    Write-Host "ETF SCREENER - TEST & CODE QUALITY SUITE" -ForegroundColor $Cyan
    Write-Host ("="*60) -ForegroundColor $Cyan

    # ===================== PYTEST =====================
    Start-Section -Name "Running Unit Tests (pytest)" -Label "Running Unit Tests (pytest)..."

    $pytestArgs = @('-m', 'pytest', 'tests/', '-v')
    if (Test-Path $playwrightTest) {
        $pytestArgs += @('--ignore', $playwrightTest)
    }
    if ($Parallel) {
        $pytestArgs += @('-n', 'auto')
    }
    if ($RandomOrder) {
        # 'last' keeps sequence stable between reruns after first randomization.
        $pytestArgs += @('--randomly-seed', 'last')
    }
    if ($TimeoutSec -gt 0) {
        $pytestArgs += @('--timeout', "$TimeoutSec")
    }

    & $python @pytestArgs
    if ($LASTEXITCODE -ne 0) {
        $failedTests += "pytest"
        Write-Host "[FAIL] Unit tests failed" -ForegroundColor $Red
    } else {
        Write-Host "[OK] Unit tests passed" -ForegroundColor $Green
    }

    # ===================== PLAYWRIGHT =====================
    if ((-not $SkipPlaywright) -and (Test-Path $playwrightTest)) {
        Start-Section -Name "Running Playwright Browser Tests" -Label "Running Playwright Browser Tests..."

        & $python -c "import playwright, pytest_playwright" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $failedTests += "playwright"
            Write-Host "[FAIL] Playwright pytest dependencies are missing. Install requirements.txt, then run: python -m playwright install chromium" -ForegroundColor $Red
        } else {
            $playwrightArgs = @('-m', 'pytest', $playwrightTest, '-v')
            if ($TimeoutSec -gt 0) {
                $playwrightArgs += @('--timeout', "$TimeoutSec")
            }

            & $python @playwrightArgs
            if ($LASTEXITCODE -ne 0) {
                $failedTests += "playwright"
                Write-Host "[FAIL] Playwright browser tests failed. If Chromium is missing, run: python -m playwright install chromium" -ForegroundColor $Red
            } else {
                Write-Host "[OK] Playwright browser tests passed" -ForegroundColor $Green
            }
        }
    } elseif ($SkipPlaywright) {
        Write-Host "[SKIP] Playwright browser tests skipped by -SkipPlaywright" -ForegroundColor $Yellow
    }

    # ===================== RUFF (optional) =====================
    if ($Full -or $Ruff) {
        Start-Section -Name "Running Ruff Linter" -Label "Running Ruff Linter..."
        
        $pythonFiles = Get-ChildItem -Path "src" -Recurse -Filter "*.py" | Select-Object -ExpandProperty FullName
        if ($pythonFiles) {
            & $python -m ruff check src/ --statistics
            if ($LASTEXITCODE -ne 0) {
                $failedTests += "ruff"
                Write-Host "[WARN] Ruff found issues" -ForegroundColor $Yellow
            } else {
                Write-Host "[OK] Ruff passed" -ForegroundColor $Green
            }
        } else {
            Write-Host "[SKIP] No Python files found in src/" -ForegroundColor $Yellow
        }
    }

    # ===================== MYPY (optional) =====================
    if ($Full -or $Mypy) {
        Start-Section -Name "Running Mypy Type Checker" -Label "Running Mypy Type Checker..."
        
        & $python -m mypy src/ETF_screener/ --ignore-missing-imports --no-error-summary 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] No type errors found" -ForegroundColor $Green
        } else {
            $failedTests += "mypy"
            Write-Host "[WARN] Mypy found type issues" -ForegroundColor $Yellow
        }
    }

    # ===================== COVERAGE (optional) =====================
    if ($Full -or $Coverage) {
        Start-Section -Name "Running Test Coverage Analysis" -Label "Running Test Coverage Analysis..."
        
        $coverageArgs = @('-m', 'coverage', 'run', '-m', 'pytest', 'tests/', '-q')
        if (Test-Path $playwrightTest) {
            $coverageArgs += @('--ignore', $playwrightTest)
        }
        & $python @coverageArgs
        & $python -m coverage report --include="src/*" --omit="*/__init__.py"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Coverage report generated" -ForegroundColor $Green
        } else {
            Write-Host "[WARN] Coverage analysis had issues" -ForegroundColor $Yellow
        }
    }

    # ===================== VULTURE (optional) =====================
    if ($Full -or $Vulture) {
        Start-Section -Name "Running Vulture Dead Code Scanner" -Label "Running Vulture Dead Code Scanner..."
        
        & (Join-Path $root 'scripts\run_vulture.ps1')
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] Vulture found potential dead code" -ForegroundColor $Yellow
        } else {
            Write-Host "[OK] No dead code detected" -ForegroundColor $Green
        }
    }

    # ===================== BLACK (optional) =====================
    if ($Full -or $Black) {
        Start-Section -Name "Running Black Code Formatter (check mode)" -Label "Running Black Code Formatter (check mode)..."
        
        & $python -m black --check src/ tests/ 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Code formatting is correct" -ForegroundColor $Green
        } else {
            Write-Host "[WARN] Code formatting issues detected" -ForegroundColor $Yellow
            Write-Host "       Run: black src/ tests/" -ForegroundColor $Cyan
        }
    }

    # ===================== BANDIT (optional) =====================
    if ($Full -or $Bandit) {
        Start-Section -Name "Running Bandit Security Scanner" -Label "Running Bandit Security Scanner..."
        
        & $python -m bandit -c .bandit -r src/ -q -f screen 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] No security issues found" -ForegroundColor $Green
        } else {
            $failedTests += "bandit"
            Write-Host "[WARN] Bandit found potential security issues" -ForegroundColor $Yellow
        }
    }

    # ===================== SUMMARY =====================
    Write-Host "`n" + ("="*60) -ForegroundColor $Cyan
    Write-Host "SUMMARY" -ForegroundColor $Cyan
    Write-Host ("="*60) -ForegroundColor $Cyan

    if ($failedTests.Count -eq 0) {
        Write-Host "[SUCCESS] All checks passed!" -ForegroundColor $Green
        $exitCode = 0
    } else {
        Write-Host "[ATTENTION] Some checks had issues:" -ForegroundColor $Yellow
        foreach ($failed in $failedTests) {
            Write-Host "  - $failed" -ForegroundColor $Red
        }
        $exitCode = 1
    }

    $retentionMax = if ($LogRetentionMaxPerType -gt 0 -and $LogRetentionMaxPerType -lt $LogRetentionMaxFiles) {
        $LogRetentionMaxPerType
    } else {
        $LogRetentionMaxFiles
    }
    Remove-OldLogs -Directory $logDir -RetentionDays $LogRetentionDays -MaxFiles $retentionMax

    Write-Host "`nTest log saved to: $logFile" -ForegroundColor $Cyan
    Write-Host ("="*60) -ForegroundColor $Cyan
    Write-Progress -Activity $progressActivity -Completed
    
    exit $exitCode
}
finally {
    Write-Progress -Activity $progressActivity -Completed
    Stop-Transcript | Out-Null
    Pop-Location
}
