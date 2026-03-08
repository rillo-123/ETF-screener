<#
run_vulture.ps1

Convenience shim to run vulture inside the project's virtualenv (if present),
exclude common vendored directories, and produce a report file.

Usage examples:
  # Run with default min-confidence 70
  .\run_vulture.ps1

  # Run with custom min-confidence and open the report on completion
  .\run_vulture.ps1 -MinConfidence 50 -Open

  # Pass extra vulture args
  .\run_vulture.ps1 -ExtraArgs "--exclude static/assets/js" -OutFile my_report.txt
#>

Param(
    [int]$MinConfidence = 70,
    [string]$OutFile = "data/vulture_report.txt",
    [switch]$Open,
    [string]$ExtraArgs = "",
    [string]$Exclude = ".venv,.git",
    [switch]$RunTests
)

# Normalize exclude list
$excludeList = @()
if ($Exclude) { $excludeList = ($Exclude -split ',') | ForEach-Object { $_.Trim() } }
# Always exclude .venv and .git
$excludeList += ".venv" , ".git"
$excludeList = $excludeList | Select-Object -Unique

function Write-Info($msg) { Write-Host "[vulture] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[vulture] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[vulture] $msg" -ForegroundColor Red }

# Determine python binary to use (prefer venv)
$venvPython = "";
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPythonCandidate = Join-Path $venvPath "Scripts\python.exe"
if (Test-Path $venvPythonCandidate) {
    $venvPython = $venvPythonCandidate
    Write-Info "Using venv python: $venvPython"
} else {
    $venvPython = "python"
    Write-Info "Using system python: python (no .venv/python.exe found)"
}

# Parse ExtraArgs to extract any --exclude flags and add to $excludeList (supports --exclude path or --exclude=path)
$remainingExtra = @()
if ($ExtraArgs) {
    $tokens = $ExtraArgs -split '\s+'
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        $t = $tokens[$i]
        if ($t -like '--exclude=*') {
            $val = $t.Substring(10)
            $excludeList += ($val -split ',') | ForEach-Object { $_.Trim() }
        } elseif ($t -eq '--exclude' -or $t -eq '-e') {
            if ($i + 1 -lt $tokens.Count) {
                $i++
                $val = $tokens[$i]
                $excludeList += ($val -split ',') | ForEach-Object { $_.Trim() }
            }
        } else {
            $remainingExtra += $t
        }
    }
}
$remainingExtra = $remainingExtra -join ' '

# Resolve exclude full paths
$excludeFull = @()
foreach ($ex in $excludeList) {
    if ([string]::IsNullOrWhiteSpace($ex)) { continue }
    $full = (Resolve-Path -Path (Join-Path $PSScriptRoot $ex) -ErrorAction SilentlyContinue)
    if ($full) { $excludeFull += $full.Path } else { $excludeFull += (Join-Path $PSScriptRoot $ex) }
}
$excludeFull = $excludeFull | Select-Object -Unique

# Build list of .py files excluding those under any excluded full path
$pyFiles = Get-ChildItem -Path $PSScriptRoot -Recurse -File -Filter *.py -ErrorAction SilentlyContinue | Where-Object {
    $keep = $true
    foreach ($ef in $excludeFull) { if ($_.FullName.StartsWith($ef, [System.StringComparison]::OrdinalIgnoreCase)) { $keep = $false; break } }
    $keep
}

if ($pyFiles.Count -eq 0) {
    Write-Err "No Python files to scan after applying excludes: $($excludeList -join ', ')"
    exit 2
}

$targetsArgArray = $pyFiles | ForEach-Object { $_.FullName }

# Build final argument list: options first, then file targets
$argList = @('--min-confidence', $MinConfidence)
if ($remainingExtra) { $argList += ($remainingExtra -split '\s+') }
$argList += $targetsArgArray

$cmdPreview = "$venvPython -m vulture $($argList -join ' ')"
Write-Info "Scanning $(($targetsArgArray).Count) Python file(s); excludes: $($excludeList -join ', ')"
Write-Info "Running: $cmdPreview"

function Invoke-VultureRun {
    param([string]$OutFilePath)
    try {
        Write-Info "Running vulture -> $OutFilePath"
        & $venvPython -m vulture @argList > $OutFilePath 2>&1
        return $LASTEXITCODE
    } catch {
        Write-Err "Failed to execute vulture: $_"
        return 2
    }
}

