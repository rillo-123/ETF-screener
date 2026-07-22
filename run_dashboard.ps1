param()
$target = Join-Path $PSScriptRoot "scripts\run_dashboard.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
