@echo off
title Shubham's JobHunt - Test Run (No Email)
cd /d "%~dp0"
call .\.venv\Scripts\activate.bat
echo Starting Shubham's test run (dry run, cap 10 candidates)...
python -m jobhunt run --limit 10
if exist out\digest.html (
    echo Opening generated digest in your default browser...
    start "" out\digest.html
)
echo.
pause