# If RunTests is requested, do an initial vulture run, execute tests, then re-run vulture
if ($RunTests) {
    $beforeFile = ([System.IO.Path]::GetFileNameWithoutExtension($OutFile) + ".before.txt")
    $afterFile = ([System.IO.Path]::GetFileNameWithoutExtension($OutFile) + ".after.txt")

    $rc1 = Invoke-VultureRun -OutFilePath $beforeFile
    if ($rc1 -ne 0) { Write-Info "Initial vulture run completed with code $rc1" }

    # Run the test script if available
    $testScript = Join-Path $PSScriptRoot 'run_all_tests.ps1'
    if (Test-Path $testScript) {
        Write-Info "Running test suite via $testScript"
        try {
            & powershell -ExecutionPolicy Bypass -File $testScript
            $testRC = $LASTEXITCODE
            if ($testRC -eq 0) { Write-Info "Tests passed (exit code 0)" } else { Write-Warn "Tests failed (exit code $testRC)" }
        } catch {
            Write-Err "Failed to execute test script: $_"
            $testRC = 2
        }
    } else {
        Write-Warn "Test script not found at $testScript - skipping tests"
        $testRC = 3
    }

    $rc2 = Invoke-VultureRun -OutFilePath $afterFile
    if ($rc2 -ne 0) { Write-Info "Post-test vulture run completed with code $rc2" }

    # Summarize both reports
    Write-Host "\n=== Vulture summary (before tests) ===" -ForegroundColor Green
    if (Test-Path $beforeFile) { Get-Content $beforeFile | Select-Object -First 20 | ForEach-Object { Write-Host $_ } } else { Write-Host "(no report)" }
    Write-Host "\n=== Tests summary ===" -ForegroundColor Green
    if ($testRC -eq 0) { Write-Host "Tests passed" -ForegroundColor Cyan } elseif ($testRC -eq 3) { Write-Host "Tests skipped (script not found)" -ForegroundColor Yellow } else { Write-Host "Tests failed (exit code $testRC)" -ForegroundColor Red }
    Write-Host "\n=== Vulture summary (after tests) ===" -ForegroundColor Green
    if (Test-Path $afterFile) { Get-Content $afterFile | Select-Object -First 20 | ForEach-Object { Write-Host $_ } } else { Write-Host "(no report)" }

    # Determine proper exit code for CI: prefer failing tests' code, otherwise fail if vulture found issues
    $finalExit = 0
    if ($rc1 -ne 0) { Write-Warn "Initial vulture run found issues (exit code $rc1)"; $finalExit = 1 }
    if ($testRC -ne 0 -and $testRC -ne 3) { Write-Err "Tests failed with exit code $testRC"; $finalExit = $testRC }
    if ($rc2 -ne 0) { Write-Warn "Post-test vulture run found issues (exit code $rc2)"; if ($finalExit -eq 0) { $finalExit = 1 } }

    if ($Open) { Invoke-Item $afterFile }
    exit $finalExit
}

# Default single-run behavior
$rcFinal = Invoke-VultureRun -OutFilePath $OutFile
if ($rcFinal -eq 0) { Write-Info "No issues found by vulture (report is empty)."; if ($Open) { Invoke-Item $OutFile }; exit 0 } else { Write-Warn "vulture reported issues (see $OutFile)"; if ($Open) { Invoke-Item $OutFile }; exit 1 }

# Show brief summary
if (Test-Path $OutFile) {
    $lines = Get-Content $OutFile -ErrorAction SilentlyContinue
    $count = ($lines | Measure-Object -Line).Lines
    if ($count -eq 0) {
        Write-Info "No issues found by vulture (report is empty)."
        if ($Open) { Invoke-Item $OutFile }
        exit 0
    } else {
        Write-Warn "vulture reported $count potential issue(s). Report written to: $OutFile"
        # Show top 20 lines
        Write-Host "--- BEGIN vulture_report (first 20 lines) ---" -ForegroundColor Green
        $lines | Select-Object -First 20 | ForEach-Object { Write-Host $_ }
        Write-Host "--- END vulture_report ---" -ForegroundColor Green
        if ($Open) { Invoke-Item $OutFile }
        exit 1
    }
} else {
    Write-Err "Report file not created: $OutFile"
    exit 2
}