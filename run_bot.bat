@echo off
title JobHunt Telegram Bot Assistant
echo ========================================================
echo  JobHunt AI Telegram Command Center (@ShubhamJobHunt_Bot)
echo ========================================================
echo.
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Starting Telegram Bot listener...
echo Press Ctrl+C at any time to stop.
echo.

:loop
"%PYTHON_EXE%" -m jobhunt bot
echo.
echo Bot stopped or disconnected. Reconnecting in 5 seconds...
timeout /t 5 >nul
goto loop
