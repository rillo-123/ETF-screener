$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Matrix data must be at Describe scope (not inside BeforeAll) so that Pester
# can discover the parameterised It blocks at collection time.
# ---------------------------------------------------------------------------

$matrix = @(
    @{ ScriptArgs = '-Help';           ExpectedExitCode = 0 }
    @{ ScriptArgs = '';                ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Parallel';       ExpectedExitCode = 0 }
    @{ ScriptArgs = '-RandomOrder';    ExpectedExitCode = 0 }
    @{ ScriptArgs = '-TimeoutSec 120'; ExpectedExitCode = 0 }
    @{ ScriptArgs = '-QualityGate';    ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Ruff';           ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Mypy';           ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Coverage';       ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Vulture';        ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Black';          ExpectedExitCode = 0 }
    @{ ScriptArgs = '-Bandit';         ExpectedExitCode = 1 }
    @{ ScriptArgs = '-All';            ExpectedExitCode = 1 }
    @{ ScriptArgs = '-QualityGate -Parallel -RandomOrder -TimeoutSec 120 -LogRetentionDays 30 -LogRetentionMaxFiles 500'
                                       ExpectedExitCode = 0 }
)

Describe 'run_all_tests.ps1 option matrix' {
    BeforeAll {
        $repoRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
        $scriptPath = Join-Path $repoRoot 'run_all_tests.ps1'

        if (-not (Test-Path $scriptPath)) {
            throw "Could not find run_all_tests.ps1 at $scriptPath"
        }

        $commonArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath)

        function Invoke-Runner {
            param(
                [string]$ScriptArgs,
                [int]$TimeoutSec = 900
            )

            $argList = [System.Collections.Generic.List[string]]::new()
            foreach ($a in $commonArgs) { $argList.Add($a) }
            if (-not [string]::IsNullOrWhiteSpace($ScriptArgs)) {
                foreach ($a in ($ScriptArgs -split ' ')) {
                    if (-not [string]::IsNullOrWhiteSpace($a)) {
                        $argList.Add($a)
                    }
                }
            }

            $stdoutFile = [System.IO.Path]::GetTempFileName()
            $stderrFile = [System.IO.Path]::GetTempFileName()

            try {
                $proc = Start-Process -FilePath 'pwsh' -ArgumentList $argList -Wait -PassThru -NoNewWindow `
                    -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile
                return [pscustomobject]@{
                    ExitCode = $proc.ExitCode
                    StdOut   = (Get-Content -Raw -ErrorAction SilentlyContinue $stdoutFile)
                    StdErr   = (Get-Content -Raw -ErrorAction SilentlyContinue $stderrFile)
                    Args     = $ScriptArgs
                }
            }
            finally {
                Remove-Item -LiteralPath $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue
            }
        }
    }

    It "run_all_tests.ps1 <ScriptArgs> exits <ExpectedExitCode>" -ForEach $matrix {
        $result = Invoke-Runner -ScriptArgs $ScriptArgs

        if ($result.ExitCode -ne $ExpectedExitCode) {
            $tailOut = ($result.StdOut -split "`r?`n" | Select-Object -Last 40) -join "`n"
            $tailErr = ($result.StdErr -split "`r?`n" | Select-Object -Last 40) -join "`n"
            throw "ScriptArgs '$ScriptArgs' expected exit $ExpectedExitCode, got $($result.ExitCode).`nSTDOUT:`n$tailOut`nSTDERR:`n$tailErr"
        }

        $result.ExitCode | Should -Be $ExpectedExitCode
    }
}
