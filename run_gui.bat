@echo off
title Shubham's JobHunt - Local Dashboard GUI
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
echo Starting Shubham's JobHunt Executive GUI Dashboard...
echo Opening in your browser at http://localhost:8080 ...
python gui/server.py
pause
