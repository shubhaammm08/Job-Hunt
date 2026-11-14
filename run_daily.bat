@echo off
title Shubham's JobHunt - Daily Automated Run
cd /d "%~dp0"
call .\.venv\Scripts\activate.bat
echo Starting Shubham's daily JobHunt pipeline...
python -m jobhunt run --send
if exist out\digest.html (
    echo Opening generated digest in your default browser...
    start "" out\digest.html
)
echo.
echo Completed!
pause
