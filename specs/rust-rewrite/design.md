# 墨灵 Rust 重写 — 核心架构决策 + 模块清单

> 作者：高见远（架构师）  
> 日期：2025-06-21

---

## Part A：核心架构决策

### ADR-001：混合架构边界

**决策**：Rust 接管全部 HTTP/API/DB/中间件/Auth/Worker；Python LLM 编排通过 localhost HTTP 保留。

**理由**：
- Python LLM 编排（prompt 组装、结果解析、多步推理）高度依赖 prompt 模板迭代，属于高频变更区
- Rust 在 HTTP/DB/并发领域有明显性能优势
- 通过 localhost HTTP 调用实现语言边界，双方独立部署和扩展

**Rust 侧 LLM 职责**（新增决策）：
- `moling-llm` 提供完整的 DeepSeek client、KeyRotator、TokenBudget
- `moling-services` 的 prompt_service 组装 prompt 上下文
- 实际的 `chat/completions` HTTP 调用由 `moling-llm` 完成
- Python sidecar 仅用于需要复杂推理链的场景（如连贯性检查中的多步判断）

### ADR-002：12-Step Pipeline 的单体服务拆分

**问题**：Python `generation_service.py` 的 `execute_generation_pipeline` 方法承载了 12 个步骤，导致文件 938 行。

**决策**：Rust 实现中保持 `GenerationService` 作为编排器，但将各步骤委托给独立的子服务：

```
GenerationService::execute_pipeline()
  ├── step1:  AlgorithmService::weight_allocation()
  ├── step2:  VaultFilterService::filter_by_cards()
  ├── step3:  ConflictDetectionService::detect_conflicts()
  ├── step4:  DirectionScoringService::score_direction_conflicts()
  ├── step5:  WeavingSchemeService::match_scheme()
  ├── step6:  AlgorithmService::fill_outline()
  ├── step7:  PromptService::build_full_prompt()  (Layer 0-4)
  ├── step8:  LLM Client (chat/completions)
  ├── step9:  SecretService::extract_secrets_from_content()
  ├── step10: CoherenceService::validate_post_generation()
  ├── step11: MergeService::auto_merge()  (置信度 HIGH/MEDIUM 自动合并)
  └── step12: DynamicLayerService::update() + CardPoolService::refresh()
```

所有子服务在 `moling-services/src/` 下各自独立文件，通过 `Arc<Service>` 注入到 `GenerationService`。

### ADR-003：Phase4 调度器架构

**问题**：Python 的 `Phase4Scheduler` 有 1,338 行，包含内存队列、Redis 分布式锁、指数退避重试、竞态防护。

**决策**：采用 **Actor 模式**，将 Phase4 调度器实现为一个独立的 tokio task：

```
Phase4Scheduler (独立 tokio task)
  ├── 输入通道: tokio::sync::mpsc::Receiver<Phase4Task>
  ├── 状态管理: Phase4Store (Redis 优先 / 内存回退)
  ├── 并发控制: tokio::sync::Semaphore (限制并发收纳数)
  ├── 幂等性: Redis SET NX (nonce 去重)
  ├── 重试: 指数退避 [10, 30, 60, 120, 300]s，最多 5 次
  └── 内容安全: SourceText Grounding (编辑距离校验)
```

**与 Python 差异**：
- Python 用 `asyncio.Lock` + 内存 OrderedDict → Rust 用 tokio channel + Redis
- Python 手动管理竞态 → Rust 利用类型系统确保 Send + Sync
- 分布式锁：Python 自实现 SETNX → Rust 复用 `moling-core::redis` 的锁原语

### ADR-004：四库合并引擎设计

**问题**：Python `merge_service.py`（1,106 行）实现了四库各自的合并策略 + 置信度降级。

**决策**：采用 **策略模式**，每个库类型一个 MergeStrategy trait：

```rust
trait MergeStrategy<T> {
    fn find_match(&self, incoming: &ChangeEntry, existing: &[T]) -> Option<usize>;
    fn apply_merge(&self, incoming: &ChangeEntry, existing: &mut T) -> MergeResult;
    fn confidence(&self, incoming: &ChangeEntry, matched: &T) -> f64;
}
```

