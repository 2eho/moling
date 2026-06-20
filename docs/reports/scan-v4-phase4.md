# Phase 4 引擎深度扫描报告

| 元数据 | 值 |
|--------|-----|
| **扫描日期** | 2026-06-21 |
| **扫描范围** | moling-server/app/ 中所有 Phase 4 相关文件 |
| **扫描人** | phase4-scanner |
| **THOROUGHNESS** | very thorough |

---

## 扫描文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `app/models/phase4_task.py` | 118 | 状态机 ORM 模型 |
| `app/schemas/phase4.py` | 46 | API Schema 定义 |
| `app/service/phase4_service.py` | ~2000+ | Phase 4 核心服务 (LLM 提取、四库合并、卡牌池) |
| `app/service/phase4_scheduler.py` | 1311 | 调度器 (分布式锁、幂等、状态机、内容安全验证) |
| `app/service/phase4_store.py` | 190 | 双模存储 (Redis/内存) |
| `app/service/merge_service.py` | 1127 | 四库合并核心引擎 |
| `app/service/vault_filter.py` | 630 | 四库过滤 (卡牌→上下文) |
| `app/service/conflict_detection.py` | 809 | 冲突检测服务 (基线/秘密矩阵/状态机) |
| `app/service/direction_scoring.py` | 626 | 方向冲突评分服务 |
| `app/service/weaving_scheme.py` | 804 | 编织方案匹配服务 |
| `app/service/import_service.py` | 618 | 导入引擎 |
| `app/service/health_monitor.py` | 473 | 子情节健康监控 |
| `app/worker/phase4_task.py` | 116 | Celery 异步任务 |
| `app/router/phase4.py` | 224 | API 路由层 |
| `app/dao/phase4_dao.py` | 91 | Phase 4 DAO |

**总计代码量**: ~9000+ 行

---

## 1. 状态机完整性

### 定义 (models/phase4_task.py:16-28)

```python
class Phase4State(str, Enum):
    IDLE = "idle"               # 初始
    QUEUED = "queued"           # 入队列
    LOCKING = "locking"         # 获取锁
    EXTRACTING = "extracting"   # LLM 提取
    VERIFYING = "verifying"     # 验证
    MERGING = "merging"         # 合并
    COMMITTING = "committing"   # 提交
    DONE = "done"               # 完成
    FAILED = "failed"           # 失败
    RETRY = "retry"             # 重试
```

### 状态流转 (phase4_scheduler.py:122-306)

**主路径** (schedule_phase4):
```
[1] generate nonce + 幂等检查
[2] task.state = QUEUED
[4] task.state = LOCKING → 获取分布式锁
[6] task.state = EXTRACTING → 内容安全验证
[7] task.state = VERIFYING ✓
[8] task.state = MERGING → 执行四库合并
[9] task.state = COMMITTING
[10] task.state = DONE
```

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| IDLE→QUEUED | ✅ 正确 | 创建任务时直接设为 QUEUED (行162-168) |
| QUEUED→LOCKING | ✅ 正确 | 获取锁前设置 LOCKING (行187) |
| LOCKING→EXTRACTING | ✅ 正确 | 锁获取成功后设置 (行213) |
| EXTRACTING→VERIFYING | ✅ 正确 | 验证通过后 (行229) |
| VERIFYING→MERGING | ✅ 正确 | 合并前设置 (行235) |
| MERGING→COMMITTING | ✅ 正确 | 合并完成后 (行249) |
| COMMITTING→DONE | ✅ 正确 | 提交后 (行255) |
| 失败→RETRY | ✅ 正确 | 可重试异常→RETRY (行283-296) |
| RETRY→FAILED | ✅ 正确 | 5次后标记 (行289-290, 636-637) |
| 手动RETRY→QUEUED | ✅ 正确 | retry_task 端点 (router/phase4.py:199-223) |

### ⚠ 发现的问题

