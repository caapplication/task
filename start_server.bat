@echo off
echo Starting Task Management API Server...
echo.
cd /d "%~dp0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
pause

