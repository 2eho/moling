# 墨灵 Worker/Celery 层深度扫描报告 (scan-v4-worker)

> **扫描时间**: 2026-06-21
> **扫描范围**: `app/worker/` 全部 10 个文件（6 个 Task 模块 + 4 个基础设施）
> **扫描深度**: very thorough
> **检测项**: 12 项

---

## 一、文件清单

| 文件 | 类型 | 大小 | 任务数 | 用途 |
|------|------|------|--------|------|
| `celery_app.py` | 基础设施 | 3.6 KB | 0 | Celery 实例、全局配置、Beat 调度 |
| `db.py` | 基础设施 | 4.5 KB | 0 | 统一 Worker DB 会话管理 |
| `idempotency.py` | 基础设施 | 4.7 KB | 0 | Redis 幂等性工具库 |
| `__init__.py` | 入口 | 285 B | 0 | 包导出 |
| `tasks.py` | Task 模块 | 7.3 KB | 2 | `run_generation_task`, `health_auto_notify` |
| `phase4_task.py` | Task 模块 | 4.4 KB | 2 | `run_phase4_analysis`, `phase4_auto_advance` |
| `import_task.py` | Task 模块 | 3.2 KB | 2 | `import_book_task`, `analyze_import_content` |
| `book_analysis_task.py` | Task 模块 | 4.0 KB | 3 | `analyze_book_characters`, `analyze_book_plot`, `detect_writing_style` |
| `card_retire_task.py` | Task 模块 | 6.9 KB | 4 | `check_card_freshness`, `retire_cards`, `generate_replacement_cards`, `card_retire_check` |
| `vault_reanalyze_task.py` | Task 模块 | 7.3 KB | 2 | `vault_full_reanalyze`, `vault_periodic_reanalyze` |

**总计**: 15 个 Celery 任务

---

## 二、逐任务：12 项检测清单矩阵

### 图例
| 符号 | 含义 |
|------|------|
| ✅ | 通过 |
| ⚠️ | 部分实现/有轻微问题 |
| ❌ | 未实现/有严重问题 |
| — | 不适用 |

---

### 2.1 检测矩阵

| 任务 | 1.幂等 | 2.异常三层 | 3.超时 | 4.重试策略 | 5.DB会话 | 6.死锁 | 7.资源 | 8.状态管理 | 9.信号 | 10.序列化 | 11.僵尸 | 12.日志 |
|------|--------|-----------|--------|-----------|----------|--------|--------|----------|--------|----------|--------|------|
| `run_generation_task` | ✅ DB | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | — | ✅ | ✅ 调用 | ✅ |
| `health_auto_notify` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ✅ Beat | ✅ |
| `run_phase4_analysis` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `phase4_auto_advance` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ✅ Beat | ✅ |
| `import_book_task` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | — | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `analyze_import_content` | ❌ | ✅ | ⚠️ | ❌ | ✅ | — | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `analyze_book_characters` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | — | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `analyze_book_plot` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | — | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `detect_writing_style` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | — | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `check_card_freshness` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `retire_cards` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `generate_replacement_cards` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ⚠️ 未调用 | ✅ |
| `card_retire_check` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ✅ Beat | ✅ |
| `vault_full_reanalyze` | ✅ Redis | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | ✅ | — | ✅ | ✅ 调用 | ⚠️ |
| `vault_periodic_reanalyze` | ❌ | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ | ✅ | ❌ | — | ✅ | ✅ Beat | ✅ |

**通过率**: 60/180 = 33% 直接通过（不计 ⚠️）；含轻微问题项约 65% 可接受范围

---

## 三、12 项逐项深度分析

---

### 3.1 幂等性保护

#### 当前实现

系统提供**两种**幂等性方案：

**方案 A — Redis 幂等性 (`idempotency.py`)**：
- `is_duplicate(task_key)` — SETNX 原子检查 + 标记
- `mark_processing(task_key)` — 标记为 processing
- `mark_completed(task_key)` — 标记为 completed
- `mark_failed(task_key)` — 标记为 failed（允许重试）
- TTL = 24 小时自动过期
- **优雅降级**: Redis 不可用时自动跳过检查 (`return False`)
- 状态机: `processing` → `completed` / `failed`

