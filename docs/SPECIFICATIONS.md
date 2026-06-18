# 墨灵 (Moling) 规格文档

> **版本**: 2.0.0 | **最后更新**: 2026-06-18
> 本文档整合了 P0/P1 规格、P0 剩余架构项及卡牌组合算法规格。

---

## 目录

1. [P0 规格](#1-p0-规格)
2. [P1 规格](#2-p1-规格)
3. [卡牌组合算法](#3-卡牌组合算法)
4. [质量门禁](#4-质量门禁)

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

## 4. 质量门禁

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
| 2.0.0 | 2026-06-18 | 整合 p0-specs.md + p1-specs.md + p0-remaining-arch.md + 算法文档 |
| 1.0.0 | 2026-06-17 | 原始三份规格文档分拆版本 |

---

**END**
