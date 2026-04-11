<#
run_all_tests.ps1

Comprehensive test and code quality suite for ETF Screener project.

Also writes a parsed companion log for each run in logs/:
	test_results_YYYYMMDD_HHMMSS.parsed.log

Usage:
  .\run_all_tests.ps1                    # Run pytest only
	.\run_all_tests.ps1 -Parallel          # Run pytest in parallel (-n auto)
	.\run_all_tests.ps1 -RandomOrder       # Randomize pytest order (pytest-randomly)
	.\run_all_tests.ps1 -TimeoutSec 120    # Per-test timeout in seconds
	.\run_all_tests.ps1 -LogRetentionDays 30 -LogRetentionMaxFiles 500  # Enforce logs/ retention
	.\run_all_tests.ps1 -QualityGate       # Run pytest + ruff + mypy + vulture + black (no coverage/bandit)
	.\run_all_tests.ps1 -Full              # Run all checks (pytest, ruff, mypy, coverage, vulture, black, bandit)
	.\run_all_tests.ps1 -All               # Alias for -Full
  .\run_all_tests.ps1 -Ruff              # Run pytest + ruff linter
  .\run_all_tests.ps1 -Mypy              # Run pytest + mypy type checker
  .\run_all_tests.ps1 -Coverage          # Run pytest with coverage report
  .\run_all_tests.ps1 -Vulture           # Run pytest + vulture dead code detection
  .\run_all_tests.ps1 -Black             # Run black code formatter (check mode)
  .\run_all_tests.ps1 -Bandit            # Run bandit security scanner
#>

param(
	[Alias('All')]
	[switch]$Full,
	[switch]$QualityGate,
	[switch]$Parallel,
	[switch]$RandomOrder,
	[int]$TimeoutSec = 0,
	[int]$LogRetentionDays = 30,
	[int]$LogRetentionMaxFiles = 500,
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

$failedTests = @()
$progressActivity = "run_all_tests progress"
$progressCurrent = 0
$progressTotal = 1

function Add-FailedCheck {
	param([string]$Name)
	if ($script:failedTests -notcontains $Name) {
		$script:failedTests += $Name
	}
}

function Test-PythonModule {
	param([string]$ModuleName)
	& $python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)" | Out-Null
	return ($LASTEXITCODE -eq 0)
}

function Invoke-LogRetention {
	param(
		[string]$Directory,
		[int]$RetentionDays,
		[int]$MaxFiles
	)

	if (-not (Test-Path $Directory)) {
		return
	}

	if ($RetentionDays -lt 0) { $RetentionDays = 0 }
	if ($MaxFiles -lt 1) { $MaxFiles = 1 }

	$allFiles = Get-ChildItem -Path $Directory -Recurse -File -ErrorAction SilentlyContinue
	if (-not $allFiles) {
		return
	}

	$deletedCount = 0
	$cutoff = (Get-Date).AddDays(-$RetentionDays)

	# Rule 1: delete files older than retention window.
	$expiredFiles = $allFiles | Where-Object { $_.LastWriteTime -lt $cutoff }
	foreach ($file in $expiredFiles) {
		try {
			Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
			$deletedCount++
		} catch {
			Write-Host "[WARN] Could not delete old log file: $($file.FullName)" -ForegroundColor Yellow
		}
	}

	# Rule 2: keep only the most recent N files.
	$remainingFiles = Get-ChildItem -Path $Directory -Recurse -File -ErrorAction SilentlyContinue |
		Sort-Object LastWriteTime -Descending
	if ($remainingFiles.Count -gt $MaxFiles) {
		$extraFiles = $remainingFiles | Select-Object -Skip $MaxFiles
		foreach ($file in $extraFiles) {
			try {
				Remove-Item -LiteralPath $file.FullName -Force -ErrorAction Stop
				$deletedCount++
			} catch {
				Write-Host "[WARN] Could not delete excess log file: $($file.FullName)" -ForegroundColor Yellow
			}
		}
	}

	if ($deletedCount -gt 0) {
		Write-Host "[INFO] Log retention removed $deletedCount file(s) from logs/" -ForegroundColor Cyan
	}
}

