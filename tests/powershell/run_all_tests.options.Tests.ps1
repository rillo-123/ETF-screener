$ErrorActionPreference = 'Stop'

Describe 'run_all_tests.ps1 option matrix' {
    BeforeAll {
        $repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
        $scriptPath = Join-Path $repoRoot 'run_all_tests.ps1'

        if (-not (Test-Path $scriptPath)) {
            throw "Could not find run_all_tests.ps1 at $scriptPath"
        }

        $commonArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath)

        function Invoke-Runner {
            param(
                [string]$Args,
                [int]$TimeoutSec = 900
            )

            $argList = [System.Collections.Generic.List[string]]::new()
            foreach ($a in $commonArgs) { $argList.Add($a) }
            if (-not [string]::IsNullOrWhiteSpace($Args)) {
                foreach ($a in ($Args -split ' ')) {
                    if (-not [string]::IsNullOrWhiteSpace($a)) {
                        $argList.Add($a)
                    }
                }
            }

            $stdoutFile = [System.IO.Path]::GetTempFileName()
            $stderrFile = [System.IO.Path]::GetTempFileName()

            try {
                $proc = Start-Process -FilePath 'pwsh' -ArgumentList $argList -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
                return [pscustomobject]@{
                    ExitCode = $proc.ExitCode
                    StdOut = (Get-Content -Raw -ErrorAction SilentlyContinue $stdoutFile)
                    StdErr = (Get-Content -Raw -ErrorAction SilentlyContinue $stderrFile)
                    Args = $Args
                }
            }
            finally {
                Remove-Item -LiteralPath $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue
            }
        }

        $matrix = @(
            @{ Args = '-Help'; ExpectedExitCode = 0 },
            @{ Args = ''; ExpectedExitCode = 0 },
            @{ Args = '-Parallel'; ExpectedExitCode = 0 },
            @{ Args = '-RandomOrder'; ExpectedExitCode = 0 },
            @{ Args = '-TimeoutSec 120'; ExpectedExitCode = 0 },
            @{ Args = '-QualityGate'; ExpectedExitCode = 0 },
            @{ Args = '-Ruff'; ExpectedExitCode = 0 },
            @{ Args = '-Mypy'; ExpectedExitCode = 0 },
            @{ Args = '-Coverage'; ExpectedExitCode = 0 },
            @{ Args = '-Vulture'; ExpectedExitCode = 0 },
            @{ Args = '-Black'; ExpectedExitCode = 0 },
            @{ Args = '-Bandit'; ExpectedExitCode = 1 },
            @{ Args = '-All'; ExpectedExitCode = 1 },
            @{ Args = '-QualityGate -Parallel -RandomOrder -TimeoutSec 120 -LogRetentionDays 30 -LogRetentionMaxFiles 500'; ExpectedExitCode = 0 }
        )
    }

    It 'supports all documented option combinations' -TestCases $matrix {
        param($Args, $ExpectedExitCode)

        $result = Invoke-Runner -Args $Args

        if ($result.ExitCode -ne $ExpectedExitCode) {
            $tailOut = ($result.StdOut -split "`r?`n" | Select-Object -Last 40) -join "`n"
            $tailErr = ($result.StdErr -split "`r?`n" | Select-Object -Last 40) -join "`n"
            throw "Args '$Args' expected exit $ExpectedExitCode, got $($result.ExitCode).`nSTDOUT:`n$tailOut`nSTDERR:`n$tailErr"
        }

        $result.ExitCode | Should -Be $ExpectedExitCode
    }
}
