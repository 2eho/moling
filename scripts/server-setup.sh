#!/bin/bash
# ==============================================================================
# 墨灵 Moling — 服务器初始化脚本
# ==============================================================================
# 用途: 在新服务器上一键完成墨灵生产环境的初始化
# 运行: curl -fsSL https://raw.githubusercontent.com/2eho/moling/main/scripts/server-setup.sh | bash
# 或:   bash scripts/server-setup.sh
#
# 前置条件:
#   - Ubuntu 20.04+ / Debian 11+ / OpenCloudOS 8+ / CentOS 8+
#   - root 或 sudo 权限
#
# 执行内容:
#   1. 安装 Docker + Docker Compose
#   2. 安装 Nginx
#   3. 配置防火墙
#   4. 创建目录结构
#   5. 配置 Nginx 反向代理
#   6. 设置 systemd 自启动
# ==============================================================================

set -euo pipefail

# ---- 配置 ----
DEPLOY_PATH="${DEPLOY_PATH:-/opt/moling}"
DOMAIN="${DOMAIN:-124.222.163.79}"
PORT="${PORT:-8080}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[X]${NC} $1"; exit 1; }

echo "========================================="
echo "  Moling 服务器初始化"
echo "  目标: ${DEPLOY_PATH}"
echo "  端口: ${PORT}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

# ---- Step 1: 检测系统 ----
log "检测系统环境..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    OS_VERSION=$VERSION_ID
    log "系统: ${OS} ${OS_VERSION}"
else
    warn "无法检测系统版本"
fi

# ---- Step 2: 安装 Docker ----
log "安装 Docker..."
if ! command -v docker &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL/OpenCloudOS
        yum install -y yum-utils
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    else
        err "不支持的包管理器"
    fi

    systemctl enable docker
    systemctl start docker
    log "Docker 安装完成"
else
    log "Docker 已安装: $(docker --version)"
fi

# ---- Step 3: 安装 Nginx ----
log "安装 Nginx..."
if ! command -v nginx &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        apt-get install -y -qq nginx
    elif command -v yum &> /dev/null; then
        yum install -y nginx
    fi
    systemctl enable nginx
    log "Nginx 安装完成"
else
    log "Nginx 已安装: $(nginx -v 2>&1)"
fi

# ---- Step 4: 配置防火墙 ----
log "配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow ${PORT}/tcp 2>/dev/null || true
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    log "UFW 规则已添加"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=${PORT}/tcp 2>/dev/null || true
    firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
    firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    log "firewalld 规则已添加"
fi

# ---- Step 5: 创建目录结构 ----
log "创建目录结构..."
mkdir -p "${DEPLOY_PATH}"/{data/{postgres,redis},backups,nginx/ssl}
log "目录已创建: ${DEPLOY_PATH}"

# ---- Step 6: 生成 SSH 密钥（用于 CI/CD） ----
if [ ! -f "${DEPLOY_PATH}/moling-ci-key" ]; then
    log "生成 CI/CD SSH 密钥对..."
    ssh-keygen -t ed25519 -C "moling-ci-deploy" -f "${DEPLOY_PATH}/moling-ci-key" -N ""
    cat "${DEPLOY_PATH}/moling-ci-key.pub" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    log "CI/CD 密钥已生成并添加到 authorized_keys"
    echo ""
    echo -e "${YELLOW}=========================================${NC}"
    echo -e "${YELLOW}  ⚠️  重要：请将以下私钥配置为 GitHub Secret:${NC}"
    echo -e "${YELLOW}     Secret Name: SSH_PRIVATE_KEY${NC}"
    echo -e "${YELLOW}=========================================${NC}"
    echo ""
    cat "${DEPLOY_PATH}/moling-ci-key"
    echo ""
    echo -e "${YELLOW}=========================================${NC}"
fi

# ---- Step 7: 拉取项目 ----
log "克隆项目仓库..."
if [ ! -d "${DEPLOY_PATH}/.git" ]; then
    git clone https://github.com/2eho/moling.git "${DEPLOY_PATH}" 2>/dev/null || {
        warn "无法克隆仓库（可能是私有仓库），请手动拉取:"
        echo "  git clone https://github.com/2eho/moling.git ${DEPLOY_PATH}"
    }
else
    log "项目已存在，更新..."
    cd "${DEPLOY_PATH}" && git pull
fi

# ---- Step 8: 配置环境变量 ----
if [ ! -f "${DEPLOY_PATH}/moling-server/.env" ]; then
    log "创建环境变量文件..."
    cp "${DEPLOY_PATH}/moling-server/.env.example" "${DEPLOY_PATH}/moling-server/.env"

    # 生成安全密钥
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "${DEPLOY_PATH}/moling-server/.env"

    warn "请编辑 ${DEPLOY_PATH}/moling-server/.env 并填写必要的配置:"
    echo "  - LLM_API_KEY（AI 模型 API 密钥）"
    echo "  - DATABASE_URL（如使用 PostgreSQL）"
fi

# ---- Step 9: 配置 Nginx ----
log "配置 Nginx 反向代理..."
if [ -f "${DEPLOY_PATH}/deploy/nginx/moling.conf" ]; then
    cp "${DEPLOY_PATH}/deploy/nginx/moling.conf" /etc/nginx/conf.d/moling.conf
    nginx -t && systemctl reload nginx
    log "Nginx 配置已应用"
else
    warn "Nginx 配置文件未找到，请手动配置"
fi

# ---- Step 10: 验证 ----
log "验证安装..."
echo ""
echo "  Docker:  $(docker --version 2>/dev/null || echo '未安装')"
echo "  Nginx:   $(nginx -v 2>&1 || echo '未安装')"
echo "  Git:     $(git --version 2>/dev/null || echo '未安装')"
echo ""

# ---- 完成 ----
echo "========================================="
echo -e "  ${GREEN}✅ 服务器初始化完成${NC}"
echo "========================================="
echo ""
echo "下一步操作:"
echo "  1. 编辑环境变量:"
echo "     vim ${DEPLOY_PATH}/moling-server/.env"
echo ""
echo "  2. 配置 GitHub Secrets:"
echo "     参考: ${DEPLOY_PATH}/docs/CI_CD_SETUP.md"
echo ""
echo "  3. 手动启动服务:"
echo "     cd ${DEPLOY_PATH}"
echo "     make prod"
echo ""
echo "  4. 运行健康检查:"
echo "     make health"
echo ""
echo "========================================="
