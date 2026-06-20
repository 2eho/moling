# 墨灵 (Moling) 部署指南

> **版本**: 2.1.0 | **最后更新**: 2026-06-21 | **维护者**: Moling Team

---

## 目录

1. [架构概览](#1-架构概览)
2. [环境要求](#2-环境要求)
3. [快速本地启动](#3-快速本地启动)
4. [Docker 部署](#4-docker-部署)
5. [云服务器部署实战](#5-云服务器部署实战)
6. [生产环境建议](#6-生产环境建议)
7. [常见问题排查](#7-常见问题排查)

---

## 1. 架构概览

```
用户浏览器 → http://服务器IP:8080/moling/
                  ↓
            Nginx (宿主机，端口 8080)
              /moling       → proxy_pass → moling-web:3000（前端）
              /moling/api/  → proxy_pass → moling-app:8000（后端）
                  ↓
            Docker 容器: moling-web / moling-app / moling-db / moling-redis
```

| 组件 | 技术栈 | 端口 | 说明 |
|------|--------|------|------|
| 反向代理 | Nginx | 80 / 443 / 8080 | 统一入口；开发用 8080，生产用 80/443 |
| 前端 | Next.js 19 + React 19 + TypeScript | 3000 | `basePath: "/moling"` |
| 后端 | FastAPI + PostgreSQL + Redis | 8000 | 无 basePath，由 Nginx rewrite |
| 数据库 | PostgreSQL 16 | 5432 | 主数据库 |
| 缓存 | Redis 7 | 6379 | 缓存 + Celery 消息队列 |
| 监控指标 | Prometheus | 9090 | 指标收集（仅生产编排） |
| 可视化 | Grafana | 3001 | 仪表板（仅生产编排；宿主机 3001→容器内 3000） |

### Nginx 路由规则（关键）

```nginx
location /moling { proxy_pass http://127.0.0.1:3000; }                # 前端不透传
location /moling/api/ { rewrite ^/moling(/api/.*)$ $1 break; proxy_pass http://127.0.0.1:8000; }  # API 必须 rewrite
```

---

## 2. 环境要求

### 必需软件

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.10 | 3.12 |
| Node.js | 18 | 22 |
| Docker | 20.10.0 | 26.0.0+ |
| Docker Compose | 2.0.0 | 2.24.0+ |
| Nginx | 1.20+ | 1.24+ |

### 推荐服务器配置

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 20GB SSD | 50GB+ SSD |

---

## 3. 快速本地启动

### 3.1 后端启动

```bash
cd moling-server

# 创建虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证：访问 http://localhost:8000/docs

**启动 Celery Worker 和 Beat**（生产必需，开发可选）：
```bash
# Worker（消费异步任务）
celery -A app.worker.celery_app worker -Q default,llm --loglevel=info

# Beat（定时调度器，另一个终端）
celery -A app.worker.celery_app beat --loglevel=info
```

验证健康检查：`GET http://localhost:8000/api/v1/health`，应返回 `{"status":"ok","database":"ok","redis":"ok","celery":"ok"}`

### 3.2 前端启动

```bash
cd moling-web
npm install
npm run dev
```

验证：访问 http://localhost:3000

### 3.3 环境变量配置

**后端** (`moling-server/.env`)：
```bash
# --- 数据库 (生产用 PostgreSQL, 开发可用 SQLite) ---
DATABASE_URL=sqlite+aiosqlite:///./moling.db     # 开发用 SQLite
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/moling  # 生产用 PostgreSQL

# --- 安全 ---
SECRET_KEY=your-secret-key-here                    # openssl rand -hex 32 生成
# REDIS_PASSWORD=your-redis-password               # 生产环境必须设置；开发可选

# --- 环境 ---
ENVIRONMENT=development
APP_VERSION=0.1.0

# --- CORS ---
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# --- LLM 配置 ---
LLM_MODEL=deepseek-chat                            # 默认模型
LLM_API_KEY=sk-your-api-key                        # API Key（通过后台 LlmConfigTab 也可配置）
# LLM_PRO_KEYS=sk-key1,sk-key2,sk-key3             # Pro Pool（逗号分隔或 JSON 数组）
# LLM_FLASH_KEYS=sk-fast1,sk-fast2                 # Flash Pool 快速模型

# --- LLM Provider ---
LLM_PROVIDER=deepseek                              # deepseek / openai / custom
LLM_BASE_URL=https://api.deepseek.com/v1

# --- Redis / Celery ---
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# --- 安全限制 ---
MAX_BODY_SIZE=10485760                             # 10MB 请求体限制

# --- Sentry（可选） ---
# SENTRY_DSN=https://xxx@sentry.io/xxx
```

**前端** (`moling-web/.env.local`)：
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 4. Docker 部署

### 4.1 完整 Docker Compose 编排

项目提供两套 Docker Compose 编排：

**根目录 `docker-compose.yml`** — 开发 / 快速部署（4 个核心服务）：

| 服务 | 容器名 | 镜像 | 端口 |
|------|--------|------|------|
| `db` | `moling-db` | `postgres:16-alpine` | 5432 |
| `redis` | `moling-redis` | `redis:7-alpine` | 6379 |
| `app` | `moling-app` | 本地构建 (moling-server) | 8000 |
| `web` | `moling-web` | 本地构建 (moling-web) | 3000 |

**`docker/docker-compose.yml`** — 生产级完整编排（8 个服务）：

| 服务 | 容器名 | 镜像 | 端口 | 说明 |
|------|--------|------|------|------|
| `frontend` | `moling-frontend` | 本地构建 (moling-web) | 80 / 443 | Nginx 静态文件 + 反向代理 |
| `app` | `moling-api` | 本地构建 (moling-server) | 8000 (expose) | FastAPI 应用，仅内网可达 |
| `worker` | `moling-worker` | 本地构建 (moling-server) | — | Celery Worker（消费 default+llm 队列） |
| `beat` | `moling-beat` | 本地构建 (moling-server) | — | Celery Beat（4 个周期性任务调度） |
| `db` | `moling-db` | `pgvector/pgvector:pg17` | 5432 (内网) | PostgreSQL 17 + pgvector |
| `redis` | `moling-redis` | `redis:7-alpine` | 6379 (内网) | 带密码持久化（--requirepass） |
| `prometheus` | `moling-prometheus` | `prom/prometheus:latest` | 9090 | 指标收集 |
| `grafana` | `moling-grafana` | `grafana/grafana:latest` | 3001 | 可视化仪表板 |

### 4.2 Docker 镜像构建要点

**后端 Dockerfile** (`moling-server/Dockerfile`)：
- Debian Trixie 基础镜像用 `libffi8`（非 `libffi7`）
- 添加阿里云镜像加速
- `pyproject.toml` 中 `bcrypt>=4.0,<5.0`

**前端 Dockerfile** (`moling-web/Dockerfile`)：
- `ENV NODE_ENV=production` 必须在 `npm ci` **之后**
- 使用 `output: "standalone"` 模式
- 启动命令 `node server.js`

### 4.3 构建和启动

```bash
# 首次部署
docker compose up -d --build

# 更新部署（代码变更后）
git pull origin main
docker compose up -d --build

# 仅前端更新（NEXT_PUBLIC_* 变更时必须重建）
docker compose build --no-cache web
docker compose up -d web
```

---

## 5. 云服务器部署实战

### 5.1 首次部署步骤

```bash
# 1. 克隆代码
cd /root
git clone git@github.com:2eho/moling.git
cd moling

# 2. 配置环境变量
cp moling-server/.env.example moling-server/.env
# 编辑 .env，修改 SECRET_KEY / POSTGRES_PASSWORD / LLM_API_KEY 等

# 3. 复制 Nginx 配置
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -t
sudo nginx -s reload

# 4. 构建并启动所有服务
docker compose up -d --build

# 5. 验证
curl http://localhost:8000/api/v1/health
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/moling
```

浏览器访问：`http://服务器IP:8080/moling/`

### 5.2 关键配置

**Nginx 配置** (`deploy/nginx/moling.conf`) 需复制到 `/etc/nginx/conf.d/moling.conf`。

**前端 API 地址**通过构建参数 `NEXT_PUBLIC_API_BASE_URL` 注入，生产环境值为 `/moling/api/v1`（相对路径）。

**后端 CORS** 通过环境变量 `CORS_ORIGINS` 配置，默认允许 `localhost:8080` 和 `localhost:3000`。

**数据库 URL** 在 Docker 内使用服务名：`postgresql+asyncpg://moling:moling@db:5432/moling`

### 5.3 安全配置

- 修改默认密码：所有密码使用 `openssl rand -base64 32` 生成
- 启用 HTTPS：申请 SSL 证书（推荐 Let's Encrypt），配置 Nginx 强制跳转 HTTPS
- 配置防火墙：仅开放必要端口（22、80、443、8080）
- 详情见 `SECURITY_HARDENING.md`

---

## 6. 生产环境建议

### 6.1 安全加固

| 措施 | 说明 | 参考文档 |
|------|------|----------|
| Rate Limiting | 认证端点限速（登录5次/分钟，注册3次/分钟） | `docs/SECURITY_HARDENING.md` |
| JWT 黑名单 | Redis 存储登出 token，登出立即失效 | `app/auth/blacklist.py` |
| HTTPS + HSTS | Nginx 配置 301 跳转 + 安全响应头 | Nginx 配置 |
| CSP 防 XSS | Next.js layout.tsx + Nginx 双重配置 | `src/app/layout.tsx` |
| SQL 注入防护 | 所有查询使用 SQLAlchemy ORM，参数化 | 代码审计通过 |

### 6.2 性能优化

| 优化项 | 说明 |
|--------|------|
| 数据库索引 | 为 chapters.project_id、chapters.order 等添加索引 |
| Redis 缓存 | 项目详情 TTL 60s、项目统计 TTL 300s、通知列表 TTL 30s |
| AI 生成异步化 | 返回任务 ID，前端轮询，避免同步等待 |
| 连接池 | SQLAlchemy 默认启用连接池 |

### 6.3 监控和日志

| 工具 | 用途 | 配置位置 |
|------|------|----------|
| Sentry | 错误追踪（前后端） | `moling-server/.env` + `moling-web/.env.local` |
| Prometheus | 指标收集 | `docker/prometheus.yml` |
| Grafana | 可视化仪表板 | `docker/grafana/` |
| Docker 日志 | 容器日志 | `docker compose logs -f` |

### 6.4 Docker Compose 健康检查

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## 7. 常见问题排查

| 问题 | 原因 | 修复 |
|------|------|------|
| 前端 404 | Nginx 前端 location 加了 rewrite | 删除 rewrite，Next.js 已有 `basePath` |
| API 404 | Nginx API location 没加 rewrite | 必须加 `rewrite ^/moling(/api/.*)$ $1 break;` |
| `Failed to fetch` | 前端 API 地址配置错误 | 检查 `NEXT_PUBLIC_API_BASE_URL` 构建参数 |
| 注册/登录 404 | 前端字段名与后端不匹配 | 前端发 `nickname` 而非 `username` |
| 后端数据库连接失败 | PostgreSQL 未启动或 URL 错误 | Docker 内用服务名 `db` 而非 `localhost` |
| Docker 构建慢 | 国内网络问题 | 已配置阿里云镜像加速 |
| 前端样式丢失 | `basePath` 配置后静态资源路径变化 | 确保 Nginx `/moling` 正确代理到前端容器 |

### 快速诊断脚本

```bash
#!/bin/bash
echo "=== 容器状态 ==="
docker compose ps
echo "=== 后端健康检查 ==="
curl -s http://localhost:8000/api/v1/health
echo "=== 前端可访问性 ==="
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/moling
echo "=== Nginx 配置测试 ==="
sudo nginx -t
echo "=== 端口监听 ==="
ss -tlnp | grep -E ':(8080|3000|8000|5432)'
```

---

## 更新记录

| 日期 | 内容 |
|:---|:---|
| 2026-06-18 | 整合三份部署文档为统一 `DEPLOYMENT.md` |
| 2026-06-17 | 修复 PostgreSQL 外键类型不匹配、Nginx 配置、注册字段名 |

---

**END**