**P1-1: IDLE 状态未显式使用**。Phase4State.IDLE 定义了但调度流程中从未显式设置 task.state = IDLE。默认值在模型中设置为 IDLE，但创建任务时立刻设为 QUEUED。`app/service/phase4_service.py:158` 使用 `task.status = "pending"` 而非 `task.state` —— status 和 state 是两套独立的状态标记，存在**双状态系统不一致**。

**P1-2: RETRY 无显式回到 QUEUED 的路径**。scheduler 文档注释说 "⏎ (回补到 QUEUED，最多 5 次)"，但代码中 RETRY 状态的任务设置的是 `retry_at` 时间戳，没有显式转换回 QUEUED。实际的重新执行需要外部轮询任务表或手动触发 retry_task API。

**P1-3: state vs status 双轨**。Phase4Task 同时维护 `state`(Phase4State enum) 和 `status`(str: pending/running/done/failed)，两套状态在多个地方同时更新但可能存在不一致（如 `analyze_project` 将 status 设为 "analyzed" 但 state 不改）。

---

## 2. 分布式锁

### 实现 (phase4_store.py + phase4_scheduler.py)

**Redis 模式**:
```python
# phase4_store.py:100-101
async def setnx_ex(self, lock_key, owner_id, ttl=30):
    return bool(await self._redis.set(lock_key, owner_id, nx=True, ex=ttl))
```
✅ Redis SET NX EX 实现正确。

**锁释放验证**:
```python
# phase4_scheduler.py:468-478
async def _release_distributed_lock(self, project_id):
    existing = self._lock_store.get(lock_key)
    expected_owner = self._current_lock_owner.get(lock_key)
    if existing is not None and expected_owner is not None:
        if isinstance(existing, dict) and existing.get("scheduler_id") == expected_owner:
            del self._lock_store[lock_key]   # ✅ owner 验证
```

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| Redis SET NX EX | ✅ 正确 | `nx=True, ex=ttl` |
| TTL 30s | ✅ 正确 | `SCHEDULER_LOCK_TTL = 30` (行58) |
| Owner 验证释放 | ✅ 正确 | 只有 lock owner 能释放 (行474-478) |
| 超时强制抢占 | ✅ 正确 | 内存模式下检测超时→强制释放 (行446-457) |
| 轮询策略 | ✅ 正确 | 15 次 × 0.2s = 3s 总重试窗口 |

### ⚠ 发现的问题

**P2-1: 内存模式无真实 TTL**。`phase4_scheduler.py` 的 `_acquire_distributed_lock` 使用内存 dict 模拟锁，TTL 通过 `time.monotonic()` 比较实现，没有真正的后台过期机制。如果进程崩溃，锁记录会永久残留直到 scheduler 重新初始化。

**P2-2: Redis 释放锁无 owner 验证**。`phase4_store.py:107-108` 的 `release_lock` 直接删除 key，没有通过 Lua 脚本检查 owner：
```python
# 当前实现 - 不安全
async def release_lock(self, lock_key: str) -> None:
    await self._redis.delete(lock_key)

# 正确实现应该是
# if redis.call("get", KEYS[1]) == ARGV[1] then return redis.call("del", KEYS[1]) else return 0 end
```
虽然 `_release_distributed_lock` (内存层) 做了 owner 验证，Redis 层的 `release_lock` 缺乏此保护。如果锁已因 TTL 过期被其他 Worker 持有，当前 Worker 仍可能删除他人持有的锁。

**P2-3: 锁粒度评估**。锁 key 是 `phase4:lock:{project_id}`，即项目级锁。同一个 project 的多章节提交是序列化的（P0-10 分析见下文），对于多章节并行的场景是瓶颈，但保证了安全性。

---

## 3. 幂等性三层

### 实现 (phase4_scheduler.py:311-368)

