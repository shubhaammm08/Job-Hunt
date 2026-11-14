@echo off
title Shubham's JobHunt - Reset Seen History
cd /d "%~dp0"
echo {} > seen.json
echo seen.json has been reset to empty. Shubham's next run will scan all matching jobs anew.
pause
