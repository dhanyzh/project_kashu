@echo off
title PROJECT KASHI - Banking Management System
echo ====================================================================
echo                PROJECT KASHI - BANKING SYSTEM
echo       DBMS Course Project (3-Tier: HTML + Flask + MySQL)
echo ====================================================================
echo.

set PYTHON_CMD=C:\Users\DELL\anaconda3\python.exe

if not exist "%PYTHON_CMD%" (
    set PYTHON_CMD=python
)

echo [1/3] Checking Python environment...
"%PYTHON_CMD%" --version
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python or verify path.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Initializing and verifying MySQL Database (project_kashi)...
"%PYTHON_CMD%" database\setup_database.py
if %errorlevel% neq 0 (
    echo [WARNING] Database setup returned an issue. Please verify MySQL service.
)

echo.
echo [3/3] Launching Project Kashi Flask Web Application...
echo.
echo ====================================================================
echo * Application URL:  http://127.0.0.1:5000
echo * Press CTRL+C to stop the server
echo ====================================================================
echo.

"%PYTHON_CMD%" backend\app.py
pause
