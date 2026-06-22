# 墨灵后端 Rust 重写深度分析报告

> **生成时间**: 2026-06-21 14:00
> **分析范围**: moling-server/ (190文件 / 42,298行 Python)
> **策略**: 混合架构 + 逐模块深度重写 + 零技术债零文档债
> **原则**: 过程中发现更优方案则直接改进

---

## 一、当前架构全景图

```
┌─────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                      │
│                    http://124.222.163.79:8080                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              FastAPI Application (main.py)                   │
│  Middleware Stack: ContentLength → RequestID → CORS →       │
│     SlowAPI → RateLimit → AuditLog → ResponseFormat         │
├─────────────────────────────────────────────────────────────┤
│  19 Router Files / 136 API Endpoints                        │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │  Auth    │ Project  │ Chapter  │   Card   │  Vault   │  │
│  │  8 端点  │ 11 端点  │ 13 端点  │  8 端点  │ 22 端点  │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤  │
│  │Generation│  Admin   │Setting   │ Template │ Phase4   │  │
│  │  7 端点  │  8 端点  │ 10 端点  │  6 端点  │ 10 端点  │  │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┤  │
│  │  Weave   │  Secret  │  Ingest  │  Genre   │ Notif    │  │
│  │  4 端点  │  4 端点  │ 10 端点  │  3 端点  │  5 端点  │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
├─────────────────────────────────────────────────────────────┤
│  30 Service Classes / ~280 methods                          │
│  ┌──────────────────────┬──────────────────────────────┐    │
│  │  LLM 依赖 (9 svc)    │  纯计算/CRUD (21 svc)        │    │
│  │  generation_service  │  auth/project/chapter/card   │    │
│  │  coherence_service   │  vault/card_pool/merge       │    │
│  │  phase4_service      │  validation/vault_filter     │    │
│  │  secret_service      │  prompt_service(纯组装)      │    │
│  │  weave_service       │  health_monitor(纯算法)      │    │
│  │  conflict_detection  │  book_analysis               │    │
│  │  direction_scoring   │  notification/setting        │    │
│  │  weaving_scheme      │  template/subscription       │    │
│  │  health_service      │  card_retire/import_service  │    │
│  └──────────────────────┴──────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  20 DAO Classes / ~120 自定义方法                           │
│  22 SQLAlchemy Models / 22 DB Tables                        │
│  5 自定义 Middleware                                         │
├─────────────────────────────────────────────────────────────┤
│              LLM Module (1,953 行 / 6 文件)                 │
│  LLMClient · KeyManager · ContextBudget · PromptArchitecture│
├─────────────────────────────────────────────────────────────┤
│              Worker Module (1,378 行 / 10 文件)             │
│  15 Celery Tasks · 4 Beat Periodic · Idempotency · DB Pool  │
└─────────────────────────────────────────────────────────────┘
```

### 核心指标

| 维度 | 数量 | 说明 |
|------|:----:|------|
| Python 源文件 | 190 | app/ 目录下 |
| 总代码行数 | 42,298 | 不含测试和迁移 |
| 数据库表 | 22 | SQLAlchemy ORM |
| API 端点 | 136 | RESTful |
| Service 服务 | 30 | 含 DI 单例注册 |
| DAO 数据访问 | 20 | 含 BaseDAO 通用父类 |
| Celery Worker 任务 | 15 | 含 4 个 Beat 定时 |
| LLM 模块文件 | 6 | 1,953 行 |
| Middleware | 5 | 自定义 |
| Alembic 迁移 | 8 | 数据库版本管理 |

---

## 二、Rust 等价技术栈映射

