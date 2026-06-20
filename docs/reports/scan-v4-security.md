# 墨灵 (Moling) — 安全审计报告 v4

> **扫描器**: security-scanner (deep-scan-v4)
> **审计日期**: 2026-06-21
> **扫描范围**: `app/config.py`, `app/dependencies.py`, `app/router/auth.py`, `app/service/auth_service.py`, `app/auth/blacklist.py`, `app/errors.py`, `app/schemas/auth.py`, `app/schemas/admin.py`, `app/middleware/audit_log.py`, `app/middleware/rate_limit.py`, `app/main.py`, `app/router/admin.py`
> **完整性**: very thorough — 逐行审查 14 项安全清单

---

## 1. JWT 签名

### 配置

- **算法**: HS256（对称签名）
- **密钥**: `config.py:48` → `SECRET_KEY: str = "dev-secret-key-change-in-production"`（开发默认值）
- **算法白名单**: `dependencies.py:319` → `algorithms=[settings.ALGORITHM]` — 显式传入算法列表

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| HS256 vs RS256 | HS256 | 对称算法，密钥泄露 = 任意伪造 |
| 防 "none" 算法 | 安全 | `jwt.decode(... algorithms=[settings.ALGORITHM])` 显式指定，python-jose 拒绝 "none" |
| 密钥迁移路径 | 缺失 | 无 RS256 升级路径；对称算法不适合多服务架构 |

**风险评估**: 低（开发） / 中（生产 — 取决于实际密钥强度）

### 建议

- 生产环境：通过环境变量设置至少 32 字节随机密钥（`openssl rand -hex 32`）
- 多服务架构：考虑迁移到 RS256/ES256 非对称签名
- 增加密钥轮换机制（`config.py` 中有无 key-version header？无）

---

## 2. 密钥管理

### 配置

- `config.py:48`: `SECRET_KEY: str = "dev-secret-key-change-in-production"`
- `config.py:172-189`: `_reject_production_default_secret` validator — 生产环境拒绝默认 key

### 审计发现

| 项目 | 状态 | 详情 |
|------|------|------|
| 硬编码密钥 | 警告 | 开发默认值 `"dev-secret-key-change-in-production"` 可用于 JWT 签名 |
| 生产防护 | 安全 | `ENVIRONMENT="production"` 时 REFUSE 启动 |
| 密钥轮换 | 缺失 | 无 key rotation，无 kid/jwk header |
| .env 泄露风险 | 警告 | 依赖 .env 文件，无 vault/HashiCorp/cloud KMS 集成 |
| 密钥日志泄露 | 安全 | 未发现 SECRET_KEY 出现在日志或响应中 |

**风险评估**: 中（无轮换，单密钥长期使用风险）

### 建议

- 添加密钥轮换支持：在 JWT payload 中加入 `kid` (Key ID)，支持多密钥并存
- 考虑集成 cloud KMS（AWS KMS / GCP Secret Manager / Azure Key Vault）或 HashiCorp Vault
- 添加自动化密钥强度检查（启动时验证 `len(SECRET_KEY) >= 32`）

---

## 3. Token 过期时间

### 当前配置

```python
# config.py:52-53
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

### **严重 BUG：Refresh Token 过期时间不一致**

```
auth_service.py:67  →  expire = datetime.now(timezone.utc) + timedelta(days=30)   # ❌ 硬编码 30 天
config.py:53        →  REFRESH_TOKEN_EXPIRE_DAYS: int = 7                         # ✓ 配置 7 天
```

`_create_refresh_token()` 在 `auth_service.py:59-71` 中硬编码 `timedelta(days=30)`，完全忽略 `settings.REFRESH_TOKEN_EXPIRE_DAYS`。

| Token 类型 | 配置值 | 实际值 | 差距 |
|------------|--------|--------|------|
| Access Token | 15 min | 15 min (硬编码) | 一致 |
| Refresh Token | 7 days | **30 days** (硬编码) | **4x 超额** |

**风险评估**: **高** — Refresh Token 有效期是预期的 4 倍+，扩大 Token 泄露窗口

### 建议

立即修复 `_create_refresh_token()` 使用 `settings.REFRESH_TOKEN_EXPIRE_DAYS`：

```python
def _create_refresh_token(user_id: int) -> tuple[str, str, int]:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS  # ← 使用配置值
    )
    ...
