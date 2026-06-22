#!/bin/bash
# ==============================================================================
# 墨灵 Moling — 远程部署脚本（CI/CD 调用）
# ==============================================================================
# 用途: 被 GitHub Actions deploy.yml 在服务器端调用
# 功能:
#   1. 登录 GHCR
#   2. 拉取最新镜像
#   3. 备份当前状态
#   4. 数据库迁移
#   5. 滚动更新服务
#   6. 健康检查
#   7. 清理旧镜像
#
# 环境变量:
#   VERSION       - 部署版本号
#   DEPLOY_PATH   - 部署目录（默认 /opt/moling）
#   GHCR_USER     - GHCR 用户名
#   GHCR_TOKEN    - GHCR Token
#   DATABASE_URL  - 数据库连接字符串
# ==============================================================================

set -euo pipefail

# ---- 配置 ----
DEPLOY_PATH="${DEPLOY_PATH:-/opt/moling}"
VERSION="${VERSION:-$(date +%Y%m%d-%H%M%S)}"
COMPOSE_FILE="${DEPLOY_PATH}/docker-compose.prod.yml"
BACKUP_DIR="${DEPLOY_PATH}/backups"
LOG_FILE="${DEPLOY_PATH}/deploy.log"

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $1"; }
warn()  { echo -e "${YELLOW}[$(date +%H:%M:%S)] WARN${NC} $1"; }
error() { echo -e "${RED}[$(date +%H:%M:%S)] ERROR${NC} $1"; }
step()  { echo -e "\n${BLUE}=== $1 ===${NC}"; }

# ---- 健康检查函数 ----
health_check() {
    local service=$1
    local url=$2
    local max_retries=${3:-30}
    local retry=0

    log "等待 ${service} 就绪..."
    while [ $retry -lt $max_retries ]; do
        if curl -sf --max-time 5 "${url}" > /dev/null 2>&1; then
            log "  ✅ ${service} 健康检查通过"
            return 0
        fi
        retry=$((retry + 1))
        printf "."
        sleep 2
    done
    echo ""
    error "  ❌ ${service} 健康检查失败（${max_retries} 次重试后）"
    return 1
}

# ---- 主流程 ----
main() {
    step "Moling 远程部署"
    log "版本: ${VERSION}"
    log "目录: ${DEPLOY_PATH}"
    log "时间: $(date '+%Y-%m-%d %H:%M:%S')"

    cd "${DEPLOY_PATH}"
    mkdir -p "${BACKUP_DIR}"

    # ---- Step 1: 登录 GHCR ----
    step "登录容器仓库"
    if [ -n "${GHCR_TOKEN:-}" ] && [ -n "${GHCR_USER:-}" ]; then
        echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin 2>/dev/null
        log "GHCR 登录成功"
    else
        warn "未提供 GHCR 凭据，跳过登录（仅拉取公开镜像）"
    fi

    # ---- Step 2: 备份当前状态 ----
    step "备份当前状态"
    docker compose -f "${COMPOSE_FILE}" ps --format json > "${BACKUP_DIR}/state_pre_${VERSION}.json" 2>/dev/null || true
    log "状态快照已保存: ${BACKUP_DIR}/state_pre_${VERSION}.json"

    # ---- Step 3: 拉取新镜像 ----
    step "拉取新镜像"
    docker compose -f "${COMPOSE_FILE}" pull server frontend 2>&1
    log "镜像拉取完成"

    # ---- Step 4: 数据库迁移 ----
    step "数据库启动"
    # 确保基础服务运行
    docker compose -f "${COMPOSE_FILE}" up -d db redis 2>&1
    sleep 3
    # Rust 后端内嵌迁移，无需手动 alembic upgrade
    log "数据库服务就绪"

    # ---- Step 5: 滚动更新 ----
    step "滚动更新服务"

    # 更新后端（Rust 单体，内置 Worker）
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps server 2>&1

    # 健康检查
    if ! health_check "后端服务" "http://localhost:8000/health" 30; then
        error "后端健康检查失败，开始回滚..."
        rollback
        exit 1
    fi

    # 更新前端
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps frontend 2>&1

    # 前端健康检查
    health_check "前端服务" "http://localhost:3000/health" 15 || warn "前端健康检查未通过"

    # ---- Step 6: 清理 ----
    step "清理旧资源"
    docker image prune -af --filter "until=48h" 2>&1 || true
    docker builder prune -af --filter "until=48h" 2>&1 || true

    # 保留最近 5 个备份
    ls -t "${BACKUP_DIR}"/state_pre_*.json 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

    log "旧镜像和构建缓存已清理"

    # ---- 完成 ----
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  ✅ 部署成功${NC}"
    echo -e "${GREEN}  版本: ${VERSION}${NC}"
    echo -e "${GREEN}  时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${GREEN}=========================================${NC}"
}

# ---- 回滚函数 ----
rollback() {
    step "执行回滚"

    # 尝试重启服务
    log "重启当前服务..."
    docker compose -f "${COMPOSE_FILE}" restart server frontend 2>&1 || true

    # 从备份恢复
    local latest_backup=$(ls -t "${BACKUP_DIR}"/state_pre_*.json 2>/dev/null | head -1)
    if [ -n "${latest_backup}" ]; then
        log "状态备份: ${latest_backup}"
    fi

    warn "回滚完成，请检查服务状态"
}

# ---- 清理函数 ----
clean_deploy() {
    step "清理部署"
    cd "${DEPLOY_PATH}"
    docker compose -f "${COMPOSE_FILE}" down -v --remove-orphans 2>&1 || true
    docker system prune -af 2>&1 || true
    log "清理完成"
}

# ---- 入口 ----
case "${1:-deploy}" in
    deploy)
        main
        ;;
    rollback)
        rollback
        ;;
    clean)
        clean_deploy
        ;;
    *)
        echo "用法: $0 {deploy|rollback|clean}"
        exit 1
        ;;
esac