四个实现：
- `CharacterMerge` — 编辑距离模糊匹配（阈值=3）+ 姓氏匹配
- `TimelineMerge` — 事件去重 + 日期归一化
- `PlotPromiseMerge` — 状态机驱动（create/advance/redeem/cancel/escalate）
- `WorldMerge` — 条目合并 + 冲突标记

### ADR-005：卡牌池算法

**问题**：Python 的 CardService 有 442 行抽卡算法，CardPoolService 有 216 行新鲜度计算。

**决策**：保持 Python 的三因子权重模型：

```rust
fn card_weight(card: &CardPool, draw_history: &[DrawRecord]) -> f64 {
    let base = RARITY_WEIGHTS[card.rarity];     // common=1, rare=2, epic=3, legendary=4
    let pity = if should_trigger_pity(draw_history) { 3.0 } else { 1.0 };
    let freshness = if card.draw_count < FRESHNESS_THRESHOLD { FRESHNESS_BONUS } else { 1.0 };
    base * pity * freshness
}
```

抽卡流程：
1. 计算所有活跃卡牌的权重
2. 加权随机选择（`rand::distributions::WeightedIndex`）
3. 重试机制：若抽中已在本次抽牌中的卡，最多重试 `MAX_DRAW_RETRIES` 次
4. 记录抽牌历史到 `draw_history` 表

### ADR-006：Worker 可靠性模型

**决策**：Rust Worker 基于 `moling-worker` crate 的 `TaskQueue` + `CronScheduler`，补充以下能力：

| 能力 | 实现方案 |
|------|---------|
| 任务超时 | `tokio::time::timeout(duration, task).await` |
| 自动重试 | `TaskQueue::dead_letter()` + `retry_dead_letter()` |
| 队列分离 | `generation` 队列 + `default` 队列 |
| Worker 健康 | 定期心跳写入 Redis，超时自动重调度 |
| Panic 恢复 | `std::panic::catch_unwind` 包裹每个 worker |
| 优雅关闭 | `tokio::signal::ctrl_c()` → drain queue → shutdown |

### ADR-007：Prompt 分层架构

保留 Python 的 4 层架构，Rust 侧实现：

```
Layer 0: System Instruction  → PromptBuilder::build_layer0()
Layer 1: Dynamic Context     → PromptBuilder::build_layer1(dynamic_layer)
Layer 2: Vault Filtered Data → PromptBuilder::build_layer2(vault_filter_result)
Layer 3: Card Fusion         → PromptBuilder::build_layer3(cards, weights)
Layer 4: Style Constraints   → PromptBuilder::build_layer4(project.style)
```

TokenBudget 在组装完成后执行分层截断（Layer 4→3→2 逐层压缩）。

---

## Part B：模块清单

### 8 Crate 两级结构

