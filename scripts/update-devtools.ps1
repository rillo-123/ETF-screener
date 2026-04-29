$ErrorActionPreference = "Stop"

$vsCodeWingetId = "Microsoft.VisualStudioCode"

function Get-ToolCommand {
    param([Parameter(Mandatory = $true)][string]$Name)

    try {
        return Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    } catch {
        return $null
    }
}

function Invoke-ExternalTool {
    param(
        [Parameter(Mandatory = $true)][string]$CommandPath,
        [string[]]$Arguments = @()
    )

    $output = @(& $CommandPath @Arguments 2>&1)
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $output
    }
}

function Invoke-WingetCli {
    param([string[]]$Arguments = @())

    $wingetCommand = Get-ToolCommand -Name "winget"
    if (-not $wingetCommand) {
        return [pscustomobject]@{
            ExitCode = 127
            Output = @("winget is not available")
        }
    }

    return Invoke-ExternalTool -CommandPath $wingetCommand.Source -Arguments $Arguments
}

function Invoke-CodeCli {
    param(
        [Parameter(Mandatory = $true)][string]$CodePath,
        [string[]]$Arguments = @()
    )

    return Invoke-ExternalTool -CommandPath $CodePath -Arguments $Arguments
}

function Write-ExternalOutput {
    param([object[]]$Lines = @())

    foreach ($line in $Lines) {
        $text = "$line".TrimEnd()
        if ($text) {
            Write-Host "  $text"
        }
    }
}

function Get-WingetPackageRecord {
    param(
        [object[]]$Output = @(),
        [Parameter(Mandatory = $true)][string]$PackageId
    )

    $outputText = ($Output | Out-String)
    $packageMatch = [regex]::Match(
        $outputText,
        "(?m)^(?<line>.*" + [regex]::Escape($PackageId) + ".*)$"
    )

    if (-not $packageMatch.Success) {
        return $null
    }

    $line = $packageMatch.Groups["line"].Value.Trim()
    $idIndex = $line.IndexOf($PackageId, [System.StringComparison]::OrdinalIgnoreCase)
    if ($idIndex -lt 0) {
        return $null
    }

    $name = $line.Substring(0, $idIndex).Trim()
    $rightSide = $line.Substring($idIndex + $PackageId.Length).Trim()
    $tokens = @($rightSide -split '\s+' | Where-Object { $_ })

    if ($tokens.Count -lt 1) {
        return $null
    }

    $version = $tokens[0]
    $available = $null
    $source = $null

    if ($tokens.Count -eq 2) {
        if ($tokens[1] -match '^(winget|msstore)$') {
            $source = $tokens[1]
        } else {
            $available = $tokens[1]
        }
    } elseif ($tokens.Count -ge 3) {
        $available = $tokens[1]
        $source = $tokens[2]
    }

    return [pscustomobject]@{
        Name = $name
        Id = $PackageId
        Version = $version
        Available = $available
        Source = $source
    }
}

function Get-RunningVsCodeProcess {
    return @(Get-Process -Name "Code" -ErrorAction SilentlyContinue)
}

function Get-ExtensionUpdateErrors {
    param([object[]]$Output = @())

    return @(
        foreach ($line in $Output) {
            $text = "$line".Trim()
            if ($text -match '^(Error while updating extension|Failed to update extension|Failed Installing)') {
                $text
            }
        }
    )
}

