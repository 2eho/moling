@echo off
REM =============================================================================
REM Moling 部署脚本（Windows）
REM =============================================================================
REM 功能:
REM   1. 检查系统依赖
REM   2. 加载环境变量
REM   3. 构建 Docker 镜像
REM   4. 运行数据库迁移
REM   5. 启动服务
REM   6. 健康检查
REM
REM 使用方法:
REM   deploy.bat              - 默认部署
REM   deploy.bat --rollback   - 回滚到上一个版本
REM   deploy.bat --clean      - 清理所有数据并重新部署
REM =============================================================================

setlocal enabledelayedexpansion

REM 配置变量
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set BACKEND_DIR=%PROJECT_ROOT%\moling-server
set DOCKER_DIR=%PROJECT_ROOT%\docker
set COMPOSE_FILE=%DOCKER_DIR%\docker-compose.yml
set ENV_FILE=%BACKEND_DIR%\.env

REM 颜色代码（Windows 10+）
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "NC=[0m"

REM =============================================================================
REM 辅助函数
REM =============================================================================

REM 打印信息
:log_info
echo %GREEN%[INFO]%NC% %~1
goto :eof

REM 打印警告
:log_warn
echo %YELLOW%[WARN]%NC% %~1
goto :eof

REM 打印错误
:log_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM 打印步骤
:log_step
echo.
echo %YELLOW%========================================%NC%
echo %YELLOW%  %~1%NC%
echo %YELLOW%========================================%NC%
goto :eof

REM =============================================================================
REM 主流程
REM =============================================================================

call :log_step "Moling 部署脚本 (Windows)"

REM 检查 Docker
call :log_info "检查 Docker..."
docker --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Docker 未安装或未启动"
    exit /b 1
)

REM 检查 .env 文件
if not exist "%ENV_FILE%" (
    call :log_warn ".env 文件不存在，从 .env.example 复制"
    copy "%BACKEND_DIR%\.env.example" "%ENV_FILE%"
    call :log_warn "请编辑 %ENV_FILE% 并填写正确的配置，然后重新运行此脚本"
    exit /b 1
)

REM 解析命令行参数
if "%~1"=="" goto :deploy
if "%~1"=="--rollback" goto :rollback
if "%~1"=="--clean" goto :clean

goto :deploy

REM =============================================================================
REM 部署
REM =============================================================================

:deploy
call :log_step "开始部署"

REM 构建镜像
call :log_info "构建 Docker 镜像..."
cd /d "%DOCKER_DIR%"
docker-compose build

REM 运行数据库迁移
call :log_info "运行数据库迁移..."
docker-compose run --rm app alembic upgrade head

REM 启动服务
call :log_info "启动服务..."
docker-compose down
docker-compose up -d

REM 验证部署
call :log_info "验证部署..."
timeout /t 10 /nobreak >nul
curl -f http://localhost:80/health >nul 2>&1
if errorlevel 1 (
    call :log_error "部署验证失败"
    goto :eof
)

call :log_info "部署成功！"
call :log_info "前端访问地址: http://localhost"
call :log_info "API 文档地址: http://localhost/api/v1/docs"
goto :eof

REM =============================================================================
REM 回滚
REM =============================================================================

:rollback
call :log_step "回滚到上一个版本"
call :log_warn "回滚功能需要手动操作（git checkout 到上一个版本）"
goto :eof

REM =============================================================================
REM 清理
REM =============================================================================

:clean
call :log_step "清理部署"
set /p confirm="确认清理所有数据？(y/N): "
if /i "%confirm%"=="y" (
    cd /d "%DOCKER_DIR%"
    docker-compose down -v
    docker-compose down --rmi all
    call :log_info "清理完成"
) else (
    call :log_info "取消清理"
)
goto :eof

REM =============================================================================
REM 脚本结束
REM =============================================================================

:end
endlocal
