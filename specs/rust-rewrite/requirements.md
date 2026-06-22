# 墨灵 Rust 重写 — 差距分析汇总

> 作者：高见远（架构师）  
> 日期：2025-06-21  
> 基线：Python 后端 `moling-server/app/` ↔ Rust 重写 `moling-server-rs/crates/`

---

## 1. 总体概览

| 指标 | Python | Rust | 差距 |
|------|--------|------|------|
| Service 代码总行数 | ~17,421 | ~1,339 | **16,082 行待移植** |
| Service 模块数 | 30 | 16 | 14 个缺失 |
| DAO 代码行数 | ~2,467 | 结构完整 | 功能基本对齐 |
| Model/Entity 数 | 22 | 20 | 差 2 个 (ingest_job, plan) |
| Route 文件数 | 20 | 18 | 接近对齐 |
| Worker 模块数 | 6 (完整Celery) | 7 (全部stub) | 实现度 < 5% |

**总体完成度估算：~15%**（基础设施 70%，业务逻辑 5%）

---

## 2. 逐模块差距扫描

### 2.1 moling-core（基础设施）

| 组件 | Python 对应 | Rust 状态 | 差距等级 |
|------|-----------|----------|---------|
| config.rs | `app/config.py` | 完成 | ✅ DONE |
| error.rs | `app/errors.py` | 完成（含 AppError 枚举） | ✅ DONE |
| redis.rs | Redis pool | 完成 | ✅ DONE |
| types.rs | 通用类型 | 完成 | ✅ DONE |
| logging.rs | logging 配置 | 完成 | ✅ DONE |

### 2.2 moling-db（数据库层）

| 组件 | 差距分析 | 状态 |
|------|---------|------|
| 15 个 DAO | 结构完整，通用 BaseDao trait 覆盖 CRUD + 软删除 | 🟢 BASIC |
| 20 个 Entity | 字段基本对齐，缺 ingest_job 和 plan 实体 | 🟢 BASIC |
| 8 个 Migration | 按顺序可执行 | 🟢 BASIC |
| 字段对齐 | 需逐个对照 Python model 验证字段类型/默认值 | 🟡 需验证 |

**备注**：DAO 层是 Rust 重写做得最好的部分，但仍有细节差异（如 Python 的 `card_dao.py` 有 `list_active_by_project` 等专用方法，Rust 对应方法需要确认）。

### 2.3 moling-auth（认证授权）

| 组件 | Python 对应 | Rust 状态 | 差距 |
|------|-----------|----------|------|
| JWT 签发/验证 | `auth_service.py` 的 `_create_access_token` | `jwt.rs` 完成 | ✅ DONE |
| bcrypt 密码 | `passlib` + `CryptContext` | `password.rs` 完成 | ✅ DONE |
| 黑名单检查 | `auth/blacklist.py` (Redis) | `blacklist.rs` 完成 | ✅ DONE |
| 登录锁定 | 无显式锁定逻辑 | `lockout.rs` 完成（新增能力） | ✅ DONE |
| 认证中间件 | `dependencies.py` | `middleware.rs` 完成 | ✅ DONE |
| 令牌提取器 | FastAPI `Depends` | `extractor.rs` 完成 | ✅ DONE |

**GAP: 0 项。moling-auth 是完成度最高的 crate。**

### 2.4 moling-api（HTTP 路由层）

| 组件 | 差距分析 | 状态 |
|------|---------|------|
| 8 个中间件 | audit_log, content_length, cors, rate_limit, request_id, response_format, sentry — 全部完成 | ✅ DONE |
| 18 个路由文件 | 路由定义骨架存在，但 handler 中大量调用未实现的 service 方法 | 🟡 STUB |
| 状态管理 | `state.rs` 完成（AppState） | ✅ DONE |
| 类型定义 | `types.rs` 完成 | ✅ DONE |

**18 个路由详细状态**：

