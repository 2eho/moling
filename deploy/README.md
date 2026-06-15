# 墨灵部署快速指南

> 服务器：`124.222.163.79:8080`
> 最后更新：2026-06-15

---

## 首次部署

```bash
# 1. 克隆代码
cd /root
git clone git@github.com:2eho/moling.git
cd moling

# 2. 复制 Nginx 配置
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -t          # 测试配置
sudo nginx -s reload   # 重载 Nginx

# 3. 构建并启动所有服务
docker compose up -d --build

# 4. 验证
curl http://localhost:8000/api/v1/health
# 预期：{"status":"healthy","version":"0.1.0","service":"moling-api"}

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/moling
# 预期：200
```

---

## 更新部署

```bash
# 1. 拉取最新代码
cd /root/moling
git pull origin main

# 2. 如果 Nginx 配置有更新
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -s reload

# 3. 重新构建并启动
docker compose up -d --build

# 4. 查看日志，确认无错误
docker compose logs -f --tail=50
```

---

## 服务说明

| 服务 | 容器名 | 说明 |
|:---|:---|:---|
| `db` | `moling-db` | PostgreSQL 16，数据持久化到 `pgdata` 卷 |
| `app` | `moling-app` | 后端 FastAPI，等待 `db` 健康后启动 |
| `web` | `moling-web` | 前端 Next.js，依赖 `app` 启动 |

---

## 常用命令

```bash
# 查看所有容器状态
docker compose ps

# 查看日志
docker compose logs app -f       # 后端
docker compose logs web -f        # 前端
docker compose logs db -f         # 数据库

# 重启单个服务
docker compose restart app

# 停止所有服务
docker compose down

# 重新构建（代码有变更时）
docker compose up -d --build

# 进入后端容器
docker compose exec app bash

# 进入数据库
docker compose exec db psql -U moling -d moling
```

---

## 排查指南

详见 `018_墨灵部署指南.md` 第七章。

**快速诊断**：

```bash
# 1. 容器是否运行
docker compose ps

# 2. 后端是否健康
curl http://localhost:8000/api/v1/health

# 3. 前端是否可访问
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/moling

# 4. Nginx 配置是否正确
sudo nginx -t
```