| Python 当前 | Rust 替代 | 成熟度 | 迁移风险 | 备注 |
|-------------|----------|:------:|:------:|------|
| **FastAPI** | **Axum 0.8** | ✅ 生产级 | 🟢 低 | Tokio 生态，类型安全路由，extractors 对标 Depends |
| **SQLAlchemy 2.0 async** | **SeaORM 1.x** | ✅ 生产级 | 🟢 低 | Async + 关系映射 + 迁移支持 |
| **Pydantic v2** | **serde + validator** | ✅ 生产级 | 🟢 低 | 编译时类型检查更强 |
| **Celery** | **自建 Redis Queue** | 🟡 需自建 | 🔴 高 | 最大迁移难点 (见 §3.1) |
| **Redis (aioredis)** | **redis-rs + bb8** | ✅ 生产级 | 🟢 低 | 连接池 + 异步 |
| **httpx** | **reqwest** | ✅ 生产级 | 🟢 低 | 异步 HTTP 客户端 |
| **JWT (python-jose)** | **jsonwebtoken** | ✅ 生产级 | 🟢 低 | |
| **bcrypt (passlib)** | **bcrypt** | ✅ 生产级 | 🟢 低 | |
| **tenacity** | **backon** | ✅ 生产级 | 🟢 低 | 异步重试 |
| **structlog** | **tracing** | ✅ 生产级 | 🟢 低 | OpenTelemetry 兼容 |
| **Prometheus** | **metrics + exporter** | ✅ 生产级 | 🟢 低 | |
| **Sentry** | **sentry** | ✅ 生产级 | 🟢 低 | |
| **alembic** | **SeaORM Migration** | ✅ 生产级 | 🟡 中 | 需重新编写迁移 |
| **python-docx** | **docx-rs** | 🟡 可用 | 🟡 中 | 功能覆盖可能不完全 |
| **ebooklib** | **epub** | 🟡 可用 | 🟡 中 | Rust epub crate 较新 |
| **beautifulsoup4** | **scraper** | ✅ 生产级 | 🟢 低 | HTML 解析 |
| **trafilatura** | **自定义实现** | 🔴 无等价 | 🔴 高 | 正文提取无 Rust 等价库 |
| **slowapi** | **tower-rate-limit** | 🟡 可用 | 🟡 中 | |
| **orjson** | **serde_json** | ✅ 生产级 | 🟢 低 | 原生性能更好 |

---

## 三、逐模块迁移可行性评估

### 3.1 Celery → 自建任务队列 (最大难点)

**现状**：15 个 Celery 任务 + 4 个 Beat 定时任务，深度集成 Redis broker。

```
Celery Tasks:
├── run_generation_task()       ← LLM 生成长任务 (540s 软超时)
├── health_auto_notify()        ← Beat 每30分钟
├── analyze_book_characters()   ← 书籍分析
├── analyze_book_plot()
├── detect_writing_style()
├── check_card_freshness()      ← 卡片新鲜度
├── retire_cards()              ← 卡片退役
├── generate_replacement_cards()
├── card_retire_check()         ← Beat 每天凌晨2点
├── import_book_task()          ← 文件导入
├── analyze_import_content()
├── run_phase4_analysis()       ← Phase 4 分析
├── phase4_auto_advance()       ← Beat 每小时
├── vault_full_reanalyze()      ← 四库全量重分析
└── vault_periodic_reanalyze()  ← Beat 每6小时
```

**Rust 替代方案 (3选1)**：

| 方案 | 复杂度 | 可靠性 | 推荐 |
|------|:------:|:------:|:----:|
| **A. 保留 Python Celery Worker** (混合架构) | 🟢 低 | ✅ 高 | ⭐ 推荐 |
| B. Rust 自建 Redis Queue + tokio-cron | 🟡 中 | 🟡 中 | 可逐步迁移 |
| C. Lapin (AMQP/RabbitMQ) | 🔴 高 | ✅ 高 | 过度设计 |

**推荐方案 A 理由**：
- Celery 生态成熟，幂等性、重试、超时、Beat 已完善
- Rust 端通过 Redis 消息桥接调用 Python Worker
- 后续可逐个任务用 Rust 自建队列替换
- **Phase 4 编排逻辑（6,000+ 行）可先保留在 Python Worker**

### 3.2 逐模块详细评估

#### P0 核心模块 (必须重写)

| # | 模块 | 行数 | 风险 | 复杂度 | 依赖 | 重写策略 |
|---|------|:----:|:----:|:----:|------|---------|
| 1 | **LLM Client** | 735 | 🟢 | ⭐⭐⭐ | httpx, tenacity | reqwest 直译，KeyPool + RateLimit 用 Arc<RwLock> |
| 2 | **LLM Key Manager** | 275 | 🟢 | ⭐⭐ | Redis | 直接移植 |
| 3 | **LLM Context Budget** | 373 | 🟢 | ⭐⭐ | 无 | 纯算法，直接移植 |
| 4 | **LLM Prompt Architecture** | 551 | 🟢 | ⭐⭐ | 无 | 字符串模板，直接移植 |
| 5 | **Auth Service** | 526 | 🟢 | ⭐⭐ | bcrypt, JWT, Redis | Axum middleware + jsonwebtoken |
| 6 | **Middleware Stack** | 5 文件 | 🟢 | ⭐⭐ | Redis | Axum layer 塔式组合 |
| 7 | **Config/Settings** | 1 文件 | 🟢 | ⭐ | pydantic-settings | figment 或 config crate |

