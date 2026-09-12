@echo off
setlocal
title AgriSense Server

:: ============================================================
:: AGRISENSE SERVER LAUNCHER
:: ============================================================

cd /d C:\Users\karti\agrisense

:: ============================================================
:: REQUEST ADMINISTRATOR PRIVILEGES
:: ============================================================

net session >nul 2>&1

if %errorlevel% neq 0 (
    echo.
    echo Requesting Administrator privileges...
    echo.

    powershell -Command "Start-Process '%~f0' -Verb RunAs"

    exit /b
)

:: ============================================================
:: HEADER
:: ============================================================

cls

echo ============================================================
echo                    AGRISENSE SERVER
echo ============================================================
echo.
echo Project: C:\Users\karti\agrisense
echo Public URL: https://admin.tail4fe027.ts.net
echo.

:: ============================================================
:: STEP 1 - TAILSCALE SERVICE
:: ============================================================

echo [1/3] Checking Tailscale Windows service...
echo.

sc query Tailscale | findstr /I "RUNNING" >nul

if %errorlevel% neq 0 (

    echo Tailscale service is NOT running.
    echo Starting Tailscale service...
    echo.

    net start Tailscale

    if %errorlevel% neq 0 (
        echo.
        echo ====================================================
        echo ERROR: Could not start Tailscale.
        echo ====================================================
        echo.
        echo Please check that Tailscale is installed correctly.
        echo.
        pause
        exit /b 1
    )

    echo.
    echo Tailscale service started successfully.
    echo Waiting for Tailscale to initialize...
    timeout /t 8 /nobreak >nul

) else (

    echo Tailscale service is already running.
)

echo.

:: ============================================================
:: STEP 2 - VERIFY TAILSCALE
:: ============================================================

echo [2/3] Verifying Tailscale connection...
echo.

set "TAILSCALE_OK=0"

for /L %%i in (1,1,5) do (

    tailscale status >nul 2>&1

    if %errorlevel% equ 0 (
        set "TAILSCALE_OK=1"
        goto TAILSCALE_READY
    )

    echo Waiting for Tailscale...
    timeout /t 3 /nobreak >nul
)

:TAILSCALE_READY

tailscale status

echo.

:: ============================================================
:: STEP 3 - BACKEND
:: ============================================================

echo [3/3] Checking AgriSense backend...
echo.

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul

if not %errorlevel% equ 0 (

    echo Backend is NOT running.
    echo.
    echo Starting AgriSense FastAPI backend...
    echo.

    echo ========================================================
    echo                    AGRISENSE ONLINE
    echo ========================================================
    echo.
    echo Public URL:
    echo https://admin.tail4fe027.ts.net
    echo.
    echo Local URL:
    echo http://127.0.0.1:8000
    echo.
    echo ========================================================
    echo.

    python app/run_app.py

    echo.
    echo ========================================================
    echo             AgriSense backend stopped
    echo ========================================================
    echo.

    pause
    exit /b
)

:: ============================================================
:: BACKEND ALREADY RUNNING
:: ============================================================

echo Backend is already running on port 8000.
echo.

echo ========================================================
echo                    AGRISENSE ONLINE
echo ========================================================
echo.
echo Public URL:
echo https://admin.tail4fe027.ts.net
echo.
echo Local URL:
echo http://127.0.0.1:8000
echo.
echo ========================================================
echo.

pause