@echo off
setlocal enabledelayedexpansion
title AgriSense Automated Laptop Setup & Release Builder
color 0B
cls

echo ================================================================================
echo  AGRISENSE AUTOMATED LAPTOP SETUP & APK BUILDER
echo ================================================================================
echo  This script will:
echo   1. Clone / Pull the latest AgriSense repository code from GitHub.
echo   2. Install all Python dependencies from requirements.txt.
echo   3. Detect Tailscale / Tailnet network addresses.
echo   4. Build an updated AgriSense v1.7.1 release APK.
echo   5. Output the exact directory location of the compiled APK.
echo   6. Provide an option to run the backend server with live logs.
echo ================================================================================
echo.

cd /d "%~dp0"

REM 1. Clone or Pull Repo
echo [1/5] Syncing code repository...
if exist ".git" (
    echo [GIT] Existing repository detected. Pulling latest code...
    git pull origin main
) else (
    echo [GIT] Cloning AgriSense repository from GitHub...
    git clone https://github.com/Akash-3/agrisense.git .
)
echo.

REM 2. Install Python Requirements
echo [2/5] Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.

REM 3. Check / Install Tailscale (Tailnet)
echo [3/5] Checking Tailscale (Tailnet) connection...
where tailscale >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [TAILSCALE] Tailscale CLI detected.
    tailscale status
) else (
    echo [TAILSCALE WARNING] Tailscale is not installed on this system.
    echo Attempting automatic installation via winget...
    winget install Tailscale.Tailscale --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo [TAILSCALE] Tailscale successfully installed via winget!
    ) else (
        echo [TAILSCALE NOTICE] If you use Tailnet, please download Tailscale from https://tailscale.com/download
    )
)
echo.

REM 4. Build Release APK (v1.7.1)
echo [4/5] Building AgriSense v1.7.1 Release APK...
python build_release.py 1.7.1
echo.

REM 5. Display APK Output Folder Location
echo ================================================================================
echo  SETUP & BUILD COMPLETE!
echo ================================================================================
echo  📂 RELEASES FOLDER PATH:
echo     %USERPROFILE%\AgriSense_Builds
echo.
echo  📄 COMPILED APK LOCATION:
echo     %USERPROFILE%\AgriSense_Builds\AgriSense_v1.7.1.apk
echo ================================================================================
echo.

set /p launch_backend="Would you like to start the AgriSense Backend Server with live logs right now? (Y/N): "
if /i "%launch_backend%"=="Y" (
    echo Starting backend server in a new window...
    start "" "%~dp0run_backend.bat"
)

echo.
echo Done! Thank you for using AgriSense.
pause
