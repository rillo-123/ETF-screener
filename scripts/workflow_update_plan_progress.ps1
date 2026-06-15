<#
workflow_update_plan_progress.ps1

Plan/progress maintenance workflow for the ETF Screener repo.

What it does:
  1. Updates the "Last updated" stamp in root plan.md.
  2. Optionally replaces the current objective.
  3. Prepends a new progress entry at the top of progress.md.
  4. Optionally prepends new notes into the detailed companion plan files under plan/.

Usage:
  .\workflow_update_plan_progress.ps1 -Summary "Added a new workflow helper."
  .\workflow_update_plan_progress.ps1 -Objective "Build a better refresh pipeline."
  .\workflow_update_plan_progress.ps1 -Summary "Shipped the helper." -NextResumePoint "Run it after the next turn."
  .\workflow_update_plan_progress.ps1 -Summary "..." -LockedDecision "Keep a root plan.md entrypoint plus companion plan files tracked in the repo."

The Summary notes are used for both plan/current-state.md prepends and the new progress.md entry.
#>

param(
    [string[]]$Summary,
    [string]$Objective,
    [string[]]$LockedDecision,
    [string]$NextResumePoint,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @"
workflow_update_plan_progress.ps1

Plan/progress maintenance workflow for the ETF Screener repo.

Usage:
  .\workflow_update_plan_progress.ps1 -Summary "Added a new workflow helper."
  .\workflow_update_plan_progress.ps1 -Objective "Build a better refresh pipeline."
  .\workflow_update_plan_progress.ps1 -Summary "Shipped the helper." -NextResumePoint "Run it after the next turn."
  .\workflow_update_plan_progress.ps1 -Summary "..." -LockedDecision "Keep a root plan.md entrypoint plus companion plan files tracked in the repo."

Behavior:
  1. Updates the "Last updated" stamp in root plan.md.
  2. Optionally replaces the current objective.
  3. Prepends a new progress entry at the top of progress.md.
  4. Optionally prepends notes into the detailed companion plan files under plan/.

The Summary notes are used for both plan/current-state.md prepends and the new progress.md entry.
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

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
$planPath = Join-Path $root 'plan.md'
$planDir = Join-Path $root 'plan'
$currentStatePath = Join-Path $planDir 'current-state.md'
$lockedDecisionsPath = Join-Path $planDir 'locked-decisions.md'
$progressPath = Join-Path $root 'progress.md'

$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$logFile = Join-Path $logDir ("workflow_update_plan_progress_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
Start-Transcript -Path $logFile -Append | Out-Null

function Write-Info {
    param([string]$Message)
    Write-Host "[plan-progress] $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[plan-progress] $Message" -ForegroundColor Yellow
}

function Normalize-Note {
    param([string]$Text)

    $clean = "$Text".Trim()
    $clean = $clean -replace '^[\-\*]\s+', ''
    return $clean
}

function Normalize-Notes {
    param([string[]]$Text)

    $notes = @()
    foreach ($item in @($Text)) {
        $clean = Normalize-Note -Text $item
        if ($clean) {
            $notes += $clean
        }
    }

    return $notes
}

function Find-SectionBounds {
    param(
        [string[]]$Lines,
        [Parameter(Mandatory = $true)][string]$Heading
    )

    $start = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -eq $Heading) {
            $start = $i
            break
        }
    }

    if ($start -lt 0) {
        throw "Could not find section heading '$Heading' in the target file."
    }

    $end = $Lines.Count - 1
    for ($i = $start + 1; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^## ') {
            $end = $i - 1
            break
        }
    }

    return [pscustomobject]@{
        Start = $start
        End   = $end
    }
}

function Replace-SectionContent {
    param(
        [string[]]$Lines,
        [Parameter(Mandatory = $true)][string]$Heading,
        [string[]]$NewContent
    )

    $bounds = Find-SectionBounds -Lines $Lines -Heading $Heading

    $before = @()
    if ($bounds.Start -gt 0) {
        $before = @($Lines[0..$bounds.Start])
    } else {
        $before = @($Lines[0])
    }

    $after = @()
    if ($bounds.End + 1 -lt $Lines.Count) {
        $after = @($Lines[($bounds.End + 1)..($Lines.Count - 1)])
    }

    return @($before + $NewContent + $after)
}

function Prepend-MarkdownListContent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$NewNotes
    )

    $cleanNotes = Normalize-Notes -Text $NewNotes
    if ($cleanNotes.Count -eq 0) {
        return
    }

    $lines = @(Get-Content -LiteralPath $Path)
    if ($lines.Count -eq 0 -or $lines[0] -notmatch '^# ') {
        throw "Expected a top-level markdown heading in $Path."
    }

    $existing = @()
    if ($lines.Count -gt 1) {
        $existing = @($lines[1..($lines.Count - 1)])
    }

    while ($existing.Count -gt 0 -and [string]::IsNullOrWhiteSpace($existing[0])) {
        if ($existing.Count -le 1) {
            $existing = @()
        } else {
            $existing = @($existing[1..($existing.Count - 1)])
        }
    }

    $updated = @($lines[0], '')
    foreach ($clean in $cleanNotes) {
        $updated += "- $clean"
    }
    $updated += ''

    if ($existing.Count -gt 0) {
        $updated += $existing
    }

    Set-Content -LiteralPath $Path -Value $updated -Encoding utf8
}

