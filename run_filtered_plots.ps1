param()
$target = Join-Path $PSScriptRoot "scripts\run_filtered_plots.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
