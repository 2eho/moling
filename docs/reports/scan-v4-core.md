# 模块1: Core/Config/Middleware 深度扫描报告

> **扫描范围**: `app/core/` (2 文件) + `app/middleware/` (6 文件) + 上下文文件 (`app/config.py`, `app/main.py`, `app/dependencies.py`, `app/errors.py`, `app/limiter.py`, `app/worker/celery_app.py`, `app/worker/db.py`)
> **扫描日期**: 2026-06-21
> **扫描深度**: very thorough — 逐文件逐行审查

---

## 发现汇总: 4 CRITICAL, 6 HIGH, 7 MEDIUM, 12 LOW

---

## 详细发现

### [C1] `dependencies.py` — greenlet 补丁块中引用未定义的 `logger` (CRITICAL)

- **文件**: `app/dependencies.py:41,65`
- **问题**: 在 greenlet 猴子补丁代码块（第 14-69 行）中使用了 `logger.debug(...)`，但 `import logging` 和 `logger = logging.getLogger(__name__)` 在此段代码中不存在——`logger` 名称在整个 `dependencies.py` 文件中从未被定义。当 `except Exception:` 分支真正命中时，`NameError: name 'logger' is not defined` 会导致模块导入崩溃，令整个 FastAPI 应用在 Windows 上无法启动。
- **影响**: Windows 启动失败（NameError），应用完全不可用。
- **修复**:
  ```python
  # 在补丁代码块顶部添加
  import logging
  _patch_logger = logging.getLogger(__name__)
  # 将 logger.debug(...) 替换为 _patch_logger.debug(...)
  ```
  或使用 `print()` 代替，因为补丁发生在整体日志系统初始化之前。

---

### [C2] `middleware/audit_log.py` — 无条件读取请求体导致内存 DoS 风险 (CRITICAL)

- **文件**: `app/middleware/audit_log.py:67-70`
- **问题**: 对所有非 excluded 的请求无条件执行 `await request.body()`，将整个请求体加载到 `request.state.body`。攻击者可以通过发送大量接近 `MAX_BODY_SIZE` 上限（默认 10MB）的请求，快速耗尽服务器内存。此行为对 multipart 上传、大 JSON payload 等场景尤其危险。
- **影响**: 内存耗尽导致 OOM，服务崩溃。每个 10MB 请求占用 10MB 内存直到 GC 回收。
- **修复**:
  1. 将 body 读取改为**可选/可配置**——仅在需要审计日志写入 DB 时才读取
  2. 对 body 读取增加独立的大小上限（如 64KB），超过则截断或跳过
  3. 考虑对 multipart/form-data 请求跳过 body 记录，只记录 metadata

---

### [C3] `middleware/response_format.py` — 全量缓冲响应体破坏流式传输 (CRITICAL)

- **文件**: `app/middleware/response_format.py:46-61`
- **问题**: 中间件拦截所有 `http.response.body` 消息，将 body chunks 用 `b"".join(raw_body_chunks)` 全量缓冲在内存中。这意味着：
  - 文件下载、流式 SSE/JSON 等端点完全无法工作
  - 大文件下载会把整个文件加载到内存，导致 OOM
  - `elapsed_ms` 计算包含了下载时间，但下游实际尚未收到任何数据
- **影响**: 流式端点（SSE、文件下载）完全不可用；大响应 OOM 风险。
- **修复**:
  1. 检查 Content-Type，对非 `application/json` 直接透传（当前已做，但应同时检查 `Transfer-Encoding: chunked` 和 `Content-Disposition: attachment`）
  2. 对 `Content-Disposition: attachment`（文件下载）直接透传，不做任何包装
  3. 增加响应体大小阈值（如 5MB），超过则透传

---

### [C4] `middleware/rate_limit.py` — 纯内存限流不适用于多进程部署 (CRITICAL)

- **文件**: `app/middleware/rate_limit.py:38-39`
- **问题**: 限流状态存储在 `self._visitors: dict[str, list[float]]` 中，是进程级内存字典。在多 worker（gunicorn/uvicorn --workers N）或负载均衡场景下：
  - 每个 worker 有独立的计数器，实际限流 = 配置值 × worker 数
  - worker 重启后所有记录丢失
  - 无分布式协调能力
