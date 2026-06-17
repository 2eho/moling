# P0 剩余三项 — 生产级架构规格 v2

> 2026-06-17 | 比 v1 更专业：完整状态机、事务边界、错误矩阵、性能目标

---

## 架构总览

```
用户触发生成
    ↓
Phase 4 调度器 (P0-2)     ← 分布式锁 + 幂等
    ↓
SourceText 验证 (已完成)
    ↓
Phase 4 核心服务
    ├── LLM 提取变更        ← 已有
    ├── 四库合并 (P0-3)      ← 本批次核心
    ├── 卡牌充实 (P0-3)      ← 合并逻辑的一部分
    ├── 卡牌淘汰 (已完成)     ← P0-4
    └── 变更日志 (P0-3)      ← 合并的逻辑一部分
    ↓
事务提交 (P0-5)            ← 原子性保证
    ↓
更新任务状态 → DONE
```

**依赖关系**：P0-3 (四库合并) → P0-5 (事务原子性) → P0-2 (调度器)
但实现可以并行：不同文件 + 不同测试套件。

---

## P0-3: 四库合并服务（大型，核心价值）

### 新文件：`app/service/merge_service.py`

```python
class MergeService:
    """
    四库合并核心引擎。
    
    输入: LLM 提取的结构化变更 (人物/时间线/承诺/世界观/卡牌)
    输出: 合并后的数据库操作 + 变更日志
    
    每种子库都有独立的 merge_xxx 方法，
    但共享统一的错误处理、置信度评估、日志记录。
    """
```

### 通用合并模式

每种子库的合并遵循相同的 4 步模式：

```
[1] 解析验证 → 校验输入格式，丢弃无效条目
[2] 查找匹配 → 模糊匹配/精确匹配已有实体
[3] 执行合并 → 新建/更新/标记冲突
[4] 记录日志 → 写入变更日志
```

### 15-1: 人物库合并

```python
async def merge_characters(
    self, db, project_id: int, 
    extracted: List[ExtractedCharacter],
    chapter_number: int,
) -> MergeResult:
```

| 匹配策略 | 优先级 | 方法 |
|----------|:------:|------|
| 精确 ID | 1 | extracted.id == existing.id |
| 精确名称 | 2 | extracted.name == existing.name |
| 别名匹配 | 3 | extracted.name in existing.aliases |
| 编辑距离 ≤ 2 | 4 | Levenshtein distance |
| 姓氏匹配 | 5 | Same surname (Chinese: first char) |
| 无匹配 → 新建 | 6 | New character entity |

**状态变更规则**：
- `active → active`：无变化
- `active → deceased`：设置 death_chapter, status=deceased
- `active → dormant`：设置 last_active_chapter
- `active → resolved`：设置 resolution_chapter
- 其他组合：记入变更日志，标记为"异常变更"供审核

**置信度降级**：
- 精确匹配 → confidence = 1.0
- 编辑距离 = 1 → confidence = 0.9
- 编辑距离 = 2 → confidence = 0.75
- 姓氏匹配 → confidence = 0.5 (标记 low_confidence)
- 无匹配 → confidence = 0.3 (标记 new_entity)

### 15-2: 时间线库合并

```python
async def merge_timeline(
    self, db, project_id: int,
    extracted: List[ExtractedTimelineEvent],
    chapter_number: int,
) -> MergeResult:
```

| 操作类型 | 行为 |
|----------|------|
| `add` | 新建时间线事件 |
| `resolve_date` | 解决日期冲突（多事件相同日期→标注多条）|
| `correct` | 修正已有事件（附证据）|

**日期冲突处理**：
- 同一日期多个不同事件 → 都保留，标注 `multiple_events`
- 同一日期相同事件 → 去重，保留最早版本
- 关键节点事件（major_plot=True）→ 置顶

### 15-3: 剧情承诺库合并

```python
async def merge_plot_promises(
    self, db, project_id: int,
    extracted: List[ExtractedPlotPromise],
    chapter_number: int,
) -> MergeResult:
```

| 操作类型 | 行为 |
|----------|------|
| `create` | 新建承诺 |
| `advance` | 推进已有承诺（增加 progress 字段）|
| `redeem` | 兑现承诺（status=redeemed, resolution_chapter）|
| `cancel` | 废弃承诺（status=canceled, cancel_reason）|

**超时未收束检查**：
- 承诺创建超过 20 章未兑现 → 标记为 `stale`
- 承诺被引用超过 3 个子承诺 → 检查递归一致性
- 废弃的承诺 → 记录原因到 changelog

### 15-4: 世界观库合并

