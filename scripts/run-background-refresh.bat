@echo off
setlocal

rem Launch the existing quiet refresh worker without keeping a console open.
set "PROJECT_ROOT=%~dp0..\"
set "REFRESH_SCRIPT=%PROJECT_ROOT%scripts\startup-refresh.ps1"

if not exist "%REFRESH_SCRIPT%" (
    echo Refresh script not found: "%REFRESH_SCRIPT%"
    exit /b 1
)

start "ETF Screener Refresh" /b powershell.exe ^
    -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden ^
    -File "%REFRESH_SCRIPT%"

echo Background refresh started.
echo Follow progress in logs\startup-refresh.log
exit /b 0
