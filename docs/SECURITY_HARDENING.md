# 墨灵项目安全加固文档

## 概述

本文档记录了墨灵项目实施的安全加固措施：

1. **Rate Limiting（速率限制）** - 防止暴力破解
2. **JWT 黑名单** - 实现登出立即失效
3. **HTTPS 强制 + HSTS** - 传输层安全
4. **SQL 注入防护审计** - 代码审计结果
5. **CSP 防 XSS** - 内容安全策略
6. **Content-Length 请求体限制** - DoS 防护
7. **Refresh Token 轮换** - 防止 Token 泄露滥用

---

## 1. Rate Limiting（速率限制）

### 实现方式

使用 `slowapi` 库实现端点级速率限制。

### 安装依赖

```bash
cd moling-server
pip install slowapi>=0.1.9
```

或在 `pyproject.toml` 中已添加：

```toml
"slowapi>=0.1.9",  # Rate limiting
```

### 配置位置

**文件**: `moling-server/app/main.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# 初始化 slowapi limiter（用于端点级速率限制）
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter

# 添加 SlowAPI 中间件
app.add_middleware(SlowAPIMiddleware)
```

### 端点限速配置

**文件**: `moling-server/app/router/auth.py`

| 端点 | 速率限制 | 说明 |
|------|-----------|------|
| `/auth/register` | 3 次/分钟 | 防止批量注册 |
| `/auth/login` | 5 次/分钟 | 防止暴力破解密码 |
| `/auth/password-reset-request` | 3 次/分钟 | 防止邮件轰炸 |
| 其他 API | 100 次/分钟 | 全局默认限制 |

### 代码示例

```python
from app.main import limiter

@router.post("/login", response_model=TokenResp)
@limiter.limit("5/minute")  # 登录限制：5 次/分钟
async def login(
    request: Request,
    req: LoginReq,
    db: SyncSession = Depends(get_sync_db),
) -> TokenResp:
    """使用邮箱和密码登录并返回令牌。"""
    # ...
```

### 测试速率限制

```bash
# 测试登录端点速率限制
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrongpass"}' \
    -v 2>&1 | grep -E "(HTTP|x-rate-limit)"
done
```

---

## 2. JWT 黑名单（登出立即失效）

### 实现方式

使用 Redis 存储已登出的 token JTI (JWT ID)，实现登出后 token 立即失效。

### 依赖要求

- `redis>=5.2.0` (已在 `pyproject.toml` 中)
- Redis 服务器（本地或远程）

### 配置位置

**文件**: `moling-server/app/auth/blacklist.py`

### 实现细节

#### 2.1 Token 创建时加入 JTI

**文件**: `moling-server/app/service/auth_service.py`

```python
def _create_access_token(user_id: int) -> tuple[str, str, int]:
    """Create a short-lived access token (15 min).
    
    Returns:
        tuple: (token, jti, expires_in)
    """
    import uuid
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    jti = str(uuid.uuid4())  # 生成唯一的 JWT ID
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire, "jti": jti}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, 15 * 60
```

#### 2.2 黑名单操作

**文件**: `moling-server/app/auth/blacklist.py`

```python
def add_to_blacklist(jti: str, expires_in: int) -> bool:
    """
    将 JWT Token 加入黑名单.
    
    Args:
        jti: JWT ID (从 token payload 中获取)
        expires_in: token 剩余有效期（秒），用于设置 Redis key 的 TTL
        
    Returns:
        bool: 是否成功加入黑名单
    """
    redis_conn = _get_redis()
    if redis_conn is None:
        logging.warning("Redis 不可用，跳过黑名单操作")
        return False
    
    try:
        # 使用 setex 设置带 TTL 的 key
        redis_conn.setex(f"blacklist:{jti}", expires_in, "1")
        return True
    except Exception as e:
        logging.error(f"加入黑名单失败: {e}")
        return False


def is_blacklisted(jti: str) -> bool:
    """
    检查 JWT Token 是否在黑名单中.
    """
    redis_conn = _get_redis()
    if redis_conn is None:
        # Redis 不可用，降级处理：不阻止请求
        return False
    
    try:
        return redis_conn.exists(f"blacklist:{jti}") == 1
    except Exception as e:
        logging.error(f"检查黑名单失败: {e}")
        return False
```