```python
async def merge_world_building(
    self, db, project_id: int,
    extracted: List[ExtractedWorldItem],
    chapter_number: int,
) -> MergeResult:
```

**分类映射**：`geography | history | system | faction | event`

**变更标记**：
- 已有设定被修改 → 标记 `revised`，旧值记入 changelog
- 新建设定 → 正常入库
- 设定冲突（system 规则矛盾）→ `conflict_detected`

### 变更日志（[20]）

```python
async def archive_changelog(
    self, db, project_id: int,
    changes: List[ChangeEntry],
    chapter_number: int,
) -> None:
```

每条变更记录包含：
```python
@dataclass
class ChangeEntry:
    entity_type: str       # character | timeline | plot_promise | world | card
    entity_id: str
    entity_name: str
    change_type: str       # create | update | status_change | retire | conflict
    old_value: Optional[str]
    new_value: Optional[str]
    chapter: int
    confidence: float
    change_reason: str     # 人类可读的变更原因
```

### 错误处理矩阵（P0-3）

| 场景 | 行为 |
|------|------|
| 提取字段为空 | 该条目跳过，记入 warnings |
| 模糊匹配无结果 | 作为新实体创建 |
| 编辑距离匹配到多个 | 选置信度最高的，标记 possible_duplicates |
| 状态变更冲突 | 记录旧状态和新状态到 changelog，不阻止 |
| 数据库写入失败 | 抛出异常由调用方（P0-5）处理事务回滚 |
| 置信度 < 0.3 | 标记为 review_needed，不自动入库 |

### 测试要求（P0-3，至少 30 个）

| # | 测试 | 优先级 |
|---|------|:------:|
| 1-5 | 人物精确/模糊/别名/姓氏/无匹配 | P0 |
| 6-8 | 人物状态变更 active/deceased/dormant | P0 |
| 9-10 | 时间线 add/resolve_date | P0 |
| 11-12 | 时间线同日期冲突 | P0 |
| 13-16 | 承诺 create/advance/redeem/cancel | P0 |
| 17-18 | 承诺超时 stale / 废弃原因 | P1 |
| 19-22 | 世界观 create/expand/revise/conflict | P0 |
| 23-24 | 变更日志格式/完整性 | P0 |
| 25-26 | 空输入/无变更 | 边界 |
| 27-28 | 超大输入（50+条目）分段 | 性能 |
| 29-30 | 置信度降级计算 | 功能 |

---

## P0-5: 事务原子性保证（中型）

### 修改文件：`app/service/phase4_service.py`

`run_phase4()` 方法当前结构：

```python
async def run_phase4(self, db, project_id, chapter_id, ...):
    # Step 14: 构建 LLM 提取 prompt
    # Step 15-18: 调用 LLM 提取
    # Step 19: 解析 LLM 响应
    # Step 20a: 人物库合并 → catch Exception → log + continue
    # Step 20b: 时间线合并 → catch Exception → log + continue
    # Step 20c: 承诺合并 → catch Exception → log + continue
    # Step 20d: 世界观合并 → catch Exception → log + continue
    # Step 21: 卡牌充实 → catch Exception → log + continue
    # Step 22: 卡牌淘汰 → catch Exception → log + continue
    # Step 23: 变更日志 → catch Exception → log + continue
    # db.commit()  ← 没有事务保护
```

### 改造为事务安全

```python
from sqlalchemy import savepoint

async def run_phase4(self, db, project_id, chapter_id, ...):
    # 外层事务（Phase 4 主事务）
    try:
        # ... LLM 提取和解析 ...
        
        # 创建 savepoint（包含所有合并操作）
        sp = await db.begin_nested()
        try:
            # Step 20a-d: 四库合并
            # Step 21: 卡牌充实
            # Step 22: 卡牌淘汰
            # Step 23: 变更日志
            await sp.commit()  # 保存 savepoint
        except Exception:
            await sp.rollback()  # 回滚 savepoint，主事务继续
            logger.error("Phase 4 合并失败，已回滚")
            result["status"] = "merge_failed"
            result["error"] = str(e)
        
        await db.commit()  # 提交整个事务
    except Exception:
        await db.rollback()  # 完全回滚
        raise
```

### 事务边界定义

| 操作 | 是否在事务中 | 失败后果 |
|------|:----------:|----------|
| LLM 调用 | ❌ 在外 | 不计入事务，可重试 |
| 解析 LLM 响应 | ❌ 在外 | 不计入事务，可重试 |
| 四库合并写入 | ✅ 在 savepoint | 回滚到 savepoint |
| 卡牌充实 | ✅ 在 savepoint | 回滚到 savepoint |
| 卡牌淘汰 | ✅ 在 savepoint | 回滚到 savepoint |
| 变更日志 | ✅ 在 savepoint | 回滚到 savepoint |
| db.commit() | ✅ 主事务 | 全部成功 |