#### P1 数据层 (必须重写)

| # | 模块 | 行数 | 风险 | 复杂度 | 重写策略 |
|---|------|:----:|:----:|:----:|---------|
| 8 | **Models (22 表)** | 1,300 | 🟡 | ⭐⭐⭐ | SeaORM Entity derive，保留软删除 |
| 9 | **DAOs (20 个)** | 2,500 | 🟡 | ⭐⭐ | SeaORM ActiveModel + 泛型 BaseDAO |
| 10 | **Schemas (136 个)** | 1,500 | 🟢 | ⭐ | serde derive |
| 11 | **Migrations** | 8 文件 | 🟡 | ⭐⭐ | SeaORM Migration 重写 |

#### P2 业务服务 (核心功能)

| # | 模块 | 行数 | 风险 | 复杂度 | LLM依赖 | 重写策略 |
|---|------|:----:|:----:|:----:|:---:|---------|
| 12 | **Project Service** | ~300 | 🟢 | ⭐⭐ | 无 | 纯CRUD |
| 13 | **Chapter Service** | ~500 | 🟡 | ⭐⭐⭐ | 无 | CRUD + 章节号计算 + Phase4 触发 |
| 14 | **Card Service** | ~500 | 🟡 | ⭐⭐⭐ | 无 | 加权随机 + 保底机制 |
| 15 | **Card Pool Service** | ~200 | 🟢 | ⭐⭐ | 无 | 新鲜度计算 |
| 16 | **Card Retire Service** | ~150 | 🟢 | ⭐⭐ | 无 | 双策略淘汰 |
| 17 | **Vault Service** | 681 | 🟡 | ⭐⭐ | 无 | 四库CRUD |
| 18 | **Prompt Service** | ~300 | 🟢 | ⭐⭐ | 无 | 5层组装 |
| 19 | **Validation Service** | 879 | 🟡 | ⭐⭐⭐ | 无 | 14项检查，纯规则 |
| 20 | **Vault Filter** | 630 | 🟡 | ⭐⭐⭐ | 无 | 层级压缩+Token估算 |
| 21 | **Book Analysis** | 689 | 🟡 | ⭐⭐ | 无 | 正则提取+统计 |
| 22 | **Notification** | ~150 | 🟢 | ⭐ | 无 | 纯CRUD |
| 23 | **Settings** | ~200 | 🟢 | ⭐ | 无 | 纯CRUD |
| 24 | **Template** | ~200 | 🟢 | ⭐ | 无 | 纯CRUD |
| 25 | **Subscription** | ~150 | 🟢 | ⭐ | 无 | 纯CRUD |
| 26 | **Secret Service** | 725 | 🟡 | ⭐⭐⭐ | ✅ | 秘密矩阵生命周期 |
| 27 | **Weave Service** | ~400 | 🟡 | ⭐⭐ | ✅ | 编织分析 |
| 28 | **Health Service** | ~300 | 🟡 | ⭐⭐ | ✅(R1) | 健康检查 |
| 29 | **Health Monitor** | ~400 | 🟡 | ⭐⭐⭐ | 无 | R1/R2/R3纯算法 |
| 30 | **Coherence** | 627 | 🟡 | ⭐⭐⭐ | ✅ | v2分组检查 |
| 31 | **Algorithm Service** | ~500 | 🟡 | ⭐⭐⭐ | 委托调用 | 6步编排 |

#### P3 高复杂度核心 (可混合保留)