function Update-PlanDocument {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$NewObjective
    )

    $lines = @(Get-Content -LiteralPath $Path)

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^Last updated:\s*') {
            $lines[$i] = "Last updated: $timestamp"
            break
        }
    }

    if ($NewObjective) {
        $objectiveLines = @('')
        $objectiveLines += @($NewObjective -split "`r?`n")
        $objectiveLines += ''
        $lines = Replace-SectionContent -Lines $lines -Heading '## Current objective' -NewContent $objectiveLines
    }

    Set-Content -LiteralPath $Path -Value $lines -Encoding utf8
}

function Update-ProgressDocument {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$EntryNotes,
        [string]$ResumePoint
    )

    $lines = @(Get-Content -LiteralPath $Path)

    $section = New-Object System.Collections.Generic.List[string]
    $section.Add("## $timestamp") | Out-Null
    $section.Add('') | Out-Null

    foreach ($clean in (Normalize-Notes -Text $EntryNotes)) {
        $section.Add("- $clean") | Out-Null
    }

    if ($ResumePoint) {
        $section.Add("- Next resume point: $ResumePoint") | Out-Null
    }

    if ($section.Count -eq 2) {
        $section.Add('- Updated plan and progress metadata.') | Out-Null
    }

    $section.Add('') | Out-Null

    $insertAt = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^## ') {
            $insertAt = $i
            break
        }
    }

    if ($insertAt -lt 0) {
        throw "Could not find an insertion point in $Path."
    }

    $updated = New-Object System.Collections.Generic.List[string]
    if ($insertAt -gt 0) {
        foreach ($line in $lines[0..($insertAt - 1)]) {
            $updated.Add($line) | Out-Null
        }
    }
    foreach ($line in $section) {
        $updated.Add($line) | Out-Null
    }
    foreach ($line in $lines[$insertAt..($lines.Count - 1)]) {
        $updated.Add($line) | Out-Null
    }

    Set-Content -LiteralPath $Path -Value $updated -Encoding utf8
}

try {
    if (-not (Test-Path $planPath)) {
        throw "plan.md not found at $planPath"
    }

    if (-not (Test-Path $currentStatePath)) {
        throw "current-state plan file not found at $currentStatePath"
    }

    if (-not (Test-Path $lockedDecisionsPath)) {
        throw "locked-decisions plan file not found at $lockedDecisionsPath"
    }

    if (-not (Test-Path $progressPath)) {
        throw "progress.md not found at $progressPath"
    }

    $cleanSummary = Normalize-Notes -Text $Summary
    $cleanLockedDecision = Normalize-Notes -Text $LockedDecision

    $hasWork = ($null -ne $Objective) -or ($cleanSummary.Count -gt 0) -or ($cleanLockedDecision.Count -gt 0) -or ($null -ne $NextResumePoint)
    if (-not $hasWork) {
        Write-Warn "No updates were supplied. Use -Help to see examples."
        exit 1
    }

    $stateNotes = $cleanSummary
    if ($stateNotes.Count -eq 0) {
        if ($Objective) {
            $stateNotes = @('Updated the plan objective.')
        } elseif ($cleanLockedDecision.Count -gt 0) {
            $stateNotes = @('Updated the locked decisions.')
        } elseif ($NextResumePoint) {
            $stateNotes = @('Recorded the next resume point.')
        }
    }

    $progressNotes = $cleanSummary
    if ($progressNotes.Count -eq 0) {
        if ($Objective) {
            $progressNotes = @('Updated the plan objective.')
        } elseif ($cleanLockedDecision.Count -gt 0) {
            $progressNotes = @('Updated the locked decisions.')
        } else {
            $progressNotes = @('Updated the plan and progress metadata.')
        }
    }

    Write-Info "Updating plan.md, companion plan files, and progress.md..."
    Update-PlanDocument -Path $planPath -NewObjective $Objective
    Prepend-MarkdownListContent -Path $currentStatePath -NewNotes $stateNotes
    Prepend-MarkdownListContent -Path $lockedDecisionsPath -NewNotes $cleanLockedDecision
    Update-ProgressDocument -Path $progressPath -EntryNotes $progressNotes -ResumePoint $NextResumePoint

    Write-Info "Plan and progress were updated successfully."
    exit 0
}
finally {
    Stop-Transcript | Out-Null
    Pop-Location
}
