@echo off
REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%;%SCRIPT_DIR%.."
cd /d "%SCRIPT_DIR%"
python "plugins\browser_extension.py" %*
