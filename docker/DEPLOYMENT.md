# ==============================================================================
# Moling 部署文档
# ==============================================================================

## 目录
- [项目介绍](#项目介绍)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [部署步骤](#部署步骤)
- [服务管理](#服务管理)
- [常见问题](#常见问题)
- [生产环境建议](#生产环境建议)
- [监控和维护](#监控和维护)

---

## 项目介绍

Moling 是一个 AI 辅助小说创作平台，采用前后端分离架构：
- **前端**: Next.js + React (moling-web)
- **后端**: FastAPI + PostgreSQL + Redis (moling-server)
- **异步任务**: Celery Worker
- **向量数据库**: PostgreSQL + pgvector 扩展

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
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│  PostgreSQL     │    │  Redis              │
│  (pgvector)    │    │  - 缓存             │
│  - 向量存储     │    │  - 消息队列         │
└─────────────────┘    └─────────────────────┘
```

---

## 环境要求

### 必需软件
- **Docker**: >= 20.10.0
- **Docker Compose**: >= 2.0.0
- **Git**: >= 2.30.0

### 推荐配置
- **CPU**: 4 核以上
- **内存**: 8GB 以上（运行 LLM 需要 16GB+）
- **磁盘**: 50GB 以上可用空间

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
- `SECRET_KEY`: 设置为强随机密钥
- `POSTGRES_PASSWORD`: 数据库密码
- `REDIS_PASSWORD`: Redis 密码
- `LLM_API_KEY`: LLM API 密钥

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

## 配置说明

### 环境变量（moling-server/.env）

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `POSTGRES_USER` | PostgreSQL 用户名 | `moling` | 是 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | - | 是 |
| `POSTGRES_DB` | PostgreSQL 数据库名 | `moling` | 是 |
| `REDIS_PASSWORD` | Redis 密码 | - | 是 |
| `SECRET_KEY` | JWT 签名密钥 | - | 是 |
| `LLM_API_KEY` | LLM API 密钥 | - | 是 |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.deepseek.com` | 否 |
| `LLM_MODEL` | LLM 模型名称 | `deepseek-chat` | 否 |

### Docker Compose 配置

主要配置文件: `docker/docker-compose.yml`

**服务说明**:
- `frontend`: 前端服务（Nginx + 静态文件）
- `app`: 后端 API 服务（FastAPI）
- `worker`: Celery Worker 服务
- `db`: PostgreSQL 数据库
- `redis`: Redis 缓存/消息队列

---

## 部署步骤

### 首次部署

1. **检查依赖**
   ```bash
   # 检查 Docker
   docker --version
   
   # 检查 Docker Compose
   docker-compose --version
   ```

2. **配置环境变量**
   ```bash
   cp moling-server/.env.example moling-server/.env
   # 编辑 .env 文件，填写正确的配置
   ```

3. **运行部署脚本**
   ```bash
   cd docker
   bash deploy.sh
   ```

4. **验证部署**
   ```bash
   # 检查服务健康状态
   curl http://localhost:80/health
   
   # 检查 API 健康状态
   curl http://localhost:80/api/v1/health
   ```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新部署
cd docker
bash deploy.sh
```

### 回滚部署

```bash
cd docker
bash deploy.sh --rollback
```

---

## 服务管理

### 启动服务
```bash
cd docker
docker-compose up -d
```

### 停止服务
```bash
cd docker
docker-compose down
```

### 重启服务
```bash
cd docker
docker-compose restart
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f frontend
docker-compose logs -f worker
```

### 进入容器
```bash
# 进入后端容器
docker-compose exec app bash

# 进入数据库
docker-compose exec db psql -U moling -d moling

# 进入 Redis
docker-compose exec redis redis-cli -a <password>
```

---

## 常见问题

### 1. 端口 80 已被占用
**解决方法**:
- 修改 `docker-compose.yml` 中的端口映射
- 或停止占用端口的服务

```bash
# 查看占用端口的进程
sudo lsof -i :80

# 停止进程（谨慎操作）
sudo kill -9 <PID>
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

---

## 监控和维护

### 健康检查

所有服务都配置了健康检查：
```bash
# 手动检查健康状态
docker-compose ps

# 查看健康检查详情
docker inspect moling-api | grep -A 10 Health
```

### 日志管理

**日志位置**:
- 前端: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- 后端: 标准输出（通过 `docker-compose logs` 查看）

**日志轮转**:
```bash
# 配置 Docker 日志轮转
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### 更新和维护

**更新 Docker 镜像**:
```bash
# 拉取最新基础镜像
docker-compose pull

# 重新构建
docker-compose build --pull

# 重启服务
docker-compose up -d
```

**清理无用资源**:
```bash
# 删除未使用的镜像
docker image prune -a

# 删除未使用的 volumes
docker volume prune

# 删除未使用的网络
docker network prune
```

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
    ├── deploy.sh            # 部署脚本
    └── DEPLOYMENT.md        # 本文档
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

---

**文档版本**: 1.0.0  
**最后更新**: 2026-06-14  
**维护者**: Moling Team