| # | 模块 | 行数 | 风险 | 复杂度 | 策略 |
|---|------|:----:|:----:|:----:|------|
| 32 | **Generation Service** | 938 | 🔴 | ⭐⭐⭐⭐⭐ | **先保留 Python Worker**，12步流水线极复杂 |
| 33 | **Phase4 Service** | 2,396 | 🔴 | ⭐⭐⭐⭐⭐ | **先保留 Python Worker**，核心竞争壁垒 |
| 34 | **Phase4 Scheduler** | 1,338 | 🔴 | ⭐⭐⭐⭐⭐ | **先保留 Python Worker**，三层幂等+分布式锁 |
| 35 | **Phase4 Store** | ~300 | 🟡 | ⭐⭐ | Rust可移植，但依赖Phase4 |
| 36 | **Merge Service** | 1,106 | 🔴 | ⭐⭐⭐⭐ | 4大合并引擎，纯算法但极复杂 |
| 37 | **Conflict Detection** | 808 | 🟡 | ⭐⭐⭐⭐ | 3种冲突检测+U曲线置信度 |
| 38 | **Direction Scoring** | 625 | 🟡 | ⭐⭐⭐⭐ | 5步评分+LLM fallback |
| 39 | **Weaving Scheme** | 803 | 🟡 | ⭐⭐⭐⭐ | 7种编织模式模板 |
| 40 | **Import Service** | 618 | 🟡 | ⭐⭐⭐ | txt/docx/epub 解析 |
| 41 | **Ingest Pipeline** | ~5,000 | 🔴 | ⭐⭐⭐⭐⭐ | **保留 Python**，依赖 trafilatura/BS4 无 Rust 等价 |
| 42 | **Genre Module** | ~2,700 | 🟡 | ⭐⭐⭐⭐ | 冷启动+体裁分析 |

---

## 四、混合架构策略

### 4.1 架构边界

```
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (不变)                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              Rust API Server (Axum)                          │
│                                                              │
│  ✅ 重写:                                                    │
│  · Auth (JWT + bcrypt)             · Middleware 全套          │
│  · 全部 CRUD 端点 (136 个)          · REST API 层             │
│  · 全部数据模型 (22 表)              · DAO 层 (SeaORM)         │
│  · LLM Client + KeyManager          · Context Budget         │
│  · Prompt 组装 (5层)                · Validation (14项检查)  │
│  · Vault Filter (层级压缩)          · Book Analysis          │
│  · Card 抽卡算法 (加权随机)         · Health Monitor (R1-R3) │
│  · Secret Matrix 生命周期           · Coherence v2 检查      │
│  · Merge 四大引擎                   · Conflict Detection     │
│  · Direction Scoring                · Weaving Scheme         │
│  · Settings / Template / Notif 等   · Import (txt/docx/epub) │
│  · Ingest Phase 0 (Scraper)         · Genre 冷启动            │
│                                                              │
│  🔗 Python Worker (保留，通过 Redis 桥接):                    │
│  · Generation Pipeline (12步)       · Phase4 Service         │
│  · Phase4 Scheduler (含分布式锁)    · Ingest Phase 1-3 (LLM) │
│  · Celery Beat 定时任务              · 文件导入异步处理        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Rust ↔ Python 通信协议

```
Rust API Server                     Python Worker
     │                                    │
     │  LPUSH moling:jobs {...json}       │
     ├───────────────────────────────────►│
     │                                    │  BRPOP moling:jobs
     │                                    │  执行任务
     │  SET moling:results:{id} {...}     │
     │◄───────────────────────────────────┤
     │  GET moling:results:{id}           │
     │                                    │
  (长轮询/WebSocket 状态通知)