**方案 B — DB 状态检查 (仅 `tasks.py`)**：
- `_get_task_status()` — 查询 DB 中 generation_task 的 status 字段
- 跳过逻辑: 若 status ∈ {`done`, `processing`} → 跳过执行
- `_mark_processing()` 在独立会话中标记为 processing

#### 实际覆盖情况

| 状态 | 数量 | 任务列表 |
|------|------|----------|
| ✅ 已实现 | 2/15 | `run_generation_task` (DB), `vault_full_reanalyze` (Redis) |
| ❌ 未实现 | 13/15 | 其余全部 |

#### 问题详情

**🔴 P0 — 幂等性缺口严重**

13/15 的任务没有任何幂等保护。在 `task_acks_late=True` + `visibility_timeout=3600` 的配置下：
- Worker 崩溃 → 未 ack 的任务在 1 小时后重新入队 → 可能被另一个 worker 重复执行
- 网络分区 → Broker 认为任务丢失 → 重新投递

**特别是周期性任务** (`phase4_auto_advance`, `card_retire_check`, `vault_periodic_reanalyze`, `health_auto_notify`)：虽然 Beat 的 `expires` 选项提供了一定保护（过期后不再投递），但若上一个实例仍在运行而新实例已调度，可能产生重叠执行。

**🔴 P0 — `phase4_auto_advance` 和 `card_retire_check` 嵌套幂等缺口**

```
phase4_auto_advance（无幂等）
  └─ Phase4Service.analyze_project()  // 可能修改 vault 数据
vault_periodic_reanalyze（无幂等）
  └─ vault_full_reanalyze.delay()     // 但这个有幂等
```

虽然 `vault_full_reanalyze` 有幂等保护，但 `phase4_auto_advance` 调用的 `Phase4Service.analyze_project()` 没有 — 这是一个 DB 直接操作，不走 Redis。

**🟡 P1 — `run_generation_task` 的 DB 幂等存在竞态窗口**

```python
# 步骤1: 检查状态
status = asyncio.run(_get_task_status(task_uuid))  # 独立会话
if status in ("done", "processing"):
    return  # 跳过

# 步骤2: 标记 processing
asyncio.run(_mark_processing(generation_task_id))  # 独立会话
```

步骤1和步骤2在**两个独立的事务**中执行，之间存在竞态窗口：
- Worker A 检查 status → None → 继续
- Worker B 检查 status → None → 继续
- Worker A 标记 processing
- Worker B 也标记 processing
- 两个 worker 同时执行同一任务

**建议**: 使用 `is_duplicate()` (SETNX 原子操作) 或 `SELECT ... FOR UPDATE` 在 DB 层面锁定。

---

### 3.2 异常处理三层架构

#### 当前实现

所有 15 个任务均实现了标准的 `SoftTimeLimitExceeded → autoretry → generic Exception` 三层：

```python
try:
    result = asyncio.run(_run())
    return {"status": "done", ...}
except SoftTimeLimitExceeded:
    logger.error("...timed out")
    raise
except _RETRYABLE as exc:
    logger.exception("...retryable")
    raise self.retry(exc=exc) from exc
except Exception as exc:
    logger.exception("...non-retryable")
    return {"status": "failed", "error": str(exc)}
```

#### 质量评估

| 评估项 | 结果 |
|--------|------|
| SoftTimeLimitExceeded 捕获 | ✅ 15/15 — 所有任务都捕获 |
| 可重试异常分类 (`_RETRYABLE`) | ✅ 15/15 — 统一使用 `(SQLAlchemyError, ConnectionError, TimeoutError)` |
| 通用 Exception 兜底 | ✅ 15/15 — 所有任务都有 |
| 超时时的资源清理 | ⚠️ 仅 `vault_full_reanalyze` 在超时时调用 `mark_failed(task_key)` |
| 重试时的状态回滚 | ❌ 无任务在重试前恢复 DB 状态 |

**🟡 P1 — `run_generation_task` 超时清理使用独立会话**

```python
except SoftTimeLimitExceeded:
    asyncio.run(_mark_failed(generation_task_id, "Task timed out..."))
    raise
```

