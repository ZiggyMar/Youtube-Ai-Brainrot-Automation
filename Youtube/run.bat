@echo off
title Brainrot Automation Pipeline
color 0A

echo ========================================================
echo       STARTING BRAINROT AUTOMATION PIPELINE
echo ========================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Run the Main Control Script
echo [INFO] Launching main.py...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Pipeline failed! Check the logs above.
    color 0C
    pause
    exit /b
)

echo.
echo ========================================================
echo          ALL TASKS COMPLETED SUCCESSFULLY
echo ========================================================
echo.
pause
