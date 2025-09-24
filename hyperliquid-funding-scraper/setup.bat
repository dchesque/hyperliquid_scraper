@echo off
title Hyperliquid Scraper - Setup
color 0B

echo ============================================================
echo   Hyperliquid Funding Rate Scraper - Setup Utility
echo   Automated environment setup and configuration
echo ============================================================
echo.

echo [INFO] Starting automated setup...
echo [INFO] This will install all dependencies and configure the environment.
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo [INFO] Please install Python 3.10+ from https://python.org
    echo [INFO] Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [INFO] Python found. Running setup script...
echo.

REM Run the Python setup script
python setup.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] Setup completed successfully!
    echo ============================================================
    echo.
    echo Next steps:
    echo 1. Edit .env file with your Supabase credentials
    echo 2. Run database migrations if needed
    echo 3. Start the scraper with run.bat
    echo.
    echo [INFO] Press any key to open the main application...
    pause >nul
    call run.bat
) else (
    echo.
    echo ============================================================
    echo [ERROR] Setup failed!
    echo ============================================================
    echo.
    echo Please check the error messages above and:
    echo 1. Ensure you have Python 3.10+ installed
    echo 2. Check your internet connection
    echo 3. Verify you have write permissions in this directory
    echo.
    pause
    exit /b 1
)