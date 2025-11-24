@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

echo ========================================
echo   ZhiPi - Start Script
echo ========================================
echo.

REM ==================== Check Python ====================

echo [1/5] Checking Python...

REM Try python command first
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_found
)

REM Try py launcher
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_found
)

REM Try python3
python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto :python_found
)

REM Try common installation paths
set PYTHON_PATHS=^
%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe;^
%LOCALAPPDATA%\Python\pythoncore-3.13-64\python.exe;^
%LOCALAPPDATA%\Python\pythoncore-3.12-64\python.exe;^
%LOCALAPPDATA%\Python\pythoncore-3.11-64\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python314\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python313\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python312\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python311\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python310\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python39\python.exe;^
%LOCALAPPDATA%\Programs\Python\Python38\python.exe;^
C:\Python314\python.exe;^
C:\Python313\python.exe;^
C:\Python312\python.exe;^
C:\Python311\python.exe;^
C:\Python310\python.exe;^
C:\Python39\python.exe;^
C:\Python38\python.exe

for %%p in (%PYTHON_PATHS%) do (
    if exist "%%p" (
        set PYTHON_CMD=%%p
        goto :python_found
    )
)

echo [ERROR] Python not found
echo.
echo Please install Python 3.8+ from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: Check "Add Python to PATH" during installation
echo.
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('"%PYTHON_CMD%" --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python: %PYTHON_VERSION%
echo Command: %PYTHON_CMD%

REM ==================== Virtual Environment ====================

echo.
echo [2/5] Checking virtual environment...
if not exist "venv\" (
    echo Creating virtual environment...
    "%PYTHON_CMD%" -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created
) else (
    echo Virtual environment exists
)

REM Activate virtual environment
echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM ==================== Dependencies ====================

echo.
echo [4/5] Checking dependencies...

python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    echo Using Aliyun mirror...
    python -m pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
    if errorlevel 1 (
        echo [WARNING] Aliyun mirror failed, trying Tencent mirror...
        python -m pip install --no-cache-dir -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple --trusted-host mirrors.cloud.tencent.com
        if errorlevel 1 (
            echo [WARNING] Tencent mirror failed, trying Tsinghua mirror...
            python -m pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
            if errorlevel 1 (
                echo [ERROR] Failed to install dependencies
                echo.
                echo Possible reasons:
                echo   1. Network issues
                echo   2. Some packages may not support Python 3.13 yet
                echo.
                echo Try installing Python 3.11 or 3.12 instead
                pause
                exit /b 1
            )
        )
    )
    echo Dependencies installed successfully
) else (
    echo Dependencies already installed
)

REM ==================== Config File ====================

echo.
echo [5/5] Checking config file...
if not exist ".env" (
    echo [WARNING] .env file not found
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy .env.example .env >nul
        echo.
        echo [IMPORTANT] Please edit .env file and add your API key
        echo File location: %cd%\.env
        echo.
        echo Press any key to open editor...
        pause >nul
        notepad .env
        echo.
        echo Please restart this script after configuration
        exit /b 0
    ) else (
        echo [ERROR] .env.example not found
        pause
        exit /b 1
    )
) else (
    echo Config file exists
)

REM ==================== Start Service ====================

echo.
echo ========================================
echo   Starting service...
echo ========================================
echo.

REM Check if port 8000 is already in use
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Port 8000 is already in use
    echo Please run scripts\stop.bat first
    echo.
    pause
    exit /b 0
)

echo Service will start in foreground mode
echo Press Ctrl+C to stop the service
echo.
echo ========================================
echo   URL: http://localhost:8000/static/pc.html
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.

REM Open browser after 2 seconds delay
start /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000/static/pc.html"

REM Run service in foreground (so errors are visible)
python main.py
