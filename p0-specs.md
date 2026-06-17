# P0 专业实现规格（2026-06-17）

> 三路并发：① 卡牌淘汰 → ② API Key Pool → ③ SourceText 验证
> 质量门禁：全部测试通过 ✅ | 零 RuntimeWarning ✅ | 错误处理全覆盖 ✅ | 边界测试 ✅

---

## P0-4: 卡牌淘汰集成（小）

### 目标
Phase 4 写入完成后自动触发卡牌淘汰检查，确保卡牌池不超过上限，新鲜期过期卡牌自动退役。

### 现有资源
- `app/models/card.py`: CardPool(project_id, card_id, rarity, freshness_multiplier, retired, retired_at)
- `app/service/card_pool_service.py`: pool operations (deal/retire/list)
- `app/service/card_retire_task.py`: retire check skeleton

### 实现要求

#### 1. 触发集成
- `phase4_service.py` 的 `run_phase4()` 最后一步调用 `card_retire_service.check_and_retire(db, project_id)`
- 必须与 Phase 4 写入在同一事务中（失败则回滚 Phase 4 变更）
- 使用 `sqlalchemy.event.listen` 或事务后钩子

#### 2. 淘汰逻辑（`check_and_retire()`）
```python
async def check_and_retire(db, project_id) -> RetireResult:
    """
    1. 获取当前活跃卡牌：status='active' AND retired=False
    2. 计算新鲜期：freshness_multiplier × CARD_FRESHNESS_MULTIPLIER(默认1.5)
    3. 排序规则：新鲜期低的优先淘汰
    4. 上限检查：活跃池 > MAX_ACTIVE_CARDS(80) → 淘汰最旧的差额
    5. 新鲜期检查：新鲜期 < 当前进度 → 标记为 expired 并加入淘汰候选
    6. 执行淘汰：retired=True, retired_at=now
    7. 返回 RetireResult{retired_count, expired_count, remaining_active}
    """
```

#### 3. 错误处理
| 场景 | 处理 |
|------|------|
| 卡牌池为空 | 返回 retired_count=0，不报错 |
| 所有卡牌都在新鲜期内 | 不淘汰任何卡牌 |
| 数据库连接失败 | 记录日志，不阻塞 Phase 4 主流程 |
| 已有退役卡牌 | 不重复退役（幂等） |

#### 4. 测试要求（至少 8 个测试）

| # | 测试 | 类型 |
|---|------|------|
| 1 | 卡牌池超过上限时正确淘汰 | 功能 |
| 2 | 卡牌池未超上限时不淘汰 | 功能 |
| 3 | 新鲜期未过的不淘汰 | 功能 |
| 4 | 空卡牌池静默通过 | 边界 |
| 5 | 所有卡牌active时不淘汰 | 边界 |
| 6 | 幂等性：重复调用不重复退役 | 稳定性 |
| 7 | 数据库异常降级（不抛异常） | 稳定性 |
| 8 | 退役后卡牌状态正确（retired=True） | 功能 |

---

## P0-6: API Key Pool 轮转（中）

### 目标
实现 Pro Pool (9 Keys) + Flash Pool (6 Keys) 双池管理，支持 LEAST_USAGE / ROUND_ROBIN 选择策略，Key 健康度检测 + 指数退避冷却。

### 现有资源
- `app/llm/client.py`: LLMClient 类，已有 RateLimitTracker
- `app/llm/client.py`: `call_llm()` 方法
- `app/config.py`: 已有 LLM_API_KEY 等配置

### 实现要求

#### 1. KeyManager 类（`app/llm/key_manager.py` 新建）

```python
class KeyManager:
    """
    职责：
    1. 管理 Pro Pool（9 keys） + Flash Pool（6 keys）
    2. 提供 LEAST_USAGE / ROUND_ROBIN 选择策略
    3. 监控 Key 健康度（错误计数 + 冷却状态）
    4. 指数退避冷却（30s→60s→120s→300s）
    5. 自动恢复：冷却期满后重新加入可用池
    """
```