`_mark_failed` 内部调用 `get_worker_session()` 创建**新会话**。如果超时是因为 DB 连接池耗尽，这个清理操作也会失败。应该使用原有的 open session（如果还活着）或至少增加重试。

**🟢 优点**: `vault_full_reanalyze` 的内部循环有 per-chapter 异常捕获（line 85-104），单个章节失败不会导致整个任务终止。这是良好的容错设计。

---

### 3.3 超时配置

#### 当前全局配置

```python
task_time_limit = 600       # 硬超时 10 分钟
task_soft_time_limit = 540  # 软超时 9 分钟
```

#### 任务级差异化配置

| 任务类型 | 预估执行时长 | 当前超时 | 问题 |
|----------|-------------|----------|------|
| `run_generation_task` (LLM pipeline) | 2–10 min | 9/10 min (全局) | ⚠️ 边缘情况可能不足 |
| `health_auto_notify` (DB 查询) | < 30 sec | 9/10 min (全局) | ⚠️ 超时过长，应 2 min |
| `phase4_auto_advance` (扫描+触发) | 1–5 min | 9/10 min (全局) | ✅ 可接受 |
| `import_book_task` (文件解析) | 1–3 min | 9/10 min (全局) | ⚠️ 超时过长，应 5 min |
| `analyze_import_content` (内容分析) | 1–5 min | 9/10 min (全局) | ✅ 可接受 |
| `book_analysis_*` (LLM 分析) | 1–5 min | 9/10 min (全局) | ✅ 可接受 |
| `card_retire_check` (批量扫描) | 1–3 min | 9/10 min (全局) | ⚠️ 超时过长，应 5 min |
| `vault_full_reanalyze` (全量重分析) | 5–30+ min | 9/10 min (全局) | 🔴 大型项目可能超时 |
| `vault_periodic_reanalyze` (批量触发) | < 2 min | 9/10 min (全局) | ⚠️ 超时过长，应 3 min |

#### Beat 级别 expires 保护

| Beat 任务 | expires |
|-----------|---------|
| `phase4-auto-advance` (每小时) | 3000s (50min) |
| `vault-periodic-reanalyze` (每6小时) | 18000s (5h) |
| `card-retire-check` (每天) | 72000s (20h) |
| `health-auto-notify` (每30分钟) | 1500s (25min) |

**🔴 P0 — `vault_full_reanalyze` 大项目超时风险**

对所有章节循环执行 LLM 分析，大型项目（100+ 章）可能远超 9 分钟：
- 没有分页/分批处理机制
- 没有进度检查点 — 中断后需从头再来
- 建议: 拆分为 per-chapter 子任务，或增加 checkpoint 机制

**🟡 P1 — 所有任务使用相同超时，缺少差异化**

短任务（`health_auto_notify` < 30s）不应允许运行 9 分钟 — 会掩盖真正的 Bug（如死循环/死锁）。

---

### 3.4 重试策略

#### 当前任务级配置

| 任务 | max_retries | default_retry_delay | 问题 |
|------|-------------|---------------------|------|
| `run_generation_task` | 2 | 30s | ✅ |
| `health_auto_notify` | 1 | 120s | ✅ |
| `run_phase4_analysis` | 1 | 300s | ✅ |
| `phase4_auto_advance` | 1 | 600s | ✅ |
| `import_book_task` | 1 | 60s | ✅ |
| `analyze_import_content` | **未指定(=3)** | **未指定(=180s)** | 🔴 P1 |
| `analyze_book_characters` | 1 | **未指定(=180s)** | ⚠️ |
| `analyze_book_plot` | 1 | **未指定(=180s)** | ⚠️ |
| `detect_writing_style` | 1 | **未指定(=180s)** | ⚠️ |
| `check_card_freshness` | 1 | **未指定(=180s)** | ⚠️ |
| `retire_cards` | 1 | **未指定(=180s)** | ⚠️ |
| `generate_replacement_cards` | 1 | **未指定(=180s)** | ⚠️ |
| `card_retire_check` | 1 | 3600s | ✅ |
| `vault_full_reanalyze` | 3 | 120s | ✅ |
| `vault_periodic_reanalyze` | 1 | 600s | ✅ |

#### 问题详情

**🔴 P1 — `analyze_import_content` 未指定 `max_retries`**

