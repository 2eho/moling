@echo off
echo 启动墨灵后端服务器...
cd /d "C:\Users\Admin\Desktop\新建文件夹 (2)\moling-server"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
