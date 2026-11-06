@echo off
REM Daily price refresh (Station 2 automation). Schedule with Windows Task Scheduler.
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python -m finsight.cli refresh >> data\refresh.log 2>&1
