@echo off
REM Starts API + UI in two windows (after Docker SQL Server and Ollama are running).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
start "FinSight API" cmd /k python -m uvicorn finsight.api.main:app --port 8000
start "FinSight UI" cmd /k python -m streamlit run ui\app.py
