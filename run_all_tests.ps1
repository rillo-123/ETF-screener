param()
$target = Join-Path $PSScriptRoot "scripts\run_all_tests.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