- **影响**: 限流失效，单个攻击者可通过分散请求到不同 worker 完全绕过限流（如 4 worker 时实际限制为 4× 配置值）。
- **修复**: 代码第 18 行注释已指出此问题。建议：
  1. 短期：使用 `slowapi` + Redis 后端（项目已引入 slowapi 和 Redis）
  2. 或使用 Redis `INCR` + `EXPIRE` 实现滑动窗口计数
  3. 此中间件可降级为开发环境专用，生产环境切到 slowapi

---

### [H1] `audit_log.py` — 敏感数据过滤仅检查 query string (HIGH)

- **文件**: `app/middleware/audit_log.py:161`
- **问题**: 敏感信息过滤逻辑 `if "password" in str(audit_entry.get("query", "")).lower()` 仅检查 query string。请求体（已缓存在 `request.state.body`）、请求头（Authorization、API Key 等）中的敏感信息**完全不过滤**。这意味着所有 Bearer token、API key、密码字段等都会被明文写入审计日志文件。
- **影响**: 令牌泄露到本地日志文件；合规风险（GDPR/个保法）。
- **修复**:
  ```python
  SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "apikey",
                       "authorization", "credential", "access_token", "refresh_token"}
  # 递归清理 audit_entry 中所有层级的敏感字段
  # 同时对 headers 中的 Authorization 做脱敏处理
  ```

---

### [H2] `audit_log.py` — 日志路径/轮转/保留策略全部硬编码 (HIGH)

- **文件**: `app/middleware/audit_log.py:15-16,33-37,49-55`
- **问题**:
  - `LOG_DIR = Path("logs")` — 硬编码日志目录，不可配置
  - `when="midnight"`, `backupCount=30`, `encoding="utf-8"` — 全部无配置入口
  - `EXCLUDED_PATHS` — 哪些路径不记录审计硬编码为集合
- **影响**: 运维不可控；无法适配容器化部署（/var/log/app/）；磁盘写满无保护。
- **修复**: 从 `Settings` 类读取配置，如:
  ```python
  AUDIT_LOG_DIR: str = "./logs"
  AUDIT_LOG_RETENTION_DAYS: int = 30
  AUDIT_LOG_EXCLUDED_PATHS: list[str] = ["/health", "/docs", ...]
  ```

---

### [H3] `audit_log.py` — 审计日志无大小轮转保护 (HIGH)

- **文件**: `app/middleware/audit_log.py:31`
- **问题**: `TimedRotatingFileHandler` 仅按时间轮转（每天），不检查文件大小。如果单日审计日志量巨大（如遭受 API 攻击），日志文件可以增长到数百 GB 填满磁盘。
- **影响**: 磁盘写满导致服务不可用。
- **修复**: 使用 `RotatingFileHandler` 或双模式轮转（时间 + 大小），或切换到 syslog/外部日志收集。

---

### [H4] `content_length_limit.py` — Content-Length 限制与配置脱节 (HIGH)

- **文件**: `app/middleware/content_length_limit.py:16` vs `app/main.py:165-166`
- **问题**: `DEFAULT_MAX_SIZE` 在中间件模块中硬编码为 10MB，而 `main.py` 从 `settings.MAX_BODY_SIZE` 读取配置。两处可能存在不一致——如果只修改 `config.py` 中的 `MAX_BODY_SIZE` 但未正确传递到中间件构造函数，限制值不生效。当前 `main.py:166` 使用 `getattr(settings, 'MAX_BODY_SIZE', 10 * 1024 * 1024)` 读取，但 fallback 值与硬编码一致，mask 了不一致问题。
- **影响**: 修改配置不生效；安全审计时可能产生误判。
- **修复**: 从中间件模块中移除 `DEFAULT_MAX_SIZE` 常量，强制通过构造函数传入；或在中间件中使用 `get_settings()` 动态读取。

---

### [H5] `config.py` — SECRET_KEY 生产验证器依赖字段声明顺序 (HIGH)