### savepoint vs 全事务

选择 **savepoint** 而非"要么全有要么全无"的全事务：
- 合并失败不浪费 LLM 调用结果（已经花了 token）
- 下次重试时可以跳过 LLM 调用（幂等检查已有）
- 合并失败时仍可记录部分结果到日志

### 测试要求（P0-5，至少 8 个）

| # | 测试 | 类型 |
|---|------|------|
| 1 | 正常流程提交成功 | 功能 |
| 2 | 合并失败回滚 savepoint，主事务不中断 | 稳定性 |
| 3 | LLM 调用失败不触发事务 | 功能 |
| 4 | savepoint 内部分失败 + 部分成功 | 稳定性 |
| 5 | 并发事务不互相影响 | 稳定性 |
| 6 | 变更日志随 savepoint 回滚 | 功能 |
| 7 | 卡牌淘汰随 savepoint 回滚 | 功能 |
| 8 | 主事务 commit 失败 → 完全回滚 | 稳定性 |

---

## P0-2: 完整调度器状态机（大型）

### 状态定义

```python
class Phase4State(str, Enum):
    IDLE = "idle"              # 初始状态，等待任务
    QUEUED = "queued"          # 已入队列
    LOCKING = "locking"        # 获取分布式锁
    EXTRACTING = "extracting"  # 调用 LLM 提取
    VERIFYING = "verifying"    # SourceText/Grounding 验证
    MERGING = "merging"        # 四库合并
    COMMITTING = "committing"  # 事务提交
    DONE = "done"              # 完成
    FAILED = "failed"          # 失败（不可恢复）
    RETRY = "retry"            # 可重试失败
```

### 状态转换图

```
IDLE → QUEUED → LOCKING → EXTRACTING → VERIFYING → MERGING → COMMITTING → DONE
                 ↓           ↓            ↓          ↓         ↓
               RETRY       RETRY        RETRY       RETRY     FAILED
                 ↓
               ⏎ (回补到 QUEUED，最多 5 次)
                 5 次后 → FAILED
```

### 分布式锁（Redis）

```python
async def _acquire_lock(self, project_id: int, timeout: int = 30000) -> bool:
    """Redis SET NX EX 实现分布式写锁。
    
    Key: phase4:lock:{project_id}
    Value: {scheduler_id}:{timestamp}
    TTL: 30s (自动过期防死锁)
    
    轮询策略：每 200ms 重试，最多 15 次（3s 总超时）
    """
    
async def _release_lock(self, project_id: int) -> None:
    """释放锁。只有锁的持有者才能释放（通过 value 中的 scheduler_id 验证）。"""
```

### 幂等性（三层）

| 层 | 范围 | 机制 | 失效场景 |
|:--:|:----:|------|----------|
| L1 | 内存 | in-memory nonce set（最多 1000 条 LRU） | 进程重启 |
| L2 | DB | Phase4Task.nonce UNIQUE 约束 | — |
| L3 | 业务 | 幂等键：`chapter_id + chapter_text hash` | 文本变更 |

### 调度器核心循环

```python
async def schedule_phase4(self, db, project_id, chapter_id, ...):
    # [1] 幂等检查
    #   L1: nonce in _nonce_set? → return cached
    #   L2: Phase4Task.nonce exists? → return existing
    #   L3: chapter_id + text_hash matches? → return existing
    
    # [2] 创建任务
    task = Phase4Task(project_id, chapter_id, nonce=nonce, state=QUEUED)
    db.add(task)
    await db.flush()
    
    # [3] 获取锁 → state = LOCKING
    lock_acquired = await self._acquire_lock(project_id)
    if not lock_acquired:
        task.state = RETRY
        await self._enqueue_retry(task)
        return {"status": "queued", "task_id": task.id}
    
    try:
        # [4] Gate: 四库门控检查 → 等待 pending 完成
        # [5] 提取 → state = EXTRACTING
        # [6] 验证 → state = VERIFYING
        # [7] 合并 → state = MERGING
        # [8] 提交 → state = COMMITTING
        # [9] 完成 → state = DONE
    except RetryableError:
        task.state = RETRY
        await self._handle_retry(db, project_id, task)
    except FatalError:
        task.state = FAILED
        # 通知用户
    finally:
        await self._release_lock(project_id)
```

### 失败回补

