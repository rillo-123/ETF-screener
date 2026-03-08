@echo off
REM ETF Screener Auto-Refresh Launcher
REM Place this file or a shortcut to it in: C:\Users\carlr\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup

cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -NoProfile -File "auto-refresh.ps1"