```
Layer 1: 内存 nonce 集合 (_nonce_set + LRU _nonce_cache 1000条) — ~1ms
Layer 2: DB SELECT phase4_tasks WHERE nonce=xxx — ~5ms  
Layer 3: DB UNIQUE CONSTRAINT (Phase4Task.nonce unique=True) — 永不失效
```

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| L1 内存 LRU 1000 条 | ✅ 正确 | `SCHEDULER_NONCE_CACHE_SIZE = 1000`，OrderedDict 实现 |
| L2 DB SELECT | ✅ 正确 | `phase4_dao.get_by_nonce(db, nonce)` |
| L3 DB UNIQUE | ✅ 正确 | Phase4Task.nonce 设 `unique=True, index=True` |
| 非命中→缓存 | ✅ 正确 | 新 nonce 自动注册到 L1 (行365-367) |

### ⚠ 发现的问题

**P3-1: Nonce 未包含 content hash**。任务需求中提到 L3 是 `chapter_id+text_hash`，但实际实现为：
```python
# phase4_scheduler.py:313-319
nonce = f"ch{chapter_id}_{int(time.time())}_{h}"
# h = hashlib.sha256(raw.encode()).hexdigest()[:12]
# raw = f"ch{chapter_id}_{ts}"  — 只有 chapter_id + 时间戳，不含 content
```
如果同一个 chapter 内容修改后再次提交，nonce 仍然不同（时间戳变），但语义上同一 chapter 同一内容的两次提交应该被幂等拦截。当前设计仅防止并发重复提交，不防止内容相同的重复收纳。

**P3-2: Layer 1 非原子性**。`_check_idempotency` 中 L1 检查和注册分两步进行（先 check L1，再 L2，再注册 L1），在高并发下存在 TOCTOU 竞态窗口。不过 L3 DB UNIQUE 约束是最终防线。

---

## 4. 事务边界

### 实现 (phase4_service.py:1095-1277)

```
run_phase4():
  [14] LLM 调用 (事务外) ← ✅ 正确
  [14] _parse_extraction_result() (事务外)
  
  sp = db.begin_nested()   ← savepoint
  
  try:
    [15] _merge_characters()
    [16] _merge_timeline()
    [17] _merge_plot_promises()
    [18] _merge_world()
    [18a] confidence evaluation
    [19] _enrich_card_pool()
    [20] _archive_changelog()
    [21] card_retire (try/except, 降级)
    
    sp.commit()             ← 提交 savepoint
  except:
    sp.rollback()           ← 回滚 savepoint, LLM 结果保留
  
  db.commit()               ← 主事务提交
```

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| LLM 在事务外 | ✅ 正确 | `_call_extraction_llm` 在 savepoint 之前调用 |
| savepoint 在合并前 | ✅ 正确 | `sp = await db.begin_nested()` 在合并操作前 |
| savepoint 失败=局部回滚 | ✅ 正确 | 不回滚 LLM 结果 |
| 主事务提交 | ✅ 正确 | `await db.commit()` 在 savepoint 之后 |

### ⚠ 发现的问题

**P4-1: 外层 try/except 中 await db.rollback() 会回滚 savepoint 已提交部分**。`phase4_service.py:1270-1274`:
```python
except Exception as e:
    await db.rollback()  # ← 此时 sp.commit() 可能已生效
```
如果 savepoint 已 commit 但 `db.commit()` 抛出异常，此处的 `db.rollback()` 是正确的。但如果 `db.commit()` 成功后的后续代码抛出异常（在 try 块内但 db.commit() 之后），`db.rollback()` 会尝试回滚已提交的事务（通常是 no-op）。

**P4-2: 卡牌淘汰在 savepoint 内但有独立 try/except**。正确设计——卡牌淘汰失败不应阻止其他合并操作，代码实现了正确的降级（行1230-1250）。

---

## 5. 失败回补

### 实现 (phase4_scheduler.py:536-657)

```
SCHEDULER_RETRY_BACKOFF = [10, 30, 60, 120, 300]  # 秒
SCHEDULER_MAX_RETRIES = 5
```

