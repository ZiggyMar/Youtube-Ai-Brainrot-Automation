@echo off
echo ===================================================
echo      TEST SCRIPT GENERATOR (Testing Mode)
echo ===================================================
echo.
echo Generating 5 new scripts using strict logic...
echo.

python core/director.py

echo.
echo ===================================================
echo      Generation Complete. Check video_scripts.json
echo ===================================================
pause
