@echo off
echo ===================================================
echo      Brainrot Director - Build System
echo ===================================================

echo [1/3] Configuring Environment...
python -m pip install "pip<24.1"
if %errorlevel% neq 0 (
    echo ⚠️ Could not downgrade pip, proceeding anyway...
)

echo.
echo [2/3] Installing Requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ❌ Error installing requirements.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Building Executable...
python build_exe.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Error building executable.
    pause
    exit /b %errorlevel%
)

echo.
echo ===================================================
echo      ✅ BUILD SUCCESSFUL!
echo      Check 'dist/BrainrotDirector.exe'
echo ===================================================
pause