- **文件**: `app/config.py:174-177`
- **问题**: validator 中 `info.data.get("ENVIRONMENT", "")` 读取同模型的 `ENVIRONMENT` 字段值。Pydantic v2 对 `field_validator` 的执行顺序**不保证**与字段声明顺序一致。如果 `SECRET_KEY` 的 validator 在 `ENVIRONMENT` 之前运行，`info.data["ENVIRONMENT"]` 将是空字符串（""），validator 会判定为非生产环境并仅打印 warning，而非拒绝启动。
- **影响**: 在生产环境中，SECRET_KEY 可能悄悄使用默认不安全值而不触发拒绝。
- **修复**:
  ```python
  @field_validator("SECRET_KEY", mode="after")
  @classmethod
  def _reject_production_default_secret(cls, v: str, info) -> str:
      import os
      env = os.environ.get("ENVIRONMENT", "") or info.data.get("ENVIRONMENT", "")
      if v == "dev-secret-key-change-in-production" and env == "production":
          raise ValueError(...)
  ```

---

### [H6] `dependencies.py` — 数据库连接池无 recycle/health-check (HIGH)

- **文件**: `app/dependencies.py:127-132`
- **问题**: PostgreSQL 连接池配置中，`pool_size=5`, `max_overflow=10`，但缺少 `pool_recycle`（连接最大存活时间）和 `pool_pre_ping`（连接健康检查）。对于 PostgreSQL 后端，长连接可能被数据库端关闭（如 pgBouncer 超时、防火墙空闲切断），下次使用时触发异常。
- **影响**: 空闲后的首次请求可能因 stale connection 而失败；需要重试机制。
- **修复**:
  ```python
  engine = create_async_engine(
      _db_url,
      echo=False,
      pool_size=5,
      max_overflow=10,
      pool_recycle=3600,      # 1 小时后回收连接
      pool_pre_ping=True,     # 每次使用时检查连接
  )
  ```

---

### [M1] `service_registry.py` — 类方法与实例混用 (MEDIUM)

- **文件**: `app/core/service_registry.py:45-111`
- **问题**: `ServiceRegistry` 的所有方法均为 `@classmethod`，`_registry` 为类属性。但第 111 行创建了全局实例 `service_registry = ServiceRegistry()`。该实例从未被使用——所有调用都是 `service_registry.get()` 等，实际走的是类方法。这种混用会导致：
  1. 如果有代码对 Registry 进行子类化，类级别共享的 `_registry` 会导致数据污染
  2. 实例创建了但无实际用途，造成困惑
- **影响**: 代码可维护性降低；子类化时有数据隔离风险。
- **修复**: 二选一：
  - 方案 A（推荐）：改为实例方法和实例级 `self._registry`，保持 `service_registry` 作为单例
  - 方案 B：移除实例创建，全部使用类方法 + 模块级函数 `register()` / `get()`

---

### [M2] `audit_log.py` — JWT 解码失败时静默吞错 (MEDIUM)

- **文件**: `app/middleware/audit_log.py:155`
- **问题**: `except Exception: return None` 捕获所有 JWT 解码异常（ExpiredSignatureError、JWTError、ValueError 等）并静默返回 None。如果是代码 bug（如 jose 库版本不兼容）而非正常的 token 失效，该错误会被完全隐藏。
- **影响**: 配置错误（如 SECRET_KEY 不匹配）时审计日志悄悄丢失用户信息，无任何告警。
- **修复**:
  ```python
  except ExpiredSignatureError:
      return None  # 过期 token 正常
  except Exception:
      logger.warning("JWT decode failed in audit middleware", exc_info=True)
      return None
  ```

---

### [M3] `rate_limit.py` — `app` 参数缺少类型注解 (MEDIUM)

- **文件**: `app/middleware/rate_limit.py:21`
- **问题**: `__init__(self, app, ...)` 中 `app` 参数无类型注解，IDE/类型检查器无法提供帮助。
- **影响**: 类型安全性降低。
- **修复**: `app: ASGIApp` 或 `app: "fastapi.FastAPI"`

---

### [M4] `response_format.py` — Content-Type 匹配不精确 (MEDIUM)

- **文件**: `app/middleware/response_format.py:65`
- **问题**: `b"application/json" in content_type` 使用子串匹配。虽然实际场景中不太可能匹配到非 JSON 类型，但理论上 `application/x-something+json` 格式会被正确匹配（它的 mime-type 确实是 JSON），但 `application/json+something` 这种非法格式也会被误匹配。
- **影响**: 极低概率的误判。
- **修复**: 使用精确的 MIME 类型解析：
  ```python
  mime_type = content_type.decode().split(";")[0].strip()
  is_json = mime_type in ("application/json", "application/problem+json")
  ```