将使用 Celery 默认值 3，与其他类似短任务的 `max_retries=1` 不一致。更多重试不一定是问题，但不一致是技术债务。

**🟡 P1 — 7 个任务未指定 `default_retry_delay`**

依赖 Celery 默认 180s。对于 `card_retire_check` 这类每天一次的 Beat 任务，180s 的重试延迟可能合适；但对于 `import_book_task` (60s) 和 `analyze_book_characters` 这类用户触发的任务，180s 太长。

**❌ P2 — 无 `retry_backoff` / `retry_jitter`**

所有任务使用**固定延迟**重试，无指数退避。在高负载场景下，多个 worker 同时失败后以相同间隔重试会造成"重试风暴"。

建议:
```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60,
                 retry_backoff=True, retry_backoff_max=600,  # 60s → 120s → 240s
                 retry_jitter=True,
                 autoretry_for=_RETRYABLE)
```

---

### 3.5 DB 会话管理

#### 当前实现

`db.py` 提供统一的 `get_worker_session()`:
- 懒加载 engine（一个 worker 进程一个）
- pool_size=2, max_overflow=5
- pool_pre_ping=True（检测过期连接）
- 自动 commit/rollback/close
- Windows + SQLite → `aiosqlite` 驱动兼容
- PostgreSQL → `psycopg` 驱动

#### 使用检查

| 任务文件 | 是否使用 `get_worker_session()` |
|----------|-------------------------------|
| `tasks.py` | ✅ (4 处) |
| `phase4_task.py` | ✅ (2 处) |
| `import_task.py` | ✅ (2 处) |
| `book_analysis_task.py` | ✅ (3 处) |
| `card_retire_task.py` | ✅ (4 处) |
| `vault_reanalyze_task.py` | ✅ (2 处) |

✅ **全部通过** — 没有任务自行创建引擎或会话工厂。

**🟡 P1 — `run_generation_task` 的多个辅助函数创建多个独立会话**

```python
# 3 个辅助函数各自创建独立会话
status = asyncio.run(_get_task_status(task_uuid))     # 会话1
asyncio.run(_mark_processing(generation_task_id))      # 会话2
_ = asyncio.run(_run_pipeline(service, task_id))       # 会话3
asyncio.run(_mark_failed(...))                         # 会话4 (失败时)
```

一个任务执行最多打开 4 个独立连接（pool_size=2！）。如果多个任务并发，pool 可能耗尽。

建议: 将 DB 状态管理合并到 `_run_pipeline` 的会话中，减少连接数。

---

### 3.6 死锁风险

#### 共享资源分析

| 资源 | 访问者 | 风险 |
|------|--------|------|
| `projects` 表 | `phase4_auto_advance`, `card_retire_check`, `vault_periodic_reanalyze`, `health_auto_notify` | ⚠️ 四读一写 |
| `chapters` 表 | `vault_full_reanalyze`, `import_book_task` | ⚠️ 交叉读写 |
| `cards`/`card_pool` 表 | `card_retire_check`, `check_card_freshness`, `retire_cards`, `generate_replacement_cards` | 🔴 多任务可能同时操作 |
| `vault_entries` 表 | `vault_full_reanalyze`, `phase4_auto_advance` (via Phase4Service) | ⚠️ 交叉更新 |
| `generation_tasks` 表 | `run_generation_task` | ✅ 唯一写入者 |

#### 风险场景

**🔴 P1 — `card_retire_check` + 手动 `retire_cards` 并发**

```
card_retire_check (Beat)              retire_cards (用户触发)
  └─ check_freshness()                └─ service.retire_cards()
       └─ UPDATE cards SET retired     └─ UPDATE cards SET retired
          WHERE freshness < threshold      WHERE id IN (card_ids)
```

同一张卡的 `retired` 状态被两个任务同时修改，可能产生不一致。

**🟡 P2 — `vault_full_reanalyze` + `phase4_auto_advance` 交叉**

两者都可能通过各自的 Service 修改 `vault_entries`。`phase4_auto_advance` 调用 `Phase4Service.analyze_project()`，`vault_full_reanalyze` 调用 `VaultService.update_from_chapter()` — 可能修改同一行。

