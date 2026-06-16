# 墨灵(Moling) 故障处理 SOP (RUNBOOK)

> **文档版本**: 1.0.0  
> **最后更新**: 2026-06-16  
> **维护者**: Moling Team  
> **适用环境**: 生产环境 / 测试环境

---

## 目录

1. [文档说明](#文档说明)
2. [故障 1：API 500 错误](#故障-1api-500-错误)
3. [故障 2：数据库 CPU 100%](#故障-2数据库-cpu-100)
4. [故障 3：前端部署失败](#故障-3前端部署失败)
5. [故障 4：SSL 证书过期](#故障-4ssl-证书过期)
6. [故障 5：Redis 连接失败](#故障-5redis-连接失败)
7. [故障 6：Celery Worker 异步任务堆积](#故障-6celery-worker-异步任务堆积)
8. [故障 7：磁盘空间不足](#故障-7磁盘空间不足)
9. [附录：常用命令速查](#附录常用命令速查)

---

## 文档说明

### 如何使用本文档

1. **保持冷静**：故障发生时，先深呼吸，按步骤排查
2. **按症状定位**：根据观察到的症状，找到对应的故障场景
3. **按顺序执行**：严格按照"检查步骤"和"恢复步骤"执行
4. **记录操作**：在故障处理过程中，记录所有操作和结果
5. **及时升级**：如果 30 分钟内无法恢复，立即升级到技术负责人

### 紧急联系人

| 角色 | 姓名 | 电话 | 邮箱 | 备注 |
|------|------|------|------|------|
| 技术负责人 | - | - | - | 请补充 |
| 后端负责人 | - | - | - | 请补充 |
| 运维负责人 | - | - | - | 请补充 |
| 值班人员 | - | - | - | 请补充 |

> **注意**：请在实际使用时填写上表中的联系信息。

---

## 故障 1：API 500 错误

### 症状

- 所有或部分 API 调用返回 **500 Internal Server Error**
- 用户无法正常使用系统功能
- 可能在 Sentry 中看到大量错误报警

### 影响范围

- **严重性**：🔴 高
- **影响用户**：全部用户或部分功能不可用
- **SLA 影响**：可能导致 SLA 违约

### 检查步骤

#### 步骤 1：检查 Sentry 错误监控

```bash
# 访问 Sentry 仪表板
open https://sentry.io/organizations/[your-org]/issues/

# 或查看项目配置的 Sentry DSN
cat moling-server/.env | grep SENTRY_DSN
```

**关键信息**：
- 错误类型（TypeError, DatabaseError, RedisError 等）
- 错误频率（是否突然激增）
- 影响范围（所有用户还是特定用户）

#### 步骤 2：查看后端日志

```bash
# Docker 部署 - 查看实时日志
docker logs -f moling-app --tail 100

# Docker Compose 部署
docker-compose logs -f app

# 查看特定时间段的日志
docker logs moling-app --since "2026-06-16T10:00:00" --until "2026-06-16T11:00:00"
```

**关键错误日志**：
- `DatabaseError` / `OperationalError` → 数据库问题
- `RedisError` / `ConnectionError` → Redis 问题
- `ImportError` / `ModuleNotFoundError` → 代码部署问题
- `ValidationError` → 请求参数问题

#### 步骤 3：检查数据库连接

```bash
# 方法 1：在宿主机测试数据库连接
docker exec -it moling-db pg_isready -U moling -d moling

# 方法 2：进入数据库容器执行 SQL
docker exec -it moling-db psql -U moling -d moling -c "SELECT 1;"

# 方法 3：从后端容器测试连接
docker exec -it moling-app python -c "
import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory
async def test():
    async with async_session_factory() as session:
        result = await session.execute(text('SELECT 1'))
        print('Database connection OK:', result.scalar())
asyncio.run(test())
"
```

#### 步骤 4：检查 Redis 连接

```bash
# 方法 1：直接进入 Redis 容器测试
docker exec -it moling-redis redis-cli ping
# 预期输出：PONG

# 方法 2：从后端容器测试 Redis 连接
docker exec -it moling-app python -c "
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
print('Redis connection OK:', r.ping())
"
```

#### 步骤 5：检查系统资源

```bash
# 查看容器资源使用
docker stats --no-stream

# 查看磁盘空间
df -h

# 查看内存使用
free -h
```

### 恢复步骤

#### 方案 1：重启后端服务（最常用）

```bash
# Docker 部署
docker restart moling-app

# Docker Compose 部署
docker-compose restart app

# 等待服务启动（约 10-30 秒）
sleep 30

# 验证服务恢复
curl http://localhost:8000/api/health
```

#### 方案 2：如果是数据库问题

```bash
# 检查数据库日志
docker logs moling-db --tail 100

# 重启数据库（⚠️ 会中断所有连接）
docker restart moling-db

# 等待数据库启动
sleep 30

# 验证数据库就绪
docker exec -it moling-db pg_isready -U moling -d moling
```

#### 方案 3：如果是 Redis 问题

```bash
# 检查 Redis 日志
docker logs moling-redis --tail 100

# 重启 Redis（⚠️ 会清除所有缓存）
docker restart moling-redis

# 验证 Redis 就绪
docker exec -it moling-redis redis-cli ping
```

#### 方案 4：回滚到上一个版本

```bash
# 查看历史版本
docker images | grep moling-app

# 回滚到上一个版本
docker stop moling-app
docker rm moling-app
docker run -d --name moling-app \
  --network moling-network \
  -p 8000:8000 \
  --env-file moling-server/.env \
  --restart unless-stopped \
  moling-app:<previous-version>

# 验证服务恢复
curl http://localhost:8000/api/health
```

#### 方案 5：紧急修复（如果有代码错误）

```bash
# 1. 快速修复代码
vim moling-server/app/path/to/file.py

# 2. 重启服务
docker restart moling-app

# 3. 验证修复
curl http://localhost:8000/api/health
```

### 预防措施

1. **启用健康检查和自动重启**：
   ```yaml
   # docker-compose.yml
   services:
     app:
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
         interval: 30s
         timeout: 10s
         retries: 3
       restart: unless-stopped
   ```

2. **配置 Sentry 告警**：在项目 Sentry 设置中配置邮件/Slack 告警

3. **定期查看日志**：使用 `docker logs` 或集中式日志系统（ELK/Loki）

---

## 故障 2：数据库 CPU 100%

### 症状

- 数据库查询变慢，API 响应时间增加（> 5秒）
- 用户反馈系统卡顿
- `pg_stat_activity` 中大量活跃连接
- 服务器 CPU 使用率持续 100%

### 影响范围

- **严重性**：🟡 中高
- **影响用户**：所有用户（系统变慢）
- **可能原因**：慢查询、连接池耗尽、锁等待

### 检查步骤

#### 步骤 1：查看数据库慢查询日志

```bash
# 进入数据库容器
docker exec -it moling-db psql -U moling -d moling

# 启用 pg_stat_statements 扩展（如果未启用）
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

# 查看最耗时的查询
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

# 退出 psql
\q
```

#### 步骤 2：检查当前连接数和活跃查询

```bash
# 查看当前所有连接
docker exec -it moling-db psql -U moling -d moling -c "
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    now() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
"

# 查看连接数统计
docker exec -it moling-db psql -U moling -d moling -c "
SELECT 
    count(*) AS total_connections,
    count(*) FILTER (WHERE state = 'active') AS active_connections,
    count(*) FILTER (WHERE state = 'idle') AS idle_connections
FROM pg_stat_activity;
"
```

#### 步骤 3：查看数据库服务器资源使用

```bash
# 查看容器 CPU 和内存使用
docker stats moling-db --no-stream

# 进入容器查看详细资源
docker exec -it moling-db bash
top
free -h
iostat -x 1 5  # 需要安装 sysstat
exit
```

#### 步骤 4：检查数据库锁等待

```bash
# 查看锁等待情况
docker exec -it moling-db psql -U moling -d moling -c "
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
"
```

### 恢复步骤

#### 方案 1：终止慢查询

```bash
# 找到慢查询的 PID
docker exec -it moling-db psql -U moling -d moling -c "
SELECT pid, query, now() - query_start AS duration
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;
"

# 终止特定查询（替换 <PID>）
docker exec -it moling-db psql -U moling -d moling -c "SELECT pg_terminate_backend(<PID>);"

# 批量终止长时间运行的查询（超过 30 秒）
docker exec -it moling-db psql -U moling -d moling -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - query_start > interval '30 seconds'
  AND pid <> pg_backend_pid();
"
```

#### 方案 2：添加缺失的索引

```bash
# 分析慢查询的执行计划
docker exec -it moling-db psql -U moling -d moling -c "EXPLAIN ANALYZE <SLOW_QUERY>;"

# 根据执行计划添加索引
docker exec -it moling-db psql -U moling -d moling -c "
CREATE INDEX CONCURRENTLY idx_table_column ON table_name(column_name);
"

# 查看现有索引
docker exec -it moling-db psql -U moling -d moling -c "\d table_name"
```

#### 方案 3：如果是连接池耗尽

```bash
# 查看后端应用连接池配置
cat moling-server/app/core/database.py | grep -i pool

# 重启后端服务（会关闭所有数据库连接）
docker restart moling-app

# 增加数据库连接池大小（修改代码后重启）
# 在 database.py 中：
# engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)
```

#### 方案 4：优化数据库配置

```bash
# 进入数据库容器
docker exec -it moling-db bash

# 编辑 PostgreSQL 配置
vim /var/lib/postgresql/data/postgresql.conf

# 关键参数调整：
# shared_buffers = 256MB          # 设置为内存的 25%
# effective_cache_size = 1GB      # 设置为内存的 75%
# maintenance_work_mem = 64MB     # 索引创建时的内存
# checkpoint_completion_target = 0.9
# wal_buffers = 16MB
# default_statistics_target = 100

# 重启数据库使配置生效
pg_ctl reload
exit
```

#### 方案 5：扩容数据库服务器

```bash
# 如果是 Docker 部署，可以调整容器资源限制
docker update --cpus=4 --memory=8g moling-db

# 或者升级到更高配置的服务器
```

### 预防措施

1. **启用慢查询日志**：
   ```sql
   -- 在 postgresql.conf 中设置
   log_min_duration_statement = 1000  -- 记录超过 1 秒的查询
   ```

2. **定期分析慢查询**：每周分析 `pg_stat_statements`，优化慢查询

3. **添加必要索引**：使用 `EXPLAIN ANALYZE` 分析查询计划

4. **使用连接池**：确保后端使用连接池（SQLAlchemy 默认启用）

5. **读写分离**：如果读请求量大，考虑添加只读副本

---

## 故障 3：前端部署失败

### 症状

- 前端页面无法加载（白屏、404、500 错误）
- 用户看到错误页面或旧版本页面
- `npm run build` 失败
- Docker 镜像构建失败

### 影响范围

- **严重性**：🟡 中
- **影响用户**：所有用户（前端不可用时）
- **常见原因**：构建错误、环境变量配置错误、Docker 镜像构建失败

### 检查步骤

#### 步骤 1：检查前端部署日志

```bash
# Docker 部署 - 查看构建日志
docker logs moling-web --tail 100

# Docker Compose 部署
docker-compose logs web

# 查看前端容器状态
docker ps | grep moling-web
```

#### 步骤 2：检查环境变量配置

```bash
# 检查前端环境变量
cat moling-web/.env.local
cat moling-web/.env.production

# 关键变量：
# NEXT_PUBLIC_API_BASE_URL=http://124.222.163.79:8080/moling/api/v1
# NODE_ENV=production

# 检查变量是否正确注入到构建中
docker exec -it moling-web printenv | grep NEXT_PUBLIC
```

#### 步骤 3：本地验证构建

```bash
# 进入前端目录
cd moling-web

# 安装依赖
npm ci

# 本地构建（会在 .next 目录生成构建产物）
npm run build

# 如果构建失败，根据错误信息修复
# 常见错误：
# - TypeScript 类型错误 → 修复类型定义
# - 模块找不到 → 检查 import 路径大小写
# - 内存不足 → 增加 Node.js 内存限制：NODE_OPTIONS="--max-old-space-size=4096"

# 本地启动构建产物验证
npm run start
```

#### 步骤 4：检查 Nginx 反向代理配置

```bash
# 检查 Nginx 配置
sudo nginx -t

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# 检查 Nginx 反向代理配置
cat /etc/nginx/conf.d/moling.conf
```

### 恢复步骤

#### 方案 1：回滚到上一个 Docker 镜像版本

```bash
# 查看历史镜像
docker images | grep moling-web

# 停止当前容器
docker stop moling-web
docker rm moling-web

# 启动上一个版本
docker run -d --name moling-web \
  --network moling-network \
  -p 3000:3000 \
  --restart unless-stopped \
  moling-web:<previous-version>

# 验证恢复
curl http://localhost:3000/moling/
```

#### 方案 2：修复构建错误后重新部署

```bash
# 1. 修复构建错误（根据 npm run build 的错误信息）
vim moling-web/src/...

# 2. 本地验证构建
cd moling-web
npm run build

# 3. 重新构建 Docker 镜像
docker build -t moling-web:latest .

# 4. 停止旧容器，启动新容器
docker stop moling-web
docker rm moling-web
docker run -d --name moling-web \
  --network moling-network \
  -p 3000:3000 \
  --restart unless-stopped \
  moling-web:latest

# 5. 验证部署
curl http://localhost:3000/moling/
```

#### 方案 3：检查并修复 Nginx 配置

```bash
# 测试 Nginx 配置
sudo nginx -t

# 如果配置错误，编辑配置
sudo vim /etc/nginx/conf.d/moling.conf

# 重载 Nginx 配置
sudo nginx -s reload

# 如果 Nginx 未启动
sudo systemctl start nginx
```

#### 方案 4：清理 Docker 缓存后重新构建

```bash
# 清理 Docker 构建缓存
docker builder prune -a

# 清理未使用的镜像
docker image prune -a

# 重新构建（无缓存）
docker build --no-cache -t moling-web:latest moling-web/

# 重新启动容器
docker stop moling-web
docker rm moling-web
docker run -d --name moling-web \
  --network moling-network \
  -p 3000:3000 \
  --restart unless-stopped \
  moling-web:latest
```

### 预防措施

1. **在 CI/CD 中进行构建验证**：确保构建通过后再部署

2. **使用 Docker 多阶段构建**：减小镜像体积，提高构建速度

3. **配置健康检查**：
   ```dockerfile
   # moling-web/Dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
     CMD curl -f http://localhost:3000/moling/ || exit 1
   ```

4. **保留历史版本**：不要立即删除旧版本镜像，以便快速回滚

---

## 故障 4：SSL 证书过期

### 症状

- 浏览器显示"**不安全连接**"或"**您的连接不是私密连接**"
- 用户无法访问网站（被浏览器阻止）
- 证书有效期已过期或即将过期（< 7 天）

### 影响范围

- **严重性**：🔴 高
- **影响用户**：所有用户
- **SLA 影响**：网站完全不可用

### 检查步骤

#### 步骤 1：检查证书有效期

```bash
# 方法 1：使用 openssl 检查证书
openssl x509 -in /etc/nginx/ssl/cert.pem -text -noout | grep "Not After"

# 方法 2：检查远程服务器的证书
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# 方法 3：使用 curl 检查
curl -v https://example.com 2>&1 | grep "expire"

# 方法 4：使用在线工具
# https://www.ssllabs.com/ssltest/
```

#### 步骤 2：检查证书文件路径和 Nginx 配置

```bash
# 检查 Nginx SSL 配置
cat /etc/nginx/conf.d/moling.conf | grep -A 10 "ssl_certificate"

# 检查证书文件是否存在
ls -lh /etc/nginx/ssl/

# 检查证书文件权限
chmod 644 /etc/nginx/ssl/cert.pem
chmod 600 /etc/nginx/ssl/privkey.pem
```

### 恢复步骤

#### 方案 1：使用 Let's Encrypt 重新申请证书（推荐）

```bash
# 1. 安装 certbot（如果未安装）
sudo apt-get update
sudo apt-get install certbot

# 2. 停止 Nginx（certbot 需要占用 80 端口）
sudo systemctl stop nginx

# 3. 申请证书（替换 example.com 为实际域名）
sudo certbot certonly --standalone -d example.com -d www.example.com

# 4. 将证书复制到 Nginx 目录
sudo cp /etc/letsencrypt/live/example.com/fullchain.pem /etc/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/example.com/privkey.pem /etc/nginx/ssl/privkey.pem

# 5. 设置自动续期（Let's Encrypt 证书有效期 90 天）
sudo crontab -e
# 添加以下行（每天凌晨 2 点尝试续期）
0 2 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx

# 6. 启动 Nginx
sudo systemctl start nginx

# 7. 验证证书
curl -v https://example.com 2>&1 | grep "expire"
```

#### 方案 2：使用商业证书

```bash
# 1. 购买商业 SSL 证书（DigiCert、GlobalSign 等）

# 2. 生成 CSR（证书签名请求）
openssl req -new -newkey rsa:2048 -nodes -keyout example.com.key -out example.com.csr

# 3. 将 CSR 提交给 CA（证书颁发机构）

# 4. 收到证书后，合并证书链
cat example.com.crt intermediate.crt root.crt > fullchain.crt

# 5. 将证书和私钥复制到 Nginx 目录
sudo cp fullchain.crt /etc/nginx/ssl/cert.pem
sudo cp example.com.key /etc/nginx/ssl/privkey.pem

# 6. 设置权限
sudo chmod 644 /etc/nginx/ssl/cert.pem
sudo chmod 600 /etc/nginx/ssl/privkey.pem

# 7. 测试并重启 Nginx
sudo nginx -t
sudo systemctl restart nginx
```

#### 方案 3：更新 Nginx 配置并重启

```bash
# 1. 编辑 Nginx 配置
sudo vim /etc/nginx/conf.d/moling.conf

# 2. 确保 SSL 配置正确
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # ... 其他配置
}

# 3. 测试配置
sudo nginx -t

# 4. 重启 Nginx
sudo systemctl restart nginx

# 5. 验证 HTTPS 访问
curl https://example.com
```

### 预防措施

1. **设置证书过期监控**：
   ```bash
   # 使用 Prometheus Blackbox Exporter 监控证书过期
   # 或使用在线监控服务（如 UptimeRobot）
   ```

2. **启用自动续期**：Let's Encrypt 证书配置 `certbot renew` 定时任务

3. **提前续期**：在证书过期前 30 天开始续期流程

4. **使用通配符证书**：如果需要多个子域名，申请通配符证书（`*.example.com`）

---

## 故障 5：Redis 连接失败

### 症状

- API 返回 500 错误
- 后端日志显示 `RedisConnectionError` 或 `ConnectionRefusedError`
- Celery 异步任务无法执行
- 缓存功能失效（但系统可能仍能正常工作）

### 影响范围

- **严重性**：🟡 中
- **影响用户**：所有用户（缓存失效会导致性能下降）
- **常见原因**：Redis 服务停止、网络问题、密码错误

### 检查步骤

#### 步骤 1：检查 Redis 容器状态

```bash
# 查看 Redis 容器状态
docker ps | grep moling-redis

# 查看 Redis 日志
docker logs moling-redis --tail 100

# 检查 Redis 是否运行
docker exec -it moling-redis redis-cli ping
# 预期输出：PONG
```

#### 步骤 2：检查 Redis 配置

```bash
# 查看 Redis 配置文件
docker exec -it moling-redis cat /etc/redis/redis.conf

# 关键配置：
# bind 0.0.0.0        # 允许远程连接
# port 6379            # 端口
# requirepass <password>  # 密码（如果设置了）
# maxmemory <bytes>    # 最大内存
# maxmemory-policy allkeys-lru  # 内存淘汰策略
```

#### 步骤 3：测试网络连接

```bash
# 从后端容器测试连接 Redis
docker exec -it moling-app ping redis

# 从后端容器测试 Redis 端口
docker exec -it moling-app nc -zv redis 6379

# 查看 Docker 网络
docker network inspect moling-network
```

### 恢复步骤

#### 方案 1：重启 Redis 服务

```bash
# 重启 Redis 容器
docker restart moling-redis

# 等待 Redis 启动
sleep 10

# 验证 Redis 就绪
docker exec -it moling-redis redis-cli ping

# 重启后端服务（重新建立 Redis 连接）
docker restart moling-app
```

#### 方案 2：清理 Redis 内存（如果内存耗尽）

```bash
# 查看 Redis 内存使用
docker exec -it moling-redis redis-cli info memory

# 清理所有缓存（⚠️ 会丢失所有缓存数据）
docker exec -it moling-redis redis-cli flushall

# 或者只清理当前数据库的缓存
docker exec -it moling-redis redis-cli flushdb
```

#### 方案 3：增加 Redis 内存限制

```bash
# 编辑 Redis 配置
docker exec -it moling-redis vim /etc/redis/redis.conf

# 修改 maxmemory 参数
maxmemory 2gb
maxmemory-policy allkeys-lru

# 重启 Redis 使配置生效
docker restart moling-redis
```

### 预防措施

1. **配置 Redis 持久化**：
   ```conf
   # 在 redis.conf 中启用 AOF 持久化
   appendonly yes
   appendfsync everysec
   ```

2. **设置内存淘汰策略**：避免内存耗尽导致 Redis 崩溃

3. **监控 Redis 内存使用**：使用 Prometheus + Grafana 监控

4. **使用 Redis Sentinel 或 Cluster**：实现高可用

---

## 故障 6：Celery Worker 异步任务堆积

### 症状

- 异步任务（如 AI 生成、文档处理）执行很慢或卡住
- Celery Worker 日志显示任务堆积
- Redis 中任务队列长度持续增长
- 用户反馈功能无响应（如点击"生成"后一直等待）

### 影响范围

- **严重性**：🟡 中
- **影响用户**：使用异步功能的用户
- **常见原因**：Worker 停止、任务执行失败、Redis 连接问题

### 检查步骤

#### 步骤 1：检查 Celery Worker 状态

```bash
# 查看 Worker 容器状态
docker ps | grep moling-worker

# 查看 Worker 日志
docker logs moling-worker --tail 100

# 进入 Worker 容器检查 Celery 状态
docker exec -it moling-worker celery -A app.core.celery_app status
```

#### 步骤 2：查看任务队列长度

```bash
# 查看 Redis 中的任务队列长度
docker exec -it moling-redis redis-cli llen celery

# 查看任务执行情况
docker exec -it moling-worker celery -A app.core.celery_app inspect active
docker exec -it moling-worker celery -A app.core.celery_app inspect reserved
docker exec -it moling-worker celery -A app.core.celery_app inspect scheduled
```

#### 步骤 3：检查任务执行日志

```bash
# 查看失败的任务
docker exec -it moling-redis redis-cli zrange celeryev.failures 0 -1

# 查看任务结果
docker exec -it moling-redis redis-cli lrange celeryev.task-result 0 -1
```

### 恢复步骤

#### 方案 1：重启 Celery Worker

```bash
# 重启 Worker 容器
docker restart moling-worker

# 等待 Worker 启动
sleep 30

# 验证 Worker 就绪
docker exec -it moling-worker celery -A app.core.celery_app status
```

#### 方案 2：清理卡住的任务

```bash
# 清理所有任务队列（⚠️ 会丢失所有待执行任务）
docker exec -it moling-redis redis-cli flushdb

# 或者只清理特定队列
docker exec -it moling-redis redis-cli del celery

# 重启 Worker
docker restart moling-worker
```

#### 方案 3：增加 Worker 并发数

```bash
# 编辑 Celery Worker 启动命令（在 docker-compose.yml 或 Dockerfile 中）
# 增加 --concurrency 参数
celery -A app.core.celery_app worker --loglevel=info --concurrency=10

# 重启 Worker
docker restart moling-worker
```

### 预防措施

1. **配置任务超时和重试**：
   ```python
   # 在 Celery 任务中配置
   @app.task(bind=True, max_retries=3, default_retry_delay=60)
   def my_task(self):
       try:
           # 任务逻辑
           pass
       except Exception as e:
           self.retry(exc=e)
   ```

2. **监控任务队列**：使用 Prometheus + Grafana 监控 Celery 指标

3. **使用任务结果后端**：将任务结果存储到数据库，便于排查问题

---

## 故障 7：磁盘空间不足

### 症状

- Docker 容器无法启动，报错"no space left on device"
- 日志文件占用大量磁盘空间
- 数据库或 Redis 数据持久化失败
- 系统变慢或崩溃

### 影响范围

- **严重性**：🔴 高
- **影响用户**：所有用户
- **常见原因**：日志文件未清理、Docker 镜像/容器未清理、数据库增长过快

### 检查步骤

#### 步骤 1：检查磁盘空间使用

```bash
# 查看磁盘空间
df -h

# 查看 Docker 占用的磁盘空间
docker system df

# 查看具体目录占用
du -sh /var/lib/docker/*
du -sh moling-server/logs/*
```

#### 步骤 2：清理 Docker 资源

```bash
# 清理未使用的镜像、容器、网络、卷
docker system prune -a

# 清理特定类型的资源
docker image prune -a      # 清理未使用的镜像
docker container prune -a  # 清理停止的容器
docker volume prune        # 清理未使用的卷
docker network prune       # 清理未使用的网络
```

#### 步骤 3：清理应用日志

```bash
# 查看日志文件大小
du -sh moling-server/logs/*

# 清理日志文件（保留最近 7 天）
find moling-server/logs/ -name "*.log" -mtime +7 -delete

# 或者清空日志文件（不删除文件）
truncate -s 0 moling-server/logs/*.log
```

### 恢复步骤

#### 方案 1：清理磁盘空间

```bash
# 1. 清理 Docker 资源
docker system prune -a

# 2. 清理系统日志
sudo journalctl --vacuum-time=7d

# 3. 清理 apt 缓存（Ubuntu/Debian）
sudo apt-get clean

# 4. 清理临时文件
sudo rm -rf /tmp/*

# 5. 验证磁盘空间
df -h
```

#### 方案 2：扩容磁盘

```bash
# 如果是云服务器，可以在控制台扩容磁盘
# 然后扩展文件系统（以 ext4 为例）
sudo resize2fs /dev/sda1
```

#### 方案 3：迁移 Docker 数据目录

```bash
# 1. 停止 Docker 服务
sudo systemctl stop docker

# 2. 迁移 Docker 数据到新磁盘
sudo mv /var/lib/docker /mnt/new-disk/docker

# 3. 创建软链接
sudo ln -s /mnt/new-disk/docker /var/lib/docker

# 4. 启动 Docker 服务
sudo systemctl start docker
```

### 预防措施

1. **配置日志轮转**：
   ```bash
   # 编辑 /etc/logrotate.d/docker
   /var/lib/docker/containers/*/*.log {
       rotate 7
       daily
       compress
       size 100M
       missingok
       delaycompress
       copytruncate
   }
   ```

2. **设置 Docker 镜像清理定时任务**：
   ```bash
   # 添加到 crontab（每天凌晨 3 点清理）
   0 3 * * * docker system prune -a -f
   ```

3. **监控磁盘使用**：使用 Prometheus + Grafana 监控磁盘使用率

---

## 附录：常用命令速查

### Docker 常用命令

```bash
# 查看所有容器
docker ps -a

# 查看容器日志
docker logs -f <container_name>

# 进入容器
docker exec -it <container_name> bash

# 查看容器资源使用
docker stats

# 重启容器
docker restart <container_name>

# 停止并删除容器
docker stop <container_name>
docker rm <container_name>
```

### 数据库常用命令

```bash
# 进入数据库
docker exec -it moling-db psql -U moling -d moling

# 查看所有表
\dt

# 查看表结构
\d table_name

# 导出数据库
docker exec -it moling-db pg_dump -U moling moling > backup.sql

# 导入数据库
docker exec -it moling-db psql -U moling moling < backup.sql
```

### Redis 常用命令

```bash
# 进入 Redis CLI
docker exec -it moling-redis redis-cli

# 查看所有键
KEYS *

# 查看键类型
TYPE <key>

# 删除键
DEL <key>

# 清空所有数据库
FLUSHALL

# 查看信息
INFO
```

---

## 文档维护

- **版本**: 1.0.0
- **最后更新**: 2026-06-16
- **维护者**: Moling Team
- **更新频率**: 每次发生故障处理后，更新本文档

---

**END**