# Logging (after function definitions so Invoke-LogRetention is available)
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) {
	New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
Invoke-LogRetention -Directory $logDir -RetentionDays $LogRetentionDays -MaxFiles $LogRetentionMaxFiles
$logFile = Join-Path $logDir "test_results_$timestamp.log"
$pytestDetailLogFile = Join-Path $logDir "test_results_$timestamp.pytest.log"
Start-Transcript -Path $logFile -Append | Out-Null

if ($Full -or $QualityGate -or $Ruff) { $progressTotal++ }
if ($Full -or $QualityGate -or $Mypy) { $progressTotal++ }
if ($Full -or $Coverage) { $progressTotal++ }
if ($Full -or $QualityGate -or $Vulture) { $progressTotal++ }
if ($Full -or $QualityGate -or $Black) { $progressTotal++ }
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

try {
	# Colors
	$Green = 'Green'
	$Red = 'Red'
	$Yellow = 'Yellow'
	$Cyan = 'Cyan'
	$mypyPythonVersion = (& $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()

	Write-Host "`n" + ("="*60) -ForegroundColor $Cyan
	Write-Host "ETF SCREENER - TEST & CODE QUALITY SUITE" -ForegroundColor $Cyan
	Write-Host ("="*60) -ForegroundColor $Cyan

	# ===================== PYTEST =====================
	Start-Section -Name "Running Unit Tests (pytest)" -Label "Running Unit Tests (pytest)..."

	$pytestArgs = @('-m', 'pytest', 'tests/', '-v')
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

	# Keep full pytest output in a dedicated detail log so parsed logs can include concrete failures.
	$pytestOutput = & $python @pytestArgs 2>&1
	$pytestOutput | Tee-Object -FilePath $pytestDetailLogFile | ForEach-Object { Write-Host $_ }
	$pytestExitCode = $LASTEXITCODE

	if ($pytestExitCode -ne 0) {
		$failedTests += "pytest"
		Write-Host "[FAIL] Unit tests failed" -ForegroundColor $Red
	} else {
		Write-Host "[OK] All units tests passed" -ForegroundColor $Green
	}

	# ===================== RUFF (optional) =====================
	if ($Full -or $QualityGate -or $Ruff) {
		Start-Section -Name "Running Ruff Linter" -Label "Running Ruff Linter..."
        
		$pythonFiles = Get-ChildItem -Path "src" -Recurse -Filter "*.py" | Select-Object -ExpandProperty FullName
		if (-not (Test-PythonModule -ModuleName 'ruff')) {
			Add-FailedCheck "ruff"
			Write-Host "[FAIL] ruff is not installed in the active Python environment" -ForegroundColor $Red
		} elseif ($pythonFiles) {
			& $python -m ruff check src/ --statistics
			if ($LASTEXITCODE -ne 0) {
				Add-FailedCheck "ruff"
				Write-Host "[WARN] Ruff found issues" -ForegroundColor $Yellow
			} else {
				Write-Host "[OK] Ruff passed" -ForegroundColor $Green
			}
		} else {
			Write-Host "[SKIP] No Python files found in src/" -ForegroundColor $Yellow
		}
	}

	# ===================== MYPY (optional) =====================
	if ($Full -or $QualityGate -or $Mypy) {
		Start-Section -Name "Running Mypy Type Checker" -Label "Running Mypy Type Checker..."
		
		if (-not (Test-PythonModule -ModuleName 'mypy')) {
			Add-FailedCheck "mypy"
			Write-Host "[FAIL] mypy is not installed in the active Python environment" -ForegroundColor $Red
		} else {
			& $python -m mypy src/ETF_screener/ --python-version $mypyPythonVersion --ignore-missing-imports --no-error-summary 2>&1
		}
		if ($LASTEXITCODE -eq 0 -and (Test-PythonModule -ModuleName 'mypy')) {
			Write-Host "[OK] No type errors found" -ForegroundColor $Green
		} else {
			Add-FailedCheck "mypy"
			Write-Host "[WARN] Mypy found type issues" -ForegroundColor $Yellow
		}
	}

	# ===================== COVERAGE (optional) =====================
	if ($Full -or $Coverage) {
		Start-Section -Name "Running Test Coverage Analysis" -Label "Running Test Coverage Analysis..."
		
		if (-not (Test-PythonModule -ModuleName 'coverage')) {
			Add-FailedCheck "coverage"
			Write-Host "[FAIL] coverage is not installed in the active Python environment" -ForegroundColor $Red
		} else {
			& $python -m coverage run -m pytest tests/ -q
			& $python -m coverage report --include="src/*" --omit="*/__init__.py"
		}
		if ($LASTEXITCODE -eq 0 -and (Test-PythonModule -ModuleName 'coverage')) {
			Write-Host "[OK] Coverage report generated" -ForegroundColor $Green
		} else {
			Add-FailedCheck "coverage"
			Write-Host "[WARN] Coverage analysis had issues" -ForegroundColor $Yellow
		}
	}

	# ===================== VULTURE (optional) =====================
	if ($Full -or $QualityGate -or $Vulture) {
		Start-Section -Name "Running Vulture Dead Code Scanner" -Label "Running Vulture Dead Code Scanner..."

		$vultureScript = Join-Path $root 'scripts\run_vulture.ps1'
		if (-not (Test-Path $vultureScript)) {
			$vultureScript = Join-Path $root 'src\ETF_screener\scripts\run_vulture.ps1'
		}

		if (Test-Path $vultureScript) {
			& $vultureScript
			if ($LASTEXITCODE -ne 0) {
				Add-FailedCheck "vulture"
				Write-Host "[WARN] Vulture found potential dead code" -ForegroundColor $Yellow
			} else {
				Write-Host "[OK] No dead code detected" -ForegroundColor $Green
			}
		} else {
			Add-FailedCheck "vulture"
			Write-Host "[WARN] Vulture script not found" -ForegroundColor $Yellow
		}
	}

	# ===================== BLACK (optional) =====================
	if ($Full -or $QualityGate -or $Black) {
		Start-Section -Name "Running Black Code Formatter (check mode)" -Label "Running Black Code Formatter (check mode)..."
		$pythonFiles = Get-ChildItem -Path "src", "tests" -Recurse -Filter "*.py" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
		
		if (-not (Test-PythonModule -ModuleName 'black')) {
			Add-FailedCheck "black"
			Write-Host "[FAIL] black is not installed in the active Python environment" -ForegroundColor $Red
		} else {
			$blackOutput = & $python -m black --check src/ tests/ 2>&1
			if ($blackOutput) {
				$blackOutput | ForEach-Object { Write-Host $_ }
			}

			if ($LASTEXITCODE -eq 0 -and $pythonFiles -and ($blackOutput | Out-String) -match 'No Python files are present to be formatted') {
				Add-FailedCheck "black"
				Write-Host "[WARN] Black did not inspect any Python files; check [tool.black].include/exclude settings" -ForegroundColor $Yellow
			}
		}
		if ($LASTEXITCODE -eq 0 -and (Test-PythonModule -ModuleName 'black')) {
			if ($failedTests -contains "black") {
				Write-Host "[WARN] Code formatting check configuration needs attention" -ForegroundColor $Yellow
			} else {
				Write-Host "[OK] Code formatting is correct" -ForegroundColor $Green
			}
		} else {
			Add-FailedCheck "black"
			Write-Host "[WARN] Code formatting issues detected" -ForegroundColor $Yellow
			Write-Host "       Run: black src/ tests/" -ForegroundColor $Cyan
		}
	}

	# ===================== BANDIT (optional) =====================
	if ($Full -or $Bandit) {
		Start-Section -Name "Running Bandit Security Scanner" -Label "Running Bandit Security Scanner..."
		
		if (-not (Test-PythonModule -ModuleName 'bandit')) {
			Add-FailedCheck "bandit"
			Write-Host "[FAIL] bandit is not installed in the active Python environment" -ForegroundColor $Red
		} else {
			& $python -m bandit -r src/ -f screen 2>&1
		}
		if ($LASTEXITCODE -eq 0 -and (Test-PythonModule -ModuleName 'bandit')) {
			Write-Host "[OK] No security issues found" -ForegroundColor $Green
		} else {
			Add-FailedCheck "bandit"
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
	Write-Host "Pytest detail log saved to: $pytestDetailLogFile" -ForegroundColor $Cyan
	Write-Host ("="*60) -ForegroundColor $Cyan
	Write-Progress -Activity $progressActivity -Completed
    
	exit $exitCode
}
finally {
	Write-Progress -Activity $progressActivity -Completed
	Stop-Transcript | Out-Null

	# Create a concise parsed companion log from the full transcript.
	try {
		if (Test-Path $logFile) {
			$parsedLogFile = [System.IO.Path]::ChangeExtension($logFile, '.parsed.log')
			$logContent = Get-Content -Path $logFile -ErrorAction Stop
			$pytestLogContent = @()
			if (Test-Path $pytestDetailLogFile) {
				$pytestLogContent = Get-Content -Path $pytestDetailLogFile -ErrorAction SilentlyContinue
			}

			$parsedLines = [System.Collections.Generic.List[string]]::new()
			$parsedLines.Add("PARSED TEST LOG") | Out-Null
			$parsedLines.Add("Source: $logFile") | Out-Null
			if (Test-Path $pytestDetailLogFile) {
				$parsedLines.Add("Pytest detail source: $pytestDetailLogFile") | Out-Null
			}
			$parsedLines.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')") | Out-Null
			$parsedLines.Add(("=" * 60)) | Out-Null

			$statusLines = $logContent | Select-String -Pattern '\[SUCCESS\]|\[ATTENTION\]|SUMMARY|Test log saved to:'
			if ($statusLines) {
				$parsedLines.Add("OVERALL STATUS") | Out-Null
				foreach ($line in $statusLines) {
					$parsedLines.Add($line.Line.Trim()) | Out-Null
				}
				$parsedLines.Add("") | Out-Null
			}

			$failedChecks = $logContent | Select-String -Pattern '^\s*[\*\-]\s+|^\s*[-]\s+|^\s*\u2022\s+|^\s*\S+\s*$' | ForEach-Object { $_.Line.Trim() } | Where-Object { $_ -match '^(pytest|ruff|mypy|coverage|vulture|black|bandit)$' } | Select-Object -Unique
			if ($failedChecks) {
				$parsedLines.Add("CHECKS WITH ISSUES") | Out-Null
				foreach ($check in $failedChecks) {
					$parsedLines.Add("- $check") | Out-Null
				}
				$parsedLines.Add("") | Out-Null
			}

			$keyIssueLines = $logContent | Select-String -Pattern '\[FAIL\]|\[WARN\]|\[ERROR\]|Traceback|Exception|FAILED|ERROR|would be reformatted|would reformat|\berrors?\s+in\s+[0-9\.]+s\b' | Select-Object -Unique
			if ($keyIssueLines) {
				$parsedLines.Add("KEY FINDINGS") | Out-Null
				foreach ($line in $keyIssueLines) {
					$parsedLines.Add($line.Line.Trim()) | Out-Null
				}
			} else {
				$parsedLines.Add("KEY FINDINGS") | Out-Null
				$parsedLines.Add("No fail/warn/error lines matched parse patterns.") | Out-Null
			}

			if ($pytestLogContent.Count -gt 0) {
				$parsedLines.Add("") | Out-Null
				$parsedLines.Add("PYTEST FIRST FAILURE LINES") | Out-Null
				$pytestFailureLines = $pytestLogContent |
					Select-String -Pattern 'ERROR collecting|^FAILED\s|^E\s{2,}|^E\s|short test summary info|Traceback' |
					Select-Object -First 40

				if ($pytestFailureLines) {
					foreach ($line in $pytestFailureLines) {
						$parsedLines.Add($line.Line.Trim()) | Out-Null
					}
				} else {
					$parsedLines.Add("No concrete pytest failure lines were found in pytest detail log.") | Out-Null
				}
			}

			Set-Content -Path $parsedLogFile -Value $parsedLines -Encoding UTF8
			Write-Host "Parsed log saved to: $parsedLogFile" -ForegroundColor $Cyan
		}
	}
	catch {
		Write-Host "[WARN] Failed to create parsed log: $($_.Exception.Message)" -ForegroundColor $Yellow
	}
	Pop-Location
}