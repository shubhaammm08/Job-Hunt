@echo off
title Shubham's JobHunt - Daily Pipeline
cd /d "%~dp0"

echo ========================================================
echo   Starting Shubham's Daily JobHunt Pipeline
echo   (Naukri + LinkedIn + ATS + Remote Boards)
echo ========================================================
echo.

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -m jobhunt run

echo.
echo ========================================================
echo   Pipeline Completed!
echo   Dashboard updated at: index.html
echo   Live GUI available at: http://localhost:8080
echo ========================================================
echo.
pause