#### 2.3 Token 验证时检查黑名单

**文件**: `moling-server/app/dependencies.py`

```python
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security),
    db: Session = Depends(get_sync_db),
):
    """Extract and validate the JWT, returning the authenticated user."""
    # ... JWT decode ...
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti is not None:
        from app.auth.blacklist import is_blacklisted
        
        if is_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效，请重新登录",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # ... continue ...
```

#### 2.4 登出端点

**文件**: `moling-server/app/router/auth.py`

```python
@router.post("/logout", status_code=200)
async def logout(
    req: LogoutReq,
) -> dict:
    """登出用户（将 token 加入黑名单）。"""
    try:
        result = await auth_service.logout(req.access_token, req.refresh_token)
        return result
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=str(e.detail))
        raise HTTPException(status_code=500, detail="登出失败")
```

### Redis 配置

在 `.env` 或环境变量中配置：

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # 可选
```

### 部署说明

1. **安装 Redis**:

   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   
   # Docker
   docker run -d -p 6379:6379 --name moling-redis redis:7-alpine
   ```

2. **更新 docker-compose.yml**（可选）:

   在 `docker-compose.yml` 中添加 Redis 服务：

   ```yaml
   services:
     redis:
       image: redis:7-alpine
       container_name: moling-redis
       restart: unless-stopped
       ports:
         - "6379:6379"
       volumes:
         - redisdata:/var/lib/redis/data
       networks:
         - moling-net
   
   volumes:
     redisdata:
   ```

---

## 3. HTTPS 强制 + HSTS

### 实现方式

在 Nginx 配置中强制 HTTP -> HTTPS 跳转，并添加安全响应头。

### 配置位置

**文件**: `docker/nginx/nginx.conf`

### 关键配置

#### 3.1 HTTP 强制跳转 HTTPS

```nginx
server {
    listen 80;
    listen [::]:80;
    
    server_name localhost yourdomain.com;
    
    # 强制 HTTP -> HTTPS 跳转
    return 301 https://$server_name$request_uri;
}
```

#### 3.2 HTTPS 服务器配置

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name localhost yourdomain.com;
    
    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    # SSL 配置优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全响应头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; ..." always;
}
```

### 安全响应头说明

| 响应头 | 值 | 作用 |
|--------|-----|------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` | 强制浏览器使用 HTTPS（1 年） |
| `X-Content-Type-Options` | `nosniff` | 防止 MIME 类型嗅探（XSS 防护） |
| `X-Frame-Options` | `DENY` | 防止点击劫持（禁止在 frame 中显示） |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | 控制 Referrer 头泄露 |
| `Content-Security-Policy` | 见配置 | 防止 XSS 攻击 |

### SSL 证书获取

#### 使用 Let's Encrypt（推荐）

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 自动续期（已自动配置 cron）
sudo certbot renew --dry-run
```

#### 使用自签名证书（开发环境）

```bash
# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout private.key \
  -out certificate.crt \
  -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"

