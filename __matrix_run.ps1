$tests = @(
  '-Help',
  '',
  '-Parallel',
  '-RandomOrder',
  '-TimeoutSec 120',
  '-QualityGate',
  '-Ruff',
  '-Mypy',
  '-Coverage',
  '-Vulture',
  '-Black',
  '-Bandit',
  '-All',
  '-QualityGate -Parallel -RandomOrder -TimeoutSec 120 -LogRetentionDays 30 -LogRetentionMaxFiles 500'
)

$rows = @()
$fails = @()
foreach ($args in $tests) {
  $cmd = if ([string]::IsNullOrWhiteSpace($args)) { '.\\run_all_tests.ps1' } else { ".\\run_all_tests.ps1 $args" }
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $out = & pwsh -NoProfile -File .\run_all_tests.ps1 @($args -split ' ') 2>&1 | Out-String
  $code = $LASTEXITCODE
  $sw.Stop()

  $rows += [pscustomobject]@{
    Args = $args
    ExitCode = $code
    Seconds = [math]::Round($sw.Elapsed.TotalSeconds,2)
    Status = if ($code -eq 0) { 'PASS' } else { 'FAIL' }
  }

  if ($code -ne 0) {
    $fails += [pscustomobject]@{ Args = $args; Output = (($out -split "`r?`n") | Select-Object -Last 30) -join "`n" }
  }
}

$rows | Format-Table -AutoSize | Out-String -Width 500 | Write-Host
if ($fails.Count -gt 0) {
  foreach ($f in $fails) {
    Write-Host "`n==== FAIL OUTPUT: $($f.Args) ===="
    Write-Host $f.Output
  }
}

Write-Host "`nNewest logs:"
Get-ChildItem .\logs -File -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime | Format-Table -AutoSize | Out-String -Width 300 | Write-Host
