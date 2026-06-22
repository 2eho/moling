# Rust 重写 — 任务清单

> **最后更新**: 2026-06-21
> **状态**: ✅ 全部完成

---

## Phase 1: moling-db（数据库层）

- [x] 22 SeaORM 实体文件（user/project/chapter/vault_*/card/generation/secret/...）
- [x] 8 数据库迁移（m0001 至 m0008）
- [x] DatabasePool 连接池
- [x] 5 个预存 DAO：user_dao / project_dao / chapter_dao / vault_dao / card_dao
- [x] 10 个新增 DAO：secret / generation / health_alert / notification / template / subscription / phase4 / dynamic_layer / ingest / system_config
- [x] 新建 ingest_job 实体
- [x] SeaORM 1.x 兼容修复（手动 Column/PrimaryKey → DeriveEntityModel 自动生成）
- [x] 18 实体补全 `impl Related<…> for Entity`
- [x] `.count()` / `.offset()` / `.limit()` API 迁移到 `PaginatorTrait` / `QuerySelect`
- [x] `cargo check -p moling-db` — 0 errors, 1 pre-existing warning
- [x] `cargo test -p moling-db` — 10 passed

---

## Phase 2: moling-auth（认证层）

- [x] `src/jwt.rs` — HS256 JWT 生成/验证（access + refresh tokens）
- [x] `src/password.rs` — bcrypt 哈希/校验 + 密码复杂度验证
- [x] `src/middleware.rs` — `require_auth` (强制) + `optional_auth` (可选) Axum 中间件
- [x] `src/extractor.rs` — `CurrentUser` + `OptionalCurrentUser` FromRequestParts
- [x] `src/blacklist.rs` — Redis 令牌黑名单（登出立即失效）
- [x] `src/lockout.rs` — 登录锁定（5 次失败 / 15 分钟冷却）
- [x] `src/lib.rs` — 统一导出
- [x] `cargo check -p moling-auth` — 0 errors, 0 warnings
- [x] `cargo test -p moling-auth` — 27 passed

---

## Phase 3: moling-api（API 路由层）

- [x] `src/state.rs` — `AppState { db, redis, settings }`
- [x] `src/types.rs` — 34 请求/响应 struct + PaginatedList + MessageResponse
- [x] `src/error_handler.rs` — AppError → HTTP status + JSON body
- [x] 8 中间件：request-id / rate-limit / audit / content-length / response-format / cors / sentry / mod
- [x] 16 路由模块：auth / project / chapter / vault / card / generation / secret / health / admin / notification / setting / template / phase4 / weave / subscription / genre / import
- [x] `src/lib.rs` — `build_router(state)` + 嵌套路由组装
- [x] `cargo check -p moling-api` — 0 errors, 0 warnings

---

## Phase 4: moling-services（业务逻辑层）

- [x] 16 业务 Service：Project / Chapter / Vault / Card / Generation / Secret / Health / Notification / Setting / Template / Phase4 / Weave / Subscription / Prompt / Import
- [x] 依赖注入模式：`new()` 构造函数注入 DAO
- [x] 所有权验证：项目级 `verify_owner()` 私有方法
- [x] PromptService 独立：build_chapter_prompt / build_direction_prompt / build_revision_prompt / build_analysis_prompt
- [x] `cargo check -p moling-services` — 0 errors, 0 warnings
- [x] `cargo test -p moling-services` — 18 passed

---

## Phase 5: moling-llm + moling-worker

### moling-llm
- [x] `DeepSeekClient` — chat() + chat_stream() via reqwest + SSE 流式解析
- [x] `KeyRotator` — 轮转 + 错误冷却（指数退避）
- [x] `TokenBudget` — 4chars≈1token 估算 + headroom 校验
- [x] `PromptBuilder` — generation / direction / revision / analysis 四个模板
- [x] `cargo check -p moling-llm` — 0 errors, 0 warnings
- [x] `cargo test -p moling-llm` — 17 passed

### moling-worker
- [x] `TaskQueue` — Redis BRPOPLPUSH + 死信队列（lpush/brpoplpush/ack/dead_letter/retry）
- [x] `CronScheduler` — 5 字段 cron 解析 + tokio 后台轮询
- [x] 7 Worker：generation / phase4 / vault_reanalyze / card_retire / health_notify / import_task / analysis
- [x] 幂等性保护：Redis SET NX + 24h TTL
- [x] `cargo check -p moling-worker` — 0 errors, 0 warnings
- [x] `cargo test -p moling-worker` — 4 passed

---

## Phase 6: moling-server + Docker 部署

- [x] `main.rs` — 启动流程：settings → tracing → DB pool → Redis → AppState → build_router → axum::serve → graceful shutdown
- [x] `docker/Dockerfile` — 多阶段构建（rust:1.96-slim-bookworm → debian:bookworm-slim），非 root 用户
- [x] `docker/.dockerignore`
- [x] `docker/docker-compose.prod.yml` — 5 服务 + 健康检查
- [x] `deploy/moling.conf` — Nginx 反向代理 + 安全头 + gzip
- [x] `Makefile` — rust-build / test / lint + docker-build / up / down + dev / deploy
- [x] `cargo check -p moling-server` — 0 errors, 0 warnings
- [x] `cargo test -p moling-server` — 1 passed

---

## Phase 7: 文档闭环

- [x] `docs/ARCHITECTURE.md` — Rust 重写概述、Crate 架构图、部署拓扑、构建工具链、环境变量
- [x] `docs/SPECIFICATIONS.md` — Phase 完成状态、质量门禁、Python→Rust 映射表、关键技术决策
- [x] `docs/DESIGN.md` — 设计原则、数据流、API 版本化、错误码、数据库、安全
- [x] `specs/rust-rewrite/tasks.md` — 本文件

---

## 全量统计

| 指标 | 值 |
|------|-----|
| 重写 crates | 8 |
| Rust 源文件 | ~120 |
| 总测试数 | 77 |
| `cargo check --workspace` | 0 errors |
| `cargo test --workspace` | 77 passed, 0 failed |
| Docker 镜像大小 | ~50MB (runtime stage) |
| API 端点 | 99 |
| 数据库表 | 24 |
| DAO | 15 |
| Service | 16 |
| 中间件 | 8 |
