@echo off
REM Launch the Hermes Window Monitor without a console window.
REM Falls back to python.exe if pythonw is unavailable.
start "" pythonw "%~dp0hermes_monitor.py"
if errorlevel 1 start "" python "%~dp0hermes_monitor.py"