---

### [M5] `config.py` — `extra="ignore"` 可能隐藏拼写错误 (MEDIUM)

- **文件**: `app/config.py:99-104`
- **问题**: `model_config` 中 `extra="ignore"` 意味着环境变量名中的拼写错误会被静默忽略。例如设置 `DATABSE_URL`（拼写错误）不会产生任何警告，应用将使用默认值。
- **影响**: 环境变量配置错误难以排查。
- **修复**: 考虑改为 `extra="forbid"` 或在启动时打印所有识别的配置项及其来源。

---

### [M6] `audit_log.py` — `time.strftime` 时区信息缺失 (MEDIUM)

- **文件**: `app/middleware/audit_log.py:74`
- **问题**: `time.strftime("%Y-%m-%dT%H:%M:%S%z")` 使用 `%z` 格式说明符。`time.strftime` 作用于本地时间（naive），`%z` 受 `time.timezone` 影响，在 Windows 上行为可能不一致。结果是可能产生无时区后缀的时间戳，违反 ISO 8601 标准。
- **影响**: 日志时间戳可能不包含时区信息，跨时区分析困难。
- **修复**: 使用 `datetime.datetime.now(datetime.timezone.utc).isoformat()` 或 `datetime` 模块。

---

### [M7] `main.py` — CORS_ORIGINS 生产环境通配符风险 (MEDIUM)

- **文件**: `app/main.py:176-177`
- **问题**: 如果 `settings.CORS_ORIGINS` 包含 `"*"`，生产环境会将其扩展为 `allow_origins=["*"]`，即允许任意来源的跨域请求。有 validator `_warn_wildcard_cors`（config.py:140-153）发出 warning，但不会阻止。生产环境 CORS 通配符 + `allow_credentials=True` 会触发浏览器错误（CORS 规范不允许 credentials 与 `*` 同时使用），但更危险的是——它实际上**不会**让浏览器报错，因为 `allow_credentials=True` 时浏览器要求 `Access-Control-Allow-Origin` 必须是具体域名，而非 `*`。所以请求实际上会**失败**，不是安全漏洞而是功能故障。
- **影响**: 生产环境下 CORS 配置 `*` 导致跨域请求全部失败（浏览器侧阻止）。
- **修复**: 在 validator 中将 warning 升级为拒绝（类似 SECRET_KEY 的处理）：
  ```python
  if "*" in origins and env == "production":
      raise ValueError("CORS_ORIGINS must not contain '*' in production")
  ```

---

### [L1] `core/__init__.py` — 缺少 `__all__` 导出 (LOW)

- **文件**: `app/core/__init__.py:1`
- **问题**: 模块仅有一个 docstring，未导入 `ServiceRegistry` 或 sentinel 类型。使用者需从子模块导入。
- **影响**: IDE 自动补全体验下降。
- **修复**: 添加显式导出。

---

### [L2] `service_registry.py` — 缺少线程安全保护 (LOW)

- **文件**: `app/core/service_registry.py:60,77,97`
- **问题**: `_registry` 类字典的读写未加锁。在异步 FastAPI 应用中通常是单线程的，但如果 future 中引入多线程 worker 或 Celery worker 共享此模块，可能出现竞态条件。
- **影响**: 低风险——当前架构下不会触发。
- **修复**: 如 future 中可能多线程访问，添加 `import threading` + `_lock = threading.Lock()`。

---

### [L3] `service_registry.py` — `instance: Any` 类型丢失 (LOW)

- **文件**: `app/core/service_registry.py:63`
- **问题**: `register(service_type: type, instance: Any)` 中 `instance` 参数未与 `service_type` 建立类型关联，调用者可以传入错误类型的实例。
- **影响**: 编译期无法检测类型不匹配。
- **修复**: 无法在 Python 中完美解决（类型擦除），可添加运行时 isinstance 检查或协议检查。

---

### [L4] `request_id.py` — 无输入验证 (LOW)

- **文件**: `app/middleware/request_id.py:17-19`
- **问题**: 如果客户端发送超长 `X-Request-ID` 头（如 10MB），服务器会接受并存储在 `request.state` 中。虽然后续仅在响应头中返回，但大的 request_id 字符串会增加内存占用。
- **影响**: 极低——仅内存。
- **修复**: 添加长度限制：
  ```python
  if request_id and len(request_id) <= 64:
      ...
  else:
      request_id = str(uuid.uuid4())
  ```