```python
_backoff_schedule = [10, 30, 60, 120, 300]  # 秒

async def _handle_retry(self, db, project_id, task, error):
    """可重试失败处理：
    - 首次失败 → 标记 retry，合并到下一章
    - 5 次内 → 指数退避重新提交
    - 5 次后 → 标记 FAILED，通知用户
    """
    task.retry_count += 1
    task.last_error = str(error)
    if task.retry_count >= 5:
        task.state = FAILED
        # 通知: phase4_failed(project_id, chapter_id, task_id)
    else:
        task.retry_at = datetime.utcnow() + timedelta(
            seconds=self._backoff_schedule[task.retry_count - 1]
        )
```

### 配置

```python
# app/config.py 或 phase4_scheduler.py 常量
SCHEDULER_LOCK_TTL = 30        # 锁自动过期（秒）
SCHEDULER_LOCK_RETRY = 15      # 锁重试次数
SCHEDULER_LOCK_INTERVAL = 0.2  # 锁重试间隔（秒）
SCHEDULER_MAX_RETRIES = 5      # 最大重试次数
SCHEDULER_RETRY_BACKOFF = [10, 30, 60, 120, 300]  # 退避间隔
SCHEDULER_NONCE_CACHE_SIZE = 1000  # 内存 nonce 缓存上限
```

### 与已实现代码的关系

当前 `phase4_scheduler.py` 已有：
- ✅ `_make_lock_key()` / `_make_nonced_id()` / `generate_nonce()` 辅助方法
- ✅ `_check_idempotency()` 基本骨架（L1+L2）
- ✅ `_verify_source_text()` / `_normalize_entity_names()`（P0-1 已完善）
- ❌ 无分布式锁实现（需要 Redis）
- ❌ 无状态机状态流转
- ❌ 无完整重试逻辑

### 测试要求（P0-2，至少 20 个）

| # | 测试 | 类型 |
|---|------|------|
| 1-2 | QUEUED→LOCKING→DONE 完整流程 | 功能 |
| 3-4 | 幂等 L1/L2 检查 | 功能 |
| 5 | 分布式锁获取/释放 | 稳定性 |
| 6 | 锁超时自动释放（防死锁）| 稳定性 |
| 7-8 | 可重试失败/不可恢复失败 | 稳定性 |
| 9-10 | 指数退避重试 | 稳定性 |
| 11 | 5 次重试后 FAILED | 稳定性 |
| 12 | 并发请求不同项目不冲突 | 稳定性 |
| 13-14 | 任务状态正确流转 | 功能 |
| 15 | Gate 门控等待/超时 | 稳定性 |
| 16 | 空队列不崩溃 | 边界 |
| 17 | 重复 nonce 幂等 | 稳定性 |
| 18 | 锁被其他 scheduler 持有 | 并发 |
| 19 | 失败合并到下一章 | 功能 |
| 20 | 内存 nonce LRU 淘汰 | 性能 |

---

## 实现并行策略

虽然有依赖链 `P0-3 → P0-5 → P0-2`，但文件层面可以完全并行：

| Agent | 文件 | 新文件 | 依赖 |
|:------|:-----|:------:|:----:|
| **merge-pro** | `app/service/merge_service.py` + `tests/test_merge_service.py` | 新 | 无 |
| **txn-pro** | `app/service/phase4_service.py` 事务改造 + `tests/test_phase4_transaction.py` | 修改 | 无（savepoint API 不依赖 merge_service 代码）|
| **scheduler-pro** | `app/service/phase4_scheduler.py` 状态机改造 + `tests/test_phase4_state_machine.py` | 修改 | 无（状态机逻辑是独立的）|

三路完全没有代码重叠：
- `merge_service.py` 是新文件
- `phase4_service.py` 事务改造只改 `run_phase4()` 方法体
- `phase4_scheduler.py` 状态机改造只改 `schedule_phase4()` 及其辅助方法

**最终集成验证**由第四个 Agent `integration-pro` 在全部完成后统一跑回归。

---

## 质量门禁（必须全部满足）

```python
# 1. 全部测试通过
python -m pytest tests/test_merge_service.py -v --tb=short           # ≥30 tests
python -m pytest tests/test_phase4_transaction.py -v --tb=short      # ≥8 tests  
python -m pytest tests/test_phase4_state_machine.py -v --tb=short    # ≥20 tests

# 2. 零 RuntimeWarning
python -m pytest ... -W error  # 不抛异常才算通过

# 3. 全量回归
python -m pytest tests/test_phase4_service.py tests/test_phase4_scheduler.py tests/test_health_monitor.py --tb=short

# 4. 集成验证
python -m pytest tests/test_phase4_integration.py tests/test_card_retire_integration.py tests/test_sourcetext_verification.py tests/test_key_manager.py --tb=short

# 5. 全量回归（可选）
python -m pytest tests/ --tb=short
```
