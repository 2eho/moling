# 墨灵 (Moling) — 功能规格与完成状态

> **最后更新**: 2026-06-21
> **维护者**: moling-server-rs 团队

---

## Rust Phase 1-7 完成状态

> **Rust 重写 2026-06-21**

| Phase | 内容 | 状态 | crates | 测试数 |
|-------|------|------|--------|--------|
| Phase 1 | moling-db（实体 + DAO + 迁移） | ✅ 完成 | `moling-db` | 10 |
| Phase 2 | moling-auth（JWT + bcrypt + 中间件） | ✅ 完成 | `moling-auth` | 27 |
| Phase 3 | moling-api（路由 + 中间件 + 类型） | ✅ 完成 | `moling-api` | — |
| Phase 4 | moling-services（16 业务 Service） | ✅ 完成 | `moling-services` | 18 |
| Phase 5 | moling-llm + moling-worker | ✅ 完成 | `moling-llm`, `moling-worker` | 21 |
| Phase 6 | moling-server 二进制 + Docker | ✅ 完成 | `moling-server` | 1 |
| Phase 7 | 文档闭环 | ✅ 完成 | — | — |

### 质量门禁

> **Rust 重写 2026-06-21**

| 检查项 | 结果 |
|--------|------|
| `cargo check --workspace` | ✅ 0 errors（仅 1 个 moling-db 预存 warning: async_fn_in_trait） |
| `cargo test --workspace` | ✅ 77 passed, 0 failed |
| `cargo clippy --workspace -- -D warnings` | ⏳ 待执行 |
| `cargo audit` | ⏳ 待配置 |

---

## Python → Rust 映射表

> **Rust 重写 2026-06-21**

### 实体层

| Python 模型 | Rust 实体 | 文件 |
|------------|-----------|------|
| `app/models/user.py` | `user::Model` | `moling-db/src/entities/user.rs` |
| `app/models/project.py` | `project::Model` | `moling-db/src/entities/project.rs` |
| `app/models/chapter.py` | `chapter::Model` | `moling-db/src/entities/chapter.rs` |
| `app/models/secret.py` | `secret::Model` | `moling-db/src/entities/secret.rs` |
| `app/models/card_pool.py` | `card_pool::Model` | `moling-db/src/entities/card_pool.rs` |
| `app/models/draw_history.py` | `draw_history::Model` | `moling-db/src/entities/draw_history.rs` |
| `app/models/generation_task.py` | `generation_task::Model` | `moling-db/src/entities/generation_task.rs` |
| `app/models/health_alert.py` | `health_alert::Model` | `moling-db/src/entities/health_alert.rs` |
| `app/models/notification.py` | `notification::Model` | `moling-db/src/entities/notification.rs` |
| `app/models/template.py` | `template::Model` | `moling-db/src/entities/template.rs` |
| `app/models/subscription.py` | `plan::Model` / `user_subscription::Model` | `moling-db/src/entities/plan.rs` / `user_subscription.rs` |
| `app/models/phase4_task.py` | `phase4_task::Model` | `moling-db/src/entities/phase4_task.rs` |
| `app/models/dynamic_layer.py` | `dynamic_layer::Model` | `moling-db/src/entities/dynamic_layer.rs` |
| `app/models/system_config.py` | `system_config::Model` | `moling-db/src/entities/system_config.rs` |
| `app/models/sub_plot.py` | `sub_plot::Model` + `sub_plot_status_log::Model` | `moling-db/src/entities/sub_plot.rs` + `sub_plot_status_log.rs` |
| `app/models/vault_*.py` | `vault_character/timeline/plot_promise/world/changelog::Model` | `moling-db/src/entities/vault_*.rs` |
| `app/ingest/models.py` | `ingest_job::Model` | `moling-db/src/entities/ingest_job.rs` |

### DAO 层

| Python DAO | Rust DAO | 文件 |
|-----------|---------|------|
| `app/dao/user_dao.py` | `UserDao` | `moling-db/src/dao/user_dao.rs` |
| `app/dao/project_dao.py` | `ProjectDao` | `moling-db/src/dao/project_dao.rs` |
| `app/dao/chapter_dao.py` | `ChapterDao` | `moling-db/src/dao/chapter_dao.rs` |
| `app/dao/vault_dao.py` | `VaultDao` | `moling-db/src/dao/vault_dao.rs` |
| `app/dao/card_dao.py` | `CardDao` | `moling-db/src/dao/card_dao.rs` |
| `app/dao/secret_dao.py` | `SecretDao` | `moling-db/src/dao/secret_dao.rs` |
| `app/dao/generation_dao.py` | `GenerationDao` | `moling-db/src/dao/generation_dao.rs` |
| `app/dao/health_alert_dao.py` | `HealthAlertDao` | `moling-db/src/dao/health_alert_dao.rs` |
| `app/dao/notification_dao.py` | `NotificationDao` | `moling-db/src/dao/notification_dao.rs` |
| `app/dao/template_dao.py` | `TemplateDao` | `moling-db/src/dao/template_dao.rs` |
| `app/dao/subscription_dao.py` | `PlanDao` + `UserSubscriptionDao` | `moling-db/src/dao/subscription_dao.rs` |
| `app/dao/phase4_dao.py` | `Phase4Dao` | `moling-db/src/dao/phase4_dao.rs` |
| `app/dao/dynamic_layer_dao.py` | `DynamicLayerDao` | `moling-db/src/dao/dynamic_layer_dao.rs` |
| `app/dao/ingest_dao.py` | `IngestDao` | `moling-db/src/dao/ingest_dao.rs` |
| `app/dao/system_config_dao.py` | `SystemConfigDao` | `moling-db/src/dao/system_config_dao.rs` |