| 路由 | Python 源码 | Rust 状态 |
|------|-----------|----------|
| admin | `router/admin.py` | 骨架（需 service 支撑） |
| auth | `router/auth.py` | **基本完成**（auth service 完整） |
| card | `router/card.py` | 骨架（card service 缺算法） |
| chapter | `router/chapter.py` | **基本完成**（chapter service 完整） |
| generation | `router/generation.py` | 骨架（generation 缺 12-step pipeline） |
| genre | `router/genre.py` | 骨架（genre 模块 7 个文件完全未移植） |
| health | `router/health.py` | 骨架（仅系统健康，无项目健康） |
| import_route | `ingest/router.py` | 骨架（3 阶段 pipeline 全 stub） |
| notification | `router/notification.py` | **基本完成** |
| phase4 | `router/phase4.py` | 骨架（核心逻辑全缺失） |
| project | `router/project.py` | **基本完成** |
| secret | `router/secret.py` | 部分（缺 LLM 提取/传播逻辑） |
| setting | `router/setting.py` | **基本完成** |
| subscription | `router/subscription.py` | 基本完成（mock checkout） |
| template | `router/template.py` | **基本完成** |
| vault | `router/vault.py` | **基本完成**（四库 CRUD 完成） |
| weave | `router/weave.py` | 全部占位 |

### 2.5 moling-services（业务逻辑层）— **最大差距区**

| Rust Service | LOC | Python 对应 | LOC | 差距等级 | 缺失内容 |
|-------------|-----|-----------|-----|---------|---------|
| project_service | 192 | project_service.py | 202 | 🟢 BASIC | stats/suggest 缺精度 |
| chapter_service | 178 | chapter_service.py | 408 | 🟢 BASIC | confirm→Phase4 不完整 |
| vault_service | 154 | vault_service.py | 681 | 🟡 STUB | 缺 vault_filter 集成，reanalyze 占位 |
| card_service | 85 | card_service.py | 442 | 🔴 MISSING | **权重算法/保底/新鲜度/抽卡重试** |
| generation_service | 70 | generation_service.py | 938 | 🔴 MISSING | **12步 pipeline 完全缺失** |
| phase4_service | 52 | phase4_service.py | 2396 | 🔴 MISSING | **收纳流程/LLM提取/四库合并** |
| health_service | 48 | health_service.py + health_monitor.py | 823 | 🔴 MISSING | **R1/R2/R3 项目健康检查** |
| import_service | 72 | import_service.py + ingest/ | 618+ | 🔴 MISSING | **3阶段pipeline/章节拆分/格式解析** |
| secret_service | 89 | secret_service.py | 725 | 🔴 MISSING | **LLM提取/传播/债务模型** |
| prompt_service | 94 | prompt_service.py | 395 | 🟡 STUB | 4层架构缺 Layer 3/4 详细模板 |
| weave_service | 35 | weave_service.py | 326 | 🔴 MISSING | **LLM编织分析/建议应用** |
| setting_service | 53 | setting_service.py | 202 | 🟢 BASIC | 缺 export 实现 |
| template_service | 75 | template_service.py | 182 | 🟢 BASIC | 功能对齐 |
| notification_service | 65 | notification_service.py | 131 | 🟢 BASIC | 功能对齐 |
| subscription_service | 40 | — | — | 🟢 BASIC | 功能对齐 |

**缺失的完整 Python Service（Rust 中完全不存在）**：

| Python Service | LOC | 核心功能 | 优先级 |
|---------------|-----|---------|--------|
| algorithm_service.py | 252 | 6 步算法编排（step1-6） | P0 |
| direction_scoring.py | 625 | 方向相容性矩阵 + LLM fallback | P0 |
| conflict_detection.py | 808 | 3 类冲突检测 + U曲线置信度 | P0 |
| coherence_service.py | 627 | 3 组分组一致性检查 | P0 |
| validation_service.py | 879 | 14 项检查（7 pre + 7 post） | P0 |
| vault_filter.py | 630 | 四库过滤 + 层级压缩 | P0 |
| weaving_scheme.py | 803 | 3 种编织模式 + 规则引擎 | P0 |
| merge_service.py | 1106 | 四库合并 + 置信度降级 | P0 |
| book_analysis_service.py | 689 | 角色/情节/风格分析 | P1 |
| card_pool_service.py | 216 | 新鲜度计算 | P1 |
| card_retire_service.py | 186 | 退役检查 + 上限控制 | P1 |
| phase4_scheduler.py | 1338 | 调度器/竞态/幂等/重试 | P0 |
| phase4_store.py | 201 | 双模 Redis/内存后端 | P1 |