function Invoke-UpdateDevtools {
    $overallSuccess = $true
    $vsCodeStatus = "Not run"
    $extensionStatus = "Not run"

    Write-Host "--- Devtools Maintenance ---" -ForegroundColor Cyan

    $wingetCommand = Get-ToolCommand -Name "winget"
    if (-not $wingetCommand) {
        Write-Host "winget is not available; cannot manage VS Code from the CLI." -ForegroundColor Red
        return 1
    }

    Write-Host "Checking stable VS Code installation..." -ForegroundColor Cyan
    $listResult = Invoke-WingetCli -Arguments @("list", "--id", $vsCodeWingetId, "--exact")
    $packageRecord = Get-WingetPackageRecord -Output $listResult.Output -PackageId $vsCodeWingetId
    $vsCodeWasRunning = (Get-RunningVsCodeProcess).Count -gt 0

    if (-not $packageRecord) {
        $overallSuccess = $false
        $vsCodeStatus = "Stable VS Code not found via winget"
        Write-Host "Stable VS Code ($vsCodeWingetId) was not found via winget; skipping the app upgrade step." -ForegroundColor Yellow
        if ($listResult.Output.Count -gt 0) {
            Write-ExternalOutput -Lines $listResult.Output
        }
    } elseif ($packageRecord.Available) {
        if ($vsCodeWasRunning) {
            Write-Host "VS Code appears to be running; the upgrade may be blocked until it is closed." -ForegroundColor Yellow
        }

        Write-Host "Upgrading VS Code from $($packageRecord.Version) to $($packageRecord.Available)..." -ForegroundColor Cyan
        $upgradeResult = Invoke-WingetCli -Arguments @(
            "upgrade",
            "--id", $vsCodeWingetId,
            "--exact",
            "--source", "winget",
            "--accept-source-agreements",
            "--accept-package-agreements"
        )

        if ($upgradeResult.Output.Count -gt 0) {
            Write-ExternalOutput -Lines $upgradeResult.Output
        }

        if ($upgradeResult.ExitCode -eq 0) {
            $vsCodeStatus = "Updated to $($packageRecord.Available)"
            Write-Host "VS Code upgrade completed." -ForegroundColor Green
        } else {
            $overallSuccess = $false
            $vsCodeStatus = "Upgrade failed (exit code $($upgradeResult.ExitCode))"
            Write-Host "VS Code upgrade failed." -ForegroundColor Yellow
            if ($vsCodeWasRunning) {
                Write-Host "VS Code was running during the failed upgrade. Close it and retry if the installer was blocked." -ForegroundColor Yellow
            }
        }
    } else {
        $currentVersion = if ($packageRecord.Version) { $packageRecord.Version } else { "unknown" }
        $vsCodeStatus = "Already current ($currentVersion)"
        Write-Host "VS Code $currentVersion is already up to date." -ForegroundColor Green
    }

    Write-Host "Resolving the VS Code CLI..." -ForegroundColor Cyan
    $codeCommand = Get-ToolCommand -Name "code"
    if (-not $codeCommand) {
        $overallSuccess = $false
        $extensionStatus = "code CLI not found"
        Write-Host "The code CLI is not available; cannot update installed extensions." -ForegroundColor Yellow
    } else {
        Write-Host "Updating installed VS Code extensions..." -ForegroundColor Cyan
        $extensionResult = Invoke-CodeCli -CodePath $codeCommand.Source -Arguments @("--update-extensions")
        $extensionErrors = Get-ExtensionUpdateErrors -Output $extensionResult.Output

        if ($extensionResult.Output.Count -gt 0) {
            Write-ExternalOutput -Lines $extensionResult.Output
        }

        if ($extensionResult.ExitCode -eq 0 -and $extensionErrors.Count -eq 0) {
            $extensionStatus = "Extension update completed"
            Write-Host "VS Code extension update completed." -ForegroundColor Green
        } else {
            $overallSuccess = $false
            if ($extensionErrors.Count -gt 0) {
                $extensionStatus = "Extension update reported $($extensionErrors.Count) error(s)"
            } else {
                $extensionStatus = "Extension update failed (exit code $($extensionResult.ExitCode))"
            }
            Write-Host "VS Code extension update failed." -ForegroundColor Yellow
        }
    }

    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  VS Code:    $vsCodeStatus"
    Write-Host "  Extensions: $extensionStatus"

    if ($overallSuccess) {
        Write-Host "Devtools maintenance completed successfully." -ForegroundColor Green
        return 0
    }

    Write-Host "Devtools maintenance finished with issues." -ForegroundColor Yellow
    return 1
}

if ($MyInvocation.InvocationName -ne ".") {
    $global:LASTEXITCODE = Invoke-UpdateDevtools
}