---

### [L5] `rate_limit.py` — `Optional` 未使用的导入 (LOW)

- **文件**: `app/middleware/rate_limit.py:7`
- **问题**: `from typing import Callable, Optional` — `Optional` 在文件中从未使用。
- **影响**: Lint 警告。
- **修复**: 移除未使用的导入。

---

### [L6] `rate_limit.py` — `by_ip=False` 路径未实现 (LOW)

- **文件**: `app/middleware/rate_limit.py:73-75`
- **问题**: `by_ip=False` 时应按用户 ID 限流，但代码注释 "简化为 IP" 表明此功能未实现——实际上退化为和 `by_ip=True` 相同的行为。
- **影响**: 用户 ID 限流不可用。
- **修复**: 实现真正的用户 ID 提取（从 JWT token 解析 user_id），或移除该参数。

---

### [L7] `content_length_limit.py` — 413 响应 meta 中 request_id 为空 (LOW)

- **文件**: `app/middleware/content_length_limit.py:79-80`
- **问题**: 413 错误响应中 `"request_id": ""` 永远是空字符串。因为 ContentLengthLimitMiddleware 是 ASGI 级别中间件，在 `RequestIDMiddleware`（BaseHTTPMiddleware）之前执行，无法获取 request_id。同样，`version` 硬编码为 `"1.0.0"` 而未从配置读取。
- **影响**: 413 错误日志中缺少 request_id，不便于关联排查。
- **修复**: 在前置的 ContentLengthLimitMiddleware 中自行从 scope headers 读取 `X-Request-ID`（如 response_format.py 的 `_extract_request_id` 方法）。

---

### [L8] `response_format.py` — request_id 提取不完整 (LOW)

- **文件**: `app/middleware/response_format.py:101-110`
- **问题**: `_extract_request_id` 仅从 scope headers 中读取 `X-Request-ID`，但在 RequestIDMiddleware 中生成的 UUID 是存储在 `request.state.request_id` 中的（BaseHTTPMiddleware 的 state 在 ASGI scope 中不可见）。因此，除非客户端主动发送 `X-Request-ID` 头，meta 中的 `request_id` 始终为空字符串。
- **影响**: meta 字段 request_id 经常为空。
- **修复**: 将 RequestIDMiddleware 也改为 ASGI 级别中间件，将 request_id 写入 scope：
  ```python
  scope["request_id"] = request_id
  ```

---

### [L9] `audit_log.py` — `audit_entry["query"]` 记录可能包含未过滤密码 (LOW)

- **文件**: `app/middleware/audit_log.py:77,160-162`
- **问题**: 敏感信息过滤在写入前（`_write_audit_log` 中）才执行，但在 `dispatch` 方法的第 77 行，query 已经写入 `audit_entry`。如果在 `_write_audit_log` 之前的任何路径中使用了 audit_entry（如 future 变更），敏感信息可能泄露。当前代码无此风险，但设计上缺少 defensive 层。
- **影响**: 潜在回归风险。
- **修复**: 在 query 首次加入 audit_entry 时即过滤（或至少在赋值前）。

---

### [L10] `audit_log.py` — 模块导入时即创建目录 (LOW)

- **文件**: `app/middleware/audit_log.py:15-16`
- **问题**: `LOG_DIR.mkdir(exist_ok=True)` 在模块导入时执行。如果应用以非 root 用户运行且无写权限，导入即失败——即使审计日志功能未被使用。
- **影响**: 只读文件系统中应用无法启动。
- **修复**: 将 `mkdir` 移到 `_get_audit_logger()` 内部（lazy）。

---

### [L11] `config.py` — `DATABASE_URL` 默认 SQLite 无生产提示 (LOW)

- **文件**: `app/config.py:34`
- **问题**: `DATABASE_URL` 默认使用 SQLite，注释中写 "生产环境切换为 PostgreSQL"，但 validator 中未对生产环境使用 SQLite 发出警告。
- **影响**: 可能意外在生产使用 SQLite。
- **修复**: 添加 validator 在生产环境使用 SQLite 时发出 warning。

---

### [L12] `audit_log.py` — 日志 handler 重复添加风险 (LOW)