```

同样检查 `_create_access_token` 是否也忽略配置：
```python
# auth_service.py:52 — 同样硬编码 15 分钟，未使用 settings.ACCESS_TOKEN_EXPIRE_MINUTES
expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # ❌ 硬编码
```

---

## 4. Refresh Token 轮换

### 实现位置

- `auth_service.py:382-432` — `refresh_tokens()` 方法
- `auth/blacklist.py:56-81` — `add_to_blacklist()`

### 当前流程

```
1. 解码旧 Refresh Token → 提取 old_jti, old_exp
2. 计算剩余 TTL = max(0, exp - now)     ← 等于剩余有效期
3. add_to_blacklist(old_jti, old_ttl)    ← Redis SETEX with TTL
4. 签发新的 access token + refresh token
```

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| Token 轮换 | 安全 | 旧 refresh token 使用时立即黑名单 |
| Redis TTL = 剩余有效期 | 安全 | `old_ttl = max(0, int(exp - now))` |
| 轮换 race condition | 警告 | 新 token 签发后旧 token 黑名单，但若新 token 生成后请求中断，旧 token 已失效 |
| 降级策略 | 警告 | Redis 不可用时 `add_to_blacklist` 返回 False 而静默失败 |
| 轮换链检测 | 缺失 | 无检测"旧 refresh token 已被轮换"的逻辑 |

**风险评估**: 低 — 轮换机制基本正确，边缘场景概率低

### 建议

- 在轮换中间件或网关层添加 "reuse detection"：如果一个已轮换的 refresh_token 被再次使用，立即将该用户所有 token 加入黑名单（安全审计事件）
- 确保轮换操作是原子的（当前步骤 3 和 4 之间无事务保护）

---

## 5. 密码哈希

### 配置

```python
# auth_service.py:27
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| 算法 | bcrypt | 当前推荐算法 |
| rounds | 未显式设置 | passlib defaults ≈ 12 rounds (auto) |
| rounds 适配 | 缺失 | 未根据服务器性能调整 rounds |
| 已废弃算法 | 无 | 未使用 MD5/SHA1 |
| 密码升级路径 | 缺失 | 无 `deprecated=["auto"]` 的升级方案 |
| seed_data 中 | 重复定义 | `mock/seed_data.py:37` 和 `setting_service.py:19` 各有独立的 CryptContext |

### 安全说明

`deprecated="auto"` 意味着 passlib 会自动处理 bcrypt 格式升级。但未显式设置 rounds，默认 bcrypt__identify 为 "2b"，rounds=12。OWASP 建议 2024 年 bcrypt 至少 12 rounds，但已边界。

**风险评估**: 低 — bcrypt 是安全的，但 rounds 未显式声明

### 建议

- 显式设置 rounds：`CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)`
- 性能测试后在 `config.py` 中添加 `BCRYPT_ROUNDS` 配置项
- 统一 CryptContext 实例（避免在 3 个文件中重复定义）

---

## 6. 会话管理

### 架构

- 使用 JWT (stateless) — 无服务端会话
- Token 存储在客户端（假设为 localStorage 或 cookie）
- 登出通过 Redis 黑名单（JTI）实现

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| 会话固定风险 | 安全 | JWT 无会话，每次请求独立验证 |
| Token 存储位置 | 未指定 | 客户端决定；若用 localStorage 存在 XSS 风险 |
| 黑名单降级 | 警告 | Redis 不可用时 `is_blacklisted()` 返回 False，允许所有 token |
| 多设备会话 | 缺失 | 无法区分/管理多设备会话 |
| 并发登录限制 | 缺失 | 无限制同用户同时登录数 |
| Token 吊销 | 部分 | 只能通过 logout 端点吊销；无 admin 强制吊销 |

**风险评估**: 中（黑名单降级 + 无并发限制）

### 建议

- Redis 不可用时使用本地内存 LRU 缓存作为降级方案，或拒绝请求（配置 `FAIL_OPEN` vs `FAIL_CLOSED` 策略）
- 添加 Token 吊销列表 API 供管理员使用
- 考虑添加设备标识（user-agent hash）到 JWT payload，异常设备拒绝

---