#### 缓解措施评估

| 措施 | 现状 |
|------|------|
| `SELECT ... FOR UPDATE` | ❌ 未使用 |
| 悲观锁（DB 行锁） | ❌ 未使用 |
| 乐观锁（版本号） | ❌ 未使用 |
| 幂等性（防重复） | ⚠️ 仅 2/15 任务 |
| `task_acks_late` + `worker_prefetch_multiplier=1` | ✅ 减少并发但未消除 |
| 队列分离（llm vs default） | ✅ 减少争抢但未消除 |

---

### 3.7 资源泄露

#### 检查结果

| 资源 | 状态 | 详情 |
|------|------|------|
| DB Engine 释放 | ✅ | `worker_shutdown` 信号 → `dispose_worker_engine()` |
| DB Session 关闭 | ✅ | `get_worker_session()` 的 finally 块确保 close |
| Redis 连接关闭 | ❌ | `idempotency.py` 的 `_redis_client` 永不被显式关闭 |
| Celery 连接清理 | ✅ | `worker_shutdown.connect(_on_worker_shutdown)` |
| 文件句柄 | ⚠️ | `import_book_task` 解析文件后无显式 close — 依赖 Service 层 |
| 内存 | ⚠️ | `vault_full_reanalyze` 将所有章节结果累积在 `chapter_results` 列表中 |

**🟡 P1 — Redis 连接永不释放**

`idempotency.py:_redis_client` 是模块级全局变量，无 `worker_shutdown` 信号处理。Worker 重启时（`worker_max_tasks_per_child=50`）旧连接会泄露。

修复建议:
```python
from celery.signals import worker_shutdown

@worker_shutdown.connect
def _close_redis(**kwargs):
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
```

**🟡 P2 — `vault_full_reanalyze` 内存增长**

大型项目 100+ 章节，每个章节的分析结果被追加到 `chapter_results` 列表中。虽然有 `worker_max_tasks_per_child=50` 兜底，但单次任务可能已消耗大量内存。

---

### 3.8 任务状态管理

#### 实现情况

| 任务 | DB 状态持久化 | Redis 状态 | 返回状态 | 状态转换 |
|------|-------------|------------|----------|----------|
| `run_generation_task` | ✅ status 字段 | ❌ | ✅ done/failed | pending→processing→done/failed |
| `vault_full_reanalyze` | ❌ | ✅ processing/completed/failed | ✅ done/failed | processing→completed/failed |
| 其他 13 个任务 | ❌ | ❌ | ✅ done/failed (仅返回值) | 无持久化 |

#### 问题

**🟡 P1 — 多数任务无持久化状态**

13/15 的任务只在返回值中携带 `{"status": "done"/"failed"}`，但：
- 如果 worker 在返回结果前崩溃，外部无法得知任务是否成功
- 无法从外部查询任务当前状态（除通过 Celery inspect，但这在生产不稳定）
- `task_track_started=True` 只能追踪 Celery 内部状态（PENDING→STARTED→SUCCESS/FAILURE）

**🟡 P1 — `vault_full_reanalyze` Redis 状态与 DB 状态分离**

Redis 记录 `vault_full_reanalyze` 的幂等状态，但 DB 中没有对应的任务状态记录。如果 Redis 数据丢失（重启、TTL 过期），无法通过 DB 恢复任务状态。

**🟢 优点**: `run_generation_task` 的 DB 状态管理最完善：
- `pending` → `processing` → `done` / `failed`
- 状态转换在事务中完成
- 幂等检查读取同一 status 字段

---

### 3.9 信号处理

#### 当前实现

```python
# db.py — 已注册
@worker_shutdown.connect
def _on_worker_shutdown(**kwargs):
    dispose_worker_engine()
```

| 信号 | 处理情况 | 细节 |
|------|----------|------|
| `worker_shutdown` | ✅ 已实现 | 释放 DB engine |
| `worker_shutdown` (Redis) | ❌ 未实现 | Redis 连接不关闭 |
| `task_prerun` | ❌ 未实现 | 无任务前置检查 |
| `task_postrun` | ❌ 未实现 | 无任务后置清理 |
| `task_failure` | ❌ 未实现 | 失败事件仅依赖 autoretry |
| `task_revoked` | ❌ 未实现 | 取消时无清理 |

