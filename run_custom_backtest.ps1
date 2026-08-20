param()
$target = Join-Path $PSScriptRoot "scripts\run_custom_backtest.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