## 7. CSRF 防护

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| CSRF Token | 不需要 | Bearer Token 认证（Authorization header），非 Cookie-based |
| 状态 | 安全 | CSRF 仅影响 cookie 携带凭证的场景；Bearer Token 无法被 CSRF 利用 |
| SPA 场景 | 安全 | 前端手动在请求头中加入 `Authorization: Bearer <token>` |

**风险评估**: N/A — Bearer Token 架构天然免疫 CSRF

---

## 8. 权限模型

### 当前实现

1. **User 模型** (`models/user.py:46-51`):
   ```python
   status: Mapped[str] = mapped_column(String(20), default="active",
        comment="用户状态: active / disabled / admin")
   ```

2. **Admin 检查** (`dependencies.py:386-400`):
   ```python
   if getattr(current_user, "status", None) != "admin":
       raise PermissionError(detail="需要管理员权限")
   ```

3. **Admin 端点保护** (`router/admin.py`)：所有端点使用 `_admin=Depends(require_admin)`

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| RBAC 完整性 | 不完整 | 将角色混入 status 字段；只有 "admin"/"active"/"disabled" 三种状态 |
| 角色定义 | 模糊 | status 既是"账户状态"又是"角色"；没有独立的 roles 表 |
| Admin 自保护 | 缺失 | admin 可修改任意用户（包括其他 admin）的 status |
| 细粒度权限 | 无 | 无项目级/章节级/操作级权限控制 |
| 权限提升 | 潜在风险 | `admin/update_user` PATCH 路由使用 `setattr(user, field, value)` 可修改任意模型字段 |

### Admin UpdateUserReq 重大发现

`schemas/admin.py:83-90` 定义了 `role` 字段：
```python
class UpdateUserReq(BaseModel):
    role: Optional[str] = Field(default=None, description="角色")  # ← 此字段在 User 模型中不存在
```

但 User 模型没有 `role` 属性。Admin 端点的 `if hasattr(user, field)` 检查会静默忽略 "role" → admin 无法通过此字段更改角色。只有 `status` 字段有效。

**风险评估**: 中 — RBAC 不够成熟，admin 端点存在静默忽略的安全问题

### 建议

- 将角色与状态解耦：添加 `user_role` 独立列
- 实现完整的 RBAC：定义角色（admin/moderator/user/premium_user）和权限（create_project/delete_user/view_stats...）
- 添加 admin 自我保护：admin 不能降级/删除自己
- 修复 `UpdateUserReq.role` 字段（映射到正确模型属性 或 移除）

---

## 9. 审计日志

### 实现

`middleware/audit_log.py:45-165` — `AuditLogMiddleware`

### 记录内容

| 字段 | 记录 | 说明 |
|------|------|------|
| 时间戳 | 是 | `"%Y-%m-%dT%H:%M:%S%z"` |
| HTTP 方法 | 是 | `request.method` |
| 请求路径 | 是 | `request.url.path` |
| Query 参数 | 是 | 密码参数被过滤为 `[FILTERED]` |
| 客户端 IP | 是 | 支持 X-Forwarded-For / X-Real-IP |
| User-Agent | 是 | 用于安全事件分析 |
| 用户 ID/Email | 是 | 尝试从 JWT 解析（允许过期 token） |
| 响应状态码 | 是 | 正常和异常路径均记录 |
| 响应耗时 | 是 | `duration_ms` |
| 错误详情 | 是 | exception 路径记录 `error` 字段 |
| Request ID | 是 | 用于全链路追踪 |

### 排除路径

- `/health`, `/docs`, `/redoc`, `/openapi.json`, `/docs-static`

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| 登录审计 | 是 | 中间件层面记录（路径 + 用户 + 状态码） |
| 登出审计 | 是 | 同上 |
| 关键操作审计 | 部分 | admin 路由记录 → 但不记录具体操作类型 |
| 日志格式 | 安全 | JSON 结构化，按天轮转，保留 30 天 |
| 请求体记录 | 小心 | `request.state.body` 可能包含密码等敏感数据 |

**注意**: `dispatch()` 中 `request.state.body = body_bytes.decode(...)` 会存储完整请求体到 request.state，包括注册/登录时的明文密码。虽不直接写入审计日志，但在错误处理路径中可能被意外暴露。