```

**消息格式 (统一 JSON)**：
```json
{
  "job_id": "uuid",
  "job_type": "generation|phase4|import|ingest",
  "project_id": "uuid",
  "user_id": "uuid",
  "payload": { ... },
  "created_at": "ISO8601"
}
```

### 4.3 Rust 项目结构设计

```
moling-server-rs/
├── Cargo.toml                    # workspace root
├── crates/
│   ├── moling-core/              # 核心类型 + 错误体系
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── error.rs          # AppError + ErrorCode enum
│   │       ├── types.rs          # 共享类型 (ID, DateTime, etc.)
│   │       └── config.rs         # Settings (figment)
│   │
│   ├── moling-db/                # 数据层
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── entities/         # SeaORM Entity (22 表)
│   │       ├── dao/              # DAO (20 个)
│   │       ├── migrations/       # SeaORM Migration
│   │       └── redis.rs          # Redis 连接池 (bb8)
│   │
│   ├── moling-llm/               # LLM 模块
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── client.rs         # LLMClient (reqwest + SSE stream)
│   │       ├── key_manager.rs    # KeyPool + Health
│   │       ├── context_budget.rs # Token 预算
│   │       ├── prompts.rs        # Prompt 模板
│   │       └── prompt_arch.rs    # 4层注入组装
│   │
│   ├── moling-services/          # 业务服务层
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── auth/             # 认证服务
│   │       ├── project/          # 项目服务
│   │       ├── chapter/          # 章节服务
│   │       ├── card/             # 卡牌服务 (含抽卡算法)
│   │       ├── vault/            # 四库服务 (CRUD + Filter)
│   │       ├── secret/           # 秘密矩阵
│   │       ├── validation/       # 14项检查
│   │       ├── coherence/        # v2 连贯性
│   │       ├── merge/            # 四大合并引擎
│   │       ├── conflict/         # 冲突检测
│   │       ├── direction/        # 方向评分
│   │       ├── weaving/          # 编织方案
│   │       ├── health/           # 健康检查 + 监控
│   │       ├── book_analysis/    # 文本分析
│   │       ├── prompt/           # Prompt 5层组装
│   │       ├── import/           # 文件导入解析
│   │       ├── template/         # 模板
│   │       ├── notification/     # 通知
│   │       ├── settings/         # 用户设置
│   │       └── subscription/     # 订阅
│   │
│   ├── moling-api/               # HTTP API 层 (Axum)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── main.rs           # 启动入口
│   │       ├── router.rs         # 路由注册 (19 个模块)
│   │       ├── middleware/       # 5 个中间件
│   │       ├── extractors/       # Auth extractor (对标 Depends)
│   │       └── routes/           # 路由处理函数
│   │           ├── auth.rs
│   │           ├── projects.rs
│   │           ├── chapters.rs
│   │           ├── cards.rs
│   │           ├── vault.rs
│   │           ├── secrets.rs
│   │           ├── generation.rs
│   │           ├── admin.rs
│   │           ├── settings.rs
│   │           ├── templates.rs
│   │           ├── phase4.rs
│   │           ├── weave.rs
│   │           ├── health.rs
│   │           ├── notification.rs
│   │           ├── subscription.rs
│   │           ├── genre.rs
│   │           ├── ingest.rs
│   │           └── mod.rs
│   │
│   └── moling-worker/            # Rust 端任务桥接
│       ├── Cargo.toml
│       └── src/
│           ├── lib.rs
│           └── bridge.rs         # Redis Queue 消息生产者
│
├── migrations/                   # SeaORM 迁移脚本
├── scripts/                      # 辅助脚本
├── docker/                       # Dockerfile (Rust musl build)
└── docs/                         # 文档
```

---

## 五、模块清单 (Module Manifest)

### 迁移批次规划

| 批次 | 模块组 | 文件数 | 预估行数 | 依赖 | 并行度 |
|:----:|--------|:------:|:-------:|------|:------:|
| **B0** | 脚手架 | 10 | 500 | 无 | 1 Agent |
| **B1** | 核心层 | 15 | 3,000 | B0 | 3 Agent |
| **B2** | 数据层 | 40 | 5,000 | B0 | 4 Agent |
| **B3** | 简单服务 | 25 | 3,500 | B2 | 4 Agent |
| **B4** | LLM 模块 | 6 | 2,000 | B1 | 2 Agent |
| **B5** | 复杂算法服务 | 20 | 6,000 | B2+B4 | 3 Agent |
| **B6** | API 路由层 | 20 | 2,500 | B3+B5 | 4 Agent |
| **B7** | 中间件 | 5 | 500 | B1 | 1 Agent |
| **B8** | Python 桥接 | 5 | 500 | B6 | 1 Agent |
| **B9** | 迁移脚本 | 8 | 300 | B2 | 1 Agent |
| **B10** | Docker/部署 | 5 | 200 | B6+B8 | 1 Agent |

### 详细模块清单

| # | 模块 | 批次 | 依赖 | 状态 | 设计 | 实现 | 审查 | 打磨 | 文档 | 验证 |
|---|------|:----:|------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| **B0 脚手架** |
| M01 | 项目骨架 (workspace/Cargo) | B0 | - | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M02 | 错误体系 (AppError/ErrorCode) | B0 | - | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M03 | 配置系统 (Settings/figment) | B0 | - | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B1 核心层** |
| M04 | 核心类型 (ID/UUID/DateTime) | B1 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M05 | Redis 连接池 (bb8) | B1 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M06 | 基础日志 (tracing) | B1 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B2 数据层** |
| M07 | Base Entity + TimestampMixin | B2 | M04 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M08 | User Entity + DAO | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M09 | Project Entity + DAO | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M10 | Chapter Entity + DAO | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M11 | Card Entity + DAO | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M12 | Vault Entities (5) + DAOs | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M13 | Other Entities (10) + DAOs | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M14 | BaseDAO 泛型实现 | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M15 | SeaORM Migrations (8) | B2 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B3 简单服务** |
| M16 | Auth Service (JWT+bcrypt) | B3 | M08+M05 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M17 | Project Service | B3 | M09 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M18 | Chapter Service | B3 | M10+M09 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M19 | Notification Service | B3 | M13 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M20 | Settings Service | B3 | M08 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M21 | Template Service | B3 | M13 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M22 | Subscription Service | B3 | M13 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M23 | Vault Service (四库CRUD) | B3 | M12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B4 LLM 模块** |
| M24 | LLMClient (reqwest+SSE) | B4 | M05+M03 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M25 | KeyManager (KeyPool) | B4 | M05 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M26 | ContextBudget | B4 | - | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M27 | Prompt Architecture (4层) | B4 | - | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B5 复杂算法服务** |
| M28 | Prompt Service (5层组装) | B5 | M27+M12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M29 | Card Service (加权随机+保底) | B5 | M11+M09 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M30 | Card Pool Service | B5 | M11 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M31 | Card Retire Service | B5 | M11 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M32 | Validation Service (14项) | B5 | M12+M14 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M33 | Vault Filter (层级压缩) | B5 | M12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M34 | Secret Service (秘密矩阵) | B5 | M12+M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M35 | Book Analysis (文本分析) | B5 | M10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M36 | Health Monitor (R1-R3) | B5 | M12+M10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M37 | Health Service (+LLM R1) | B5 | M36+M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M38 | Coherence Service (v2) | B5 | M24+M10+M12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M39 | Merge Service (4引擎) | B5 | M12 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M40 | Conflict Detection (3种) | B5 | M12+M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M41 | Direction Scoring (5步) | B5 | M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M42 | Weaving Scheme (7种模式) | B5 | M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M43 | Import Service (文件解析) | B5 | M09+M10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M44 | Weave Service | B5 | M24+M09+M10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M45 | Algorithm Service (6步编排) | B5 | M39-M42 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B6 API 路由层** |
| M46 | Auth Routes (8端点) | B6 | M16 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M47 | Project Routes (11端点) | B6 | M17 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M48 | Chapter Routes (13端点) | B6 | M18 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M49 | Card Routes (8端点) | B6 | M29 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M50 | Vault Routes (22端点) | B6 | M23 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M51 | Secret Routes (4端点) | B6 | M34 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M52 | Generation Routes (7端点) | B6 | M53 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M53 | Admin Routes (8端点) | B6 | M09+M08 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M54 | Settings Routes (10端点) | B6 | M20 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M55 | Template Routes (6端点) | B6 | M21 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M56 | Phase4/Weave/Health/etc. | B6 | M36-M44 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M57 | Genre Routes (3端点) | B6 | M24 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M58 | Ingest Routes (10端点) | B6 | M43 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B7 中间件** |
| M59 | RequestID Middleware | B7 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M60 | ContentLength Limit | B7 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M61 | RateLimit (Redis) | B7 | M05 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M62 | AuditLog | B7 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M63 | ResponseFormat | B7 | M01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B8 Python桥接** |
| M64 | Redis Job Bridge (Pub/Sub) | B8 | M05+M52 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M65 | Worker任务调用封装 | B8 | M64 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B9 迁移脚本** |
| M66 | SeaORM Migration (8个) | B9 | M07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **B10 部署配置** |
| M67 | Dockerfile (musl multi-stage) | B10 | M66 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M68 | docker-compose.yml | B10 | M67 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| M69 | GitHub Actions CI/CD | B10 | M67 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

**总计: 69 个模块**

---

## 六、执行路线图

### 阶段划分

```
Phase A: 基础设施 (B0-B2)        ~2-3 周
├── B0: 脚手架 (M01-M03)
├── B1: 核心层 (M04-M06)
└── B2: 数据层 (M07-M15)