| # | Crate | Module | Python Source | Rust File | Status | LOC Py | LOC Rs | Priority | Deps |
|---|-------|--------|--------------|-----------|--------|--------|--------|---------|------|
| 1 | moling-core | config | `app/config.py` | `config.rs` | ✅ | ~100 | ~80 | — | — |
| 2 | moling-core | error | `app/errors.py` | `error.rs` | ✅ | ~50 | ~120 | — | — |
| 3 | moling-core | redis | Redis pool | `redis.rs` | ✅ | ~30 | ~60 | — | — |
| 4 | moling-core | types | 通用类型 | `types.rs` | ✅ | ~20 | ~50 | — | — |
| 5 | moling-core | logging | logging 配置 | `logging.rs` | ✅ | ~20 | ~40 | — | — |
| 6 | moling-db | entities (20) | `app/models/` (22) | `entities/` (20) | 🟢 | ~1500 | ~1200 | P1 | core |
| 7 | moling-db | dao (15) | `app/dao/` (17) | `dao/` (15) | 🟢 | ~2467 | ~2000 | P1 | core |
| 8 | moling-db | migration (8) | `alembic/` | `migration/` (8) | 🟢 | ~500 | ~800 | P1 | core |
| 9 | moling-db | pool | — | `pool.rs` | ✅ | — | ~30 | — | core |
| 10 | moling-auth | jwt | `auth_service.py` JWT | `jwt.rs` | ✅ | ~50 | ~80 | — | core |
| 11 | moling-auth | password | passlib/bcrypt | `password.rs` | ✅ | ~20 | ~30 | — | core |
| 12 | moling-auth | blacklist | `auth/blacklist.py` | `blacklist.rs` | ✅ | ~30 | ~50 | — | core, redis |
| 13 | moling-auth | lockout | — | `lockout.rs` | ✅ | — | ~60 | — | core |
| 14 | moling-auth | middleware | `dependencies.py` | `middleware.rs` | ✅ | ~40 | ~50 | — | core |
| 15 | moling-auth | extractor | FastAPI Depends | `extractor.rs` | ✅ | ~30 | ~40 | — | core |
| 16 | moling-api | middleware (8) | `app/middleware/` (5) | `middleware/` (7) | ✅ | ~250 | ~500 | — | core, auth |
| 17 | moling-api | routes/auth | `router/auth.py` | `routes/auth.rs` | 🟢 | ~100 | ~60 | P2 | auth, services |
| 18 | moling-api | routes/project | `router/project.py` | `routes/project.rs` | 🟢 | ~80 | ~60 | P2 | services |
| 19 | moling-api | routes/chapter | `router/chapter.py` | `routes/chapter.rs` | 🟢 | ~80 | ~60 | P2 | services |
| 20 | moling-api | routes/vault | `router/vault.py` | `routes/vault.rs` | 🟢 | ~100 | ~60 | P2 | services |
| 21 | moling-api | routes/card | `router/card.py` | `routes/card.rs` | 🟡 | ~120 | ~50 | P0 | services |
| 22 | moling-api | routes/generation | `router/generation.py` | `routes/generation.rs` | 🔴 | ~150 | ~40 | P0 | services |
| 23 | moling-api | routes/phase4 | `router/phase4.py` | `routes/phase4.rs` | 🔴 | ~100 | ~30 | P0 | services |
| 24 | moling-api | routes/secret | `router/secret.py` | `routes/secret.rs` | 🟡 | ~80 | ~40 | P1 | services |
| 25 | moling-api | routes/health | `router/health.py` | `routes/health.rs` | 🟡 | ~60 | ~30 | P1 | services |
| 26 | moling-api | routes/import | `ingest/router.py` | `routes/import_route.rs` | 🔴 | ~80 | ~30 | P1 | services |
| 27 | moling-api | routes/weave | `router/weave.py` | `routes/weave.rs` | 🔴 | ~40 | ~20 | P2 | services |
| 28 | moling-api | routes/genre | `router/genre.py` | `routes/genre.rs` | 🔴 | ~40 | ~20 | P2 | services |
| 29 | moling-api | routes/template | `router/template.py` | `routes/template.rs` | 🟢 | ~40 | ~30 | P2 | services |
| 30 | moling-api | routes/setting | `router/setting.py` | `routes/setting.rs` | 🟢 | ~40 | ~30 | P2 | services |
| 31 | moling-api | routes/notification | `router/notification.py` | `routes/notification.rs` | 🟢 | ~40 | ~30 | P2 | services |
| 32 | moling-api | routes/subscription | `router/subscription.py` | `routes/subscription.rs` | 🟢 | ~40 | ~30 | P2 | services |
| 33 | moling-api | routes/admin | `router/admin.py` | `routes/admin.rs` | 🟡 | ~50 | ~30 | P2 | services |
| 34 | moling-api | state | — | `state.rs` | ✅ | — | ~40 | — | core, db |
| 35 | moling-api | types | — | `types.rs` | ✅ | — | ~30 | — | core |
| 36 | moling-services | project | `project_service.py` | `project_service.rs` | 🟢 | 202 | 192 | P2 | db |
| 37 | moling-services | chapter | `chapter_service.py` | `chapter_service.rs` | 🟢 | 408 | 178 | P2 | db |
| 38 | moling-services | vault | `vault_service.py` | `vault_service.rs` | 🟡 | 681 | 154 | P1 | db |
| 39 | moling-services | card | `card_service.py` | `card_service.rs` | 🔴 | 442 | 85 | P0 | db |
| 40 | moling-services | generation | `generation_service.py` | `generation_service.rs` | 🔴 | 938 | 70 | P0 | db, llm, algorithm |
| 41 | moling-services | phase4 | `phase4_service.py` | `phase4_service.rs` | 🔴 | 2396 | 52 | P0 | db, llm, merge |
| 42 | moling-services | health | `health_service.py` + `health_monitor.py` | `health_service.rs` | 🔴 | 823 | 48 | P1 | db |
| 43 | moling-services | import | `import_service.py` + `ingest/` | `import_service.rs` | 🔴 | 618 | 72 | P1 | db |
| 44 | moling-services | secret | `secret_service.py` | `secret_service.rs` | 🔴 | 725 | 89 | P1 | db, llm |
| 45 | moling-services | prompt | `prompt_service.py` | `prompt_service.rs` | 🟡 | 395 | 94 | P0 | llm |
| 46 | moling-services | weave | `weave_service.py` | `weave_service.rs` | 🔴 | 326 | 35 | P2 | db, llm |
| 47 | moling-services | setting | `setting_service.py` | `setting_service.rs` | 🟢 | 202 | 53 | P2 | db |
| 48 | moling-services | template | `template_service.py` | `template_service.rs` | 🟢 | 182 | 75 | P2 | db |
| 49 | moling-services | notification | `notification_service.py` | `notification_service.rs` | 🟢 | 131 | 65 | P2 | db |
| 50 | moling-services | subscription | — | `subscription_service.rs` | 🟢 | — | 40 | P2 | db |
| 51 | moling-services | **algorithm** | `algorithm_service.py` | **缺失** | 🔴 | 252 | 0 | P0 | vault_filter, conflict, direction, weaving |
| 52 | moling-services | **direction_scoring** | `direction_scoring.py` | **缺失** | 🔴 | 625 | 0 | P0 | llm |
| 53 | moling-services | **conflict_detection** | `conflict_detection.py` | **缺失** | 🔴 | 808 | 0 | P0 | db, llm |
| 54 | moling-services | **coherence** | `coherence_service.py` | **缺失** | 🔴 | 627 | 0 | P0 | db, llm |
| 55 | moling-services | **validation** | `validation_service.py` | **缺失** | 🔴 | 879 | 0 | P0 | db |
| 56 | moling-services | **vault_filter** | `vault_filter.py` | **缺失** | 🔴 | 630 | 0 | P0 | db |
| 57 | moling-services | **weaving_scheme** | `weaving_scheme.py` | **缺失** | 🔴 | 803 | 0 | P0 | llm |
| 58 | moling-services | **merge** | `merge_service.py` | **缺失** | 🔴 | 1106 | 0 | P0 | db |
| 59 | moling-services | **phase4_scheduler** | `phase4_scheduler.py` | **缺失** | 🔴 | 1338 | 0 | P0 | db, redis, phase4 |
| 60 | moling-services | **book_analysis** | `book_analysis_service.py` | **缺失** | 🔴 | 689 | 0 | P1 | db |
| 61 | moling-services | **card_pool** | `card_pool_service.py` | **缺失** | 🔴 | 216 | 0 | P1 | db |
| 62 | moling-services | **card_retire** | `card_retire_service.py` | **缺失** | 🔴 | 186 | 0 | P1 | db, card_pool |
| 63 | moling-services | **dynamic_layer** | `dynamic_layer_dao.py` | **缺失** | 🔴 | 0 | 0 | P0 | db |
| 64 | moling-llm | client | `llm/client.py` | `client.rs` | ✅ | ~300 | 261 | — | — |
| 65 | moling-llm | key_rotator | `llm/key_manager.py` | `key_rotator.rs` | 🟡 | ~200 | ~80 | P0 | — |
| 66 | moling-llm | budget | `llm/context_budget.py` | `budget.rs` | 🟡 | ~150 | ~50 | P0 | — |
| 67 | moling-llm | prompt | `service/prompt_service.py` | `prompt.rs` | 🟡 | 395 | ~50 | P0 | — |
| 68 | moling-worker | queue | Celery + Redis | `queue.rs` | ✅ | ~80 | 194 | — | core, redis |
| 69 | moling-worker | scheduler | Celery Beat | `scheduler.rs` | ✅ | ~40 | 204 | — | — |
| 70 | moling-worker | workers/generation | `worker/tasks.py` | `generation.rs` | 🔴 | ~200 | 93 | P0 | db, llm, services |
| 71 | moling-worker | workers/phase4 | `worker/phase4_task.py` | `phase4.rs` | 🔴 | ~150 | 66 | P0 | db, services |
| 72 | moling-worker | workers/vault_reanalyze | `worker/vault_reanalyze_task.py` | `vault_reanalyze.rs` | 🔴 | ~80 | ~30 | P1 | db, services |
| 73 | moling-worker | workers/card_retire | `worker/card_retire_task.py` | `card_retire.rs` | 🔴 | ~60 | ~30 | P1 | db, services |
| 74 | moling-worker | workers/health_notify | — | `health_notify.rs` | 🔴 | — | ~30 | P1 | db, services |
| 75 | moling-worker | workers/import_task | `worker/import_task.py` | `import_task.rs` | 🔴 | ~80 | ~30 | P1 | db, services |
| 76 | moling-worker | workers/analysis | `worker/book_analysis_task.py` | `analysis.rs` | 🔴 | ~80 | ~30 | P1 | db, services |
| 77 | moling-server | main | `app/main.py` | `main.rs` | 🟢 | ~100 | ~80 | P2 | all |

