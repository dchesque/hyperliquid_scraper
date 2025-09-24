@echo off
title Hyperliquid Funding Rate Scraper
color 0F

echo ============================================================
echo   Hyperliquid Funding Rate Scraper v2.0
echo   Professional cryptocurrency funding rate collector
echo ============================================================
echo.

REM Check for administrator privileges for better error handling
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo WARNING: Not running as administrator. Some features may be limited.
    echo.
)

REM Environment checks
echo [INFO] Checking environment...

if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo [INFO] Please run: python setup.py
    echo.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARNING] Environment file (.env) not found!
    echo [INFO] Using .env.example as template...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul 2>&1
        echo [INFO] Created .env file. Please configure your Supabase credentials.
    ) else (
        echo [ERROR] No .env.example found. Please configure environment manually.
    )
    echo.
)

if not exist "chromedriver.exe" (
    echo [WARNING] ChromeDriver not found!
    echo [INFO] The scraper will try to download it automatically.
    echo.
)

REM Create directories if they don't exist
if not exist "logs" mkdir logs >nul 2>&1
if not exist "exports" mkdir exports >nul 2>&1
if not exist "screenshots" mkdir screenshots >nul 2>&1

echo [INFO] Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)

echo [INFO] Environment ready!
echo.

:menu
echo ============================================================
echo                     MAIN MENU
echo ============================================================
echo.
echo  1. Test Database Connection         [Quick connectivity test]
echo  2. Run Scraping Once               [Single scraping run]
echo  3. Run Continuous Daemon           [Background scheduler]
echo  4. Show Arbitrage Opportunities    [Latest arbitrage data]
echo  5. Show Statistics                 [Database statistics]
echo  6. Export Data to CSV              [Data export tool]
echo  7. Run Database Migrations         [Setup/update database]
echo  8. View Recent Logs                [Check scraper logs]
echo  9. Configure Auto Schedule         [Setup automatic execution]
echo  A. Quick Setup Check               [Verify installation]
echo  0. Exit                           [Close application]
echo.
echo ============================================================

set /p choice="[INPUT] Select option (0-9,A): "

if "%choice%"=="1" goto test_connection
if "%choice%"=="2" goto run_once
if "%choice%"=="3" goto run_daemon
if "%choice%"=="4" goto show_arbitrage
if "%choice%"=="5" goto show_stats
if "%choice%"=="6" goto export_csv
if "%choice%"=="7" goto run_migrations
if "%choice%"=="8" goto view_logs
if "%choice%"=="9" goto configure_schedule
if /i "%choice%"=="A" goto setup_check
if "%choice%"=="0" goto exit
goto invalid_option

:test_connection
echo.
echo [INFO] Testing database connection...
python -m src.main --test-connection
echo.
pause
goto menu

:run_once
echo.
echo [INFO] Starting single scraping run...
echo [INFO] This will collect data from all available cryptocurrencies.
python -m src.main --run-once
echo.
echo [INFO] Scraping completed. Check logs/ directory for details.
pause
goto menu

:run_daemon
echo.
echo [INFO] Starting continuous daemon mode...
echo [WARNING] This will run indefinitely. Press Ctrl+C to stop.
echo.
pause
python -m src.main --daemon
echo.
echo [INFO] Daemon stopped.
pause
goto menu

:show_arbitrage
echo.
echo [INFO] Showing arbitrage opportunities...
python -m src.main --arbitrage
echo.
pause
goto menu

:show_stats
echo.
echo [INFO] Showing database statistics...
python -m src.main --stats
echo.
pause
goto menu

:export_csv
echo.
echo [INFO] Data export utility
echo [INFO] Available formats: CSV, JSON, Excel
echo.
set /p format="[INPUT] Enter format (csv/json/excel) [csv]: "
if "%format%"=="" set format=csv

set /p filename="[INPUT] Enter filename (without extension) [funding_data]: "
if "%filename%"=="" set filename=funding_data

set /p days="[INPUT] Export last N days (1-365) [7]: "
if "%days%"=="" set days=7

echo.
echo [INFO] Exporting %days% days of data in %format% format...
python -m src.main --export-%format% "exports\%filename%.%format%" --days %days%
echo.
echo [INFO] Export completed. Check exports/ directory.
pause
goto menu

:run_migrations
echo.
echo [INFO] Running database migrations...
echo [WARNING] This will modify your database structure.
set /p confirm="[INPUT] Continue? (y/n) [y]: "
if "%confirm%"=="" set confirm=y
if /i "%confirm%"=="y" (
    python migrations\migrate.py
) else (
    echo [INFO] Migration cancelled.
)
echo.
pause
goto menu

:view_logs
echo.
echo [INFO] Recent scraper logs:
echo ============================================================
if exist "logs\scraper.log" (
    powershell "Get-Content 'logs\scraper.log' -Tail 20"
) else (
    echo [INFO] No logs found. Run the scraper first.
)
echo ============================================================
echo.
pause
goto menu

:configure_schedule
echo.
echo [INFO] Opening schedule configuration...
call configure_schedule.bat
goto menu

:setup_check
echo.
echo [INFO] Performing setup verification...
echo ============================================================

REM Check Python
python --version 2>nul
if %errorlevel% equ 0 (
    echo [OK] Python is available
) else (
    echo [ERROR] Python not found
)

REM Check ChromeDriver
if exist "chromedriver.exe" (
    echo [OK] ChromeDriver found
    chromedriver.exe --version 2>nul
) else (
    echo [WARNING] ChromeDriver not found
)

REM Check environment file
if exist ".env" (
    echo [OK] Environment file exists
    findstr /C:"your_supabase_url_here" .env >nul 2>&1
    if %errorlevel% equ 0 (
        echo [WARNING] Environment file needs configuration
    ) else (
        echo [OK] Environment appears configured
    )
) else (
    echo [ERROR] Environment file missing
)

REM Check dependencies
echo [INFO] Checking key dependencies...
python -c "import selenium; print('[OK] Selenium available')" 2>nul || echo [WARNING] Selenium not available
python -c "import supabase; print('[OK] Supabase available')" 2>nul || echo [WARNING] Supabase not available
python -c "import pandas; print('[OK] Pandas available')" 2>nul || echo [WARNING] Pandas not available

echo ============================================================
echo.
pause
goto menu

:invalid_option
echo.
echo [ERROR] Invalid option! Please select 0-9.
echo.
timeout /t 2 >nul
goto menu

:exit
echo.
echo [INFO] Shutting down Hyperliquid Scraper...
echo [INFO] Thank you for using our funding rate collector!
echo.
timeout /t 2 >nul
exit /b 0