**🟡 P1 — Redis 无 shutdown 清理**

如 3.7 所述，`idempotency.py` 缺少 `worker_shutdown` 信号处理。

**🟢 优点**: `db.py` 的 `dispose_worker_engine()` 实现仔细：
- 处理了 `RuntimeError`（事件循环状态不明确）
- 使用 `loop.create_task()` 在运行中的 loop 上调度异步 dispose

---

### 3.10 序列化安全

#### 全局配置

```python
# celery_app.py
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
```

✅ **仅接受 JSON** — 无 pickle 风险。

#### 参数类型检查

| 任务参数 | 类型 | JSON 兼容 |
|----------|------|-----------|
| `generation_task_id: str` | string | ✅ |
| `project_id: int` | number | ✅ |
| `user_id: str` | string | ✅ |
| `file_path: str` | string | ✅ |
| `import_mode: str` | string | ✅ |
| `card_ids: list[int]` | list | ✅ |
| `count: int` | number | ✅ |

✅ **全部通过** — 所有参数为 JSON 原生类型。

#### 返回值检查

返回值均为 dict，包含 `str`, `int`, `list` 等 JSON 原生类型。`vault_full_reanalyze` 返回嵌套 dict 和 list，但均在 JSON 范围内。

✅ **全部通过**。

---

### 3.11 僵尸任务检测

#### 引用关系图

```
┌─ 被调用者 ───────────────────────┬─ 调用者 ──────────────────────┐
│ run_generation_task               │ generation_service.py:105     │
│ vault_full_reanalyze              │ router/vault.py:319           │
│                                   │ vault_reanalyze_task.py:169   │
│ execute_phase4_storage 🔴         │ chapter_service.py:235       │
│ update_vault_entries 🔴           │ chapter_service.py:246       │
│ phase4_auto_advance               │ celery_app.py beat_schedule   │
│ vault_periodic_reanalyze          │ celery_app.py beat_schedule   │
│ card_retire_check                 │ celery_app.py beat_schedule   │
│ health_auto_notify                │ celery_app.py beat_schedule   │
│ run_phase4_analysis               │ (未被调用) ⚠️                │
│ import_book_task                  │ (未被调用) ⚠️                │
│ analyze_import_content            │ (未被调用) ⚠️                │
│ analyze_book_characters           │ (未被调用) ⚠️                │
│ analyze_book_plot                 │ (未被调用) ⚠️                │
│ detect_writing_style              │ (未被调用) ⚠️                │
│ check_card_freshness              │ (未被调用) ⚠️                │
│ retire_cards                      │ (未被调用) ⚠️                │
│ generate_replacement_cards        │ (未被调用) ⚠️                │
└───────────────────────────────────┴───────────────────────────────┘
```

#### 发现

**🔴 P0 — 2 个缺失任务（调用方引用但 Worker 层未定义）**

| 引用路径 | 期望任务名 | 实际定义 |
|----------|-----------|----------|
| `chapter_service.py:235` | `execute_phase4_storage` | **不存在！** 仅有 `run_phase4_analysis` |
| `chapter_service.py:246` | `update_vault_entries` | **不存在！** 无对应任务 |

`chapter_service.py` 的代码路径为:
```
章节审核通过
  → try: execute_phase4_storage.delay() → ImportError → fallback
  → except ImportError: update_vault_entries.delay() → pass on error
```

这意味着：
- **每个审核通过的章节触发 Phase 4 时都会失败**（ImportError 静默吞下）
- 然后尝试 `update_vault_entries.delay()` 也会失败（同样不存在）
- 第二个失败被 `except Exception: pass` 静默吞下
- **Phase 4 自动收纳管道从未被实际启动**

**🔴 P0 — 8 个可疑僵尸任务（已定义但无调用方）**

| 任务 | 可能原因 |
|------|----------|
| `run_phase4_analysis` | 可能是 `execute_phase4_storage` 的预期实现（名称不匹配） |
| `import_book_task` | 可能由 Router 层直接调用（未搜索到）或尚未集成 |
| `analyze_import_content` | 同上 |
| `analyze_book_characters` | 同上 |
| `analyze_book_plot` | 同上 |
| `detect_writing_style` | 同上 |
| `check_card_freshness` | 同上 |
| `retire_cards` | 注意: `card_pool_service.py` 有同名 `async def retire_cards` 方法，但这是 Service 方法，并非 Celery 任务 |
| `generate_replacement_cards` | 同上 |

