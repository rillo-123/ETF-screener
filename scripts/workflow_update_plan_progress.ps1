<#
workflow_update_plan_progress.ps1

Plan/progress maintenance workflow for the ETF Screener repo.

What it does:
  1. Updates the "Last updated" stamp in plan.md.
  2. Optionally replaces the current objective.
  3. Prepends a new progress entry at the top of progress.md.
  4. Optionally prepends new notes into the current state / locked decisions sections.

Usage:
  .\workflow_update_plan_progress.ps1 -Summary "Added a new workflow helper."
  .\workflow_update_plan_progress.ps1 -Objective "Build a better refresh pipeline."
  .\workflow_update_plan_progress.ps1 -Summary "Shipped the helper." -NextResumePoint "Run it after the next turn."
  .\workflow_update_plan_progress.ps1 -Summary "..." -LockedDecision "Keep plan.md and progress.md tracked at the repo root."

The Summary notes are used for both plan.md current-state prepends and the new progress.md entry.
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
  .\workflow_update_plan_progress.ps1 -Summary "..." -LockedDecision "Keep plan.md and progress.md tracked at the repo root."

Behavior:
  1. Updates the "Last updated" stamp in plan.md.
  2. Optionally replaces the current objective.
  3. Prepends a new progress entry at the top of progress.md.
  4. Optionally prepends notes into the current state / locked decisions sections.

The Summary notes are used for both plan.md current-state prepends and the new progress.md entry.
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

function Get-SectionContent {
    param(
        [string[]]$Lines,
        [Parameter(Mandatory = $true)][string]$Heading
    )

    $bounds = Find-SectionBounds -Lines $Lines -Heading $Heading
    $contentStart = $bounds.Start + 1
    if ($contentStart -gt $bounds.End) {
        return @()
    }

    return @($Lines[$contentStart..$bounds.End])
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

function Prepend-SectionContent {
    param(
        [string[]]$Lines,
        [Parameter(Mandatory = $true)][string]$Heading,
        [string[]]$NewNotes
    )

    $existing = Get-SectionContent -Lines $Lines -Heading $Heading
    while ($existing.Count -gt 0 -and [string]::IsNullOrWhiteSpace($existing[0])) {
        if ($existing.Count -le 1) {
            $existing = @()
        } else {
            $existing = @($existing[1..($existing.Count - 1)])
        }
    }

    $replacement = @('')
    foreach ($clean in (Normalize-Notes -Text $NewNotes)) {
        $replacement += "- $clean"
    }

    $replacement += $existing
    return Replace-SectionContent -Lines $Lines -Heading $Heading -NewContent $replacement
}

function Update-PlanDocument {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string]$NewObjective,
        [string[]]$StateNotes,
        [string[]]$LockedDecisionNotes
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

    $cleanStateNotes = Normalize-Notes -Text $StateNotes
    if ($cleanStateNotes.Count -gt 0) {
        $lines = Prepend-SectionContent -Lines $lines -Heading '## Current state' -NewNotes $cleanStateNotes
    }

    $cleanLockedDecisionNotes = Normalize-Notes -Text $LockedDecisionNotes
    if ($cleanLockedDecisionNotes.Count -gt 0) {
        $lines = Prepend-SectionContent -Lines $lines -Heading '## Locked decisions' -NewNotes $cleanLockedDecisionNotes
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

    Write-Info "Updating plan.md and progress.md..."
    Update-PlanDocument -Path $planPath -NewObjective $Objective -StateNotes $stateNotes -LockedDecisionNotes $cleanLockedDecision
    Update-ProgressDocument -Path $progressPath -EntryNotes $progressNotes -ResumePoint $NextResumePoint

    Write-Info "Plan and progress were updated successfully."
    exit 0
}
finally {
    Stop-Transcript | Out-Null
    Pop-Location
}