- **文件**: `app/middleware/audit_log.py:39`
- **问题**: `_get_audit_logger()` 每次调用 `logger.addHandler(handler)` 但 `_audit_logger` 检查防止了重复初始化。如果 future 修改中移除了该检查（将 `global _audit_logger` 逻辑移除），多个 handler 会导致日志重复写入。
- **影响**: 潜在回归风险。
- **修复**: 添加 `logger.handlers` 检查作为双重保护。

---

## 专项检查结果

### 1. 配置安全

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 硬编码密钥 | WARN | SECRET_KEY 默认值 "dev-secret-key-change-in-production" 已在生产环境 validator 中拒绝（`config.py:172-189`），但依赖字段顺序 |
| 硬编码 API Key | WARN | LLM_API_KEY 默认 "sk-placeholder"，仅 warning |
| 生产默认值安全 | WARN | CORS_ORIGINS、REDIS_PASSWORD、DATABASE_URL 均有 warning validator，但 LLM_API_KEY 仅 warning 不拒绝 |
| 环境变量验证器 | PASS | 使用 pydantic-settings + field_validator，较完整（6 个 validator） |
| CORS_ORIGINS 通配符 | WARN | warning validator 存在但生产不拒绝 "*"，可能导致浏览器侧跨域失败 |

### 2. 数据库连接池

| 检查项 | 状态 | 说明 |
|--------|------|------|
| SQLite pool | PASS | 使用 `NullPool`（`dependencies.py:123`），正确 |
| PostgreSQL pool_size | WARN | `pool_size=5, max_overflow=10` 合理，但缺少 `pool_recycle` 和 `pool_pre_ping`（`dependencies.py:130-132`） |
| 连接泄漏风险 | PASS | `get_db()` 使用 `async with` + try/finally 保证关闭；Worker 使用 `get_worker_session()` + `dispose_worker_engine()` 注册到 `worker_shutdown` 信号 |
| Worker pool | PASS | `worker/db.py:67-74`: `pool_size=2, max_overflow=5, pool_pre_ping=True`，合理 |

### 3. Redis 连接

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 密码认证 | WARN | `REDIS_PASSWORD` 默认 None，validator 在非 dev 环境 warning；`dependencies.py:284` 正确传递 `password` 参数 |
| 连接超时 | PASS | `socket_connect_timeout=3`（`dependencies.py:283`） |
| 重试机制 | WARN | 无 `retry_on_timeout=True` 或 `health_check_interval`（`dependencies.py:282-285`） |
| 连接池配置 | PASS | `from_url` 使用 redis-py 默认连接池，对 Web 应用足够 |
| 优雅降级 | PASS | `main.py:81-87`: Redis 连接失败时 `_app.state.redis = None`，不阻止应用启动 |

### 4. Celery 配置

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Broker URL | WARN | `redis://localhost:6379/1` 无密码认证（`config.py:62`） |
| Result backend | WARN | `redis://localhost:6379/2` 无密码认证（`config.py:63`） |
| 序列化方式 | PASS | `task_serializer="json"`, `accept_content=["json"]`, `result_serializer="json"`——使用 JSON 而非 pickle，安全（`worker/celery_app.py:33-35`） |
| 超时控制 | PASS | `task_time_limit=600`, `task_soft_time_limit=540`（`worker/celery_app.py:44-45`） |
| 失败重试 | PASS | `task_acks_late=True`, `task_reject_on_worker_lost=True`, `broker_transport_options={"visibility_timeout": 3600}`（`worker/celery_app.py:40,55-60`） |
| 内存泄漏防护 | PASS | `worker_max_tasks_per_child=50`（`worker/celery_app.py:61`） |

### 5. 依赖注入

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 循环引用 | PASS | `ServiceRegistry` 使用 Sentinel 模式优雅解决了 Service 层循环依赖（`core/service_registry.py`） |
| 懒导入完整性 | PASS | `audit_log.py:144-146` 使用方法内 import；`main.py:9` 提前 import dependencies 确保补丁最先加载 |
| Service 注册 | PASS | 4 个 Sentinel 类型定义（`RunGenTaskSentinel`, `HealthMonitorServiceSentinel`, `Phase4SchedulerSentinel`, `CoherenceServiceSentinel`） |

