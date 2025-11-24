@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo ========================================
echo   ZhiPi - Stop Script
echo ========================================
echo.

echo Searching for service process...

REM Find process by port 8000
set FOUND=0
set FAILED=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    echo Found process on port 8000: PID %%a
    taskkill /pid %%a /f >nul 2>&1
    if errorlevel 1 (
        set FAILED=1
        set FAILED_PID=%%a
    ) else (
        echo Process %%a terminated
        set FOUND=1
    )
)

if "!FAILED!"=="1" (
    echo.
    echo [ERROR] Failed to terminate process !FAILED_PID!
    echo.
    echo Please try one of these solutions:
    echo   1. Run this script as Administrator
    echo   2. Open Task Manager, find PID !FAILED_PID!, and end it manually
    echo   3. Run in CMD as Admin: taskkill /pid !FAILED_PID! /f
    echo.
    pause
    exit /b 1
)

if "!FOUND!"=="0" (
    echo [INFO] No running service found on port 8000
)

echo.
echo ========================================
echo   Service stopped
echo ========================================
echo.
pause
