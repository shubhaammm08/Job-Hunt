@echo off
title Shubham's JobHunt - Naukri Session Auth
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python -m jobhunt naukri-auth
pause