**统计**：
- ✅ DONE: 16 模块
- 🟢 BASIC: 15 模块
- 🟡 STUB: 14 模块
- 🔴 MISSING: 32 模块

---

## Part C：架构决策补充

### ADR-008：Python LLM Sidecar 协议

Rust ↔ Python 通过 localhost HTTP 通信：

```
POST http://localhost:9001/llm/generate
Content-Type: application/json

{
  "prompt": "...",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "max_tokens": 4096,
  "response_format": "json_object"
}

Response:
{
  "content": "...",
  "tokens_used": 1234,
  "model": "deepseek-chat"
}
```

Fallback：当 Python sidecar 不可用时，Rust `moling-llm` 的 `DeepSeekClient` 直接调用 DeepSeek API。

### ADR-009：事务边界

Python 使用 SQLAlchemy 的 `AsyncSession` 手动管理 `commit/rollback`。Rust 使用 SeaORM 的 `DatabaseConnection` + `TransactionTrait`：

- 读操作：不开启事务
- 写操作：`db.begin().await` → 操作 → `tx.commit().await`
- Phase4 收纳（多表写入）：一个事务内完成 vault + card + dynamic_layer 的所有写入
- Worker 任务：每个任务独立事务，失败自动回滚

### ADR-010：错误处理策略

```rust
// moling-core/src/error.rs
pub enum ErrorCode {
    ProjectNotFound,
    ChapterNotFound,
    VaultEntryNotFound,
    CardNotFound,
    SecretNotFound,
    UserNotFound,
    AuthFailed,
    TokenExpired,
    TokenBlacklisted,
    AccountLocked,
    ValidationError,
    ConflictError,
    RateLimitExceeded,
    Forbidden,
    InternalError,
    LLMError,
    RedisError,
    DbError,
}

pub struct AppError {
    pub code: ErrorCode,
    pub message: String,
    pub status: u16,
}
```

HTTP 响应统一格式：`{ "code": "...", "message": "...", "data": ... }`
