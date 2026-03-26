# PowerShell Profile - Python Template
# This file loads automatically when PowerShell starts
# Copy this file to your PowerShell profile directory or run it manually with: . .\profile.ps1

# Disable venv automatic prompt so we handle it in our custom prompt function
$env:VIRTUAL_ENV_DISABLE_PROMPT = $true

# Git branch and dirty marker helpers for prompt

function Get-GitBranch {
    try {
        $branch = git rev-parse --abbrev-ref HEAD 2>$null | ForEach-Object { $_.Trim() }
        if ($LASTEXITCODE -eq 0 -and $branch) { return $branch }
        return $null
    } catch {
        return $null
    }
}

function Get-GitDirtyMarker {
    try {
        $status = git status --porcelain 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $status) { return '' }
        
        $markers = ""
        
        # Check for untracked files (lines starting with ??)
        if ($status -match '^\?\?') {
            $markers += '+'
        }

        # Check for modified/deleted/renamed files (lines starting with M, D, R, etc.)
        # Both staged and unstaged (the regex covers both columns)
        if ($status -match '^[ MADRC]') {
            $markers += '*'
        }
        
        return $markers
    } catch {
        return ''
    }
}

# Cache structure to reduce git calls (improves responsiveness)
if (-not (Test-Path Variable:GitPromptCache)) {
    Set-Variable -Name GitPromptCache -Value @{ 
        Path = $null
        Branch = $null
        Dirty = $null
        Timestamp = [datetime]::MinValue 
    } -Scope Global
}

function Update-GitPromptCache {
    param([string]$path)
    $cache = Get-Variable -Name GitPromptCache -Scope Global -ValueOnly
    
    # Cache is valid for 1 second to avoid excessive git calls
    if ($cache.Path -eq $path -and ((Get-Date) - $cache.Timestamp).TotalSeconds -lt 1) {
        return $cache
    }

    $branch = Get-GitBranch
    $dirty = Get-GitDirtyMarker
    $cache.Path = $path
    $cache.Branch = $branch
    $cache.Dirty = $dirty
    $cache.Timestamp = Get-Date
    Set-Variable -Name GitPromptCache -Value $cache -Scope Global
    return $cache
}

# Custom prompt that shows virtualenv, git branch, and dirty marker
function global:prompt {
    try {
        $path = (Get-Location).Path

        # Show virtualenv name if active
        $venvPart = ""
        if ($env:VIRTUAL_ENV) {
            $venvName = Split-Path -Leaf $env:VIRTUAL_ENV
            $venvPart = "($venvName) "
        }

        # Show git branch + dirty marker (if in a git repo)
        $branchName = ""
        $branchDirty = ""
        if (Get-Command git -ErrorAction SilentlyContinue) {
            $cache = Update-GitPromptCache -path $path
            if ($cache.Branch) {
                $branchName = $cache.Branch
                $branchDirty = $cache.Dirty
            }
        }

        # Use ANSI colors if terminal supports them
        $useColor = $false
        try { $useColor = $Host.UI.SupportsVirtualTerminal } catch { $useColor = $false }

        if ($useColor) {
            $esc = "`e"
            # Cyan for virtualenv
            $c_venv = ""
            if ($venvPart) { $c_venv = "${esc}[36m$venvPart${esc}[0m" }

            # Yellow for branch, Red for dirty marker
            $c_git = ""
            if ($branchName) {
                # Format: (branch+*)
                $c_git = "(${esc}[33m$branchName${esc}[0m"
                if ($branchDirty) {
                    $c_git += "${esc}[31m$branchDirty${esc}[0m"
                }
                $c_git += ") "
            }
            
            # Green for path
            $promptString = "$c_venv$c_git${esc}[32m$path${esc}[0m`n> "
            return $promptString
        } else {
            # Fallback without colors
            $fallbackGit = ""
            if ($branchName) { $fallbackGit = "($branchName$branchDirty) " }
            return "$venvPart$fallbackGit$path`n> "
        }
    } catch {
        return "PS> "
    }
}

# Function to ensure venv is activated with git prompt (easier than dot-sourcing)
function ensure-venv {
    $scriptPath = Join-Path (Split-Path -Parent $PSCommandPath) "ensure-venv.ps1"
    if (Test-Path $scriptPath) {
        . $scriptPath
    } else {
        Write-Error "ensure-venv.ps1 not found"
    }
}

