# 墨灵 (Moling) — 后端架构文档

> **最后更新**: 2026-06-21
> **维护者**: moling-server-rs 团队

---

## Rust 重写概述

> **Rust 重写 2026-06-21**

Moling 后端由 Python（FastAPI + SQLAlchemy + Celery）重写为 Rust（Axum + SeaORM + Tokio）。
采用**混合架构**：Rust 负责 HTTP/API/DB 核心链路，Python LLM 编排层保留（通过 HTTP 或队列互通）。

### 重写动机

- **性能**：Rust 零成本抽象 + 异步运行时，QPS 预期提升 5-10×
- **安全**：编译期类型检查消除 Python 运行时 `AttributeError` / `TypeError`
- **资源**：二进制 ~15MB，内存占用为 Python 的 1/10
- **部署**：单二进制 + 多阶段 Docker，无需 Python 运行时 + pip 依赖

### 混合架构边界

| 层级 | 技术 | 状态 |
|------|------|------|
| HTTP API | Rust (Axum 0.8) | ✅ 已重写 |
| 数据库访问 | Rust (SeaORM 1.1) | ✅ 已重写 |
| 认证/授权 | Rust (jsonwebtoken + bcrypt) | ✅ 已重写 |
| 业务逻辑 | Rust (moling-services) | ✅ 已重写 |
| 中间件 | Rust (tower + axum middleware) | ✅ 已重写 |
| LLM 调用 | Rust (moling-llm / reqwest) | ✅ 基础实现 |
| 后台任务队列 | Rust (moling-worker / Redis BRPOPLPUSH) | ✅ 基础实现 |
| LLM 编排 / Prompt 工程 | Python (保留) | 保持 Python |

---

## Crate 架构图

> **Rust 重写 2026-06-21**

```
moling-server (二进制入口)
├── moling-api (Axum Router + 中间件 + 16 路由组)
│   ├── moling-auth (JWT + bcrypt + 令牌黑名单 + 登录锁定)
│   └── moling-db (SeaORM 实体 + 15 DAO + 8 迁移)
├── moling-services (16 业务 Service)
│   └── moling-db
├── moling-llm (DeepSeek 客户端 + Key 轮转 + Token 预算)
├── moling-worker (Redis 任务队列 + Cron 调度 + 7 Worker)
└── moling-core (错误/配置/Redis/类型/日志)
```

### Crate 职责矩阵

| Crate | 职责 | 代码行数(估) |
|-------|------|-------------|
| `moling-core` | 统一错误系统(AppError)、配置加载(Settings)、Redis 客户端(RedisClient)、分页类型(Pagination)、日志初始化 | ~400 |
| `moling-db` | 22 SeaORM 实体、15 DAO（UserDao/ProjectDao/ChapterDao/...）、连接池(DatabasePool)、8 数据库迁移 | ~3000 |
| `moling-auth` | JWT 生成/验证(HS256)、bcrypt 密码哈希/复杂度校验、令牌黑名单(TokenBlacklist)、登录锁定(LoginLockout)、Axum CurrentUser 提取器 | ~700 |
| `moling-api` | AppState、34 请求/响应类型、8 中间件(request-id/rate-limit/audit/cors/...)、16 路由模块(auth/project/chapter/...)、Router 工厂 | ~2500 |
| `moling-services` | 16 业务 Service(ProjectService/ChapterService/VaultService/...)、依赖注入、所有权验证 | ~1500 |
| `moling-llm` | DeepSeekClient(同步+流式)、KeyRotator(轮转+冷却)、TokenBudget(4chars≈1token)、PromptBuilder | ~400 |
| `moling-worker` | TaskQueue(Redis BRPOPLPUSH+死信队列)、CronScheduler、7 Worker(生成/Phase4/重分析/卡片退役/健康/导入/分析) | ~800 |
| `moling-server` | main.rs 启动流程(settings→tracing→pool→router→serve→graceful shutdown)、Dockerfile | ~120 |

### 依赖方向

所有 crate 仅依赖 `moling-core`（零外部循环依赖）：
- `moling-db` → `moling-core`
- `moling-auth` → `moling-core` + `moling-db`
- `moling-api` → `moling-core` + `moling-db` + `moling-auth`
- `moling-services` → `moling-core` + `moling-db`
- `moling-llm` → `moling-core`
- `moling-worker` → `moling-core` + `moling-db` + `moling-llm`
- `moling-server` → `moling-core` + `moling-db` + `moling-auth` + `moling-api`

---

## 部署拓扑

> **Rust 重写 2026-06-21**

### Docker 服务（5 容器）

```
                    ┌─────────────┐
                    │    Nginx    │  :80/:443
                    │  (1.27-alp) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         /api/*        /moling/*      /health
              │            │            │
     ┌────────▼───┐  ┌───▼────────┐    │
     │ moling-app │  │ moling-web │    │
     │  (Rust)    │  │(Next.js SPA│◄───┘
     │  :8000     │  │  :3000)    │
     └──┬─────┬───┘  └────────────┘
        │     │
   ┌────▼─┐ ┌─▼────┐
   │ PG16 │ │Redis7│
   │:5432 │ │:6379 │
   └──────┘ └──────┘
```

