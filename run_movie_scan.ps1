param()
$target = Join-Path $PSScriptRoot "scripts\run_movie_scan.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $target @args
exit $LASTEXITCODE
