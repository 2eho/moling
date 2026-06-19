# ==============================================================================
# 墨灵 Moling — GitHub Actions Secrets 配置指南
# ==============================================================================
# 配置位置: GitHub 仓库 → Settings → Secrets and variables → Actions
# 或通过 gh CLI: gh secret set <NAME> --body "<VALUE>"
#
# 说明: 所有标记 [必需] 的 Secrets 必须配置才能使用自动化部署。
# ==============================================================================

# ============================================================================
# 🔑 必需 Secrets（自动化部署核心）
# ============================================================================

# ---- 服务器连接 ----
# SSH 主机地址（生产服务器 IP 或域名）
SSH_HOST=124.222.163.79
# SSH 用户名
SSH_USER=root
# SSH 私钥（完整内容，含 BEGIN/END 行）
# 生成: ssh-keygen -t ed25519 -C "moling-ci" -f moling-ci-key
# 服务器: cat moling-ci-key.pub >> ~/.ssh/authorized_keys
SSH_PRIVATE_KEY="-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----"

# ---- 部署路径 ----
# 服务器上的项目根目录
DEPLOY_PATH=/opt/moling

# ---- 数据库 ----
# 生产数据库连接字符串
# SQLite: sqlite+aiosqlite:///app/data/moling.db
# PostgreSQL: postgresql+asyncpg://user:pass@db:5432/moling
DATABASE_URL=postgresql+asyncpg://moling:REPLACE_WITH_STRONG_PASSWORD@db:5432/moling

# ============================================================================
# 🔒 生产环境变量（通过 deploy.yml 注入容器）
# ============================================================================

# JWT 签名密钥（必须修改默认值！）
# 生成: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=REPLACE_WITH_GENERATED_KEY

# 前端公开 API 路径
NEXT_PUBLIC_API_BASE_URL=/moling/api/v1

# ============================================================================
# 📊 可选 Secrets（监控和通知）
# ============================================================================

# Sentry DSN（错误追踪）
SENTRY_DSN=https://xxx@sentry.io/xxx

# LLM API 密钥（如果使用 DeepSeek）
LLM_API_KEY=sk-REPLACE_WITH_YOUR_KEY

# LLM API 地址
LLM_API_BASE=https://api.deepseek.com

# Redis 密码
REDIS_PASSWORD=REPLACE_WITH_STRONG_PASSWORD

# PostgreSQL 密码
POSTGRES_PASSWORD=REPLACE_WITH_STRONG_PASSWORD

# Grafana 管理员密码
GRAFANA_ADMIN_PASSWORD=REPLACE_WITH_STRONG_PASSWORD

# ============================================================================
# 📋 快速配置命令
# ============================================================================
# 复制以下命令并替换占位符，在项目目录执行：
#
# # 服务器连接
# gh secret set SSH_HOST --body "124.222.163.79"
# gh secret set SSH_USER --body "root"
# gh secret set SSH_PRIVATE_KEY --body "$(cat moling-ci-key)"
# gh secret set DEPLOY_PATH --body "/opt/moling"
#
# # 数据库
# gh secret set DATABASE_URL --body "postgresql+asyncpg://moling:你的密码@db:5432/moling"
#
# # 安全密钥
# gh secret set JWT_SECRET_KEY --body "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
#
# # 可选
# gh secret set LLM_API_KEY --body "sk-你的密钥"
# gh secret set SENTRY_DSN --body "https://xxx@sentry.io/xxx"
# ============================================================================
