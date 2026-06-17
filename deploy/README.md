# 墨灵部署快速指南

> 端口：`8080`（Nginx 反代）
> 最后更新：2026-06-17

---

## 架构说明

| 组件 | 说明 |
|------|------|
| Nginx | 监听 `8080`，反代前端(`:3000`)和后端(`:8000`) |
| Next.js | `basePath: "/moling"`，前端路由自动带前缀 |
| FastAPI | 无 basePath，由 Nginx rewrite 去掉 `/moling` 前缀 |

### Nginx 路由规则（关键）

```nginx
location /moling { proxy_pass http://127.0.0.1:3000; }           # 不透传
location /moling/api/ { rewrite ^/moling(/api/.*)$ $1 break; proxy_pass ...; }  # 去掉前缀
```

**注意**：前端不透传（Next.js 自己处理 `/moling` 前缀），后端必须 rewrite。

---

## 首次部署

```bash
# 1. 克隆代码
cd /root
git clone git@github.com:2eho/moling.git
cd moling

# 2. 复制 Nginx 配置（关键！）
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

# 2. 如果 Nginx 配置有更新（必须执行！）
sudo cp deploy/nginx/moling.conf /etc/nginx/conf.d/
sudo nginx -t          # 测试配置
sudo nginx -s reload    # 重载 Nginx

# 3. 重新构建前端（前端代码有变更时必做）
docker compose build --no-cache web
docker compose up -d web

# 4. 查看日志，确认无错误
docker compose logs -f --tail=50 web
```

### 前端更新必须重建镜像！
NEXT_PUBLIC_* 变量在**构建时**注入，仅重启容器不生效。

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

### 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| 前端 404 | Nginx 前端 location 加了 rewrite | 删除 rewrite，Next.js 已有 `basePath` |
| API 404 | Nginx API location 没加 rewrite | 必须加 `rewrite ^/moling(/api/.*)$ $1 break;` |
| 登录 401 | 密码错误 / 用户不存在 | 重新注册或重置密码 |
| 前端缓存 404 | Next.js 缓存了旧响应 | `docker compose restart web` 或重建镜像 |

### 快速诊断

```bash
# 1. 容器是否运行
docker compose ps

# 2. 后端是否健康
curl http://localhost:8000/api/v1/health

# 3. 前端是否可访问
curl -I http://localhost:8080/moling

# 4. Nginx 配置是否正确
sudo nginx -t

# 5. 查看前端日志（排 404 必看）
docker compose logs web --tail=50
```
