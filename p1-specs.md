# P1 三项 — 生产级规格 v3

> 2026-06-17 | 拆书冷启动 + 导入引擎验收 + 置信度降级

---

## P1-1 + P1-2: 拆书引擎冷启动 & 数据退役

### 目标
实现 Genre Profile 在线冷启动（B1-B5），用户在新建项目时选择类型+梗概 → 系统加载 Genre Profile → 预填四库/动态层/卡牌池 → 生成 3 个开篇方向。

同时实现数据退役机制（§9.7），4 个退役触发器，渐进式权重衰减。

### 新文件：`app/genre/cold_start_loader.py`

```python
class ColdStartLoader:
    """
    拆书引擎冷启动加载器。
    
    输入: 用户选择的类型 + 故事梗概
    输出: 预填的四库数据 + 动态层 + 卡牌池 + 3个开篇方向
    """
```

### B1 类型选择 → Genre Profile 加载

用户界面流程：
1. 用户选择小说类型（玄幻/仙侠/都市/科幻/言情/悬疑/历史/游戏）
2. 用户输入故事梗概（200-500 字）
3. 系统根据类型匹配已有 Genre Profile
4. 如果无匹配 Profile → 使用通用模板 → 异步跑 A1-A5 分析补全

```python
async def load_genre_profile(self, genre: str) -> GenreProfile:
    """
    1. 从 DB 查询 genre_profiles 表，匹配 genre
    2. 如果有已分析的 Profile → 返回
    3. 如果没有 → 使用通用模板
    4. 异步触发 A1-A5 流水线补全分析
    """
```

### B2 预填四库

```python
async def prefill_vault(
    self, db, project_id: int, profile: GenreProfile, synopsis: str
) -> VaultPrefill:
    """
    1. 角色原型：根据 genre + synopsis 生成 3-5 个角色原型
    2. 世界观模板：genre 对应的基础世界观设定
    3. 时间线骨架：genre 典型的故事进程骨架（第1章-第N章节奏）
    
    使用 LLM（pro 模型）从 synopsis 提取角色和世界观元素
    """
```

**角色原型生成格式**：
```python
@dataclass
class CharacterPrototype:
    name: str
    role: str  # 主角/配角/反派
    archetype: str  # 英雄/导师/影子/信使...
    traits: List[str]
    motivation: str
    suggested_status: str = "active"
```

### B3 预填动态层

```python
async def prefill_dynamic_layer(
    self, profile: GenreProfile, synopsis: str
) -> DynamicLayerPrefill:
    """
    1. 开局状态：genre 典型开局（如修真:凡人→练气）
    2. 章节锚点：开局钩子 + 目标钩子 + 冲突钩子
    3. 初始钩子：3 个 genre 相关的故事钩子
    """
```

### B4 预填卡牌池

```python
async def prefill_card_pool(
    self, db, project_id: int, profile: GenreProfile, synopsis: str
) -> List[CardPrefill]:
    """
    1. 根据 genre 选取 15-20 条增强方向
    2. 根据 synopsis 个性化排序（相关度高的优先）
    3. 每条卡牌设置初始权重（freshness_multiplier=1.0）
    """
```

### B5 用户审核界面 API

```python
# API 端点（app/router/genre.py 新增）
POST /api/v1/genre/prefill            # 触发 B1-B5 并返回预填数据
GET  /api/v1/genre/prefill/{project_id}  # 获取预填结果供用户审核
POST /api/v1/genre/prefill/{project_id}/confirm  # 用户确认并入库

# 预填数据支持逐个删改（前端控制）
```

### P1-2: 数据退役机制（§9.7）

```python
class DataRetirementManager:
    """
    4 个退役触发器:
    A: 连续 3 次零命中 → 退役（权重 80%→50%→20%→0%）
    B: 超过 100 章未使用 → 归档
    C: 引擎版本更新 → 旧版数据标记退役
    D: 用户手动指定 → 即时退役
    
    权重衰减：
    - 首次触发: 80% 权重
    - 二次触发: 50% 权重
    - 三次触发: 20% 权重
    - 四次触发: 0% 权重（归档，不可用）
    """
```

### 测试要求（≥25）

| # | 测试 | 模块 |
|---|------|:----:|
| 1-3 | B1 类型匹配/通用模板/异步补全 | 冷启动 |
| 4-6 | B2 角色原型/世界观/时间线 | 冷启动 |
| 7-8 | B3 开局状态/钩子生成 | 冷启动 |
| 9-10 | B4 卡牌选取/排序 | 冷启动 |
| 11-13 | B5 API 端点/审核/确认入库 | 冷启动 |
| 14-15 | 预填数据为空/无效 genre | 边界 |
| 16-17 | LLM 生成失败降级 | 稳定性 |
| 18-20 | 退役触发器 A/B/C/D | 数据退役 |
| 21 | 权重衰减计算 | 数据退役 |
| 22 | 归档数据可查看 | 数据退役 |
| 23-24 | 无统计数据的空状态 | 边界 |
| 25 | 预填后用户修改再确认 | 集成 |

