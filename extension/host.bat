@echo off
REM Get the parent directory (spider_manager root)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"
python "plugins\browser_extension.py" %*