**回补逻辑** (_handle_failure):
| 连续失败次数 | 动作 |
|-------------|------|
| 1 | 自动合并到下一章 fallback_merge |
| 2 | 四库管理页角标 |
| 3 | 弹窗建议全量分析 |
| ≥5 | 强制暂停 Phase 4 调度 |

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 退避序列 [10,30,60,120,300] | ✅ 正确 | 指数增长序列 |
| 5 次后→FAILED | ✅ 正确 | `task.state = FAILED, task.status = "failed"` |
| retry_at 计算 | ✅ 正确 | `datetime.now() + timedelta(seconds=backoff)` |
| consecutive_failures 计数 | ✅ 正确 | `_state_lock` 保护 |

### ⚠ 发现的问题

**P5-1: schedule_phase4 中的 retry 处理有两套逻辑**。在异常处理块（行275-303）中，先检查 `RetryableError` 和非 `LockNotAcquiredError` → 调用 `_handle_retry`；否则走另一条路径直接调度指数退避。这两套逻辑可能导致状态不一致：`_handle_retry` 设置 `task.state = RETRY`，而 else 分支设置 `task.state = RETRY` + `retry_at`。

**P5-2: fallback_queue 缺乏持久化**。回补队列存储在内存 `self._state.fallback_queue` 中，进程重启丢失。虽有 `_assemble_input` 消费，但如果消费前进程重启，回补记录丢失。

**P5-3: 连续失败计数器是全局的（非 per-project）**。`self._state.consecutive_failures` 是所有项目共享的。如果 project A 失败 2 次，project B 失败 1 次，计数器=3，会导致项目 B 收到 "弹窗建议全量分析"（对应 3 次失败的动作），这不准确。

---

## 6. 四库合并

### merge_service.py 4 个子合并

| 子合并 | 方法 | 行数 | 匹配策略 |
|--------|------|------|----------|
| 人物库 | `merge_characters` | 293-440 | 精确名→别名→编辑距离≤2→姓氏→新建 |
| 时间线库 | `merge_timeline` | 516-657 | (day, event) 精确→子串 |
| 剧情承诺库 | `merge_plot_promises` | 678-872 | 标题精确→描述精确 |
| 世界观库 | `merge_world_building` | 903-1079 | 名称精确→扩展/修订/冲突 |

### 置信度降级

| 等级 | 阈值 | 行为 |
|------|------|------|
| HIGH | > 0.8 | 自动入库 |
| MEDIUM | 0.5-0.8 | 自动入库 + 标记需审核 |
| LOW | 0.3-0.5 | 暂停入库 + 弹窗确认 |
| REJECT | < 0.3 | 忽略 |

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 4 个子合并实现 | ✅ 正确 | 全部独立实现 |
| 匹配策略完整 | ✅ 正确 | 多级降级匹配 |
| 置信度降级正确 | ✅ 正确 | `evaluate_confidence()` 正确映射 |
| 编辑距离算法 | ✅ 正确 | `_calc_edit_distance` 标准 Levenshtein |

### ⚠ 发现的问题

**P6-1: merge_characters 别名来源不一致**。`_get_character_aliases()` 从 traits 和 state_machine 中提取别名，但 `phase4_scheduler._get_aliases()` 仅从 traits 提取。两个实现不一致可能导致别名匹配遗漏。

**P6-2: 时间线去重仅按 (day, event) 精确匹配**。同一天不同表述的相同事件不会被去重（如 "张三离开" 和 "角色张三离开了村庄"可能描述同一事件）。

**P6-3: 世界观系统规则冲突检测过于简单**。仅检查否定词列表（不能/不可/禁止），无法检测更复杂的规则矛盾。

**P6-4: merge_plot_promises 的 stale 检查仅看 `planted_chapter`**，不考虑 `advancement_log` 中的推进记录。一个在第 5 章创建、第 25 章推进的承诺在第 30 章会被标记 stale（30-5=25 > 20），但实际上它最近才被推进。