---

## P1-3: 导入引擎验收测试

### 目标
对连载书导入引擎（Phase 0-3）进行边界条件验收测试，覆盖短篇/长篇/批量/覆盖写入场景。

### 现有资源
- `app/ingest/` — 导入引擎完整流水线
- `tests/test_ingest.py` — 已有 20 个测试

### 新增测试（≥15）

```python
# tests/test_ingest_edge_cases.py
```

| # | 测试场景 | 说明 |
|---|---------|------|
| 1 | 1-2 章短篇导入 | Phase 0-3 完整流程，验证短文本处理 |
| 2 | 100+ 章长篇分批分析 | 验证分批（15章/批）逻辑 |
| 3 | 30+ 章 Level 2 压缩 | 验证 vault_filter 压缩处理 |
| 4 | 拆书→生成→重新导入的覆盖流程 | 拆书后修改再导入，验证覆盖 |
| 5 | 空章节内容导入 | 边界：空字符串 |
| 6 | 超大章节（10000+字） | 边界：超长文本 |
| 7 | 重复章节号导入 | 幂等性检查 |
| 8 | 断点续传模拟 | Phase 中断后恢复 |
| 9 | 并发导入同一个项目 | 竞态防护 |
| 10 | 不支持的文件格式 | 错误处理 |
| 11 | Phase 0 采集网络超时 | 稳定性 |
| 12 | Phase 1 四库合并冲突 | 集成 |
| 13 | Phase 2 动态层全空 | 边界 |
| 14 | Phase 3 确认前取消 | 用户中断 |
| 15 | full-import 一键流程完整 E2E | 集成 |

### 性能目标
- 单章导入 < 2s（不含 LLM 调用时间）
- 100 章批量导入 < 60s

---

## P1-4: 置信度降级策略实现

### 目标
在 Phase 4 合并结果中添加置信度评估，根据置信度决定自动入库/后台标记/弹窗确认/忽略。

### 修改文件：`app/service/phase4_service.py` + `app/service/merge_service.py`

### 4 级置信度区间

| 区间 | 行为 | 颜色 |
|:----:|:----:|:----:|
| > 0.8 | 自动入库，无需确认 | 🟢 |
| 0.5-0.8 | 自动入库 + 后台标记为 "需审核" | 🟡 |
| 0.3-0.5 | 暂停入库，弹窗要求用户确认 | 🟠 |
| < 0.3 | 忽略，不写入数据库 | 🔴 |

### 实现

```python
# 新增 ConfidenceLevel 枚举
class ConfidenceLevel(enum.Enum):
    HIGH = "high"       # > 0.8
    MEDIUM = "medium"   # 0.5-0.8
    LOW = "low"         # 0.3-0.5
    REJECT = "reject"   # < 0.3

def evaluate_confidence(self, confidence_score: float) -> ConfidenceLevel:
    if confidence_score > 0.8:
        return ConfidenceLevel.HIGH
    elif confidence_score >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.3:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.REJECT

def should_auto_apply(self, level: ConfidenceLevel) -> bool:
    """HIGH 和 MEDIUM 自动入库，LOW 需确认，REJECT 忽略"""
    return level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
```

### MergeService 集成

```python
# 在 merge_characters/merge_timeline 等方法中：
# 每个合并项都附带 confidence_score（见 P0-3 规格）
# 合并结果中新增:
result.confidence_level = evaluate_confidence(avg_confidence)
result.auto_applied = should_auto_apply(result.confidence_level)
result.items_requiring_review = [...]  # confidence LOW 的条目
```

### 变更日志增强

每条 ChangeEntry 增加 `confidence_level` 字段，方便前端过滤显示。

### 测试要求（≥10）

| # | 测试 | 类型 |
|---|------|------|
| 1-4 | 4 级区间边界值测试 | 功能 |
| 5-6 | HIGH/MEDIUM 自动应用 | 功能 |
| 7 | LOW 触发标记 | 功能 |
| 8 | REJECT 忽略 | 功能 |
| 9 | 平均置信度计算 | 功能 |
| 10 | 空列表默认 HIGH | 边界 |
| 11 | 混合置信度条目 | 集成 |
| 12 | 前端过滤字段存在 | 集成 |

---

## 质量门禁

```bash
# 每个 Agent 必须通过
python -m pytest tests/test_cold_start.py -v --tb=short           # ≥25
python -m pytest tests/test_ingest_edge_cases.py -v --tb=short    # ≥15
python -m pytest tests/test_confidence_level.py -v --tb=short     # ≥10

# 零 RuntimeWarning
python -m pytest ... -W error

# 回归
python -m pytest tests/ --tb=short
```