**风险评估**: 低 — 审计日志覆盖完善

### 建议

- 在 `request.state.body` 存储前对敏感字段（password, token, refresh_token）进行脱敏
- 添加登录/登出事件的专门审计日志条目（带事件类型标记：login_success, login_failed, logout, token_refresh）
- 记录操作类型到审计日志（如：admin.llm_config_update）

---

## 10. 密码策略

### 当前实现

#### 注册 (`schemas/auth.py:18-20`)
```python
password: str = Field(..., min_length=8, max_length=128, description="密码 (至少 8 位)")
```

#### 密码重置 (`schemas/auth.py:77`)
```python
new_password: str = Field(..., min_length=8, max_length=128, description="新密码 (至少 8 位)")
```

#### 修改密码 (`setting_service.py:104-109`)
```python
if len(new_password) < 8:
    raise ValidationError(...)
```

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| 最小长度 | 8 字符 | OWASP 建议 ≥ 8 (刚达到最低标准) |
| 最大长度 | 128 字符 | 合理（防止 DoS） |
| 复杂度要求 | 缺失 | 无大小写/数字/特殊字符要求 |
| 密码强度检查 | 无 | 无 zxcvbn 等强度库集成 |
| 通用密码拒绝 | 无 | 无密码字典检查 |
| 暴力破解防护 | 部分 | 5 次/分钟 (slowapi rate limit)；无账户锁定 |
| 密码历史 | 无 | 重复使用旧密码不拒绝 |
| 凭据填充检测 | 无 | 无失败登录计数和延迟递增 |

**严重缺失 1: 无账户锁定机制**

`grep` 搜索 `LOGIN_LOCKOUT|MAX_LOGIN_ATTEMPTS|lockout|failed.*login` → **0 结果**

登录端点:
- `auth_service.py:314-347` login_sync → 只检查邮箱/密码/状态
- `auth_service.py:349-380` login → 同上
- `router/auth.py:39-47` → `@limiter.limit("5/minute")` 仅作为全局速率限制

缺点：5 次/分钟的限流可被 5 个不同 IP 绕过。

**严重缺失 2: 无密码复杂度要求**

允许以下弱密码：
- `12345678` (纯数字，8 位)
- `password` (字典词，8 位)
- `aaaaaaaa` (重复字符，8 位)

**风险评估**: **高** — 无账户锁定 + 无密码复杂度 = 暴力破解风险

### 建议

1. 实现登录失败计数器和账户锁定：
   ```python
   MAX_LOGIN_ATTEMPTS = 5
   LOCKOUT_DURATION_MINUTES = 15
   ```
