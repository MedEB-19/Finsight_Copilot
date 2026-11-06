@echo off
REM Registers a daily task at 22:30 local time (after US market close in Europe/Morocco time zones).
schtasks /Create /SC DAILY /ST 22:30 /TN "FinSightDailyRefresh" /TR "\"%~dp0daily_refresh.bat\"" /F