---

## 7. LLM 提取

### 实现 (phase4_service.py)

**Prompt 模板** (_build_extraction_prompt, 行1283-1317):
- 包含四库上下文摘要
- 章节正文
- 灵感卡 ID 列表
- JSON 格式定义

**响应解析** (_parse_extraction_result, 行1444-1503):
- 清除 markdown 代码块标记
- 尝试直接解析 JSON
- 查找 `{...}` 提取 JSON
- 验证结果字段类型（确保 item 是 dict）
- 失败→返回 empty result（优雅降级）

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| Prompt 模板正确 | ✅ 正确 | 结构化 JSON Schema 定义 |
| 响应解析鲁棒 | ✅ 正确 | 多层 fallback (直接解析→提取JSON→空结果) |
| 解析失败降级 | ✅ 正确 | 返回空结果，不中断流水线 |
| LLM 调用失败降级 | ✅ 正确 | `_call_extraction_llm` 返回空提取 |
| max_tokens=4096 | ✅ 正确 | 中等章节足够 |

### ⚠ 发现的问题

**P7-1: 无 LLM 超时处理**。`llm_client.chat()` 没有可见的 timeout 参数。如果 LLM 服务挂起，Phase 4 流程将无限期阻塞。应添加显式超时。

**P7-2: EXTRACTION_SCHEMA 与 _analyze_chapter_content 的 prompt 不一致**。`_analyze_chapter_content` (行432-495) 使用另一套 prompt 和分析方式，返回的 JSON 结构（characters/timeline_events/plot_promises/world_elements）与 `run_phase4` 使用的 EXTRACTION_SCHEMA（character_updates/timeline_updates/plot_promise_updates/world_updates）不同。这构成了**两套 LLM 提取体系**：
- `execute_storage` → `_analyze_chapter_content`（旧版，简单 JSON 提取）
- `run_phase4` → `_call_extraction_llm` → `_parse_extraction_result`（新版，结构化 Schema）

**P7-3: 四库上下文可能超 token 限制**。`_get_vault_summary_async` 列出所有角色（无截断），大型项目（100+ 角色）可能导致 prompt 远超模型上下文窗口。

---

## 8. 卡牌系统

### 完整流水线

```
抽卡 → vault_filter (Step 2) → conflict_detection (Step 3) 
     → direction_scoring (Step 4) → weaving_scheme (Step 5) 
     → 大纲填充
```

### 各步骤分析

| 步骤 | 服务 | Fallback |
|------|------|----------|
| 四库过滤 | vault_filter.py | filter_all() 兜底（无卡牌时取 Top-N） |
| 冲突检测 | conflict_detection.py | LLM fallback (置信度<0.3) |
| 方向评分 | direction_scoring.py | LLM fallback (置信度<0.3) |
| 编织方案 | weaving_scheme.py | LLM fallback (置信度<0.3) |
| 大纲填充 | (外部) | 单段式兜底 |

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 抽卡 | ✅ | 由外部模块处理 |
| 四库过滤 | ✅ | 层级压缩 (Level1/Level2) |
| 冲突检测 | ✅ | 三种检测 + U-curve 置信度 |
| 方向评分 | ✅ | 相容性矩阵 + 实体冲突 + 情感冲突 |
| 编织方案 | ✅ | 7 种模式 + 规则引擎 + LLM fallback |
| 每步 fallback | ✅ | 每步都有 |

### ⚠ 发现的问题

**P8-1: 步骤间无错误传递**。每个步骤独立运行，步骤间的 fallback 机制是独立的。如果一个步骤的 LLM fallback 失败，该步骤降级，但下游步骤不知情。缺乏全局协调。

**P8-2: 编织方案选择模式与方向评分未联动**。`direction_scoring.py` 检测到了 "高冲突方向对"（如稳妥+神之一手），但 `weaving_scheme.py` 在选择编织模式时不考虑这个信息。