### 2.6 moling-llm（LLM 客户端）

| 组件 | Python 对应 | Rust 状态 | 差距 |
|------|-----------|----------|------|
| DeepSeekClient | `llm/client.py` (含流式+重试) | `client.rs` **完成**（含流式） | ✅ DONE |
| KeyRotator | `llm/key_manager.py` (双池) | `key_rotator.rs` — 需验证双池支持 | 🟡 STUB |
| TokenBudget | `llm/context_budget.py` (分层截断) | `budget.rs` — 需验证策略完整性 | 🟡 STUB |
| PromptBuilder | `service/prompt_service.py` (4 层架构) | `prompt.rs` — 需验证多模板 | 🟡 STUB |
| RateLimitTracker | `llm/client.py` | Rust 中**缺失** | 🔴 MISSING |

### 2.7 moling-worker（后台 Worker）

| 组件 | Python 对应 | Rust 状态 | 差距 |
|------|-----------|----------|------|
| TaskQueue | Celery + Redis | `queue.rs` **完成**（BRPOPLPUSH + DLQ） | ✅ DONE |
| CronScheduler | Celery Beat | `scheduler.rs` **完成**（cron 解析 + 调度） | ✅ DONE |
| generation worker | `worker/tasks.py:run_generation_task` | Stub — 无真实 LLM 调用 | 🔴 MISSING |
| phase4 worker | `worker/phase4_task.py` | Stub — 4 步全部占位 | 🔴 MISSING |
| vault_reanalyze | `worker/vault_reanalyze_task.py` | Stub | 🔴 MISSING |
| card_retire | `worker/card_retire_task.py` | Stub | 🔴 MISSING |
| health_notify | — | Stub | 🔴 MISSING |
| import_task | `worker/import_task.py` | Stub | 🔴 MISSING |
| analysis | `worker/book_analysis_task.py` | Stub | 🔴 MISSING |
| Idempotency | `worker/idempotency.py` (Redis SETNX) | Worker 中使用 Redis SETNX | 🟢 BASIC |

---

## 3. 关键差距总结

### 🔴 红色（核心业务逻辑完全缺失）

1. **Generation 12-Step Pipeline** — Python `execute_generation_pipeline()` 938 行，Rust 仅有 CRUD 操作
2. **Phase4 收纳流程** — Python 2,396 行核心逻辑（LLM 提取 + 四库合并 + 动态层更新），Rust 仅 52 行占位
3. **Phase4 调度器** — Python 1,338 行（分布式锁/竞态防护/指数退避重试），Rust 完全不存在
4. **四库合并引擎** — Python 1,106 行（模糊匹配/状态变更/置信度降级），Rust 完全不存在
5. **算法编排 6 步** — Python 全套（权重→过滤→冲突→评分→编织→大纲），Rust 完全不存在
6. **项目健康检查 R1/R2/R3** — Python 823 行（角色一致性/时间线连续性/伏笔债务），Rust 仅系统级 ping
7. **导入引擎** — Python 3 阶段 pipeline + 章节拆分 + 多格式解析，Rust 全部 stub
8. **秘密矩阵** — Python LLM 提取 + 传播 + 债务模型，Rust 仅 CRUD

### 🟡 黄色（有骨架但缺关键逻辑）

