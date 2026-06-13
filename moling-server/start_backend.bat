@echo off
REM 墨灵后端自动重启脚本（保活）
REM 如果后端崩溃，3秒后自动重启

:loop
echo [%date% %time%] 启动后端...
cd /d C:\Users\Admin\Desktop\MolingProject\moling-server
set PYTHONPATH=C:\Users\Admin\Desktop\MolingProject\moling-server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a backend.log
echo [%date% %time%] 后端已停止，3秒后重启...
timeout /t 3 /nobreak > nul
goto loop