---

## 9. 健康监控

### R1/R2/R3 三级预警

| 规则 | 条件 | 级别 |
|------|------|------|
| R1 | 8章未推进 | 🟡 yellow |
| R2 | ≥4次同类型重复推进 | 🟠 orange |
| R3 | 10章静默 + 无提及 | 🔴 red |
| R3→R1 | 10章静默但有提及 | 🟡 yellow (降级) |

### 防疲劳过滤

- 同一 (promise_id, rule) 在 3 章窗口内不重复
- `ANTI_FATIGUE_WINDOW = 3`

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| R1 实现正确 | ✅ | 8 章窗口 + 状态过滤 |
| R2 实现正确 | ✅ | ≥4 次 + event_type 去重 |
| R3 实现正确 | ✅ | 10 章 + 提及降级 |
| 防疲劳过滤 | ✅ | 3 章窗口去重 |
| 零 LLM 成本 | ✅ | 纯 SQL/数据结构计算 |

### ⚠ 发现的问题

**P9-1: 不是 O(1)**。健康监控对每个承诺都执行三个检查，复杂度 O(n_promises)。对于大项目（可能数百个 promise），每次调用都全量扫描。虽不需要 O(1)，但可以添加缓存优化。

**P9-2: R2 的 event_type 检测依赖 advancement_log 中的 event_type 字段**，但实际代码中 advancement_log 条目只存储 `chapter`, `event`, `timestamp`，没有 `event_type` 字段。这意味着 R2 几乎永远不会触发，因为 `event_types` 集合为空。

**P9-3: 缺少 R3→red 后的行动建议**。R3 告警只返回 red 等级和原因，但没有自动建议（如"建议考虑回收或废弃该伏笔"）。

---

## 10. 并发安全

### 锁粒度分析

```
锁 Key: phase4:lock:{project_id}
```

| 场景 | 安全性 |
|------|--------|
| 同一 project 多个章节同时提交 | ✅ 安全（序列化执行） |
| 不同 project 同时提交 | ✅ 安全（不同锁 key） |
| Worker 崩溃 | ✅ 安全（TTL 自动释放） |

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 分布式锁粒度 | ✅ 正确 | 项目级锁，细粒度足够 |
| 并发安全 | ✅ 正确 | 多 project 可并行 |

### ⚠ 发现的问题

**P10-1: 锁粒度可能导致大项目阻塞**。如果 Project A 有 100 个章节排队，Project B 只有 1 个章节，Project B 需要等待 Project A 的当前章节处理完才能开始（不同 project 不同锁 key，无问题）。但如果同一 project 有多个章节，它们是序列化的——这保证了数据一致性，但牺牲了吞吐量。

**P10-2: 内存锁无真实 TTL**。如前分析（P2-1），内存模式下的锁依赖于 monotonic 时间比较，进程崩溃未清理。

---

## 11. 导入引擎

### import_service.py 分析

| 功能 | 实现状态 |
|------|----------|
| 文件格式支持 | txt / docx / epub |
| 编码检测 | 多编码回退 (utf-8→gbk→gb2312→gb18030→latin-1) |
| 章节拆分 | 正则匹配 (4 种模式) |
| 元数据提取 | 文件名解析 |
| 导入模式 | replace / append |

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 批量插入 | ⚠ | 逐条 add + 单次 commit，非 BulkInserter |
| 事务安全 | ⚠ | 单个会话内执行，无 savepoint 保护 |
| 断点续传 | ❌ 未实现 | 失败后无恢复点 |

### ⚠ 发现的问题

**P11-1: 无 BulkInserter**。章节创建使用逐条 `db.add(chapter)`（行327-339），大型导入（1000+ 章）性能差。应使用 `db.add_all()` 或 `db.execute(insert(Chapter), [...])`。

