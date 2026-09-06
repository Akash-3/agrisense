@echo off
title AgriSense Backend Server Logs
color 0A
cls
echo ================================================================================
echo  AGRISENSE BACKEND SERVER & REAL-TIME LOG MONITOR
echo ================================================================================
echo  Starting FastAPI Server on http://localhost:8000 ...
echo  Swagger API Documentation: http://localhost:8000/docs
echo  Press Ctrl+C at any time to gracefully stop the server.
echo ================================================================================
echo.

cd /d "%~dp0"
python -u app/run_app.py
pause
