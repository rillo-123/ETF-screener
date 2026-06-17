<#
workflow_milestone.ps1

Milestone maintenance workflow for the ETF Screener repo.

What it does:
  1. Updates the plan docs and progress.md.
  2. Runs the test suite.
  3. Optionally applies light auto-fixes when tests fail.
  4. Reruns the tests after those fixes.
  5. Stops if tests are still failing; otherwise commits and pushes the current branch.

Conversation convention:
  "Set the milestone" means the work should be carried to a clean checkpoint:
    - update the plan docs and progress.md
    - run the full test suite
    - fix remaining bugs until everything passes
    - commit and push the finished checkpoint

This script handles the reproducible gate/publish portion of that workflow.
If substantive bugs remain after the automatic fix pass, repair them and rerun
the milestone workflow.

Usage:
  .\workflow_milestone.ps1
  .\workflow_milestone.ps1 -NoAutoFix
  .\workflow_milestone.ps1 -CommitMessage "chore: milestone sync"
  .\workflow_milestone.ps1 -- -Parallel -TimeoutSec 120

Any extra arguments are forwarded to `scripts/run_all_tests.ps1`.
#>

param(
    [switch]$NoAutoFix,
    [string]$CommitMessage = "chore: milestone sync",
    [switch]$Help,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TestRunnerArgs
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @"
workflow_milestone.ps1

Milestone maintenance workflow for the ETF Screener repo.

Usage:
  .\workflow_milestone.ps1
  .\workflow_milestone.ps1 -NoAutoFix
  .\workflow_milestone.ps1 -CommitMessage "chore: milestone sync"
  .\workflow_milestone.ps1 -- -Parallel -TimeoutSec 120

Behavior:
  1. Updates the plan docs and progress.md with the current milestone outcome.
  2. Runs scripts/run_all_tests.ps1.
  3. Applies light auto-fixes with ruff and black if the tests fail.
  4. Reruns the tests after those fixes.
  5. Stops if tests are still failing; otherwise commits and pushes the current branch.

Conversation convention:
  "Set the milestone" means: update plan/progress, run all tests, fix bugs
  until everything passes, and then commit/push the checkpoint. This script
  performs the repeatable gate/publish step after the code is ready.

Any extra arguments are forwarded to scripts/run_all_tests.ps1.
"@
    exit 0
}

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $scriptRoot) -ieq 'scripts') {
    $root = Split-Path -Parent $scriptRoot
} else {
    $root = $scriptRoot
}

Push-Location $root

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir "workflow_milestone_$timestamp.log"
Start-Transcript -Path $logFile -Append | Out-Null

function Write-Info {
    param([string]$Message)
    Write-Host "[workflow] $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[workflow] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "[workflow] $Message" -ForegroundColor Red
}

function Test-PythonModule {
    param([string]$ModuleName)
    & $python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)" | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Invoke-TestSuite {
    param([string[]]$RunnerArgs = @())

    $runner = Join-Path $root 'scripts\run_all_tests.ps1'
    if (-not (Test-Path $runner)) {
        throw "Test runner not found at $runner"
    }

    Write-Info "Running test suite..."
    if ($RunnerArgs.Count -gt 0) {
        Write-Info ("Forwarded test args: " + ($RunnerArgs -join ' '))
    }

    $powershellExe = (Get-Process -Id $PID).Path
    if ([string]::IsNullOrWhiteSpace($powershellExe)) {
        $powershellExe = 'powershell.exe'
    }

    $testOutput = & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $runner @RunnerArgs 2>&1
    $testExitCode = $LASTEXITCODE
    if ($null -ne $testOutput) {
        $testOutput | Out-Host
    }

    return $testExitCode
}

function Invoke-AutoFix {
    $appliedFixes = [System.Collections.Generic.List[string]]::new()

    if (Test-PythonModule -ModuleName 'ruff') {
        Write-Info "Trying ruff auto-fixes..."
        $ruffOutput = & $python -m ruff check --fix src/ tests/ 2>&1
        $ruffExitCode = $LASTEXITCODE
        if ($null -ne $ruffOutput) {
            $ruffOutput | Out-Host
        }

        if ($ruffExitCode -eq 0) {
            $appliedFixes.Add('ruff --fix') | Out-Null
        } else {
            Write-Warn "ruff auto-fix reported issues."
        }
    } else {
        Write-Warn "ruff is not installed; skipping ruff auto-fix."
    }

    if (Test-PythonModule -ModuleName 'black') {
        Write-Info "Running black formatter..."
        $blackOutput = & $python -m black src/ tests/ 2>&1
        $blackExitCode = $LASTEXITCODE
        if ($null -ne $blackOutput) {
            $blackOutput | Out-Host
        }

        if ($blackExitCode -eq 0) {
            $appliedFixes.Add('black') | Out-Null
        } else {
            Write-Warn "black reported formatting issues."
        }
    } else {
        Write-Warn "black is not installed; skipping black formatting."
    }

    return $appliedFixes
}

