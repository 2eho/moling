# ==============================================================================
# Moling 部署指南
# ==============================================================================
# 本文档提供完整的 Moling 项目部署说明
# 包括 Docker 部署、CI/CD 管道、监控配置等
#
# 文档版本: 1.1.0
# 最后更新: 2026-06-15
# 维护者: Moling Team
# ==============================================================================

---

## 目录
1. [项目介绍](#项目介绍)
2. [环境要求](#环境要求)
3. [快速开始](#快速开始)
4. [云服务器部署实战](#云服务器部署实战)
5. [Docker 部署](#docker-部署)
6. [CI/CD 管道](#cicd-管道)
7. [监控配置](#监控配置)
8. [故障排除](#故障排除)
9. [生产环境建议](#生产环境建议)

---

## 项目介绍

Moling（墨灵）是一个 AI 辅助小说创作平台，采用前后端分离架构：

| 组件 | 技术栈 | 说明 |
|------|---------|------|
| 前端 | Next.js + React | moling-web |
| 后端 | FastAPI + PostgreSQL + Redis | moling-server |
| 异步任务 | Celery Worker | 文档处理、AI 生成 |
| 向量数据库 | PostgreSQL + pgvector | 知识库向量存储 |

### 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Frontend (Nginx:80)                      │
│  - 静态文件服务                                       │
│  - API 反向代理 (/api/* -> Backend)                  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│  Backend (8000) │    │  Celery Worker      │
│  - FastAPI       │    │  - 异步任务处理    │
└────────┬────────┘    └──────────┬──────────┘
         │                         │
         └───────────┬───────────┘
                     ▼
        ┌─────────────────┐
        │   数据库 + Redis  │
        │   - PostgreSQL    │
        │   - Redis         │
        └─────────────────┘
```

---

## 环境要求

### 必需软件

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker | 20.10.0 | 26.0.0+ |
| Docker Compose | 2.0.0 | 2.24.0+ |
| Git | 2.30.0 | 2.45.0+ |

### 推荐配置

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB | 100GB+ |

### 操作系统

- Ubuntu 22.04 LTS（推荐）
- Debian 11+
- CentOS 8+
- Windows 10/11（需要 WSL2）

---

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd MolingProject
```

### 2. 配置环境变量

```bash
# 复制后端环境变量模板
cp moling-server/.env.example moling-server/.env

# 编辑配置文件
vim moling-server/.env
```

**必需修改的配置**:

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | JWT 签名密钥 | `openssl rand -hex 32` 生成 |
| `POSTGRES_PASSWORD` | 数据库密码 | 强密码 |
| `REDIS_PASSWORD` | Redis 密码 | 强密码 |
| `LLM_API_KEY` | LLM API 密钥 | `sk-...` |

### 3. 部署

```bash
# 进入 docker 目录
cd docker

# 运行部署脚本
bash deploy.sh
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 访问前端
open http://localhost

# 访问 API 文档
open http://localhost/api/v1/docs
```

---

## 云服务器部署实战

> **适用场景**: 将 Moling 部署到云服务器（如 OpenCloudOS、CentOS、Ubuntu），通过子路径访问（如 `/moling`）
> 
> **实际案例**: `http://124.222.163.79:8080/moling/`

### 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户浏览器                            │
│           http://124.222.163.79:8080/moling/              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Nginx（宿主机，端口 8080）                  │
│  location /moling       → proxy_pass :3000（前端）       │
│  location /moling/api/  → proxy_pass :8000（后端）       │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│  moling-web     │    │  moling-app          │
│  Next.js :3000  │    │  FastAPI :8000       │
└────────┬────────┘    └──────────┬──────────┘
         │                         │
         └───────────┬───────────┘
                     ▼
        ┌─────────────────┐
        │   moling-redis   │
        │   Redis :6379    │
        └─────────────────┘
```

### 前置条件

| 软件 | 版本 | 说明 |
|------|------|------|
| Docker | 20.10.0+ | 容器运行时 |
| Docker Compose | 2.0.0+ | 容器编排（可选） |
| Nginx | 1.20+ | 反向代理（宿主机安装） |

### 部署步骤

#### 1. 构建 Docker 镜像

```bash
# 克隆项目
git clone <repository-url>
cd MolingProject

# 构建后端镜像
cd moling-server
docker build -t moling-app:latest .

# 构建前端镜像
cd ../moling-web
docker build -t moling-web:latest .
```

**常见构建错误参见[故障排除](#故障排除)第 6-11 条。**

#### 2. 启动 Docker 容器

```bash
# 创建 Docker 网络
docker network create moling-network 2>/dev/null || true

# 启动 Redis
docker run -d --name moling-redis \
  --network moling-network \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine

# 启动后端
docker run -d --name moling-app \
  --network moling-network \
  -p 8000:8000 \
  --env-file moling-server/.env \
  --restart unless-stopped \
  moling-app:latest

# 启动前端
docker run -d --name moling-web \
  --network moling-network \
  -p 3000:3000 \
  --restart unless-stopped \
  moling-web:latest
```

#### 3. 配置 Nginx 反向代理

创建 `/etc/nginx/conf.d/moling.conf`：

```nginx
server {
    listen 8080;
    listen [::]:8080;
    server_name _;

    # 根路径重定向到 /moling
    location = / {
        return 301 /moling;
    }

    # 前端（Next.js standalone 模式）
    location /moling {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /moling/api/ {
        rewrite ^/moling(/api/.*)$ $1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    # API 文档
    location /moling/api/docs {
        proxy_pass http://127.0.0.1:8000/api/docs;
        proxy_set_header Host $host;
    }
}
```

**测试并重载 Nginx：**

```bash
# 检查配置
sudo nginx -t

# 重载配置
sudo nginx -s reload

# 如 Nginx 未启动
sudo systemctl start nginx
```

#### 4. 验证部署

```bash
# 检查容器状态
docker ps

# 测试前端
curl -s http://127.0.0.1:3000 | head -20

# 测试后端 API
curl http://127.0.0.1:8000/api/health

# 浏览器访问
open http://124.222.163.79:8080/moling/
```

### Next.js 子路径部署要点

在 `moling-web/next.config.ts` 中配置 `basePath`：

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/moling",   // ← 所有前端路由自动加上 /moling 前缀
  output: "standalone",  // ← standalone 模式，Docker 中直接 node server.js
};

export default nextConfig;
```

**注意**：配置 `basePath` 后，所有前端路由变为 `/moling/*`，Nginx 只需将 `/moling` 前缀代理到前端容器，无需额外改写。

### 更新记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-15 | 1.1.0 | 新增云服务器部署实战章节；新增故障排除第 6-13 条 |

---

## Docker 部署

### Docker Compose 配置说明

主要配置文件: `docker/docker-compose.yml`

**服务列表**:

| 服务名 | 镜像 | 说明 |
|--------|------|------|
| `frontend` | 自定义（Nginx） | 前端服务 |
| `app` | 自定义（FastAPI） | 后端 API 服务 |
| `worker` | 自定义（Celery） | 异步任务 Worker |
| `db` | pgvector/pgvector:pg17 | PostgreSQL + pgvector |
| `redis` | redis:7-alpine | Redis 缓存/消息队列 |
| `prometheus` | prom/prometheus:latest | 指标收集 |
| `grafana` | grafana/grafana:latest | 可视化仪表板 |

### 健康检查

所有服务都配置了健康检查：

```bash
# 查看服务健康状态
docker-compose ps

# 查看详细健康信息
docker inspect moling-api | grep -A 10 Health
```

### 数据持久化

| Volume | 说明 | 路径 |
|--------|------|------|
| `pgdata` | PostgreSQL 数据 | `/var/lib/postgresql/data` |
| `redisdata` | Redis 数据 | `/data` |
| `prometheusdata` | Prometheus 数据 | `/prometheus` |
| `grafanadata` | Grafana 数据 | `/var/lib/grafana` |

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f [service_name]

# 进入容器
docker-compose exec app bash

# 查看资源使用
docker stats
```

---

## CI/CD 管道

### 管道配置

配置文件: `.github/workflow/s/ci-cd.yml`

**管道阶段**:

```mermaid
graph LR
    A[代码提交] --> B[Lint 检查]
    B --> C[单元测试]
    C --> D[构建镜像]
    D --> E[推送镜像]
    E --> F[部署到测试环境]
    F --> G[部署到生产环境]
```

### 触发条件

| 事件 | 分支 | 说明 |
|------|------|------|
| Push | main, master, develop | 触发完整 CI/CD |
| Pull Request | main, master, develop | 触发 CI 检查 |
| 手动触发 | 所有分支 | 通过 workflow_dispatch |

### 环境变量配置

需要在 GitHub 仓库 Settings -> Secrets and variables -> Actions 中配置：

```bash
# Docker 镜像仓库
DOCKER_REGISTRY= docker.io/username
DOCKER_USERNAME= your_username
DOCKER_PASSWORD= your_password

# SSH 部署密钥
SSH_PRIVATE_KEY= -----BEGIN OPENSSH PRIVATE KEY-----...

# Slack 通知（可选）
SLACK_WEBHOOK_URL= https://hooks.slack.com/...
```

### 环境配置

需要在 GitHub 仓库 Settings -> Environments 中创建：

1. **staging** - 测试环境
   - 无需手动批准
   - URL: https://staging.moling.example.com

2. **production** - 生产环境
   - 需要手动批准
   - URL: https://moling.example.com

---

## 监控配置

### Prometheus 配置

配置文件: `docker/prometheus.yml`

**访问地址**: http://localhost:9090

**监控目标**:

| 目标 | 状态 | 说明 |
|------|------|------|
| Prometheus | ✅ | 自身监控 |
| Moling Backend | ⚠️ | 需要添加 `/metrics` 端点 |
| Node Exporter | ❌ | 需要添加 node-exporter 服务 |
| Redis | ❌ | 需要添加 redis_exporter |
| PostgreSQL | ❌ | 需要添加 postgres_exporter |

### Grafana 配置

配置文件: `docker/grafana/provision_ing/`

**访问地址**: http://localhost:3001
- 默认用户名: `admin`
- 默认密码: `admin`（可在 `.env` 中修改）

**预装仪表板**:

| 仪表板 | 说明 |
|---------|------|
| Moling 概览 | 服务整体状态 |

### 添加 Prometheus 指标到后端

后端已添加 `prometheus-fastapi-instrumentator` 依赖，访问：

```
http://localhost:8000/metrics
```

---

## 故障排除

### 1. 端口 80 已被占用

**解决方法**:

```bash
# 查看占用端口的进程
sudo lsof -i :80

# 停止进程（谨慎操作）
sudo kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口映射
ports:
  - "8080:80"  # 改为 8080 端口
```

### 2. 数据库连接失败

**可能原因**:
- 数据库未启动
- 密码错误
- 网络配置错误

**解决方法**:

```bash
# 检查数据库服务状态
docker-compose ps db

# 查看数据库日志
docker-compose logs db

# 测试数据库连接
docker-compose exec app python -c "import asyncio; from app.core.database import check_database; asyncio.run(check_database())"
```

### 3. 前端无法访问后端 API

**可能原因**:
- Nginx 代理配置错误
- 后端服务未启动
- 网络不通

**解决方法**:

```bash
# 检查 Nginx 配置
docker-compose exec frontend nginx -t

# 查看 Nginx 日志
docker-compose logs frontend

# 测试 API 代理
curl http://localhost/api/v1/health
```

### 4. Celery Worker 不工作

**可能原因**:
- Redis 连接失败
- 任务模块未正确导入

**解决方法**:

```bash
# 查看 Worker 日志
docker-compose logs worker

# 检查 Celery 状态
docker-compose exec worker celery -A app.core.celery_app status
```

### 5. 镜像构建失败

**可能原因**:
- 依赖安装失败
- 网络问题
- 磁盘空间不足

**解决方法**:

```bash
# 清理 Docker 缓存
docker system prune -a

# 重新构建（无缓存）
docker-compose build --no-cache

# 检查磁盘空间
df -h
```

### 6. Debian Trixie 包名变更 (libffi7 → libffi8)

**问题**: Docker 构建时报错 `Unable to locate package libffi7`

**原因**: `python:3.11-slim` 基础镜像已升级到 Debian Trixie，其中 `libffi` 运行时库的包名是 `libffi8`，不再是 `libffi7`

**解决方法**:

```dockerfile
# 在 Dockerfile 中修改
# 错误写法
RUN apt-get install -y --no-install-recommends libffi7

# 正确写法
RUN apt-get install -y --no-install-recommends libffi8
```

**文件**: `moling-server/Dockerfile`

### 7. bcrypt 版本约束无效

**问题**: `pip install` 时报错 `Could not find a version that satisfies the requirement bcrypt<4.1`

**原因**: `pyproject.toml` 中 `bcrypt<4.1` 无下限且最新 bcrypt 已 > 4.1，导致无可用版本

**解决方法**:

```toml
# 在 pyproject.toml 中修改
# 错误写法
"bcrypt<4.1"

# 正确写法
"bcrypt>=4.0,<5.0"
```

**文件**: `moling-server/pyproject.toml`

### 8. Dockerfile NODE_ENV 顺序错误

**问题**: Next.js 构建时报错 `Cannot find module 'typescript'`

**原因**: `ENV NODE_ENV=production` 在 `npm ci` 之前，导致 devDependencies（含 typescript）被跳过

**解决方法**:

```dockerfile
# 在 Dockerfile 中修改顺序
# 错误写法
ENV NODE_ENV=production
RUN npm ci

# 正确写法
RUN npm ci                    # ← 先装，devDependencies 全会装上
ENV NODE_ENV=production
```

**文件**: `moling-web/Dockerfile`

### 9. Windows 大小写不敏感导致 Linux 构建失败

**问题**: 本地能跑的代码，Docker Linux 环境报 `Module not found: Can't resolve './Settings.module.css'`

**原因**: Windows 不区分大小写，`import './Settings.module.css'` 在本地能匹配 `settings.module.css`，但 Linux 区分大小写

**解决方法**:

```bash
# 确保 import 语句和文件名完全一致
# import 语句
import styles from './Settings.module.css';

# 文件名必须是（注意大写 S）
# Settings.module.css  ✅
# settings.module.css  ❌（Linux 下找不到）
```

**检查命令**:

```bash
# 在 Linux 或 Git Bash 中检查
find src -name "*.module.css" -type f
```

### 10. Next.js 动态路由 slug 名称冲突

**问题**: 构建时报错 `You cannot use different slug names for the same dynamic path ('id' !== 'projectId')`

**原因**: 同一路由目录下有多个动态路由文件夹，使用了不同的参数名

**解决方法**:

```bash
# 错误示例：同一路由下有两个动态参数名
src/app/vaults/[id]/
src/app/vaults/[projectId]/

# 正确做法：统一使用一个参数名，删除重复的
rm -rf src/app/vaults/[id]/
# 保留
src/app/vaults/[projectId]/
```

**文件**: `moling-web/src/app/vaults/[id]/` (需删除)

### 11. pydantic 需要 email-validator

**问题**: 后端启动时报错 `ImportError: email-validator is not installed, run pip install 'pydantic[email]'`

**原因**: pydantic 的 EmailStr 类型需要 `email-validator` 包，但未被安装

**解决方法**:

```toml
# 在 pyproject.toml 中添加
dependencies = [
    # ... 其他依赖
    "email-validator>=2.2.0",
]
```

**文件**: `moling-server/pyproject.toml`

### 12. Nginx 反向代理重定向循环

**问题**: 浏览器报错 `ERR_TOO_MANY_REDIRECTS`

**原因**: Nginx `location /moling/` 只匹配带末尾斜杠的路径，Next.js 重定向导致循环

**解决方法**:

```nginx
# 在 Nginx 配置中修改
# 错误写法
location /moling/ {
    proxy_pass http://127.0.0.1:3000;
}

# 正确写法（去掉末尾斜杠）
location /moling {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**文件**: `/etc/nginx/conf.d/moling.conf`

### 13. Docker 镜像构建加速（国内网络）

**问题**: `apt-get update` 或 `pip install` 速度极慢（17 分钟+）

**解决方法**:

```dockerfile
# apt 使用国内镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends ...

# pip 使用国内镜像
RUN pip install --upgrade pip && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir .
```

**文件**: `moling-server/Dockerfile`, `moling-web/Dockerfile`

---

## 生产环境建议

### 1. 安全配置

**修改默认密码**:

```bash
# 生成强密码
openssl rand -base64 32
```

**启用 HTTPS**:

1. 申请 SSL 证书（Let's Encrypt 或商业证书）
2. 将证书放到 `docker/nginx/ssl/` 目录
3. 修改 Nginx 配置启用 HTTPS

```nginx
# docker/nginx/nginx.conf
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    # ... 其他配置
}
```

**配置防火墙**:

```bash
# 仅允许必要端口
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 2. 性能优化

**数据库优化**:

```ini
# 修改 PostgreSQL 配置（需要挂载自定义配置文件）
# 增加共享内存、连接数等
```

**Redis 优化**:

```conf
# 修改 Redis 配置
maxmemory 2gb
maxmemory-policy allkeys-lru
```

**后端多进程**:

```yaml
# docker-compose.yml
app:
  deploy:
    replicas: 2  # 启动 2 个后端实例
```

### 3. 备份策略

**数据库备份**:

```bash
# 每日自动备份（添加到 crontab）
0 2 * * * cd /path/to/docker && bash backup.sh
```

**文件备份**:

```bash
# 备份上传文件
tar -czf uploads_$(date +%Y%m%d).tar.gz moling-server/uploads/
```

### 4. 监控和告警

**使用 Prometheus + Grafana**:
- 监控 Docker 容器状态
- 监控数据库性能
- 监控 API 响应时间

**日志收集**:
- 使用 ELK (Elasticsearch + Logstash + Kibana)
- 或使用 Loki + Grafana

**错误追踪**:
- 配置 Sentry DSN 到 `.env` 文件
- 访问 Sentry 仪表板查看错误

---

## 附录

### A. 目录结构

```
MolingProject/
├── moling-web/              # 前端项目
│   ├── src/                 # 源代码
│   ├── public/              # 静态资源
│   ├── Dockerfile           # 前端 Dockerfile
│   └── nginx.conf           # Nginx 配置
├── moling-server/           # 后端项目
│   ├── app/                 # 应用代码
│   ├── alembic/             # 数据库迁移
│   ├── Dockerfile           # 后端 Dockerfile
│   └── .env.example        # 环境变量模板
└── docker/                  # Docker 配置
    ├── docker-compose.yml   # Docker Compose 配置
    ├── nginx/               # Nginx 配置
    │   ├── nginx.conf       # Nginx 主配置
    │   └── ssl/            # SSL 证书
    ├── grafana/             # Grafana 配置
    │   └── provisioning/    # 预配置
    ├── prometheus.yml       # Prometheus 配置
    ├── deploy.sh            # Linux 部署脚本
    ├── deploy.bat           # Windows 部署脚本
    └── DEPLOYMENT.md        # 部署文档
```

### B. 有用的命令

```bash
# 查看所有容器
docker ps -a

# 查看容器资源使用
docker stats

# 进入运行的容器
docker exec -it <container_name> bash

# 查看容器 IP
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <container_name>

# 导出数据库
docker-compose exec db pg_dump -U moling moling > backup.sql

# 导入数据库
docker-compose exec -T db psql -U moling moling < backup.sql
```

### C. 参考链接

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Next.js 文档](https://nextjs.org/docs)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [Redis 文档](https://redis.io/docs/)
- [Prometheus 文档](https://prometheus.io/docs/)
- [Grafana 文档](https://grafana.com/docs/)

---

**文档版本**: 1.0.0  
**最后更新**: 2026-06-15  
**维护者**: Moling Team
