@echo off
cd /d "C:\Users\admin\Desktop\Hunt\PWP_jobhunt"
if not exist out mkdir out
call .venv\Scripts\python.exe mail_summarizer.py >> "out\mail_summary.log" 2>&1
