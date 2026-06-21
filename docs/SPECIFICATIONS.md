# 墨灵 (Moling) 规格文档

> **版本**: 2.6.0 | **最后更新**: 2026-06-21
> 本文档整合了 P0/P1 规格、P0 剩余架构项、卡牌组合算法规格及架构加固实现规格。

---

## 目录

1. [P0 规格](#1-p0-规格)
2. [P1 规格](#2-p1-规格)
3. [卡牌组合算法](#3-卡牌组合算法)
4. [架构加固规格](#4-架构加固规格)
5. [质量门禁](#5-质量门禁)

---

## 1. P0 规格

### 1.1 P0-4: 卡牌淘汰集成（小）

**目标**: Phase 4 写入完成后自动触发卡牌淘汰检查，确保卡牌池不超过上限，新鲜期过期卡牌自动退役。

**实现要求**:
- `phase4_service.py` 的 `run_phase4()` 最后一步调用 `card_retire_service.check_and_retire(db, project_id)`
- 必须与 Phase 4 写入在同一事务中
- 淘汰逻辑：上限检查（`MAX_ACTIVE_CARDS=80`）、新鲜期检查、幂等性

**测试要求**: ≥8 个（功能/边界/稳定性）

### 1.2 P0-6: API Key Pool 轮转（中）

**目标**: 实现 Pro Pool (9 Keys) + Flash Pool (6 Keys) 双池管理。

**实现要求**:
- `app/llm/key_manager.py` 新建 `KeyManager` 类
- `LEAST_USAGE` / `ROUND_ROBIN` 选择策略
- 指数退避冷却（30s→60s→120s→300s）
- 线程安全（`asyncio.Lock`）

**测试要求**: ≥12 个

### 1.3 P0-1: SourceText 内容安全验证（大）

**目标**: Phase 4 入口的 SourceText Grounding，防止幻觉入库。

**实现要求**:
- RapidFuzz `partial_ratio` ≥ 85% → 通过
- < 85% → 调用 LLM-as-Judge 二次确认
- 超大章节（>5000字）分段处理

**测试要求**: ≥15 个

### 1.4 P0-3: 四库合并服务（大型，核心价值）

**新文件**: `app/service/merge_service.py`

通用合并模式：解析验证 → 查找匹配 → 执行合并 → 记录日志

| 子库 | 匹配策略 | 置信度降级 |
|------|----------|-----------|
| 人物库 | 精确ID→精确名称→别名→编辑距离≤2→姓氏→新建 | 1.0→0.9→0.75→0.5→0.3 |
| 时间线 | add/resolve_date/correct | 日期冲突处理 |
| 剧情承诺 | create/advance/redeem/cancel | 超时20章标记stale |
| 世界观 | 分类映射：geography/history/system/faction/event | 冲突标记 |

**测试要求**: ≥30 个

### 1.5 P0-5: 事务原子性保证（中型）

**改造**: `phase4_service.py` 使用 savepoint 保护合并操作。

事务边界：
- LLM 调用在外（不计入事务，可重试）
- 四库合并/卡牌充实/淘汰/变更日志在 savepoint 内
- savepoint 失败不回滚 LLM 结果（节省 token）

**测试要求**: ≥8 个

### 1.6 P0-2: 完整调度器状态机（大型）

**状态定义**:
```
IDLE → QUEUED → LOCKING → EXTRACTING → VERIFYING → MERGING → COMMITTING → DONE
                 ↓          ↓           ↓          ↓         ↓
               RETRY      RETRY       RETRY      RETRY     FAILED
```

**分布式锁**: Redis SET NX EX，TTL 30s，轮询 200ms/次，最多 15 次

**幂等性**: 三层（内存 nonce LRU 1000条 → DB UNIQUE 约束 → chapter_id+text_hash）

**失败回补**: 指数退避 [10, 30, 60, 120, 300] 秒，最多 5 次重试

**测试要求**: ≥20 个

---

## 2. P1 规格

### 2.1 P1-1 + P1-2: 拆书引擎冷启动 & 数据退役

**新文件**: `app/genre/cold_start_loader.py`

B1-B5 流程：
1. 用户选择类型 + 输入梗概
2. 系统加载 Genre Profile
3. 预填四库（角色原型 3-5 个 + 世界观模板 + 时间线骨架）
4. 预填动态层（开局状态 + 章节锚点 + 初始钩子）
5. 预填卡牌池（15-20 条，按 synopsis 排序）

**数据退役**（§9.7）：4 个触发器（连续零命中/超100章未用/引擎版本更新/用户手动）
权重衰减：80%→50%→20%→0%

**测试要求**: ≥25 个

### 2.2 P1-3: 导入引擎验收测试

**目标**: 连载书导入引擎（Phase 0-3）边界条件验收。

**新增测试**: ≥15 个（短篇/长篇/批量/覆盖/空章节/超大/重复/断点续传/并发）

**性能目标**: 单章 < 2s（不含 LLM），100 章批量 < 60s

### 2.3 P1-4: 置信度降级策略实现

4 级置信度区间：

| 区间 | 行为 | 颜色 |
|:----:|:----:|:----:|
| > 0.8 | 自动入库 | 🟢 |
| 0.5-0.8 | 自动入库 + 后台标记"需审核" | 🟡 |
| 0.3-0.5 | 暂停入库，弹窗确认 | 🟠 |
| < 0.3 | 忽略 | 🔴 |

**测试要求**: ≥12 个

---

## 3. 卡牌组合算法

### 3.1 核心流程

```
Step 1: 抽卡 → Step 2: 四库过滤 → Step 3: 冲突检测 → Step 4: 方向评分 → Step 5: 编织方案 → Step 6: 大纲填充
```

### 3.2 已实现的服务

| 服务 | 文件 | 测试数 |
|------|------|:------:|
| VaultFilterService | `app/service/vault_filter.py` | 42 |
| ConflictDetectionService | `app/service/conflict_detection.py` | 32 |
| DirectionScoringService | `app/service/direction_scoring.py` | 49 |
| WeavingSchemeService | `app/service/weaving_scheme.py` | 62 |
| **总计** | | **185** |

### 3.3 核心改进

- **四库过滤**: 按卡牌ID精准过滤 + 层级压缩
- **冲突检测**: 连贯性基线 + 秘密矩阵 + 状态机（三类冲突）
- **方向评分**: 4x4 相容矩阵 + 实体 + 情感 + LLM fallback
- **编织方案**: 因果链/平行交替/主线+支线 + LLM fallback

---

## 4. 架构加固规格

> **新增于 2026-06-21 R1+R2+R3 架构深度扫描修复**

### 4.1 AppError 统一错误体系

**目标**: 替代散落的 `HTTPException` 直接抛出，建立机器可读、人类可理解、调用方可捕获的三层错误体系。

**实现位置**: `app/errors.py`

| 组件 | 说明 |
|------|------|
| `ErrorCode` (IntEnum) | 数字编码 = `HTTP状态码 × 100 + 序号`，如 `40101` (未认证), `50001` (内部错误) |
| `_ERROR_MESSAGES` | 每个 ErrorCode 对应中文可读消息 |
| `_ERROR_TO_STATUS` | ErrorCode → HTTP 状态码自动映射 |
| `AppError(HTTPException)` | 统一基类，接收 `ErrorCode` + 可选 `detail` |
| 子异常类 | `NotFoundError`, `AuthError`, `PermissionError`, `ValidationError`, `RateLimitError`, `ConflictError`, `VaultNotFoundError` |

**异常处理器**: `app/main.py` 全局注册 `@app.exception_handler(AppError)`，自动格式化 JSON 响应并写入错误日志。

**验收标准**:
- 所有 Service/Worker 层使用 AppError 子类抛出异常
- 全局异常处理器覆盖所有 AppError 子类
- 错误日志自动记录 `_write_error_log()`（含 request_id, timestamp）

### 4.2 Worker 数据库会话管理

**目标**: 消除 Worker 各自创建引擎的模式，统一为 `get_worker_session()` 单一路径。

**实现位置**: `app/worker/db.py`

| 组件 | 说明 |
|------|------|
| `get_worker_session()` | 惰性引擎创建 (`_ensure_engine()`)，pool_size=2, pool_pre_ping=True |
| `dispose_worker_engine()` | 通过 Celery `worker_shutdown` 信号触发释放 |
| `WorkerSession` | 异步上下文管理器，自动 commit / rollback / close |

**约束**: 全部 6 个 Worker 模块 (`phase4_task`, `import_task`, `book_analysis_task`, `card_retire_task`, `vault_reanalyze_task`, `tasks`) 已统一使用 `get_worker_session()`。

### 4.3 Worker 三层异常处理

**目标**: 区分可恢复错误和不可恢复错误，避免任务静默失败。

**模式** (以 `phase4_task.py` 为例):

```
SoftTimeLimitExceeded → 捕获后 raise 重新投递（不走 autoretry）
    ↓
可重试异常元组 _RETRYABLE = (SQLAlchemyError, ConnectionError, TimeoutError)
    → Celery autoretry_for 自动重试（max_retries=1, delay=300/600s）
    ↓
通用 Exception → 记录结构化日志，标记任务 FAILED
```

**验收标准**:
- 6 个 Worker 全部使用三层异常处理
- `SoftTimeLimitExceeded` 在所有 Worker 中被捕获
- `_RETRYABLE` 元组覆盖所有可恢复的临时故障

### 4.4 Celery Beat 定时调度

**目标**: 4 个周期性任务免外部 cron 自动执行。

**实现位置**: `app/worker/celery_app.py` → `beat_schedule`

| 任务 | 调度周期 | 用途 |
|------|---------|------|
| `phase4-auto-advance` | 每小时 | 扫描自动审核项目，触发 Phase 4 |
| `vault-periodic-reanalyze` | 每 6 小时 | 对近期活跃项目触发 Vault 重分析 |
| `card-retire-check` | 每天 | 检查卡片池新鲜度，标记过期卡片 |
| `health-auto-notify` | 每 30 分钟 | 活跃项目健康检查，生成 HealthAlert |

**启动命令**:
```bash
celery -A app.worker.celery_app worker -Q default,llm --loglevel=info  # Worker
celery -A app.worker.celery_app beat --loglevel=info                    # Beat 调度器
```

### 4.5 健康检查端点

**目标**: `GET /api/v1/health` 验证 DB + Redis + Celery 三方连通性。

| 检查项 | 方法 | 超时 | 失败行为 |
|--------|------|------|----------|
| Database | `SELECT 1` | 继承 session 超时 | status="degraded" |
| Redis | `PING` | 3s | status="degraded" |
| Celery | `control.ping()` | 3s | status="degraded" |

### 4.6 子情节健康监控

**目标**: 对活跃项目的剧情承诺执行三级预警检测，零 LLM 成本。

**实现位置**: `app/service/health_monitor.py`

| 级别 | 触发条件 | 行为 |
|:----:|----------|------|
| R1 (黄) | 连续 8 章无对应 promise 推进 | 生成 HealthAlert |
| R2 (橙) | 连续 4+ 次同类型重复推进 | 生成 HealthAlert + 结构调整建议 |
| R3 (红) | 连续 10 章静默 | 先关键词降级检查 → 降级为 R1 或生成严重告警 |

**防疲劳**: 同一 `(promise_id, rule)` 3 章内最多 1 次。章级增量算法 O(1)。

### 4.7 DAO 层统一规范

**目标**: 13 个 DAO 子类共享统一的查询行为和安全约束。

| 规范 | 实现 |
|------|------|
| limit 钳制 | `DEFAULT_MAX_LIMIT=500`, `_CURSOR_MAX_LIMIT=200` |
| 软删除约定 | `include_deleted=False` 默认过滤，6 DAO 24 处 `is_deleted=False` |
| 游标分页 | `list_cursor()` 返回 `(items, next_cursor)` |
| 事务契约 | DAO 只 flush，禁止 commit |

### 4.8 安全加固

| 加固项 | 位置 | 说明 |
|--------|------|------|
| Content-Length 拦截 | `app/middleware/content_length_limit.py` | ASGI 层前置拦截，10MB 默认限制，`excluded_paths` 排除机制 |
| Redis 密码 | `config.py` + `dependencies.py` | `REDIS_PASSWORD` env var，生产环境警告 |
| CORS 审查 | `config.py` | 生产环境禁用 `*` 通配符 |
| Refresh Token 轮换 | `app/router/auth.py` | 签发新 token 同时作废旧 token（Redis 黑名单） |
| File upload 限制 | `app/middleware/content_length_limit.py` | 排除路径白名单 |

### 4.9 Windows 平台兼容

**实现位置**: `app/dependencies.py`

| 适配 | 原理 |
|------|------|
| greenlet 猴子补丁 → `ThreadPoolExecutor` | Windows 无原生 greenlet |
| `_SyncAsyncSessionWrapper` | 同步 Session → awaitable |
| 事件系统补丁 `_get_exec_once_mutex` | SQLAlchemy Windows bug |
| 双轨会话 `get_db` + `get_sync_db` | auth 依赖避开 greenlet |

### 4.10 模型关系补全

**目标**: 19 个 SQLAlchemy 模型补 `relationship()` 定义，支持 ORM 级联查询。

**变更**: 18 文件修改（19 模型），覆盖所有 FK 列的 `back_populates` 双向关系。

### 4.11 API 端点加固

| 加固项 | 影响 |
|--------|------|
| 7 个新 Pydantic Schema | 8 个端点 response_model 从 dict → 具体 Schema 类型 |
| Template 端点认证 | 3 个端点添加 `Depends(get_current_user)` |
| 角色校验 | admin 路由添加 `Depends(require_admin)` |
| `current_user` 类型一致化 | 7 个 Router 文件 32 处 `dict` → `User` |
| Schema `__init__.py` 全量导出 | admin(8)/phase4(4)/setting(6)/weave(3) 共 21 类 |
| Token Budget Redis 持久化 | `app/llm/client.py` TokenBudgetManager 异步 Redis 化 |

### 4.12 Token 预算 Redis 持久化 (RF2.10)

> **状态**: ✅ 已完成 — 2026-06-21  
> **关联文档**: `docs/ARCHITECTURE.md` — Token 预算管理章节

| 变更 | 文件 | 说明 |
|------|------|------|
| TOKEN_BUDGET_LIMIT | `app/config.py` | 环境变量配置（默认 1,000,000 tokens/天） |
| TokenBudgetManager 重构 | `app/llm/client.py` (+196/-66) | 同步内存 → 异步 Redis (redis.asyncio) |
| Caller 适配 | `client.py` + `app/router/admin.py` | 3 处 await 化 + admin note 更新 |
| 多 Worker 共享 | Redis Sorted Set | Key: `moling:token_budget:{user_id}`, 按日分区 |

### 4.13 ID 类型统一风险评估 (R3.4)

> **状态**: ⚠️ 评估完成，不执行 DB 迁移 | 部分战术修复已执行  
> **关联文档**: `docs/id-type-unification-plan.md` (350 行完整评估)

- 21 个模型 3 种 PK 类型混用（String(36) ×15, Integer ×4, Uuid ×1, Key ×1）
- 28 条 FK 关系，2 条类型不匹配（IngestJob.user_id 🔴 严重 Bug）
- 推荐方案 C：保持现状 + ID 抽象层

**已执行的战术修复** (2026-06-21):
- `vault` 模块 Response Schema：`CharacterResp.id` / `PlotPromiseResp.id` 从 `int` 修正为 `str`（匹配 ORM UUID 主键）
- `vault` router 路径参数 `character_id` 同步修正 `int` → `str`
- `SystemConfig` 模型重构为 `TimestampMixin` + alembic 迁移 0005

### 4.14 LOW 问题 7 项全修复

| LL# | 问题 | 修复文件 | 状态 |
|-----|------|---------|:--:|
| LL1 | 编码中文乱码 | `phase4_store.py` +2 `decode("utf-8")` | ✅ |
| LL2 | engine dispose | 已有保护（main.py, worker/db.py） | ✅ |
| LL3 | Redis 无密码 | 已有 REDIS_PASSWORD validator | ✅ |
| LL4 | DAO 类型注解 | 4 dao 文件 | ✅ |
| LL5 | 导入文件未清理 | `import_service.py` +os.remove | ✅ |
| LL6 | Driver 重复 | 仅 2 处（dependencies, worker/db） | ✅ |
| LL7 | Schema 未导出 | `__init__.py` +21 类 | ✅ |

### 4.15 Phase 4 深度扫描 v4 发现（2026-06-21）

> **扫描范围**: 核心流水线 15 文件 ~9000 行 | **加权总分**: 71.5/100 (B 级)  
> **完整报告**: `docs/reports/scan-v4-phase4.md`

#### Critical 技术债（4 项）

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| **P2-2** | Redis `release_lock()` 无 owner 验证，直接 DELETE key | `phase4_store.py:107` | ✅ 修复：添加 owner 验证逻辑 |
| **P9-2** | R2 健康规则 `event_type` 字段不存在，实际为 `event` | `health_monitor.py` | ✅ 修复：`event_type` → `event` |
| **P5-3** | `consecutive_failures` 计数器全局共享 | `phase4_scheduler.py` | ✅ 修复：按项目区分 `Dict[str,int]` |
| **P6-4** | Stale 检查只看 `planted_chapter` 不看 `advancement_log` | `merge_service.py:758,864` | ✅ 修复：新增 `_get_last_advance_chapter` 辅助函数 |

#### High 技术债（4 项）

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| **P1-3** | `state`/`status` 双状态系统不一致 | `phase4_task.py` 模型 + service | 状态查询不可靠 |
| **P7-2** | 两套 LLM 提取体系共存（旧 `_analyze_chapter_content` vs 新 `run_phase4`） | `phase4_service.py` | 结果结构不一致 |
| **P11-1** | 导入引擎逐条 `db.add()` 无 BulkInserter | `import_service.py:327` | 大批量导入性能极差 |
| **P11-2** | 导入引擎无 savepoint 事务回滚保护 | `import_service.py` | 部分失败数据状态不确定 |

#### 修复优先级

```
P2-2 (锁安全) → P9-2 (R2 失效) → P5-3 (全局计数器)
    ↓
P11-1 → P11-2 (导入引擎) → P1-3 (双状态) → P7-2 (两套提取)
```

**目标**: 修复后 Phase 4 引擎评分 85+/100 (A 级)

### 4.16 Core/Middleware 深度扫描 v4 发现（2026-06-21）

> **扫描范围**: core/ + middleware/ + config.py/main.py/dependencies.py | **发现**: 4 CRITICAL, 6 HIGH, 7 MEDIUM, 12 LOW  
> **完整报告**: `docs/reports/scan-v4-core.md`

#### Critical 技术债（4 项）

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| **C1** | greenlet 补丁块引用未定义 `logger` | `dependencies.py:41,65` | ✅ 修复：移除未定义引用 |
| **C2** | 审计日志无条件 `await request.body()` 全量缓冲 | `audit_log.py:67` | OOM 攻击向量 |
| **C3** | ResponseFormat 全量缓冲响应体 | `response_format.py:46` | SSE/文件下载不可用，大响应 OOM |
| **C4** | 纯内存限流多 Worker 独立计数 | `rate_limit.py:38` | 限流形同虚设 |

#### High 技术债（6 项）

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| **H1** | 审计日志敏感过滤仅查 query string | `audit_log.py:161` | Token 明文泄露到日志 |
| **H2** | 日志路径/轮转/保留全硬编码 | `audit_log.py:15-55` | 运维不可控 |
| **H3** | 审计日志仅按时间轮转无大小保护 | `audit_log.py:31` | 磁盘写满 |
| **H4** | Content-Length 限制与 config 脱节 | `content_length_limit.py:16` | 配置修改不生效 |
| **H5** | SECRET_KEY validator 依赖字段声明顺序 | `config.py:174` | 生产可能用弱密钥 |
| **H6** | PostgreSQL 连接池缺 pool_recycle/pool_pre_ping | `dependencies.py:127` | 空闲连接过期异常 |

#### 修复优先级

```
C1 (Windows 崩溃) → C2/C3 (OOM) → C4 (限流)
    ↓
H1 (敏感数据泄露) → H5 (弱密钥) → H6 (连接池) → H2-H4 (运维化)
```

### 4.17 认证安全深度扫描 v4 发现（2026-06-21）

> **扫描范围**: config.py/auth_service.py/blacklist.py/dependencies.py 共 14 项安全检查 | **发现**: 3 P0, 3 P1  
> **完整报告**: `docs/reports/scan-v4-security.md`

| ID | 问题 | 位置 | 严重度 | 影响 |
|----|------|------|:--:|------|
| **S1** | Access Token 硬编码 `timedelta(minutes=15)` 忽视 `ACCESS_TOKEN_EXPIRE_MINUTES` | `auth_service.py:52` | P0 | ✅ 修复：读取 settings |
| **S2** | Refresh Token 硬编码 `timedelta(days=30)` 忽视 `REFRESH_TOKEN_EXPIRE_DAYS=7` | `auth_service.py:67` | P0 | ✅ 修复：读取 settings |
| **S3** | 密码策略不足：无账户锁定/无复杂度要求/无密码历史 | `auth_service.py` | P0 | 暴力破解+弱密码 |
| **S4** | 黑名单降级：Redis 不可用时 `is_blacklisted()` 返回 False | `auth/blacklist.py` | P1 | 已登出 Token 仍然有效 |
| **S5** | RBAC 不成熟：`status` 字段过载（既是状态又是角色） | `models/user.py` | P1 | 权限模型脆弱 |
| **S6** | python-jose 维护停滞（最后更新 2021），建议迁移 PyJWT | `dependencies.py` | P1 | 长期风险 |

**修复优先级**: `S1/S2 → S3 → S4 → S5 → S6`

### 4.18 LLM 集成深度扫描 v4 — 全部 CRITICAL+HIGH 已修复（2026-06-21 03:30）

> **扫描范围**: `app/llm/` 6 文件 | **发现**: 2 CRITICAL, 2 HIGH, 4 MEDIUM  
> **完整报告**: `docs/reports/scan-v4-llm.md`

| ID | 严重度 | 问题 | 位置 | 状态 |
|----|:--:|------|------|:--:|
| **L1** | CRITICAL | Token 预算绕过：`_chat_stream` 流式请求不调用 `budget_manager.record_usage()` | `client.py:584` | ✅ |
| **L2** | CRITICAL | `ContextBudget` 完整实现但 LLMClient 从未调用 | `client.py` | ✅ |
| **L3** | HIGH | KeyManager `_recover_key` 后 backoff_level 不重置 | `key_manager.py:257` | ✅ |
| **L4** | HIGH | `get_effective_llm_config()` 硬编码 default，不读 `LLM_MODEL` 配置 | `config.py:263` | ✅ |

**修复详情**: L1 (流式 Token 记录) / L2 (ContextBudget 集成到 chat()) / L3 (backoff 重置) / L4 (LLM_MODEL 读取) — 4 项全部修复

---

## 5. 质量门禁

### 4.1 通用门禁

```python
# 1. 格式检查
pdm run lint           # flake8 / ruff 零错误
# 2. 类型检查
pdm run type-check     # mypy / pyright 严格模式
# 3. 单元测试
pdm run test           # 新测试 100% 通过 + 零回归
# 4. 零 RuntimeWarning
pdm run test -W error  # RuntimeWarning 转化为错误
# 5. 边界测试覆盖
#     空值、超长、并发、异常、幂等
```

### 4.2 前端构建门禁

```bash
cd moling-web
npx next build 2>&1 | findstr "error"   # 构建检查
npx tsc --noEmit 2>&1 | findstr "error"  # 类型检查
npx vitest run --reporter=verbose        # 单元测试
```

### 4.3 后端回归门禁

```bash
cd moling-server
python -m pytest tests/ --tb=short
# P0 专项:
python -m pytest tests/test_merge_service.py -v --tb=short           # ≥30
python -m pytest tests/test_phase4_transaction.py -v --tb=short      # ≥8
python -m pytest tests/test_phase4_state_machine.py -v --tb=short    # ≥20
# P1 专项:
python -m pytest tests/test_cold_start.py -v --tb=short              # ≥25
python -m pytest tests/test_ingest_edge_cases.py -v --tb=short       # ≥15
python -m pytest tests/test_confidence_level.py -v --tb=short        # ≥10
```

---

## 版本历史

| 版本 | 日期 | 内容 |
|:----|:----|:-----|
| 2.5.0 | 2026-06-21 | 🛠 全体 7 模块修复闭环 — CRITICAL(4修复/physical吞异常+重试+调试残留) + Service(5修复/helper抽取+事务保护+AppError迁移) + Router+DAO+Model(5修复/AppError+is_deleted+Schema化+去重) + Worker(4修复/四模块全量幂等) + Ingest+Genre+Schema(4修复/Schema化+LLM超时+scraper合并+Field补齐) + Frontend(3修复/error.tsx边界+Mock数据+settings去use client) + Infra(3修复/docker-compose+CI对齐+Nginx安全头)。共 28+ 项修复，覆盖 7 模块 | Moling Team |
| 2.3.0 | 2026-06-21 | 🛠 架构加固 Batch 5 — 扫描 v4 CRITICAL+HIGH 修复闭环：Phase4(P2-2锁/P9-2健康字段/P5-3项目隔离/P6-4 stale) + Core(C1 Windows崩溃) + Auth(S1/S2 Token过期) + LLM(L1流式预算/L3 key退避/L4配置)，共 8 CRITICAL + 2 HIGH = 10 项修复，9 文件变更 |
| 2.2.2 | 2026-06-21 | 文档债：§4.17 新增认证安全深度扫描 v4 发现 — 3 P0 + 3 P1 安全技术债入档（Token过期/密码/RBAC） |
| 2.2.1 | 2026-06-21 | 文档债：§4.16 新增 Core/Middleware 深度扫描 v4 发现 — 4 Critical + 6 High 技术债入档 |
| 2.2.0 | 2026-06-21 | 文档债：§4.15 新增 Phase 4 深度扫描 v4 发现 — 4 Critical + 4 High 技术债入档，含修复优先级 |
| 2.1.1 | 2026-06-21 | 文档债消灭：§4.13 更新 vault Schema UUID 修复 + SystemConfig TimestampMixin 迁移的战术执行记录 |
| 2.0.0 | 2026-06-18 | 整合 p0-specs.md + p1-specs.md + p0-remaining-arch.md + 算法文档 |
| 1.0.0 | 2026-06-17 | 原始三份规格文档分拆版本 |

---

## 6. Phase 2 专项优化修复记录

> **日期**: 2026-06-21 | **范围**: M8-M13 全模块

### 6.1 M8: Ingest 类型安全

| 问题 | 修复 | 原因 |
|------|------|------|
| Phase 间传递裸 `dict`，无类型校验 | 新建 `app/schemas/ingest_data.py`（18 个 Pydantic 模型），调用方改用 `model_dump()` | 消除字段拼写错误和遗漏风险 |
| `conflict.py` 直接操作 ORM `select()` | 3 处迁移至 `IngestJobDAO` | 遵循 DAO 层统一规范，确保异常处理一致 |
| Ingest 操作无 DAO 封装 | 新建 `app/dao/ingest_dao.py`（`IngestJobDAO`） | 统一 CRUD + 软删除 + 游标分页 |
| Phase 失败后事务未回滚 | 添加 `db.rollback()` | 防止脏数据残留 |
| Committer 去重逻辑外层无 rollback | 外层添加 `rollback()` | 避免幂等键未命中时事务泄漏 |

### 6.2 M9: Model 规范化

| 问题 | 修复 | 原因 |
|------|------|------|
| 5 张表 `__tablename__` 单数形式 | 改为复数（`vault_world→vault_worlds` 等） | 遵循 SQLAlchemy 命名约定，与 DB 物理表名一致 |
| 数据库表名与 ORM 不一致 | Alembic 迁移 `c8e0a2417478` 执行 `rename_table` | 物理表同步重命名 |
| 模型继承链未审查 | 确认 `Base→TimestampMixin→业务Model` 三层合理 | 排除菱形继承和 MRO 冲突 |

### 6.3 M10: Router + DAO 一致性

| 问题 | 修复 | 原因 |
|------|------|------|
| auth 路由 `register`/`login` 使用同步 `Depends(get_db)` | 改为 `async` + `Depends(get_db)` | 统一异步会话，消除 sync/async 混用 |
| `user_dao` 3 个 sync 方法无异常保护 | 添加 `try/except SQLAlchemyError → AppError` | 防止 DB 错误直接抛到 Router 层 |
| `card_dao` 5 个 sync 方法无异常保护 | 添加 `try/except SQLAlchemyError → AppError` | 同上 |

### 6.4 M11: Service 深度清理

| 问题 | 修复 | 原因 |
|------|------|------|
| `phase4_scheduler` 抛裸 `Exception()` | 改为 `AppError` 子类 | 统一错误码 + 中文消息 + 前端可解析 |
| `card_service` 魔术数字无注释 | `MAX_ACTIVE_CARDS=80` / `FRESHNESS_DAYS` 等添加文档 | 常量来源和含义可追溯 |
| vault/auth Service 缺少返回值类型注解 | 补充 `-> ModelType` / `-> list[ModelType]` | 消除 mypy 严格模式警告 |
| LLM tenacity 未区分读/写超时 | 添加 `ReadError` / `WriteError` 分类 | 读超时可立即重试，写超时需幂等检查 |

### 6.5 M12: 前端补齐

| 问题 | 修复 | 原因 |
|------|------|------|
| 8 个子路由缺少 `loading.tsx` | 新建 `loading.tsx`（Suspense fallback） | 路由切换时显示骨架屏，消除白屏闪烁 |
| 11 个组件无无障碍标注 | 添加 `aria-label` / `role` / `aria-describedby` | 符合 WCAG 2.1 AA 标准，支持屏幕阅读器 |
| 颜色令牌混用 `var(--color-*)` 旧命名 | 全部替换为 `var(--th-*)` | 对齐 8 主题设计系统，保证主题切换一致 |
| `Project` / `WritingProject` 类型分裂 | 统一为 `WritingProject` | 消除类型重复定义，减少维护成本 |
| `api.ts` 端点硬编码 URL | 引用 `constants.ts` 中的 `API_ENDPOINTS` | 端点集中管理，修改一处全局生效 |
| 3 个空目录残留 | 删除 | 清理无效目录，减少导航噪音 |

### 6.6 M13: 基础设施 + Schema

| 问题 | 修复 | 原因 |
|------|------|------|
| `nginx.conf` 与生产配置冲突风险 | 标记为备用模板（添加注释 `# TEMPLATE: 非生产配置`） | 防止误用 |
| `backup-test` 使用 PG15 | 升级至 PG16 | 对齐生产 PostgreSQL 版本 |
| `ci-cd.yml` GHCR 认证失败 | 添加 `docker/login-action@v3` + `GITHUB_TOKEN` | 修复镜像推送权限问题 |
| `DEPLOYMENT.md` / `RUNBOOK.md` 过时 | 更新部署步骤和运维命令 | 匹配当前 Docker Compose 两套编排 |
| 19 个 Schema 文件 `Optional[X]` | 改为 `X \| None` | 遵循 Python 3.10+ 类型注解最佳实践 |

### 版本历史（续）

| 版本 | 日期 | 内容 |
|:----|:----|:-----|
| 2.6.0 | 2026-06-21 | Phase 2 专项优化文档回填 — M8 Ingest类型安全(18 Pydantic+IngestJobDAO+conflict迁移+rollback)、M9 Model规范化(5表复数+迁移+继承确认)、M10 Router+DAO一致性(auth async+user/card dao try/except)、M11 Service清理(AppError+常量文档+类型注解+tenacity读写分离)、M12 前端补齐(loading.tsx+aria+颜色令牌+类型统一+端点常量化+空目录清理)、M13 基础设施(nginx模板+PG16+GHCR+部署文档更新+19 Schema Optional→\| None) | Moling Team |

---
**END**