### 服务说明

| 服务 | 镜像 | 端口 | 职责 |
|------|------|------|------|
| moling-app | `moling-server:latest`（自构建） | 8000 | Rust API 服务器 |
| postgres | `postgres:16-alpine` | 5432 | 主数据库 |
| redis | `redis:7-alpine` | 6379 | 缓存 / 队列 / 限流 |
| nginx | `nginx:1.27-alpine` | 80/443 | 反向代理 + 安全头 |
| moling-web | `nginx:1.27-alpine`（前端占位） | 3000 | 前端 SPA（Next.js） |

### 健康检查

| 服务 | 检查方式 | 间隔 |
|------|---------|------|
| moling-app | `curl -sf localhost:8000/api/v1/health` | 30s |
| postgres | `pg_isready -U moling -d moling` | 10s |
| redis | `redis-cli ping` | 10s |
| nginx | `nginx -t` | 30s |

---

## 构建工具链

> **Rust 重写 2026-06-21**

| 组件 | 版本 | 用途 |
|------|------|------|
| rustc | 1.96.0 | Rust 编译器 |
| cargo | 1.96.0 | 包管理 / 构建系统 |
| GCC | 16.1.0 (MinGW-w64) | C 链接器（Windows 交叉编译） |
| rustfmt | 1.8.0 | 代码格式化 |
| clippy | 0.1.96 | Lint 检查 |

### Cargo 镜像源

```toml
# ~/.cargo/config.toml
[source.crates-io]
replace-with = 'tuna'

[source.tuna]
registry = "https://mirrors.tuna.tsinghua.edu.cn/git/crates.io-index"
```

### Docker 镜像源

Base image 从 `ccr.ccs.tencentyun.com`（腾讯云容器镜像）拉取以加速国内构建。

---

## 环境变量

> **Rust 重写 2026-06-21**

所有配置通过 `MOLING_` 前缀的环境变量注入，由 `figment` crate 解析。

### 核心变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MOLING_DATABASE_URL` | `sqlite:./moling.db` | 数据库连接串（支持 postgres:// / sqlite: ） |
| `MOLING_DATABASE_POOL_SIZE` | `20` | 连接池最大连接数 |
| `MOLING_DATABASE_MAX_OVERFLOW` | `10` | 连接池溢出上限 |
| `MOLING_REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `MOLING_REDIS_PASSWORD` | — | Redis 密码（可选） |
| `MOLING_SECRET_KEY` | `dev-secret-key-change-in-production` | JWT 签名密钥 |
| `MOLING_ALGORITHM` | `HS256` | JWT 算法 |
| `MOLING_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access Token 有效期（分钟） |
| `MOLING_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 有效期（天） |
| `MOLING_LLM_API_BASE` | `https://api.deepseek.com` | LLM API 地址 |
| `MOLING_LLM_API_KEY` | `sk-placeholder` | LLM API 密钥 |
| `MOLING_LOG_LEVEL` | `INFO` | 日志级别 |
| `RUST_LOG` | `info` | tracing 过滤器 |
| `MOLING_CORS_ORIGINS` | `*` | CORS 允许的源 |
| `MOLING_HOST` | `0.0.0.0` | 监听地址 |
| `MOLING_PORT` | `8000` | 监听端口 |
| `MOLING_MAX_BODY_SIZE` | `10485760` | 请求体最大字节数（10MB） |

### 生产部署建议

```bash
export MOLING_DATABASE_URL="postgres://moling:<password>@postgres:5432/moling"
export MOLING_REDIS_URL="redis://redis:6379/0"
export MOLING_SECRET_KEY="$(openssl rand -hex 32)"
export MOLING_LLM_API_KEY="sk-<your-deepseek-key>"
export RUST_LOG="info,moling_server=debug"
```

---

## Cargo Workspace 结构

```
moling-server-rs/
├── Cargo.toml              # workspace root
├── Cargo.lock
├── Makefile
├── docker/
│   ├── Dockerfile           # 多阶段构建
│   ├── .dockerignore
│   └── docker-compose.prod.yml
├── deploy/
│   └── moling.conf          # Nginx 配置
└── crates/
    ├── moling-core/         # 核心：错误/配置/Redis/类型/日志
    ├── moling-db/           # 数据库：实体/DAO/连接池/迁移
    ├── moling-auth/         # 认证：JWT/密码/令牌管理
    ├── moling-api/          # API 层：路由/中间件/类型
    ├── moling-services/     # 业务逻辑层
    ├── moling-llm/          # LLM 客户端
    ├── moling-worker/       # 后台任务
    └── moling-server/       # 二进制入口
```
