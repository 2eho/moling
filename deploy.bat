@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM =============================================================================
REM 墨灵一键部署脚本 (Windows)
REM =============================================================================
REM 用法:
REM   1. 编辑项目根目录 .env 文件填入服务器 IP / 域名
REM   2. 双击 deploy.bat
REM =============================================================================

echo ==========================================
echo  墨灵 (Moling) 一键部署
echo ==========================================

REM 1. 检查 .env 是否存在
if not exist .env (
    echo [ERROR] 根目录 .env 文件不存在！
    echo   SERVER_IP=你的服务器IP
    echo   FRONTEND_URL=http://你的服务器IP:8080
    echo   BACKEND_API_URL=http://你的服务器IP:8000/api/v1
    pause
    exit /b 1
)

REM 2. 检查是否还是占位值
findstr "YOUR_SERVER_IP" .env >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] .env 中仍有占位符 YOUR_SERVER_IP
    echo  请替换为实际 IP 或域名后再运行！
    pause
    exit /b 1
)

echo [1/3] 构建并启动所有服务...
docker compose up -d --build

echo [2/3] 等待服务就绪...
timeout /t 15 /nobreak >nul

echo [3/3] 部署完成！
echo.
echo ==========================================
echo  部署完成！
echo ==========================================
echo  日志查看:   docker compose logs -f
echo  重新部署:   deploy.bat
echo  停止服务:   docker compose down
echo ==========================================

pause