#### 2. 配置
```python
# app/config.py 新增
LLM_PRO_KEYS: List[str] = []     # 9 keys from env
LLM_FLASH_KEYS: List[str] = []   # 6 keys from env
KEY_SELECT_STRATEGY: str = "LEAST_USAGE"  # LEAST_USAGE | ROUND_ROBIN
KEY_BACKOFF_BASE: int = 30       # 初始冷却秒数
KEY_BACKOFF_MAX: int = 300       # 最大冷却秒数
KEY_RECOVERY_CHECK_INTERVAL: int = 60  # 恢复检查间隔（秒）
```

#### 3. Key 健康模型
```python
@dataclass
class KeyHealth:
    key: str
    pool: str  # "pro" | "flash"
    usage_count: int = 0
    consecutive_errors: int = 0
    last_error_at: Optional[datetime] = None
    cooling_until: Optional[datetime] = None  # 冷却到期时间
    backoff_level: int = 0  # 0=正常, 1=30s, 2=60s, 3=120s, 4=300s
    is_healthy: bool = True
```

#### 4. 选择策略

| 策略 | 行为 |
|------|------|
| `LEAST_USAGE` | 选择 usage_count 最低的健康 Key |
| `ROUND_ROBIN` | 轮询选择健康 Key |
| 全部冷却 | 抛出 `NoAvailableKeyError`（明确告知调用方） |

#### 5. 错误处理
| 场景 | 处理 |
|------|------|
| Key 返回 429 | 立即标记冷却，指数退避 |
| Key 连续错误 3 次 | 标记为不健康，冷却 300s |
| 所有 Key 冷却 | 返回 `NoAvailableKeyError`，不阻塞调用方 |
| Key 冷却期满 | 自动恢复为健康（惰性检查，下次请求时） |

#### 6. 与 LLMClient 集成
- `call_llm()` 接受可选 `pool="pro"|"flash"` 参数
- 默认 `pool="pro"`
- Key 选中后传递给 LiteLLM 调用
- 调用结果（成功/失败/429）反馈给 KeyManager

#### 7. 线程安全
- 使用 `asyncio.Lock` 保护 Key 状态变更
- 选择 Key 时锁定，减少竞态
- 冷却状态检查和更新原子化

#### 8. 测试要求（至少 12 个测试）

| # | 测试 | 类型 |
|---|------|------|
| 1 | LEAST_USAGE 选择 usage 最低的 Key | 功能 |
| 2 | ROUND_ROBIN 轮询顺序正确 | 功能 |
| 3 | Key 返回 429 后被冷却 | 稳定性 |
| 4 | 冷却期满后自动恢复 | 稳定性 |
| 5 | 连续 3 次错误后保持冷却 | 稳定性 |
| 6 | 所有 Key 冷却时抛出异常 | 边界 |
| 7 | Pro Pool 和 Flash Pool 独立管理 | 功能 |
| 8 | 并发请求不导致 Key 重复选择（线程安全） | 稳定性 |
| 9 | 空 Pool 不崩溃 | 边界 |
| 10 | 调用成功后重置错误计数 | 功能 |
| 11 | 指数退避时间正确（30→60→120→300） | 功能 |
| 12 | `call_llm()` 传入 pool 参数正确路由 | 集成 |

---

## P0-1: SourceText 内容安全验证（大）

### 目标
实现 Phase 4 入口的 SourceText Grounding（§11.6 第一道防线），确保 LLM 提取的所有信息都可在原文中找到依据，防止幻觉入库。

### 现有资源
- `app/service/phase4_scheduler.py`: 已有 `_verify_source_text()` 骨架（async，使用 RapidFuzz）
- `app/service/phase4_scheduler.py`: 已有 `_normalize_entity_names()` 骨架
- `app/service/phase4_scheduler.py`: 已有 `_fuzzy_match()` 方法（RapidFuzz partial_ratio）

### 实现要求

#### 1. SourceText Grounding（第一道防线）

```python
async def verify_extraction(
    self,
    chapter_text: str,
    chapter_analysis: Dict[str, Any]
) -> VerificationResult:
    """
    对每个提取条目：
    1. 获取 source_text（LLM 在提取时标注的来源文本片段）
    2. RapidFuzz partial_ratio ≥ SIMILARITY_THRESHOLD(85) → 通过
    3. partial_ratio < 85 → 调用 LLM-as-Judge 二次确认
    4. LLM 判 fail → 标记为可疑（skipped）
    5. LLM 判 pass → 通过
    6. 缺少 source_text → 直接跳过（标记 warn）
    
    Returns:
        VerificationResult {
            passed: bool,           # 全部通过或仅有 warn
            total_items: int,
            passed_items: int,
            skipped_items: List[str],  # 被跳过的条目名+原因
            warnings: List[str],    # 缺少 source_text 的 warn
        }
    """
```

