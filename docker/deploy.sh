#!/bin/bash
# ==============================================================================
# Moling 部署脚本（Linux）
# ==============================================================================
# 功能:
#   1. 检查系统依赖
#   2. 加载环境变量
#   3. 构建 Docker 镜像
#   4. 运行数据库迁移
#   5. 启动服务
#   6. 健康检查
#   7. 失败回滚
#
# 使用方法:
#   ./deploy.sh              # 默认部署
#   ./deploy.sh --rollback   # 回滚到上一个版本
#   ./deploy.sh --clean      # 清理所有数据并重新部署
# ==============================================================================

set -e  # 遇到错误立即退出

# ==============================================================================
# 配置变量
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/moling-server"
DOCKER_DIR="$PROJECT_ROOT/docker"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"
ENV_FILE="$BACKEND_DIR/.env"
BACKUP_DIR="$DOCKER_DIR/backups"
LOG_FILE="$DOCKER_DIR/deploy.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==============================================================================
# 辅助函数
# ==============================================================================

# 打印信息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "[INFO] $1" >> "$LOG_FILE"
}

# 打印警告
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "[WARN] $1" >> "$LOG_FILE"
}

# 打印错误
log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "[ERROR] $1" >> "$LOG_FILE"
}

# 打印步骤
log_step() {
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo "" >> "$LOG_FILE"
    echo "=== $1 ===" >> "$LOG_FILE"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 '$1' 未找到，请先安装"
        exit 1
    fi
}

# 检查服务健康状态
check_health() {
    local max_retries=30
    local retry=0
    
    log_info "等待服务启动..."
    
    while [ $retry -lt $max_retries ]; do
        if curl -f http://localhost:80/health &> /dev/null; then
            log_info "服务健康检查通过"
            return 0
        fi
        
        retry=$((retry + 1))
        echo -n "."
        sleep 2
    done
    
    log_error "服务健康检查失败"
    return 1
}

# ==============================================================================
# 部署函数
# ==============================================================================

# 检查系统依赖
check_dependencies() {
    log_step "检查系统依赖"
    
    check_command "docker"
    check_command "docker-compose"
    check_command "curl"
    
    # 检查 Docker 服务是否运行
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请启动 Docker"
        exit 1
    fi
    
    log_info "系统依赖检查通过"
}

# 加载环境变量
load_env() {
    log_step "加载环境变量"
    
    if [ ! -f "$ENV_FILE" ]; then
        log_warn ".env 文件不存在，从 .env.example 复制"
        cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
        log_warn "请编辑 $ENV_FILE 并填写正确的配置，然后重新运行此脚本"
        exit 1
    fi
    
    # 读取环境变量（排除注释和空行）
    export $(grep -v '^#' "$ENV_FILE" | grep -v '^$' | xargs)
    
    log_info "环境变量加载成功"
}

# 备份数据库
backup_database() {
    log_step "备份数据库"
    
    mkdir -p "$BACKUP_DIR"
    local backup_file="$BACKUP_DIR/moling_db_$(date +%Y%m%d_%H%M%S).sql"
    
    log_info "备份数据库到 $backup_file"
    
    # 使用 docker-compose 执行备份
    docker-compose -f "$COMPOSE_FILE" exec -T db \
        pg_dump -U ${POSTGRES_USER:-moling} ${POSTGRES_DB:-moling} > "$backup_file" || {
        log_warn "数据库备份失败，继续执行..."
    }
    
    log_info "数据库备份完成"
}

# 构建镜像
build_images() {
    log_step "构建 Docker 镜像"
    
    cd "$DOCKER_DIR"
    
    log_info "构建前端镜像..."
    docker-compose build frontend
    
    log_info "构建后端镜像..."
    docker-compose build app
    
    log_info "构建 Worker 镜像..."
    docker-compose build worker
    
    log_info "镜像构建完成"
}

# 运行数据库迁移
run_migrations() {
    log_step "运行数据库迁移"
    
    cd "$DOCKER_DIR"
    
    # 确保数据库服务运行
    docker-compose up -d db
    sleep 5
    
    # 运行 Alembic 迁移
    log_info "运行 Alembic 迁移..."
    docker-compose run --rm app alembic upgrade head
    
    log_info "数据库迁移完成"
}

# 启动服务
start_services() {
    log_step "启动服务"
    
    cd "$DOCKER_DIR"
    
    # 停止旧服务
    log_info "停止旧服务..."
    docker-compose down || true
    
    # 启动新服务
    log_info "启动新服务..."
    docker-compose up -d
    
    log_info "服务启动完成"
}

# 验证部署
verify_deployment() {
    log_step "验证部署"
    
    # 检查服务状态
    log_info "检查服务状态..."
    docker-compose -f "$COMPOSE_FILE" ps
    
    # 健康检查
    if check_health; then
        log_info "部署成功！"
        log_info "前端访问地址: http://localhost"
        log_info "API 文档地址: http://localhost/api/v1/docs"
    else
        log_error "部署验证失败"
        rollback
        exit 1
    fi
}

# 回滚
rollback() {
    log_step "回滚到上一个版本"
    
    cd "$DOCKER_DIR"
    
    # 获取上一个备份
    local latest_backup=$(ls -t "$BACKUP_DIR"/moling_db_*.sql 2>/dev/null | head -1)
    
    if [ -n "$latest_backup" ]; then
        log_info "恢复数据库备份: $latest_backup"
        docker-compose exec -T db psql -U ${POSTGRES_USER:-moling} ${POSTGRES_DB:-moling} < "$latest_backup"
    else
        log_warn "未找到数据库备份，跳过数据库恢复"
    fi
    
    # 重启服务到上一个版本（需要版本标签支持）
    log_warn "代码回滚需要手动操作（git checkout 到上一个版本）"
    
    log_info "回滚完成"
}

# 清理
clean_deployment() {
    log_step "清理部署"
    
    cd "$DOCKER_DIR"
    
    # 停止并删除容器
    docker-compose down -v
    
    # 删除镜像
    docker-compose down --rmi all
    
    # 清理 volumes
    docker volume prune -f
    
    log_info "清理完成"
}

# ==============================================================================
# 主函数
# ==============================================================================

main() {
    # 创建日志文件
    mkdir -p "$DOCKER_DIR"
    touch "$LOG_FILE"
    
    log_step "Moling 部署脚本"
    log_info "项目目录: $PROJECT_ROOT"
    log_info "日志文件: $LOG_FILE"
    
    # 解析命令行参数
    case "${1:-}" in
        --rollback)
            check_dependencies
            rollback
            exit 0
            ;;
        --clean)
            log_warn "即将清理所有数据，确认继续？(y/N)"
            read -r confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                clean_deployment
            else
                log_info "取消清理"
            fi
            exit 0
            ;;
        "")
            # 默认部署流程
            check_dependencies
            load_env
            backup_database
            build_images
            run_migrations
            start_services
            verify_deployment
            ;;
        *)
            echo "使用方法: $0 [选项]"
            echo "  无参数    - 默认部署"
            echo "  --rollback - 回滚到上一个版本"
            echo "  --clean    - 清理所有数据并重新部署"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
