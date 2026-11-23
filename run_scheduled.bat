@echo off
cd /d "C:\Users\admin\Desktop\Hunt\PWP_jobhunt"
if not exist out mkdir out
echo ======================================================== >> "out\scheduler.log"
echo [%date% %time%] Starting Shubham's daily JobHunt run... >> "out\scheduler.log"
if exist .venv\Scripts\python.exe (
    call .venv\Scripts\python.exe -m jobhunt run >> "out\scheduler.log" 2>&1
) else (
    call python -m jobhunt run >> "out\scheduler.log" 2>&1
)
echo [%date% %time%] Shubham's JobHunt run finished with exit code %ERRORLEVEL% >> "out\scheduler.log"
echo ======================================================== >> "out\scheduler.log"
