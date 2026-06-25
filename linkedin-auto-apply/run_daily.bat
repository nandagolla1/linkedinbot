@echo off
:: run_daily.bat — Run LinkedIn bot daily via Windows Task Scheduler
:: Set up Task Scheduler to call this file at your preferred time

SET PROJECT_DIR=C:\Users\maith\linkedin-auto-apply
SET VENV=%PROJECT_DIR%\.venv\Scripts\activate.bat
SET LOG=%PROJECT_DIR%\scheduler.log

echo [%date% %time%] Starting LinkedIn Auto-Apply Bot >> %LOG%

cd /d %PROJECT_DIR%
call %VENV%
python main.py >> %LOG% 2>&1

echo [%date% %time%] Bot finished >> %LOG%