# 合并为 fullchain.pem（Nginx 需要）
cat certificate.crt > fullchain.pem
```

---

## 4. SQL 注入防护审计

### 审计结果

**状态**: ✅ 通过 - 未发现 SQL 注入漏洞

### 审计范围

- `moling-server/app/dao/*.py` - 所有 DAO 文件
- `moling-server/app/service/*.py` - 所有 Service 文件

### 安全检查项

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 使用 ORM 查询 | ✅ | 所有查询使用 SQLAlchemy ORM |
| 参数化查询 | ✅ | 未发现字符串拼接 SQL |
| 输入验证 | ✅ | 使用 Pydantic 模型验证 |
| 原生 SQL | ⚠️ | 未发现（如需要，必须使用参数化） |

### 安全代码示例

**✅ 安全** - 使用 SQLAlchemy ORM：

```python
# 文件：moling-server/app/dao/user_dao.py

async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
    """Find a user by their email address."""
    stmt = select(User).where(User.email == email)  # ✅ 安全：ORM 自动参数化
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

**✅ 安全** - 使用参数化查询：

```python
from sqlalchemy import text

# 如果需要原生 SQL，必须使用参数化
result = await db.execute(
    text("SELECT * FROM users WHERE id = :user_id"),
    {"user_id": user_id}  # ✅ 安全：参数化
)
```

**❌ 危险** - 字符串拼接（未发现）：

```python
# ❌ 危险：SQL 注入漏洞
result = await db.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))

# ❌ 危险：SQL 注入漏洞
sql = "SELECT * FROM users WHERE name = '" + user_input + "'"
result = await db.execute(text(sql))
```

### 建议

1. **继续使用 ORM**: 避免编写原生 SQL 查询
2. **如果必须使用原生 SQL**: 始终使用参数化查询（命名参数 `:param` 或位置参数 `$1`）
3. **输入验证**: 所有用户输入先通过 Pydantic 模型验证
4. **最小权限原则**: 数据库用户只授予必要的权限

---

## 5. CSP 防 XSS

### 实现方式

在 Next.js 应用中配置 Content Security Policy，防止 XSS 攻击。

### 配置位置

**文件**: `moling-web/src/app/layout.tsx`

### 配置内容

```typescript
export const metadata: Metadata = {
  // ... 其他 metadata ...
  
  other: {
    'Cache-Control': 'no-cache',
    
    // Content Security Policy (CSP) - 防止 XSS 攻击
    'Content-Security-Policy': `
      default-src 'self';
      script-src 'self' 'unsafe-eval' https://www.googletagmanager.com;
      style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
      img-src 'self' data: https: blob:;
      font-src 'self' https://fonts.gstatic.com;
      connect-src 'self' https://api.yourdomain.com wss://api.yourdomain.com;
      frame-src 'self';
      media-src 'self' blob:;
      object-src 'none';
    `.replace(/\s+/g, ' ').trim(),
  },
};
```

### CSP 指令说明

| 指令 | 值 | 说明 |
|------|-----|------|
| `default-src` | `'self'` | 默认策略：只允许同源资源 |
| `script-src` | `'self' 'unsafe-eval'` | 脚本来源：同源 + Google Tag Manager |
| `style-src` | `'self' 'unsafe-inline'` | 样式来源：同源 + 内联样式（Next.js 需要） |
| `img-src` | `'self' data: https: blob:` | 图片来源：同源 + data URIs + HTTPS + Blob |
| `font-src` | `'self' https://fonts.gstatic.com` | 字体来源：同源 + Google Fonts |
| `connect-src` | `'self' https://api.yourdomain.com` | AJAX/WebSocket 连接：API 服务器 |
| `frame-src` | `'self'` | iframe 来源：只允许同源 |
| `media-src` | `'self' blob:` | 媒体来源：同源 + Blob |
| `object-src` | `'none'` | 禁止加载插件（Flash 等） |

### 同时配置 Nginx CSP

**文件**: `docker/nginx/nginx.conf`

```nginx
# Content Security Policy (CSP) — 防止 XSS 攻击
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.yourdomain.com wss://api.yourdomain.com;" always;
```

### 调试 CSP

在开发环境中，使用 `Content-Security-Policy-Report-Only` 头来代替 `Content-Security-Policy`，这样只会报告违规而不会阻止：

```typescript
other: {
  'Content-Security-Policy-Report-Only': '...',  // 只报告，不阻止
}
```

### 常见问题

#### 1. Next.js 需要 `'unsafe-inline'` 和 `'unsafe-eval'`

Next.js 的开发模式需要这些选项。生产构建通常会内联样式和脚本，因此可能仍然需要 `'unsafe-inline'`。

**解决方案**: 使用 Next.js 的 `nonce` 支持（需要自定义 Document 组件）。

#### 2. 第三方脚本被阻止

如果使用了 Google Analytics、Stripe 等第三方服务，需要将它们的域名添加到相应的 CSP 指令中。

示例：

```typescript
script-src 'self' https://www.googletagmanager.com https://js.stripe.com;
connect-src 'self' https://api.yourdomain.com https://www.google-analytics.com;
```

---

## 6. Content-Length 请求体限制

> **新增于 2026-06-21 R1+R2 架构加固**

### 目标

在 ASGI 层前置拦截超大请求体，**在读取 body 之前**就根据 `Content-Length` 头拒绝，防止大请求体内存攻击。

### 实现位置

**文件**: `moling-server/app/middleware/content_length_limit.py`

### 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEFAULT_MAX_SIZE` | 10MB | 通过 `MAX_BODY_SIZE` 环境变量覆盖 |
| `excluded_paths` | `("/api/v1/import/upload",)` | 排除路径白名单 |

### 413 响应格式

```json
{
  "code": 41301,
  "message": "请求体过大",
  "data": null,
  "meta": {
    "max_size": 10485760,
    "request_id": "...",
    "timestamp": "2026-06-21T02:00:00Z"
  }
}
```

### 集成方式

在 `app/main.py` 中通过 `app.add_middleware()` 注册，位于其他中间件之前。

---

## 7. Refresh Token 轮换

> **新增于 2026-06-21 R1 架构加固**

### 目标

防止 Refresh Token 泄露后的长期滥用。
登录接口返回 `access_token` + `refresh_token`，
`POST /api/v1/auth/refresh` 端点实现轮换逻辑：
- 验证 refresh token → 签发新 access token + 新 refresh token
- 旧 refresh token 加入 Redis 黑名单（TTL = 原过期时间）

### 安全优势

- 即使 Refresh Token 被窃取，旧 Token 也会在下次合法使用时被作废
- 攻击者无法同时持有新旧两个有效 Token
- 黑名单持久化在 Redis 中，Worker/Celery 共享

---

## 部署检查清单

### 1. 环境变量

确保生产环境中设置了以下环境变量：

```bash
# .env.production

# 强制 HTTPS（生产环境）
ENVIRONMENT=production

# Secret Key（必须修改！）
SECRET_KEY=your-super-secret-key-change-this

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS 配置（生产环境必须指定域名）
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate Limiting
RATE_LIMIT_CALLS=1000
RATE_LIMIT_PERIOD=60
```

### 2. Redis 部署

**Docker Compose**（推荐）:

更新 `docker-compose.yml`，添加 Redis 服务（见第 2 节）。

**独立部署**:

```bash
# 安装 Redis
sudo apt-get install redis-server

# 配置 Redis（绑定、密码、最大内存等）
sudo vim /etc/redis/redis.conf

# 启动 Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 3. SSL 证书

**生产环境**（必须）:

```bash
# 使用 Let's Encrypt
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 将证书挂载到 Nginx 容器
# docker-compose.yml:
services:
  nginx:
    volumes:
      - ./ssl:/etc/nginx/ssl:ro
```

**开发环境**（可选）:

使用自签名证书或注释掉 Nginx 配置中的 SSL 证书行。

### 4. Nginx 配置测试

```bash
# 测试 Nginx 配置
docker exec moling-nginx nginx -t

# 重新加载 Nginx 配置
docker exec moling-nginx nginx -s reload

# 测试 HTTPS
curl -I https://yourdomain.com

# 测试 HSTS
curl -I https://yourdomain.com | grep -i "strict-transport"
```

### 5. 安全扫描

```bash
# 使用 OWASP ZAP 或 Nikto 进行安全扫描
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://yourdomain.com

# 使用 SSL Labs 测试 SSL 配置
# 访问：https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

---

## 故障排查

### 1. Redis 连接失败

**症状**: 日志显示 `Redis 连接失败，黑名单功能禁用`

**解决方案**:

```bash
# 检查 Redis 是否运行
redis-cli ping

# 检查 Redis 配置（moling-server/.env）
REDIS_HOST=localhost  # 如果在 Docker 中，使用容器名
REDIS_PORT=6379

# 检查防火墙
sudo ufw allow 6379
```

### 2. Rate Limiting 不生效

**症状**: 超过限制后仍能发送请求

**解决方案**:

1. 检查 `slowapi` 是否正确安装
2. 检查中间件顺序（`SlowAPIMiddleware` 必须在路由注册之前添加）
3. 检查装饰器是否正确应用（`@limiter.limit()`）

### 3. CSP 阻止了合法资源

**症状**: 浏览器控制台显示 CSP 违规错误

**解决方案**:

1. 检查浏览器控制台的 CSP 违规报告
2. 将需要的域名添加到相应的 CSP 指令中
3. 在开发环境中使用 `Content-Security-Policy-Report-Only` 来调试

### 4. HTTPS 证书错误

**症状**: 浏览器显示 `NET::ERR_CERT_AUTHORITY_INVALID`

**解决方案**:

1. 检查证书路径是否正确
2. 确保证书文件权限正确（`chmod 644`）
3. 使用 Let's Encrypt 代替自签名证书（生产环境）

---

## 安全加固检查表

完成以下检查项，确保所有安全加固措施已正确实施：

- [ ] `slowapi` 已安装
- [ ] Rate Limiting 装饰器已应用到认证端点
- [ ] JWT token 包含 `jti` 字段
- [ ] 登出端点已将 token 加入黑名单
- [ ] Token 验证时检查黑名单
- [ ] Redis 密码已设置（生产环境）并验证
- [ ] Content-Length 中间件已注册，MAX_BODY_SIZE 已配置
- [ ] Refresh Token 轮换端点已测试
- [ ] Nginx 配置包含 HTTPS 强制跳转
- [ ] Nginx 配置包含所有安全响应头
- [ ] SSL 证书已配置（生产环境）
- [ ] Next.js 应用配置了 CSP
- [ ] 所有 ORM 查询都使用参数化（无字符串拼接）
- [ ] 生产环境变量已正确设置
- [ ] 安全扫描已完成，无高危漏洞

---

## 附录：快速部署命令

```bash
# 1. 安装依赖
cd moling-server
pip install -e .

# 2. 部署 Redis（Docker）
docker run -d -p 6379:6379 --name moling-redis redis:7-alpine

# 3. 更新 docker-compose.yml（添加 Redis）
# 见第 2 节

# 4. 获取 SSL 证书（生产环境）
sudo certbot --nginx -d yourdomain.com

# 5. 构建并启动所有服务（Docker）
docker-compose up -d --build

# 6. 测试安全配置
curl -I http://yourdomain.com  # 应返回 301 跳转到 HTTPS
curl -I https://yourdomain.com  # 应返回 HSTS 头

# 7. 查看日志
docker-compose logs -f app
```

---

## 维护建议

1. **定期更新依赖**: 每月检查并更新依赖包（`pip list --outdated`）
2. **监控失败登录**: 使用 Prometheus/Grafana 监控速率限制触发情况
3. **审查访问日志**: 定期检查 Nginx 访问日志中的异常请求
4. **续期 SSL 证书**: Let's Encrypt 证书每 90 天需续期（已自动配置）
5. **备份 Redis 数据**: 如果黑名单数据重要，配置 Redis 持久化

---

**文档版本**: 1.1.0  
**最后更新**: 2026-06-21  
**作者**: Moling Team