#### 2. LLM-as-Judge（第二道防线）

```python
async def _llm_judge(self, source_text: str, chapter_text: str) -> str:
    """
    当 RapidFuzz 不确定时（相似度 < 85%），
    调用 LLM（使用 flash 模型）判断 source_text 是否可接受。
    
    Prompt 结构：
    - source_text: {提取的来源}
    - chapter_text: {原文章节}
    - 问题: "source_text 的内容是否可以在 chapter_text 中找到依据？"
    - 输出: "pass" | "fail"
    """
```

#### 3. 性能要求
- RapidFuzz 匹配：应在 10ms 内完成（平均每个字符）
- LLM-as-Judge：仅当 RapidFuzz < 85% 时才调用（减少 LLM 调用次数）
- 对于超过 5000 字的章节：分段处理，每段独立验证

#### 4. 配置
```python
# app/config.py 或 phase4_scheduler.py 常量
SIMILARITY_THRESHOLD: float = 85.0  # RapidFuzz 相似度阈值
LLM_JUDGE_MODEL: str = "flash"  # Judge 使用 flash 模型（更便宜）
MAX_CHAPTER_LENGTH: int = 5000  # 分段处理阈值（字）
```

#### 5. 错误处理
| 场景 | 处理 |
|------|------|
| LLM Judge 调用失败 | 信任 RapidFuzz 结果（保守策略） |
| source_text 为空 | 标记为 warn，不阻止入库 |
| 整章无任何提取 | VerificationResult.empty = True |
| RapidFuzz 异常 | 降级为 warn（保守策略） |

#### 6. 与 Phase 4 调度器集成
- `schedule_phase4()` 调用 `verify_extraction()` 作为第二步（幂等检查后）
- 验证结果写入 `Phase4Task.safety_check` 字段
- 如果 `verification.warnings` 非空，记录日志但不阻止入库
- 允许用户后续查看验证报告

#### 7. 实体名规范化（背景）
`_normalize_entity_names()` 已实现骨架，补齐 RapidFuzz 匹配逻辑 + 别名注册。

#### 8. 测试要求（至少 15 个测试）

| # | 测试 | 类型 |
|---|------|------|
| 1 | source_text 精确匹配原文 | 功能 |
| 2 | source_text 模糊匹配 ≥85% | 功能 |
| 3 | source_text 模糊匹配 <85% 但 LLM 判 pass | 功能 |
| 4 | source_text 模糊匹配 <85% 且 LLM 判 fail → skip | 功能 |
| 5 | 缺少 source_text → warn | 边界 |
| 6 | 空分析结果 | 边界 |
| 7 | 超大章节分段处理 | 性能 |
| 8 | LLM Judge 故障 → 信任 RapidFuzz | 稳定性 |
| 9 | RapidFuzz 异常 → 降级 warn | 稳定性 |
| 10 | 所有条目被 skipped → passed=False | 功能 |
| 11 | Unicode/特殊字符匹配 | 边界 |
| 12 | 实体名规范化：精确别名匹配 | 功能 |
| 13 | 实体名规范化：模糊匹配注册别名 | 功能 |
| 14 | 实体名规范化：无匹配注册新实体 | 功能 |
| 15 | 实体名规范化：空名字过滤 | 边界 |

---

## 质量门禁（三路统一）

每条代码提交前必须完成：

```python
# 1. 格式检查
pdm run lint          # flake8 / ruff 零错误
# 2. 类型检查  
pdm run type-check    # mypy / pyright 零错误（严格模式）
# 3. 单元测试
pdm run test          # 新测试 100% 通过 + 零回归
# 4. 零 RuntimeWarning
pdm run test -W error # RuntimeWarning 转化为错误，确保零
# 5. 边界测试覆盖
#    空值、超长、并发、异常、幂等
```