**P11-2: 无事务回滚保护**。如果 100 个章节中的第 50 个插入失败，前 49 个已 flush 但未 commit。代码未使用 savepoint，失败时的行为依赖 SQLAlchemy 的隐式回滚。

**P11-3: 无断点续传**。导入过程无进度记录。如果导入 1000 章内容的中途失败，已导入的章节要么全部回滚（无 commit），要么需要手动清理。

**P11-4: 替换模式下的批量删除**。`import_mode == "replace"` 时，使用 `for ch in existing: await db.delete(ch)` 逐条删除（行316-321），大量章节时性能差。应使用 `db.execute(delete(Chapter).where(...))`。

---

## 12. 资源清理

### 审查结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 临时文件清理 | ✅ | import_service 清理上传文件 (行360-364) |
| Worker 内存积累 | ⚠ | 无明显防护 |

### ⚠ 发现的问题

**P12-1: Scheduler 内存积累**。`Phase4Scheduler` 中以下数据结构随任务执行持续增长：
- `_nonce_set`: 无上限清理 (只有 set 操作)
- `_nonce_cache`: 有 1000 上限 (LRU)
- `_fallback_queue`: 在 `_assemble_input` 中消费，但如果输入组装未被调用则累积
- `_task_store`: 无容量限制

**P12-2: 无 Worker 重启后的状态恢复**。Celery worker 重启后，内存中的 nonce_set 和 nonce_cache 全部丢失，仅靠 L2 (DB) 和 L3 (UNIQUE) 防护。

**P12-3: 无定期 GC 机制**。Lock 记录在内存模式下（_lock_store, _current_lock_owner）没有定期清理机制，异常情况下的残留锁记录不会自动清除。

---

## 总结评分

| 模块 | 得分 | 关键问题数 |
|------|------|-----------|
| 状态机 | 7.5/10 | 3 个 (P1-1, P1-2, P1-3) |
| 分布式锁 | 7.0/10 | 3 个 (P2-1, P2-2, P2-3) |
| 幂等性三层 | 7.5/10 | 2 个 (P3-1, P3-2) |
| 事务边界 | 8.0/10 | 2 个 (P4-1, P4-2) |
| 失败回补 | 6.5/10 | 3 个 (P5-1, P5-2, P5-3) |
| 四库合并 | 7.0/10 | 4 个 (P6-1, P6-2, P6-3, P6-4) |
| LLM 提取 | 7.0/10 | 3 个 (P7-1, P7-2, P7-3) |
| 卡牌系统 | 8.0/10 | 2 个 (P8-1, P8-2) |
| 健康监控 | 7.5/10 | 3 个 (P9-1, P9-2, P9-3) |
| 并发安全 | 7.5/10 | 2 个 (P10-1, P10-2) |
| 导入引擎 | 5.0/10 | 4 个 (P11-1, P11-2, P11-3, P11-4) |
| 资源清理 | 6.0/10 | 3 个 (P12-1, P12-2, P12-3) |

**加权总分**: **71.5 / 100** (B 级)

### 按优先级汇总

#### Critical (P0)
- **P2-2**: Redis 释放锁无 owner 验证——可能导致锁被错误释放
- **P9-2**: R2 规则依赖的 event_type 字段不存在——R2 告警将永不被触发
- **P5-3**: 连续失败计数是全局的——可能导致错误告警
- **P6-4**: Stale 检查忽略 advancement_log——可能导致误报 stale

#### High (P1)
- **P1-3**: 双状态系统 (state/status) 不一致
- **P7-2**: 两套 LLM 提取体系不一致
- **P11-1**: 导入引擎无 BulkInserter
- **P11-2**: 导入引擎无事务回滚保护

#### Medium (P2)
- **P3-1**: Nonce 未包含 content hash
- **P5-2**: fallback_queue 无持久化
- **P6-1**: 别名来源不一致
- **P7-1**: LLM 调用无超时
- **P12-1**: Scheduler 内存数据结构累积