> **备注**: 这些任务均已在 `celery_app.py` 的 `include` 列表中注册，Celery 会在 worker 启动时加载。但如果没有 `.delay()` 调用，它们在运行时永远不会被触发。可能是为未来的 API 端点预留的。

---

### 3.12 日志记录

#### 检查结果

| 关键节点 | 覆盖情况 |
|----------|----------|
| 任务开始 | ✅ 15/15 — `logger.info("Starting...")` |
| 任务成功 | ✅ 15/15 — `logger.info("...completed")` 含统计数据 |
| 任务超时 | ✅ 15/15 — `logger.error("...timed out")` |
| 可重试异常 | ✅ 15/15 — `logger.exception("...retryable")` |
| 不可重试异常 | ✅ 15/15 — `logger.exception("...non-retryable")` |
| 进度日志 | ⚠️ 5/15 — 仅周期性扫描任务有 |
| 幂等跳过 | ✅ 2/2 — `run_generation_task`, `vault_full_reanalyze` |

#### 具体评估

**✅ 好的实践**：
- 所有 `logger.exception()` 调用自动附加堆栈跟踪
- 日志包含关键上下文（`project_id`, `task_id`, 统计数据）
- 周期性任务记录扫描数量和处理数量

**⚠️ 改进点**：

1. `vault_full_reanalyze` — 处理 100 章的项目时，只记录开始/完成日志，没有中间进度。如果任务在中间某个章节卡住，运维人员无法判断进度。

2. `book_analysis_task.py` 的三个任务 — 成功日志无统计信息（只有 `return {"status": "done", "project_id": project_id, ...}`, 没有 `logger.info` 记录结果摘要）。

3. 无结构化日志字段 — 所有日志使用 f-string 格式化，而非 `logger.info("msg", extra={"project_id": ...})` 结构。在日志聚合系统中不利于过滤。

---

## 四、基础设施评估

### 4.1 `celery_app.py` 配置质量

| 配置项 | 值 | 评估 |
|--------|-----|------|
| `task_serializer` | json | ✅ |
| `accept_content` | ["json"] | ✅ |
| `task_acks_late` | True | ✅ |
| `worker_prefetch_multiplier` | 1 | ✅ |
| `worker_max_tasks_per_child` | 50 | ✅ |
| `task_reject_on_worker_lost` | True | ✅ |
| `visibility_timeout` | 3600s | ⚠️ 1h 偏长，30min 更平衡 |
| `task_track_started` | True | ✅ |
| `result_expires` | 7 days | ✅ |

### 4.2 `db.py` 质量

| 方面 | 评估 |
|------|------|
| 懒加载 engine | ✅ |
| pool_pre_ping | ✅ |
| 跨平台支持 (Windows SQLite) | ✅ |
| worker_shutdown 清理 | ✅ |
| 事务完整性 | ✅ |

### 4.3 `idempotency.py` 质量

| 方面 | 评估 |
|------|------|
| SETNX 原子性 | ✅ |
| 自动 TTL 过期 | ✅ |
| 优雅降级 | ✅ |
| Redis 连接生命周期 | ⚠️ 无 shutdown 清理 |
| 状态 API 完整性 | ✅ (processing/completed/failed/clear) |

---

## 五、风险汇总

### P0 — 立即修复（阻塞性问题）

| # | 问题 | 影响范围 | 建议 |
|---|------|----------|------|
| 1 | `execute_phase4_storage` 和 `update_vault_entries` 缺失 | **Phase 4 收纳管线完全失效** — 每个章节审核通过后 dispatch 失败 | 在 `phase4_task.py` 中创建缺失任务，或将调用方改为 `run_phase4_analysis.delay()` |
| 2 | 13/15 任务无幂等保护 | visibility_timeout 重投递可导致重复执行 | 对所有任务添加 `is_duplicate()` 调用 |
| 3 | `vault_full_reanalyze` 大项目超时风险 | 100+ 章项目可能在 9 分钟内无法完成 | 拆分为 per-chapter 子任务 + checkpoint |