Phase B: 业务核心 (B3-B5)        ~4-6 周
├── B3: 简单服务 (M16-M23)
├── B4: LLM 模块 (M24-M27)
└── B5: 复杂算法服务 (M28-M45)

Phase C: API 层 (B6-B7)          ~1-2 周
├── B6: API 路由 (M46-M58)
└── B7: 中间件 (M59-M63)

Phase D: 集成与混合 (B8-B10)     ~1 周
├── B8: Python 桥接 (M64-M65)
├── B9: 迁移脚本 (M66)
└── B10: 部署配置 (M67-M69)

Phase E: 灰度部署与验证          ~1 周
├── 单元测试 + 集成测试
├── 性能对比 (wrk/oha 压测)
├── 灰度切流 (Nginx split)
└── 全量迁移
```

### 性能预期

| 指标 | Python (FastAPI) | Rust (Axum) | 提升 |
|------|:---------------:|:-----------:|:----:|
| 请求延迟 (P50) | ~15ms | ~2ms | 7.5x |
| 请求延迟 (P99) | ~150ms | ~8ms | 18x |
| 吞吐量 (req/s) | ~3,000 | ~80,000 | 26x |
| 内存占用 (idle) | ~150MB | ~15MB | 10x |
| 内存占用 (peak) | ~500MB | ~50MB | 10x |
| 启动时间 | ~3s | ~0.1s | 30x |
| 镜像大小 | ~300MB | ~15MB | 20x |

---

## 七、风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|:----:|---------|
| **Celery 生态缺失** | 🔴 高 | 混合架构保留 Python Worker，逐步替换 |
| **trafilatura 无 Rust 等价** | 🟡 中 | Ingest 管线保留 Python |
| **Phase 4 复杂度** | 🔴 高 | 核心竞争壁垒保留 Python，API 层 Rust 化 |
| **ORM 语义差异** | 🟡 中 | SeaORM 功能完备，软删除用自定义 trait |
| **异步运行时差异** | 🟢 低 | Tokio 更成熟，无 GIL 限制 |
| **调试生态** | 🟡 中 | tracing + sentry，但缺少 pdb 级交互 |
| **团队 Rust 熟练度** | 🟡 中 | 逐模块渐进迁移，边学边重构 |

---

## 八、ADR: 为什么选择混合架构而非全量 Rust 重写

**决策**: 混合架构 — Rust API 层 + Python Worker 层

**理由**:
1. **Celery 不可替代**: Python Celery 生态（幂等性、重试、超时、Beat、监控）在 Rust 生态无等价成熟方案。自建需 3+ 月且引入新 Bug 风险。
2. **Phase 4 是竞争壁垒**: 2,396 行经过多轮架构加固的代码，包含大量 Python 特有的动态特性（LLM JSON 解析、灵活的类型推断）。全量 Rust 重写风险收益不成比例。
3. **trafilatura 无替代**: 高质量正文提取库 trafilatura 没有 Rust 等价实现，自建需要 NLP 背景和大量语料训练。
4. **80/20 原则**: 80% 的请求是 CRUD + LLM 调用，这些在 Rust 中收益最大（延迟降低 7-18x）。20% 的复杂编排逻辑可渐进迁移。
5. **渐进式零风险**: 每个模块独立验证后再切流，不引入全量迁移的一次性大爆炸风险。

**后果**:
- ✅ 保留 Python 运行时用于 Worker 进程
- ✅ Rust API 层获得极致性能和低资源占用
- ⚠️ 需要维护 Rust ↔ Python 的 JSON 通信协议
- ⚠️ 部署需要同时运行 Rust 和 Python 两个容器（或同一 Pod 两个 sidecar）

---

## 九、下一步行动

1. **确认混合架构方案** ← 当前步骤
2. **B0 脚手架搭建** — 创建 Rust workspace，配置 Cargo.toml，建立 CI
3. **B1 核心层** — Redis 连接池、错误体系、配置系统、日志
4. **B2 数据层** — SeaORM Entity 定义 + 迁移脚本 + BaseDAO
5. **逐模块推进** B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10

**预计总工期**: 8-12 周 (69 模块，高并发多代理并行)
**预计 Rust 代码量**: ~25,000-30,000 行
