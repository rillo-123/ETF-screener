param()
$target = Join-Path $PSScriptRoot "scripts\run_discovery.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
