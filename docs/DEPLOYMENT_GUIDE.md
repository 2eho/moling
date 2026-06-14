# ==============================================================================
# Moling 部署指南
# ==============================================================================
# 本文档提供完整的 Moling 项目部署说明
# 包括 Docker 部署、CI/CD 管道、监控配置等
#
# 文档版本: 1.0.0
# 最后更新: 2026-06-14
# 维护者: Moling Team
# ==============================================================================

---

## 目录
1. [项目介绍](#项目介绍)
2. [环境要求](#环境要求)
3. [快速开始](#快速开始)
4. [Docker 部署](#docker-部署)
5. [CI/CD 管道](#cicd-管道)
6. [监控配置](#监控配置)
7. [故障排除](#故障排除)
8. [生产环境建议](#生产环境建议)

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
**最后更新**: 2026-06-14  
**维护者**: Moling Team