function Invoke-PlanProgressUpdate {
    param(
        [string[]]$SummaryLines = @(),
        [string]$NextResumePoint = ""
    )

    $helper = Join-Path $root 'scripts\workflow_update_plan_progress.ps1'
    if (-not (Test-Path $helper)) {
        throw "Plan/progress workflow not found at $helper"
    }

    $helperArgs = @()
    foreach ($line in $SummaryLines) {
        $helperArgs += @('-Summary', $line)
    }

    if (-not [string]::IsNullOrWhiteSpace($NextResumePoint)) {
        $helperArgs += @('-NextResumePoint', $NextResumePoint)
    }

    & $helper @helperArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Plan/progress update failed with exit code $LASTEXITCODE"
    }
}

function Invoke-Git {
    param([string[]]$Arguments)

    & git @Arguments
    return $LASTEXITCODE
}

function Get-CurrentBranch {
    $branch = (& git branch --show-current).Trim()
    return $branch
}

try {
    Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
    Write-Host "ETF SCREENER - MILESTONE WORKFLOW" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan

    $testExitCode = Invoke-TestSuite -RunnerArgs $TestRunnerArgs
    $fixes = @()
    $appliedFixes = @()
    if ($testExitCode -ne 0 -and -not $NoAutoFix) {
        Write-Warn "Initial test run failed. Attempting light auto-fixes..."
        $fixes = Invoke-AutoFix
        if ($fixes.Count -gt 0) {
            Write-Info ("Applied fixes: " + ($fixes -join ', '))
        } else {
            Write-Warn "No auto-fixes were applied."
        }

        Write-Info "Re-running the test suite after fixes..."
        $testExitCode = Invoke-TestSuite -RunnerArgs $TestRunnerArgs
    }

    if ($fixes) {
        $appliedFixes = @($fixes)
    }

    $summaryLines = @()
    if ($testExitCode -eq 0) {
        if ($appliedFixes.Count -gt 0) {
            $summaryLines += "Milestone workflow completed successfully after applying fixes: $($appliedFixes -join ', ')."
        } else {
            $summaryLines += "Milestone workflow completed successfully with no auto-fixes required."
        }
    } else {
        $summaryLines += "Milestone workflow stopped because the test suite still fails."
        if ($appliedFixes.Count -gt 0) {
            $summaryLines += "Applied fixes before stopping: $($appliedFixes -join ', ')."
        }
    }

    $nextResumePoint = if ($testExitCode -eq 0) {
        "Review the latest commit and pick up the next implementation task."
    } else {
        "Inspect the failing test output and fix the remaining bug before rerunning the milestone workflow."
    }

    Write-Info "Updating plan.md and progress.md..."
    Invoke-PlanProgressUpdate -SummaryLines $summaryLines -NextResumePoint $nextResumePoint

    if ($testExitCode -ne 0) {
        Write-Err "Tests are still failing. Nothing will be committed or pushed."
        exit $testExitCode
    }

    Write-Info "Test suite passed."

    Write-Info "Staging changes..."
    $addExit = Invoke-Git -Arguments @('add', '-A')
    if ($addExit -ne 0) {
        throw "git add failed with exit code $addExit"
    }

    # Keep obviously local runtime artifacts out of the milestone commit.
    $excludePaths = @(
        'etf.db',
        'config/delisting_state.json'
    )
    foreach ($excludePath in $excludePaths) {
        if (Test-Path (Join-Path $root $excludePath)) {
            & git reset -- $excludePath | Out-Null
        }
    }

    $stagedFiles = @(git diff --cached --name-only)
    if ($stagedFiles.Count -eq 0) {
        Write-Warn "Nothing remains staged after exclusions. Skipping commit and push."
        exit 0
    }

    $branch = Get-CurrentBranch
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw "Could not determine the current branch."
    }

    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        $CommitMessage = "chore: milestone sync"
    }

    Write-Info "Creating commit on branch '$branch'..."
    & git commit -m $CommitMessage
    if ($LASTEXITCODE -ne 0) {
        throw "git commit failed with exit code $LASTEXITCODE"
    }

    Write-Info "Pushing to origin/$branch..."
    & git push origin $branch
    if ($LASTEXITCODE -ne 0) {
        throw "git push failed with exit code $LASTEXITCODE"
    }

    $commitSha = (& git rev-parse --short HEAD).Trim()
    Write-Info "Commit and push completed successfully at $commitSha."
    exit 0
}
finally {
    Stop-Transcript | Out-Null
    Pop-Location
}