1. **卡牌抽卡算法** — 缺失权重计算（稀有度/保底/新鲜度三重因子）
2. **Prompt 构建** — 4 层架构仅实现 Layer 0-2 简易版
3. **LLM KeyRotator** — 缺失双池管理/健康检测/指数退避
4. **TokenBudget** — 缺失分层截断策略
5. **四库过滤** — 缺失 ID 过滤 + 层级压缩算法

### 🟢 绿色（基本完成，需微调）

1. Auth 全套（JWT/bcrypt/黑名单/锁定/中间件）
2. Project CRUD
3. Chapter CRUD（含 confirm/reorder）
4. Vault 四库 CRUD（list/create/update/delete）
5. Template CRUD
6. Notification CRUD
7. Setting/Subscription 基本功能

---

## 4. Worker 可靠性对比

| 能力 | Python (Celery) | Rust | 差距 |
|------|----------------|------|------|
| 任务队列 | Celery + Redis | BRPOPLPUSH + DLQ | ✅ 对齐 |
| 幂等性 | Redis SETNX + DB 检查 | Redis SETNX + DB 检查 | ✅ 对齐 |
| 超时控制 | soft(9min)/hard(10min) | **缺失** | 🔴 |
| 重试策略 | Celery max_retries + backoff | **缺失** | 🔴 |
| 死信队列 | Celery DLX 等效 | `TaskQueue::dead_letter()` | ✅ 对齐 |
| Cron 调度 | Celery Beat | `CronScheduler` | ✅ 对齐 |
| Worker 重启 | max_tasks_per_child=50 | **缺失** | 🟡 |
| 队列分离 | default / llm 双队列 | **缺失** | 🟡 |

---

## 5. Python 独有但 Rust 需特别设计的子系统

### 5.1 Genre 分析模块（7 文件）
- `a1_opening.py` / `a2_characters.py` / `a3_hooks.py` / `a4_rhythm.py` / `a5_profile_output.py`
- `cold_start_loader.py` / `models.py`
- **状态**：Rust 中完全不存在
- **复杂度**：中等（约 1,500 行总代码）
- **建议**：P1 优先级，独立 crate 或 moling-services 子模块

### 5.2 Scraper 爬虫模块（14 文件）
- `core/` — fetcher, extractor, cleaner, toc_crawler, style_analyzer, style_prompt_builder
- `splitter/` — base, chapter, paragraph, strategies
- `pipeline.py` — 编排
- **状态**：Rust 中完全不存在
- **复杂度**：高（约 2,000 行总代码）
- **建议**：P2 优先级（独立功能，不阻塞核心流程）

---

## 6. 数据库字段对齐风险

Python Model 使用了 SQLAlchemy 的 `JSON` 字段类型和灵活的 nullable 处理。Rust SeaORM 需要显式处理：
- `serde_json::Value` ↔ `JSONB` 的序列化差异
- UUID 主键：Python 使用 `UUID(as_uuid=True)`，Rust 使用 `String`
- 时间字段：Python `datetime(timezone.utc)` vs Rust `chrono::DateTime<Utc>`
- 枚举字段：Python `enum.Enum` vs Rust 字符串比较

**建议**：作为 P0 任务对每个 Entity 做字段级校验。

---

## 7. 重写策略建议

基于差距分析，推荐以下优先级顺序：

1. **P0-基础设施补全**：LLM KeyRotator 双池 + TokenBudget 分层截断 + Worker 超时/重试
2. **P0-核心算法移植**：12步 Pipeline 依赖链（algorithm → direction → conflict → weaving → coherence → validation）
3. **P0-Phase4 引擎**：收纳流程 + 四库合并 + 调度器 + 卡牌池更新
4. **P1-辅助模块**：健康检查、秘密矩阵、书籍分析、导入引擎
5. **P2-增强模块**：Genre、Scraper、编织建议

**混合架构边界**：Python LLM 编排通过 localhost HTTP 调用保留，Rust 负责所有 HTTP/API/DB/中间件/Auth/Worker。关键的 LLM prompt 组装和结果解析在 Rust 侧完成，仅实际 LLM API 调用可委托给 Python sidecar。
