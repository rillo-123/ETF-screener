$ErrorActionPreference = "Stop"

$vsCodeChannels = @(
    [pscustomobject]@{
        Name         = "Stable"
        WingetId     = "Microsoft.VisualStudioCode"
        CodeCommand  = "code"
        ProcessNames = @("Code")
        FallbackPaths = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code\Code.exe"),
            (Join-Path $env:ProgramFiles "Microsoft VS Code\Code.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Microsoft VS Code\Code.exe")
        )
    },
    [pscustomobject]@{
        Name         = "Insiders"
        WingetId     = "Microsoft.VisualStudioCode.Insiders"
        CodeCommand  = "code-insiders"
        ProcessNames = @("Code - Insiders")
        FallbackPaths = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Microsoft VS Code Insiders\Code - Insiders.exe"),
            (Join-Path $env:ProgramFiles "Microsoft VS Code Insiders\Code - Insiders.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Microsoft VS Code Insiders\Code - Insiders.exe")
        )
    }
)

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

function Resolve-VsCodeCliPath {
    param(
        [Parameter(Mandatory = $true)][string]$CommandName,
        [string[]]$FallbackPaths = @()
    )

    $command = Get-ToolCommand -Name $CommandName
    if ($command) {
        return $command.Source
    }

    foreach ($fallbackPath in $FallbackPaths) {
        if ($fallbackPath -and (Test-Path $fallbackPath)) {
            return $fallbackPath
        }
    }

    return $null
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
    param([string[]]$ProcessNames = @("Code"))

    $processes = @()
    foreach ($processName in $ProcessNames) {
        $processes += @(Get-Process -Name $processName -ErrorAction SilentlyContinue)
    }

    return @($processes)
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
    $channelStatuses = @()

    Write-Host "--- Devtools Maintenance ---" -ForegroundColor Cyan

    $wingetCommand = Get-ToolCommand -Name "winget"
    if (-not $wingetCommand) {
        Write-Host "winget is not available; cannot manage VS Code from the CLI." -ForegroundColor Red
        return 1
    }

    foreach ($channel in $vsCodeChannels) {
        $appStatus = "Not run"
        $extensionStatus = "Not run"

        Write-Host "Checking $($channel.Name) VS Code installation..." -ForegroundColor Cyan
        $listResult = Invoke-WingetCli -Arguments @("list", "--id", $channel.WingetId, "--exact")
        $packageRecord = Get-WingetPackageRecord -Output $listResult.Output -PackageId $channel.WingetId
        $vsCodeWasRunning = (Get-RunningVsCodeProcess -ProcessNames $channel.ProcessNames).Count -gt 0

        if (-not $packageRecord) {
            if ($listResult.Output.Count -gt 0) {
                Write-ExternalOutput -Lines $listResult.Output
            }

            Write-Host "$($channel.Name) VS Code ($($channel.WingetId)) was not found via winget; installing it now..." -ForegroundColor Yellow
            $installResult = Invoke-WingetCli -Arguments @(
                "install",
                "--id", $channel.WingetId,
                "--exact",
                "--source", "winget",
                "--accept-source-agreements",
                "--accept-package-agreements"
            )

            if ($installResult.Output.Count -gt 0) {
                Write-ExternalOutput -Lines $installResult.Output
            }

            if ($installResult.ExitCode -eq 0) {
                $appStatus = "Installed"
                Write-Host "$($channel.Name) VS Code installation completed." -ForegroundColor Green
            } else {
                $overallSuccess = $false
                $appStatus = "Install failed (exit code $($installResult.ExitCode))"
                Write-Host "$($channel.Name) VS Code installation failed." -ForegroundColor Yellow
            }
        } elseif ($packageRecord.Available) {
            if ($vsCodeWasRunning) {
                Write-Host "$($channel.Name) VS Code appears to be running; the upgrade may be blocked until it is closed." -ForegroundColor Yellow
            }

            Write-Host "Upgrading $($channel.Name) VS Code from $($packageRecord.Version) to $($packageRecord.Available)..." -ForegroundColor Cyan
            $upgradeResult = Invoke-WingetCli -Arguments @(
                "upgrade",
                "--id", $channel.WingetId,
                "--exact",
                "--source", "winget",
                "--accept-source-agreements",
                "--accept-package-agreements"
            )

            if ($upgradeResult.Output.Count -gt 0) {
                Write-ExternalOutput -Lines $upgradeResult.Output
            }

            if ($upgradeResult.ExitCode -eq 0) {
                $appStatus = "Updated to $($packageRecord.Available)"
                Write-Host "$($channel.Name) VS Code upgrade completed." -ForegroundColor Green
            } else {
                $overallSuccess = $false
                $appStatus = "Upgrade failed (exit code $($upgradeResult.ExitCode))"
                Write-Host "$($channel.Name) VS Code upgrade failed." -ForegroundColor Yellow
                if ($vsCodeWasRunning) {
                    Write-Host "$($channel.Name) VS Code was running during the failed upgrade. Close it and retry if the installer was blocked." -ForegroundColor Yellow
                }
            }
        } else {
            $currentVersion = if ($packageRecord.Version) { $packageRecord.Version } else { "unknown" }
            $appStatus = "Already current ($currentVersion)"
            Write-Host "$($channel.Name) VS Code $currentVersion is already up to date." -ForegroundColor Green
        }

        Write-Host "Resolving the $($channel.Name) VS Code CLI..." -ForegroundColor Cyan
        $codeCommandPath = Resolve-VsCodeCliPath -CommandName $channel.CodeCommand -FallbackPaths $channel.FallbackPaths
        if (-not $codeCommandPath) {
            $overallSuccess = $false
            $extensionStatus = "CLI not found"
            Write-Host "The $($channel.CodeCommand) CLI is not available; cannot update installed extensions." -ForegroundColor Yellow
        } else {
            Write-Host "Updating installed $($channel.Name) VS Code extensions..." -ForegroundColor Cyan
            $extensionResult = Invoke-CodeCli -CodePath $codeCommandPath -Arguments @("--update-extensions")
            $extensionErrors = Get-ExtensionUpdateErrors -Output $extensionResult.Output

            if ($extensionResult.Output.Count -gt 0) {
                Write-ExternalOutput -Lines $extensionResult.Output
            }

            if ($extensionResult.ExitCode -eq 0 -and $extensionErrors.Count -eq 0) {
                $extensionStatus = "Extension update completed"
                Write-Host "$($channel.Name) VS Code extension update completed." -ForegroundColor Green
            } else {
                $overallSuccess = $false
                if ($extensionErrors.Count -gt 0) {
                    $extensionStatus = "Extension update reported $($extensionErrors.Count) error(s)"
                } else {
                    $extensionStatus = "Extension update failed (exit code $($extensionResult.ExitCode))"
                }
                Write-Host "$($channel.Name) VS Code extension update failed." -ForegroundColor Yellow
            }
        }

        $channelStatuses += [pscustomobject]@{
            Name       = $channel.Name
            AppStatus  = $appStatus
            Extensions = $extensionStatus
        }
    }

    Write-Host "Summary:" -ForegroundColor Cyan
    foreach ($channelStatus in $channelStatuses) {
        Write-Host "  $($channelStatus.Name): $($channelStatus.AppStatus)"
        Write-Host "    Extensions: $($channelStatus.Extensions)"
    }

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
