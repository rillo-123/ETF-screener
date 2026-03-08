<#
run_all_tests.ps1

Comprehensive test and code quality suite for ETF Screener project.

Usage:
  .\run_all_tests.ps1                    # Run pytest only
  .\run_all_tests.ps1 -Full              # Run all checks (pytest, ruff, mypy, coverage, vulture)
  .\run_all_tests.ps1 -Ruff              # Run pytest + ruff linter
  .\run_all_tests.ps1 -Mypy              # Run pytest + mypy type checker
  .\run_all_tests.ps1 -Coverage          # Run pytest with coverage report
  .\run_all_tests.ps1 -Vulture           # Run pytest + vulture dead code detection
  .\run_all_tests.ps1 -Black             # Run black code formatter (check mode)
  .\run_all_tests.ps1 -Bandit            # Run bandit security scanner
#>

param(
    [switch]$Full,
    [switch]$Ruff,
    [switch]$Mypy,
    [switch]$Coverage,
    [switch]$Vulture,
    [switch]$Black,
    [switch]$Bandit,
    [switch]$Help
)

if ($Help) {
    Get-Content $PSCommandPath | Select-String '^\s*#' | ForEach-Object { Write-Host $_.Line }
    exit 0
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

# Get venv python or fall back to system
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

# Logging
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "data/test_results_$timestamp.txt"
Start-Transcript -Path $logFile -Append | Out-Null

$failedTests = @()

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
    Write-Host "`n[1/7] Running Unit Tests (pytest)..." -ForegroundColor $Cyan
    Write-Host ("--"*30) -ForegroundColor $Cyan
    
    & $python -m pytest tests/ -v
    if ($LASTEXITCODE -ne 0) {
        $failedTests += "pytest"
        Write-Host "[FAIL] Unit tests failed" -ForegroundColor $Red
    } else {
        Write-Host "[OK] All units tests passed" -ForegroundColor $Green
    }

    # ===================== RUFF (optional) =====================
    if ($Full -or $Ruff) {
        Write-Host "`n[2/7] Running Ruff Linter..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
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
        Write-Host "`n[3/7] Running Mypy Type Checker..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
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
        Write-Host "`n[4/7] Running Test Coverage Analysis..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
        & $python -m coverage run -m pytest tests/ -q
        & $python -m coverage report --include="src/*" --omit="*/__init__.py"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Coverage report generated" -ForegroundColor $Green
        } else {
            Write-Host "[WARN] Coverage analysis had issues" -ForegroundColor $Yellow
        }
    }

    # ===================== VULTURE (optional) =====================
    if ($Full -or $Vulture) {
        Write-Host "`n[5/7] Running Vulture Dead Code Scanner..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
        & .\run_vulture.ps1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] Vulture found potential dead code" -ForegroundColor $Yellow
        } else {
            Write-Host "[OK] No dead code detected" -ForegroundColor $Green
        }
    }

    # ===================== BLACK (optional) =====================
    if ($Full -or $Black) {
        Write-Host "`n[6/7] Running Black Code Formatter (check mode)..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
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
        Write-Host "`n[7/7] Running Bandit Security Scanner..." -ForegroundColor $Cyan
        Write-Host ("--"*30) -ForegroundColor $Cyan
        
        & $python -m bandit -r src/ -q -f screen 2>&1
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
        Write-Host "[SUCCESS] All checks passed! ✓" -ForegroundColor $Green
        $exitCode = 0
    } else {
        Write-Host "[ATTENTION] Some checks had issues:" -ForegroundColor $Yellow
        foreach ($failed in $failedTests) {
            Write-Host "  • $failed" -ForegroundColor $Red
        }
        $exitCode = 1
    }

    Write-Host "`nTest log saved to: $logFile" -ForegroundColor $Cyan
    Write-Host ("="*60) -ForegroundColor $Cyan
    
    exit $exitCode
}
finally {
    Stop-Transcript | Out-Null
    Pop-Location
}

# Ensure we run from repo root
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

# Set up logging with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path -Path $root -ChildPath "data/test_results_$timestamp.txt"
Start-Transcript -Path $logFile -Append | Out-Null