### Service 层

| Python Service | Rust Service | 文件 |
|---------------|-------------|------|
| `app/service/project_service.py` | `ProjectService` | `moling-services/src/project_service.rs` |
| `app/service/chapter_service.py` | `ChapterService` | `moling-services/src/chapter_service.rs` |
| `app/service/vault_service.py` | `VaultService` | `moling-services/src/vault_service.rs` |
| `app/service/card_service.py` | `CardService` | `moling-services/src/card_service.rs` |
| `app/service/generation_service.py` | `GenerationService` | `moling-services/src/generation_service.rs` |
| `app/service/secret_service.py` | `SecretService` | `moling-services/src/secret_service.rs` |
| `app/service/health_service.py` | `HealthService` | `moling-services/src/health_service.rs` |
| `app/service/notification_service.py` | `NotificationService` | `moling-services/src/notification_service.rs` |
| `app/service/setting_service.py` | `SettingService` | `moling-services/src/setting_service.rs` |
| `app/service/template_service.py` | `TemplateService` | `moling-services/src/template_service.rs` |
| `app/service/phase4_service.py` | `Phase4Service` | `moling-services/src/phase4_service.rs` |
| `app/service/weave_service.py` | `WeaveService` | `moling-services/src/weave_service.rs` |
| `app/service/prompt_service.py` | `PromptService` | `moling-services/src/prompt_service.rs` |
| `app/service/import_service.py` | `ImportService` | `moling-services/src/import_service.rs` |
| `app/service/auth_service.py` | （内联在 routes/auth.rs） | `moling-api/src/routes/auth.rs` |

### API 路由层

| Python Router | Rust Router | 端点 |
|--------------|-------------|------|
| `app/router/auth.py` | `routes::auth` | `/api/v1/auth/*`（8 端点） |
| `app/router/project.py` | `routes::project` | `/api/v1/projects/*`（7 端点） |
| `app/router/chapter.py` | `routes::chapter` | `/api/v1/projects/{id}/chapters/*`（9 端点） |
| `app/router/card.py` | `routes::card` | `/api/v1/projects/{id}/cards/*`（5 端点） |
| `app/router/vault.py` | `routes::vault` | `/api/v1/projects/{id}/vault/*`（22 端点） |
| `app/router/secret.py` | `routes::secret` | `/api/v1/projects/{id}/secrets/*`（6 端点） |
| `app/router/generation.py` | `routes::generation` | `/api/v1/generation/*`（4 端点） |
| `app/router/health.py` | `routes::health` | `/api/v1/health` |
| `app/router/admin.py` | `routes::admin` | `/api/v1/admin/*`（4 端点） |
| `app/router/notification.py` | `routes::notification` | `/api/v1/notifications/*`（5 端点） |
| `app/router/setting.py` | `routes::setting` | `/api/v1/settings/*`（4 端点） |
| `app/router/template.py` | `routes::template` | `/api/v1/templates/*`（5 端点） |
| `app/router/phase4.py` | `routes::phase4` | `/api/v1/phase4/*`（5 端点） |
| `app/router/weave.py` | `routes::weave` | `/api/v1/weave/*`（4 端点） |
| `app/router/subscription.py` | `routes::subscription` | `/api/v1/subscriptions/*`（4 端点） |
| `app/ingest/router.py` | `routes::import_route` | `/api/v1/import/*`（5 端点） |
| `app/router/genre.py` | `routes::genre` | `/api/v1/genre/*`（2 端点） |

---

## 关键技术决策

> **Rust 重写 2026-06-21**

### 为什么选择 Axum 而不是 Actix-web

- Axum 与 Tower 生态深度集成，中间件复用率高
- 类型安全的 `State<T>` + `FromRequestParts` 提取器
- 与 Tokio 运行时无缝配合
- 社区活跃，文档完善

### 为什么选择 SeaORM 而不是 Diesel

- SeaORM 异步原生支持（Diesel 异步支持有限）
- ActiveModel 模式与 Python SQLAlchemy 概念接近
- 内置连接池 + 迁移系统
- 与 Axum + Tokio 生态兼容

### 为什么保留 Python LLM 编排

- Prompt 工程 / 模板管理需要快速迭代
- Python 生态的 LangChain / LiteLLM 等库更成熟
- LLM 调用延迟远大于 Rust/Python 性能差异（不值得重写）

### JWT leeway = 0

禁用 jsonwebtoken 默认的 60 秒时钟偏移容差，确保令牌过期后立即失效，提升安全性。

### 幂等性保护

所有后台 Worker 使用 Redis SET NX + 24h TTL 防重入。Phase4 Worker 额外使用 nonce 去重。

---

## 前端不变

> **Rust 重写 2026-06-21**

前端 `moling-web` 不变：Next.js 15 + React 19 + TypeScript + Tailwind CSS 4。
API 协议保持兼容，前端无需任何修改即可对接 Rust 后端。