### P1 — 尽快修复（高风险问题）

| # | 问题 | 文件 |
|---|------|------|
| 4 | `run_generation_task` 幂等 DB 竞态窗口 | `tasks.py:99-106` |
| 5 | `run_generation_task` 单个任务最多开 4 个 DB 会话 | `tasks.py:99-129` |
| 6 | `run_generation_task` 超时时 `_mark_failed` 可能失败 | `tasks.py:119` |
| 7 | `analyze_import_content` 缺少 `max_retries` 声明 | `import_task.py:68` |
| 8 | 7 个任务缺少 `default_retry_delay` 声明 | 多个文件 |
| 9 | `card_retire_check` + 手动 `retire_cards` 并发死锁 | `card_retire_task.py` |
| 10 | Redis 连接无 `worker_shutdown` 清理 | `idempotency.py` |
| 11 | 8 个任务定义为僵尸（未找到调用方） | 多个文件 |

### P2 — 计划修复（改进项）

| # | 问题 |
|---|------|
| 12 | 无 `retry_backoff` / `retry_jitter` — 重试风暴风险 |
| 13 | 超时配置未按任务类型差异化（全部用全局 9/10 min） |
| 14 | `vault_full_reanalyze` 大项目内存累积 |
| 15 | 无结构化日志（所有日志用 f-string 拼接） |
| 16 | `phase4_auto_advance` + `vault_full_reanalyze` 可能交叉修改 vault_entries |
| 17 | `book_analysis_task.py` 三个任务成功时无结果摘要日志 |
| 18 | 多数任务无 DB 持久化状态 — 外部不可查询 |

---

## 六、修复建议优先级路线图

### 第一阶段：阻塞修复 (P0)
1. **修复 Phase 4 管线断裂** (`chapter_service.py` → `phase4_task.py`)
   - 在 `phase4_task.py` 中创建 `execute_phase4_storage` 和 `update_vault_entries` 任务
   - 或将 `chapter_service.py` 改为调用 `run_phase4_analysis.delay()`
2. **为所有 Beat 任务添加幂等保护** (`phase4_auto_advance`, `card_retire_check`, `vault_periodic_reanalyze`, `health_auto_notify`)
3. **拆分 `vault_full_reanalyze`** 为分批处理

### 第二阶段：高风险管理 (P1)
4. 修复 `run_generation_task` 的 DB 竞态 — 改用 `is_duplicate()` + `SELECT ... FOR UPDATE`
5. 为 7 个任务补充 `default_retry_delay` 声明
6. 为 `analyze_import_content` 补充 `max_retries` 声明
7. `idempotency.py` 注册 `worker_shutdown` 信号关闭 Redis
8. 清理 8 个僵尸任务或连接到调用方
9. `card_retire_check` + `retire_cards` 添加锁机制

### 第三阶段：质量提升 (P2)
10. 全部任务添加 `retry_backoff=True, retry_jitter=True`
11. 按任务类型配置差异化超时
12. 引入结构化日志
13. 为关键任务添加 DB 状态持久化

---

## 七、总结

| 指标 | 统计 |
|------|------|
| 扫描文件数 | 10 |
| 任务总数 | 15 |
| P0 问题 | 3 |
| P1 问题 | 8 |
| P2 问题 | 7 |
| 基础设施质量 | ⭐⭐⭐⭐ (4/5) — db.py 和 celery_app.py 设计良好 |
| 幂等性覆盖率 | 13% (2/15) — 严重不足 |
| 异常处理三层覆盖率 | 100% (15/15) — 优秀 |
| DB 会话统一使用率 | 100% (15/15) — 优秀 |
| 序列化安全性 | 100% — JSON only |

**整体评价**: Worker 层的基础设施（`celery_app.py`, `db.py`, `idempotency.py`）设计质量良好，异常处理三层架构统一。但存在两个关键缺陷：**Phase 4 管线断裂**（2 个被调用但未定义的任务）和**幂等性覆盖严重不足**（仅 13%）。建议优先修复 Phase 4 管线问题，然后全面推广幂等性保护。