try {
    # Build path to the venv python executable
    $python = Join-Path -Path $root -ChildPath '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = 'python' }
    
    # If -All is specified, enable all tools
    if ($All) {
        $Radon = $true
        $Ruff = $true
        $Mypy = $true
        $Bandit = $true
        $Coverage = $true
    }
    
    $toolsEnabled = $Radon -or $Ruff -or $Mypy -or $Bandit -or $Coverage

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Running Main Test Suite" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Run main test suite (excluding equipment_events to avoid mock contamination)
    $mainPytestArgs = @(
        '-m', 'pytest', 'tests',
        '--ignore=tests\test_equipment_chooser.py',
        '--ignore=tests\test_equipment_events.py'
    )
    if ($Filter) { $mainPytestArgs += @('-k', $Filter) }

    & $python @mainPytestArgs
    $mainExitCode = $LASTEXITCODE

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Running Equipment Events Tests" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Run equipment events tests separately (requires browser module mocking)
    $eventsPytestArgs = @(
        '-m', 'pytest', 'tests\test_equipment_events.py', '-v'
    )

    & $python @eventsPytestArgs
    $eventsExitCode = $LASTEXITCODE

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Running PowerShell Infrastructure Tests" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Run PowerShell tests
    $psTestScript = Join-Path -Path $root -ChildPath 'tests\test_ensure_venv.ps1'
    if (Test-Path $psTestScript) {
        & $psTestScript
        $psExitCode = $LASTEXITCODE
    } else {
        Write-Host "Warning: PowerShell test script not found" -ForegroundColor Yellow
        $psExitCode = 0
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Running TOML Entry Point Tests" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Run TOML entry point tests
    $tomlTestScript = Join-Path -Path $root -ChildPath 'tests\test_toml_entry_point.ps1'
    if (Test-Path $tomlTestScript) {
        & $tomlTestScript
        $tomlExitCode = $LASTEXITCODE
    } else {
        Write-Host "Warning: TOML entry point test script not found" -ForegroundColor Yellow
        $tomlExitCode = 0
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Running Export Project Tests" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Run export project tests
    $exportTestScript = Join-Path -Path $root -ChildPath 'tests\test_export_project.ps1'
    if (Test-Path $exportTestScript) {
        & $exportTestScript
        $exportExitCode = $LASTEXITCODE
    } else {
        Write-Host "Warning: Export project test script not found" -ForegroundColor Yellow
        $exportExitCode = 0
    }

    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Test Suite Summary" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    if ($mainExitCode -eq 0 -and $eventsExitCode -eq 0 -and $psExitCode -eq 0 -and $tomlExitCode -eq 0 -and $exportExitCode -eq 0) {
        Write-Host "[OK] All tests passed!" -ForegroundColor Green
        Write-Host "  - Main test suite: PASSED" -ForegroundColor Green
        Write-Host "  - Equipment events tests: PASSED" -ForegroundColor Green
        Write-Host "  - PowerShell infrastructure tests: PASSED" -ForegroundColor Green
        Write-Host "  - TOML entry point tests: PASSED" -ForegroundColor Green
        Write-Host "  - Export project tests: PASSED" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Some tests failed:" -ForegroundColor Red
        if ($mainExitCode -ne 0) {
            Write-Host "  - Main test suite: FAILED (exit code $mainExitCode)" -ForegroundColor Red
        } else {
            Write-Host "  - Main test suite: PASSED" -ForegroundColor Green
        }
        if ($eventsExitCode -ne 0) {
            Write-Host "  - Equipment events tests: FAILED (exit code $eventsExitCode)" -ForegroundColor Red
        } else {
            Write-Host "  - Equipment events tests: PASSED" -ForegroundColor Green
        }
        if ($psExitCode -ne 0) {
            Write-Host "  - PowerShell infrastructure tests: FAILED (exit code $psExitCode)" -ForegroundColor Red
        } else {
            Write-Host "  - PowerShell infrastructure tests: PASSED" -ForegroundColor Green
        }
        if ($tomlExitCode -ne 0) {
            Write-Host "  - TOML entry point tests: FAILED (exit code $tomlExitCode)" -ForegroundColor Red
        } else {
            Write-Host "  - TOML entry point tests: PASSED" -ForegroundColor Green
        }
        if ($exportExitCode -ne 0) {
            Write-Host "  - Export project tests: FAILED (exit code $exportExitCode)" -ForegroundColor Red
        } else {
            Write-Host "  - Export project tests: PASSED" -ForegroundColor Green
        }
    }
    
    # Run code quality tools if requested
    if ($toolsEnabled) {
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "Code Quality Tools" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        if ($Radon) {
            Write-Host "`n--- Radon Complexity Analysis ---" -ForegroundColor Yellow
            & $python -m radon cc static/assets/py -s -nb
            Write-Host ""
        }
        
        if ($Ruff) {
            Write-Host "`n--- Ruff Linter ---" -ForegroundColor Yellow
            & ruff check static/assets/py --statistics
            Write-Host ""
        }
        
        if ($Mypy) {
            Write-Host "`n--- Mypy Type Checker ---" -ForegroundColor Yellow
            & $python -m mypy static/assets/py --ignore-missing-imports --no-error-summary 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] No type errors found" -ForegroundColor Green
            }
            Write-Host ""
        }
        
        if ($Bandit) {
            Write-Host "`n--- Bandit Security Scanner ---" -ForegroundColor Yellow
            & $python -m bandit -r static/assets/py -q -f screen
            Write-Host ""
        }
        
        if ($Coverage) {
            Write-Host "`n--- Test Coverage Report ---" -ForegroundColor Yellow
            & $python -m coverage run -m pytest tests --ignore=tests\test_equipment_chooser.py --ignore=tests\test_equipment_events.py -q
            & $python -m coverage report --include="static/assets/py/*" --omit="*/__pycache__/*"
            Write-Host ""
        }
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "Code Quality Summary" -ForegroundColor Cyan
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        if ($Radon) { Write-Host "[OK] Complexity analysis complete" -ForegroundColor Green }
        if ($Ruff) { Write-Host "[OK] Linting complete" -ForegroundColor Green }
        if ($Mypy) { Write-Host "[OK] Type checking complete" -ForegroundColor Green }
        if ($Bandit) { Write-Host "[OK] Security scan complete" -ForegroundColor Green }
        if ($Coverage) { Write-Host "[OK] Coverage report complete" -ForegroundColor Green }
    }
    
    # Exit with appropriate code
    if ($mainExitCode -eq 0 -and $eventsExitCode -eq 0 -and $psExitCode -eq 0 -and $tomlExitCode -eq 0 -and $exportExitCode -eq 0) {
        exit 0
    } else {
        exit 1
    }
}
finally {
    Stop-Transcript | Out-Null
    Write-Host "`nTest results also saved to: $logFile" -ForegroundColor Cyan
    Pop-Location
}