### 6. 中间件性能/安全

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 性能瓶颈 | FAIL | AuditLog 无条件缓冲请求体（C2）；ResponseFormat 无条件缓冲响应体（C3） |
| 内容长度限制 | PASS | `ContentLengthLimitMiddleware` 在 ASGI 级别拦截，返回 413（`content_length_limit.py`） |
| 异常处理 | PASS | 各中间件均有 try/except 覆盖，RateLimit 使用 AppError code 体系 |
| 中间件顺序 | PASS | `main.py:165-209`: CL Limit → RequestID → CORS → SlowAPI → RateLimit → Audit → ResponseFormat，合理 |

### 7. 硬编码值

| 检查项 | 状态 | 说明 |
|--------|------|------|
| LOG_DIR | FAIL | `audit_log.py:15` — `Path("logs")` 硬编码 |
| 日志保留策略 | FAIL | `audit_log.py:33-37` — `when="midnight"`, `backupCount=30` 硬编码 |
| EXCLUDED_PATHS | FAIL | `audit_log.py:49-55` — 排除路径硬编码 |
| DEFAULT_MAX_SIZE | WARN | `content_length_limit.py:16` — 10MB 硬编码，与 config 不一致 |
| 限流默认值 | PASS | RateLimit 从 `main.py` 传入配置值 |

### 8. 异常处理

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 裸 except | PASS | 所有 `except Exception` 均有合理的上下文（审计日志容错、JWT 解析容错等） |
| HTTPException vs AppError | PASS | middleware 不抛出 HTTPException（直接构造 Response）；service 层使用 AppError；`main.py:227-247` 有全局 AppError handler |
| 异常日志 | PASS | `main.py:250-343` 的 `_write_error_log` 记录详细错误信息并支持日志轮转 |

### 9. 类型安全

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Any 类型滥用 | PASS | `ServiceRegistry._registry: dict[type, Any]` 的必要使用（类型擦除注册表）；其他地方均有具体类型 |
| 类型注解完整性 | WARN | `rate_limit.py:21` `app` 参数缺少类型；整体注解较完整 |
| TypeVar 使用 | PASS | `ServiceRegistry.get` 使用 `TypeVar("T")` 实现类型安全的获取 |

### 10. Windows 兼容

| 检查项 | 状态 | 说明 |
|--------|------|------|
| greenlet 补丁 | WARN | 补丁逻辑正确（`dependencies.py:17-43`，线程池 + `run_in_executor` 替代 greenlet_spawn）；但 except 块中 logger 未定义（C1） |
| 事件系统补丁 | PASS | `_get_exec_once_mutex` 补丁（`dependencies.py:46-69`）正确修补了 Windows 下 SQLAlchemy 事件系统返回 None 的问题 |
| 双轨会话 | PASS | `dependencies.py:169-237` 的 `_SyncAsyncSessionWrapper` 将同步 Session 包装为伪异步 Session，Windows 上可无缝使用 await |
| 数据库表创建 | PASS | `main.py:38-57` 区分 Windows（同步 create_engine）和 Linux（async run_sync），避免 greenlet 问题 |
| Worker DB | PASS | `worker/db.py:50-56` 自动适配 Windows + SQLite 的 aiosqlite 驱动 |

---

## 修复优先级建议

### 立即修复（Before Production）
1. **C1** — 修复 `dependencies.py` 中 undefined `logger` 引用（1 行改动）
2. **C2** — 在 `audit_log.py` 中增加 body 读取开关和大小上限
3. **C3** — 在 `response_format.py` 中增加流式/文件下载检测和透传
4. **C4** — 启用 slowapi Redis 后端作为限流方案

### 近期修复（下一迭代）
5. **H1** — 审计日志敏感数据过滤扩展到 body/headers
6. **H2** — 审计日志配置外部化（LOG_DIR/retention/exclusions）
7. **H3** — 日志大小轮转保护
8. **H4** — 统一 Content-Length 配置来源
9. **H5** — 修复 SECRET_KEY validator 的字段顺序依赖
10. **H6** — 添加 PostgreSQL pool_recycle 和 pool_pre_ping
11. **M7** — 生产环境拒绝 CORS_ORIGINS 中的 `*`

### 低优先级（后续优化）
12. M1-M6, L1-L12 — 代码质量、类型安全、可维护性改进