2. 添加密码复杂度要求（至少包含以下 3 类中的 2 类）：
   - 大写字母 (A-Z)
   - 小写字母 (a-z)
   - 数字 (0-9)
   - 特殊字符 (!@#$%^&*...)
3. 集成 zxcvbn 密码强度库
4. 增加密码历史检查（最近 5 个密码不能重复）
5. 增加可疑登录检测（新设备/新地点 → 邮件通知）

---

## 11. HTTPS

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| HTTPS 强制 | 应用层无 | FastAPI 不处理 TLS；应由反向代理 (nginx/Caddy) 终结 |
| HSTS 头 | 缺失 | 无 `Strict-Transport-Security` 响应头 |
| Cookie secure | N/A | Bearer Token 不使用 Cookie |
| Cookie httpOnly | N/A | 同上 |
| Cookie sameSite | N/A | 同上 |
| 重定向 HTTP→HTTPS | 缺失 | 应用层不处理 |

**风险评估**: 中（若反向代理配置正确则为低风险）

### 建议

- 在 nginx/Caddy 配置中启用：
  - HSTS: `max-age=31536000; includeSubDomains; preload`
  - HTTP→HTTPS 301 重定向
  - 现代 TLS 配置 (TLS 1.2+ only；禁用弱密码套件)
- 在 FastAPI 中添加 `Strict-Transport-Security` 响应头中间件

---

## 12. 信息泄露

### 评估

| 检查点 | 状态 | 说明 |
|--------|------|------|
| 登录失败消息 | 安全 | `"Invalid email or password"` — 不区分邮箱/密码错误 |
| Token 错误消息 | 安全 | `"无效的认证令牌"` — 不区分过期/格式/黑名单 |
| 密码重置 | 安全 | `"If the email exists, a reset link has been sent."` — 统一响应 |
| 用户枚举 | 安全 | 注册返回明确的 409 → 可用于枚举（但这是常见设计） |
| 500 错误 | 风险 | 开发环境 `traceback.format_exc()` 返回完整调用栈 |
| 服务器信息 | 安全 | 无 Server/Version 响应头 |
| 密码在 URL | N/A | 未发现密码出现在 URL 中 |

### 具体问题

**1. 密码重置泄露（开发环境）** (`auth_service.py:189-194`):
```python
return {
    "message": "If the email exists, a reset link has been sent.",
    # WARNING: 以下信息仅在开发/测试环境暴露
    "reset_token_prefix": reset_token[:4] + "...",
    "reset_token_expires": reset_expires.isoformat(),
}
```

开发环境返回 `reset_token_prefix` 和 `reset_token_expires`。虽标记为开发用，但需确认生产环境不会触发。

**2. 500 错误暴露调用栈** (`main.py:353-354`):
```python
error_detail = traceback.format_exc() if settings.ENVIRONMENT == "development" else str(exc)
```

开发环境完整 traceback 在 meta.error_detail 中返回。生产环境仅返回 str(exc)。确认正确。

**3. 邮箱枚举**:
- `POST /register` → 409 明确 `"Email already registered"` （可用于用户枚举）
- `POST /login` → 401 不区分

**风险评估**: 中低

### 建议

- 生产环境验证 `reset_token_prefix` 不暴露（当前有条件，但最好彻底移除该代码路径）
- 考虑将注册时的 "Email already registered" 改为通用消息（增加隐私保护）
- 添加 `X-Content-Type-Options: nosniff` 和 `X-Frame-Options: DENY` 安全头

---

## 13. 依赖安全

### 关键认证依赖

| 依赖 | 用途 | 已知问题 |
|------|------|----------|
| `python-jose` | JWT 签名/验证 | 维护不活跃（最后更新 2021），建议迁移到 `PyJWT` |
| `passlib` | 密码哈希 | 维护不活跃（最后更新 2020），`bcrypt` 仍可用 |
| `bcrypt` | 底层加密 | 活跃维护，安全 |
| `redis` | Token 黑名单 | 安全 |
| `slowapi` | 速率限制 | 安全 |

### 分析

- `python-jose`: **建议迁移**。社区推荐 PyJWT（活跃维护，功能更全）。当前版本功能可用但缺少新的 JWT 特性（如 JWK、更强的 key 验证）。
- `passlib`: **需关注**。虽长期未更新，但 bcrypt 方案本身安全。长期可考虑迁移到 `bcrypt` 库直接使用或 `argon2-cffi`。
- 未找到 `requirements.txt` 或 `pyproject.toml` → 无法验证版本精确状态。

**风险评估**: 中（python-jose 维护停滞）

### 建议

```bash
# 迁移建议
pip install PyJWT[crypto]    # 替代 python-jose
pip install argon2-cffi      # 替代/补充 bcrypt
```

PyJWT 迁移对比：
```python
# Before (python-jose)
from jose import jwt
jwt.encode(payload, key, algorithm="HS256")
jwt.decode(token, key, algorithms=["HS256"])

# After (PyJWT)
import jwt
jwt.encode(payload, key, algorithm="HS256")
jwt.decode(token, key, algorithms=["HS256"])
```

---

## 14. CORS

### 实现 (`main.py:172-195`)

```python
_cors_origins = settings.CORS_ORIGINS.split(",")  # 默认: localhost:3000,127.0.0.1:3000,...

if settings.ENVIRONMENT == "production":
    if "*" in _cors_origins:
        allow_origins = ["*"]                     # ← 通配符 + allow_credentials
    else:
        allow_origins = _cors_origins
else:
    allow_origins = _cors_origins + localhost...  # ← 开发环境添加 localhost

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,   # ← 生产环境若用 "*" 则无效（浏览器会拒绝）
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 评估

| 项目 | 状态 | 说明 |
|------|------|------|
| 特定 origins | 部分 | 开发环境宽松；生产从 .env 读取 |
| 通配符 + credentials | 警告 | 若生产环境设置 `*` + `allow_credentials=True`，浏览器拒绝 |
| 安全验证器 | 安全 | `_warn_wildcard_cors` validator 对生产环境 `*` 发出警告 |
| methods/headers 限制 | 宽松 | `["*"]` 允许所有方法和请求头 |

**风险评估**: 低（有生产环境的 validator 保护）

### 建议

- 生产环境 `allow_origins` 应始终为具体域名列表（非 `*`）
- 考虑限制 `allow_methods` 为 `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]`
- 考虑限制 `allow_headers` 为实际需要的请求头

---

## 额外发现（超出 14 项检查清单）

### 15. Sentry PII 泄露

```python
# main.py:429
sentry_sdk.init(
    ...
    send_default_pii=True,  # ← 发送用户 IP 等 PII 到第三方
)
```

`send_default_pii=True` 会将用户 IP、Cookie 等信息发送到 Sentry 服务器。需确认符合 GDPR/个人信息保护法要求。

**建议**: 生产环境评估后决定是否启用 `send_default_pii`，或使用 `before_send` 回调手动脱敏。

### 16. RateLimitMiddleware 局限性

- `middleware/rate_limit.py`: 基于内存的 `dict`，**单进程有效**
- 多 worker 部署时无法共享计数，限制可被绕过
- 与 `slowapi` 冗余（两套限流同时运行）

**建议**: 统一限流策略，移除一套或使用 Redis 分布式限流。

### 17. Admin 端点缺少审计操作类型

Admin 路由需要明确的操作审计标签（如：`action: "update_user"`, `target: user_id`），当前仅依赖中间件的路径级记录。

### 18. 无多因素认证（MFA）

无两步验证/TOTP/WebAuthn 支持。对管理员账户尤其重要。

---

## 综合风险矩阵

| # | 项目 | 风险等级 | 优先级 |
|---|------|----------|--------|
| 3 | Refresh Token 过期不一致（30d vs 7d） | **HIGH** | P0 立即修复 |
| 10 | 无账户锁定 + 无密码复杂度 | **HIGH** | P0 立即修复 |
| 3 | Access Token 过期忽略配置（硬编码） | **HIGH** | P0 立即修复 |
| 6 | 黑名单降级策略不明确 | MEDIUM | P1 |
| 8 | RBAC 不完整（status=admin 非真正 RBAC） | MEDIUM | P1 |
| 13 | python-jose 维护停滞 | MEDIUM | P1 |
| 5 | bcrypt rounds 未显式声明 | LOW | P2 |
| 12 | 邮箱枚举（注册端点 409） | LOW | P2 |
| 11 | HTTPS/HSTS 依赖反向代理 | LOW | P2 |
| 8 | Admin UpdateUserReq.role 静默忽略 | LOW | P2 |
| 15 | Sentry PII 泄露 | LOW | P2 |
| 2 | 无密钥轮换 | LOW | P3 |
| 16 | RateLimitMiddleware 单进程 | LOW | P3 |

---

## P0 修复清单

### Fix 1: Token 过期使用配置值

**文件**: `app/service/auth_service.py:44-71`

```python
def _create_access_token(user_id: int) -> tuple[str, str, int]:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES  # ← 修复
    )
    jti = str(uuid.uuid4())
    to_encode = {"sub": str(user_id), "type": "access", "exp": expire, "jti": jti}
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # ← 修复

def _create_refresh_token(user_id: int) -> tuple[str, str, int]:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS  # ← 修复
    )
    ...
    return token, jti, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # ← 修复
```

### Fix 2: 密码策略增强

**文件**: `app/schemas/auth.py`

```python
password: str = Field(
    ...,
    min_length=8,
    max_length=128,
    pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$",  # ← 至少大小写+数字
    description="密码 (至少8位，包含大小写字母和数字)",
)
```

### Fix 3: 登录失败锁定

**文件**: `app/service/auth_service.py` (login / login_sync)

添加：
- 每邮箱登录失败计数器 (Redis: `login_attempts:{email}`，TTL=15min)
- 超过 5 次失败 → 15 分钟锁定
- `check_login_lockout()` 函数

---

*扫描完成时间: 2026-06-21 | 扫描器: security-scanner | 团队: deep-scan-v4*
