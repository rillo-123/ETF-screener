@echo off
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%"

echo [NIGHTLY] Starting refresh at %DATE% %TIME%
echo [NIGHTLY] Activating Virtual Environment...
call .venv\Scripts\activate.bat

echo [NIGHTLY] Running Database Refresh...
set PYTHONPATH=src
python -m ETF_screener.main refresh --depth 730

echo [NIGHTLY] Refresh Complete!
deactivate
pause