# ID 类型统一风险评估与专项计划

> **文档类型**: 风险评估 (Risk Assessment Only)  
> **创建日期**: 2026-06-21  
> **执行状态**: ⚠️ 评估阶段，不执行实际 DB 迁移  
> **评估人**: id-assessor (R3.4)

---

## 1. 现状统计

### 1.1 主键 (PK) 类型分布

| # | 模型 | 表名 | PK 类型 | 默认值 | 基类 | 备注 |
|---|------|------|---------|--------|------|------|
| 1 | **User** | `users` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 2 | **Chapter** | `chapters` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 3 | **CardPool** | `card_pool` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 4 | **VaultCharacter** | `vault_characters` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 5 | **VaultTimeline** | `vault_timeline` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 6 | **VaultWorld** | `vault_world` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 7 | **VaultPlotPromise** | `vault_plot_promises` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 8 | **DrawHistory** | `draw_history` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 9 | **DynamicLayer** | `dynamic_layers` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 10 | **VaultChangelog** | `vault_changelog` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 11 | **Secret** | `secrets` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 12 | **Plan** | `plans` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 13 | **UserSubscription** | `user_subscriptions` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 14 | **Template** | `templates` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 15 | **IngestJob** | `ingest_jobs` | `String(36)` UUID | `str(uuid4())` | BaseModel | |
| 16 | **Project** | `projects` | `Integer` 自增 | `autoincrement` | BaseModel (override) | ⚠️ 覆盖了 BaseModel.id |
| 17 | **HealthAlert** | `health_alerts` | `Integer` 自增 | `autoincrement` | Base + TimestampMixin | 直接继承 Base |
| 18 | **Notification** | `notifications` | `Integer` 自增 | `autoincrement` | Base + TimestampMixin | 直接继承 Base |
| 19 | **Phase4Task** | `phase4_tasks` | `Integer` 自增 | `autoincrement` | Base + TimestampMixin | 直接继承 Base |
| 20 | **GenerationTask** | `generation_tasks` | `Uuid` (原生) | `uuid.uuid4` | Base + TimestampMixin | 仅此模型用原生 Uuid |
| 21 | **SystemConfig** | `system_config` | `String(128)` (key) | 无自增 | Base | 无 id 列，key 为主键 |

**统计汇总:**

| PK 类型 | 模型数量 | 占比 |
|---------|----------|------|
| `String(36)` UUID | 15 | 71.4% |
| `Integer` 自增 | 4 | 19.0% |
| `Uuid` 原生 | 1 | 4.8% |
| `String(128)` key | 1 | 4.8% |

### 1.2 外键 (FK) 类型对照表

完整的外键关系矩阵，标注每条 FK 列的类型与参照 PK 列的类型：

| # | 子表 | FK 列 | FK 类型 | 参照表 | 参照 PK 类型 | 类型匹配？ | 风险等级 |
|---|------|-------|---------|--------|-------------|-----------|---------|
| 1 | `chapters` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 2 | `projects` | `user_id` | `String(36)` | `users.id` | `String(36)` | ✅ 匹配 | - |
| 3 | `projects` | `template_id` | `Integer` | `templates.id` | `String(36)` | ❌ **不匹配** | ⚠️ 低(预留) |
| 4 | `card_pool` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 5 | `generation_tasks` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 6 | `generation_tasks` | `chapter_id` | `String(36)` | `chapters.id` | `String(36)` | ✅ 匹配 | - |
| 7 | `generation_tasks` | `user_id` | `String(36)` | `users.id` | `String(36)` | ✅ 匹配 | - |
| 8 | `health_alerts` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 9 | `notifications` | `user_id` | `String(36)` | `users.id` | `String(36)` | ✅ 匹配 | - |
| 10 | `notifications` | `project_id` | `Integer` (可选) | `projects.id` | `Integer` | ✅ 匹配 | - |
| 11 | `draw_history` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 12 | `draw_history` | `chapter_id` | `String(36)` (可选) | `chapters.id` | `String(36)` | ✅ 匹配 | - |
| 13 | `draw_history` | `user_id` | `String(36)` | `users.id` | `String(36)` | ✅ 匹配 | - |
| 14 | `vault_characters` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 15 | `vault_timeline` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 16 | `vault_world` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 17 | `vault_plot_promises` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 18 | `vault_changelog` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 19 | `vault_changelog` | `chapter_id` | `String(36)` (可选) | `chapters.id` | `String(36)` | ✅ 匹配 | - |
| 20 | `dynamic_layers` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 21 | `dynamic_layers` | `chapter_id` | `String(36)` | `chapters.id` | `String(36)` | ✅ 匹配 | - |
| 22 | `secrets` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 23 | `user_subscriptions` | `user_id` | `String(36)` | `users.id` | `String(36)` | ✅ 匹配 | - |
| 24 | `user_subscriptions` | `plan_id` | `String(36)` | `plans.id` | `String(36)` | ✅ 匹配 | - |
| 25 | `templates` | `created_by` | `String(36)` (可选) | `users.id` | `String(36)` | ✅ 匹配 | - |
| 26 | `phase4_tasks` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 27 | `ingest_jobs` | `project_id` | `Integer` | `projects.id` | `Integer` | ✅ 匹配 | - |
| 28 | `ingest_jobs` | **`user_id`** | **`Integer`** | `users.id` | `String(36)` | ❌ **不匹配** | 🔴 严重 BUG |

**关键发现:**
- **28 条 FK 关系中，2 条类型不匹配 (7.1%)**
- `IngestJob.user_id` 使用了 `Mapped[int]` 但实际 FK 指向 `users.id` (String(36))，这会导致运行时错误或类型推断错误
- `Project.template_id` 是预留字段，影响较小

### 1.3 API Schema 类型不一致

| 响应 Schema | id 字段类型 (Schema) | id 字段类型 (Model) | project_id 类型 | 一致？ |
|------------|---------------------|--------------------|-----------------|--------|
| `CharacterResp` | `int` | `String(36)` UUID | `int` | ❌ id 类型错 |
| `TimelineResp` | `str` | `String(36)` UUID | `str` (应为 `int`) | ❌ project_id 错 |
| `PlotPromiseResp` | `int` | `String(36)` UUID | `int` | ❌ id 类型错 |
| `WorldResp` | `str` | `String(36)` UUID | `str` (应为 `int`) | ❌ project_id 错 |
| `SecretResp` | `int` | `String(36)` UUID | `int` | ❌ id 类型错 |
| `Phase4Task Resp` | `int` | `Integer` 自增 | - | ✅ 正确 |
| `HealthAlert Resp` | `int` | `Integer` 自增 | - | ✅ 正确 |
| `Notification Resp` | `int` | `Integer` 自增 | - | ✅ 正确 |
| `Auth/User Resp` | `str` | `String(36)` UUID | - | ✅ 正确 |
| `Card Resp` | `str` | `String(36)` UUID | - | ✅ 正确 |
| `Chapter Resp` | `str` | `String(36)` UUID | - | ✅ 正确 |
| `Template Resp` | `str` | `String(36)` UUID | - | ✅ 正确 |
| `Subscription/Plan` | `int` / `str` | `String(36)` UUID | - | ❌ Plan 错 |

**Schema 层不一致: 7 个 API 响应 Schema 的 ID 类型与实际 Model ID 类型不符。**

---

## 2. 影响分析

### 2.1 FK 变更影响面

如果进行 ID 类型统一迁移，所有 FK 列都需要同步变更：

| 变更方向 | 受影响的 FK 数量 | 影响的表 |
|----------|----------------|---------|
| Project Integer → UUID String(36) | **13 条 FK** | chapters, card_pool, generation_tasks, health_alerts, notifications, draw_history, vault_characters, vault_timeline, vault_world, vault_plot_promises, vault_changelog, dynamic_layers, phase4_tasks |
| 其他 Integer PK → UUID String(36) | **0 条** (无其他模型以 Integer PK 为目标) | - |
| UUID String(36) → Integer | **15 条 FK** (以 UUID PK 表为目标的所有 FK) | projects(user_id), generation_tasks(user_id, chapter_id), notifications(user_id), draw_history(user_id, chapter_id), vault_changelog(chapter_id), dynamic_layers(chapter_id), user_subscriptions(user_id, plan_id), templates(created_by), phase4_tasks(chapter_id), ingest_jobs(user_id) |

**结论: 无论向哪个方向统一，至少需要变更 13-15 条 FK 约束。**

### 2.2 代码影响面

| 层级 | 文件数 | str()/int() 转换点数 | 影响说明 |
|------|--------|---------------------|---------|
| Router (路由层) | 18 个文件 | 15+ 处 | 路由参数类型声明、ID 传递 |
| Service (服务层) | 30 个文件 | 50+ 处 | 大量 `str(id)` / `int(id)` 手动转换 |
| DAO (数据访问层) | 16 个文件 | 隐式 | 查询参数类型依赖上游传递 |
| Schema (API 契约) | 18 个文件 | 7 处类型错误 | 前后端契约不匹配 |

**代码中大量 `str(xxx.id)` 和 `int(xxx_id)` 是当前 ID 类型不一致的直接证据。**  
典型转换模式包括:
- `str(current_user.id)` — User.id 是 UUID 字符串
- `int(project_id)` — Project.id 是 Integer
- `str(project_id)` — 某些地方将其转为字符串用于 JSON payload
- `str(task.id)` — GenerationTask.id 是原生 UUID 类型

### 2.3 前端影响

前端当前接收到的 ID 格式不统一:
- **User/Chapter/CardPool/Vault 系列** → 前端收到 UUID 字符串 (如 `"a1b2c3d4-e5f6-..."`)
- **Project** → 前端收到整数 (如 `42`)
- **HealthAlert/Notification** → 前端收到整数 (如 `1`)
- **GenerationTask** → 前端收到 UUID 字符串

这导致前端需要:
1. 对不同实体使用不同的类型假设 (`typeof id === 'string'` vs `typeof id === 'number'`)
2. 路由参数类型不一致 (`/projects/:id` 的 `:id` 可能是数字或字符串)
3. 排序/比较逻辑复杂化 (不能统一对 ID 排序)

---

## 3. 迁移方案对比

### 方案 A: 全统一为 UUID String(36)

将所有 Integer/Uuid PK 统一为 `String(36)` 存储 UUID。

**变更范围:**
- 4 个 Integer PK 模型 → String(36): Project, HealthAlert, Notification, Phase4Task
- 1 个原生 Uuid PK 模型 → String(36): GenerationTask
- 13 条以 Integer PK 为目标的 FK → String(36)

| 维度 | 评估 |
|------|------|
| **彻底性** | ★★★★★ 完全统一，无任何 ID 类型差异 |
| **一致性** | ★★★★★ 所有 ID 都是字符串，API 契约统一 |
| **分布式友好** | ★★★★★ UUID 天生支持分布式 |
| **迁移成本** | ★★☆☆☆ 需修改 5 个 PK + 13 个 FK + 所有引用代码 |
| **执行风险** | ★★★☆☆ DB 迁移需停机 + 数据转换 |
| **性能影响** | ★★★☆☆ String(36) 索引比 Integer 略慢 |
| **向后兼容** | ★★☆☆☆ 已有 Integer ID 需映射为新的 UUID |

**预计工作量:** ~3-4 周
- 5 个模型的 ID 列类型变更 + 数据迁移脚本
- 13 个 FK 列变更
- 18 个 Router + 30 个 Service + 16 个 DAO 代码调整
- 18 个 Schema 文件类型修正
- 前端类型适配

### 方案 B: 全统一为 Integer 自增

将所有 UUID/String(36) PK 统一为 Integer autoincrement。

**变更范围:**
- 15 个 String(36) PK 模型 → Integer: User, Chapter, CardPool, VaultCharacter, VaultTimeline, VaultWorld, VaultPlotPromise, DrawHistory, DynamicLayer, VaultChangelog, Secret, Plan, UserSubscription, Template, IngestJob
- 1 个原生 Uuid PK 模型 → Integer: GenerationTask
- 15 条以 String(36) PK 为目标的 FK → Integer

| 维度 | 评估 |
|------|------|
| **彻底性** | ★★★★★ 完全统一 |
| **一致性** | ★★★★★ 所有 ID 都是整数 |
| **性能** | ★★★★★ Integer 索引极快，JOIN 最优 |
| **迁移成本** | ★☆☆☆☆ 成本极高，需要重新生成 16 个模型的全部 ID |
| **执行风险** | ★☆☆☆☆ 数据迁移极为复杂且危险 |
| **分布式友好** | ★★☆☆☆ 自增 ID 在分库分表场景有冲突风险 |
| **向后兼容** | ★☆☆☆☆ 所有已有 UUID 需要替换 |

**预计工作量:** ~6-8 周
- 所有 16 个 String(36)/Uuid PK 模型需要:
  - 新增 Integer PK 列
  - 生成新的自增 ID
  - 更新所有引用 FK
  - 删除旧 UUID 列
- 数据迁移脚本极其复杂
- 需要处理 API 兼容性（已有前端可能缓存 UUID）

### 方案 C: 保持现状 + ID 抽象层（推荐）

不修改数据库，引入统一的 ID 类型抽象。

**核心设计:**
```python
from typing import NewType, Union

# 统一 ID 抽象类型
UUIDStr = NewType("UUIDStr", str)   # 36-char UUID
AutoInt = NewType("AutoInt", int)   # autoincrement integer

# 统一 ID 类型 = 两种底层类型的联合
MolingID = Union[UUIDStr, AutoInt]

# Pydantic 序列化时统一输出为字符串
class IDSerializer:
    """将任意 MolingID 序列化为字符串。"""
    @staticmethod
    def serialize(id: MolingID) -> str:
        return str(id)
    
    @staticmethod
    def deserialize(s: str) -> MolingID:
        # 尝试解析为 int，失败则视为 UUID
        try:
            return AutoInt(int(s))
        except ValueError:
            return UUIDStr(s)
```

**逐步收敛策略:**
1. **Phase 1**: 修复 Schema 层类型错误（7 处）→ 统一 API 返回格式为 `str`
2. **Phase 2**: 引入 `MolingID` 抽象类型，逐步替换代码中的裸 `str`/`int`
3. **Phase 3**: 新模型统一使用 String(36) UUID（长期方向）
4. **Phase 4**: (可选) 视业务需要，在某个大版本中统一底层 DB 类型

| 维度 | 评估 |
|------|------|
| **彻底性** | ★★★☆☆ 未改变 DB 层，但 API/代码层统一 |
| **一致性** | ★★★★☆ API 层完全一致 |
| **迁移成本** | ★★★★★ 无需 DB 迁移，仅代码重构 |
| **执行风险** | ★★★★★ 零风险，渐进式改进 |
| **性能** | ★★★★☆ 保持 Integer PK 表的性能优势 |
| **分布式友好** | ★★★☆☆ 自增 ID 部分仍需注意 |
| **向后兼容** | ★★★★☆ 向前端隐藏差异 |

**预计工作量:** ~1-2 周
- 修复 7 个 Schema 类型错误
- 引入 ID 抽象工具模块
- 逐步替换代码中的显式 `str()`/`int()` 转换

---

## 4. 推荐方案及理由

### 推荐: 短期方案 C (抽象层) + 长期方向方案 A (UUID)

**理由:**

1. **风险最小**: 方案 C 不涉及 DB 迁移，无数据风险，可在当前迭代周期完成。
2. **修复即时问题**: 解决了 7 个 Schema 类型错误、`IngestJob.user_id` FK 不匹配等已有 bug。
3. **API 契约统一**: 前端立即获得一致的字符串 ID 格式。
4. **为长期迁移铺路**: ID 抽象层是方案 A 的前置依赖，完成抽象层后，未来任何时间点都可以在抽象层之下切换底层 DB 类型，上层代码无感。

**长期方向选择 String(36) UUID 的理由:**
- 墨灵是一个写作工具，未来可能涉及跨实例内容共享
- UUID 天然支持分布式和合并场景
- 已有 71% 的模型使用 UUID，是既成事实的标准
- 自增 ID 存在 ID 碰撞和信息泄露风险

---

## 5. 执行阶段规划

### 阶段 0: 紧急修复 (第 1 周)

修补已发现的关键 bug:

- [ ] 修复 `IngestJob.user_id` FK 类型不匹配 (`Mapped[int]` → `Mapped[str]`)
- [ ] 修复 7 个 Schema 的类型错误:
  - `CharacterResp.id`: `int` → `str`
  - `PlotPromiseResp.id`: `int` → `str`
  - `SecretResp.id`: `int` → `str`
  - `TimelineResp.project_id`: `str` → `int`
  - `WorldResp.project_id`: `str` → `int`
  - `Plan Resp.id`: `int` → `str`
- [ ] 生成 Alembic 迁移脚本修复 `ingest_jobs.user_id` 列类型

### 阶段 1: ID 抽象层 (第 1-2 周)

- [ ] 创建 `app/core/id_types.py` 模块:
  ```python
  # 统一 ID 类型定义
  class AnyID(str):
      """统一 ID 基类，可同时兼容 str 和 int 语义。"""
      ...
  ```
- [ ] 提供 `IDSerializer / normalize_id / coerce_id` 工具函数
- [ ] 更新 BaseDAO，在 `get()` / `get_multi()` 方法中统一 ID 处理
- [ ] 编写单元测试覆盖所有 ID 转换场景

### 阶段 2: 代码清理 (第 2-3 周)

- [ ] 逐步替换 Router 和 Service 中的裸 `str()` / `int()` 转换为抽象函数
- [ ] 更新所有 Schema 的 `Config.json_schema_extra` 让 OpenAPI 文档正确
- [ ] 前端适配：确保前端统一以 `string` 类型处理所有 ID

### 阶段 3: 长期迁移评估 (未来迭代)

- [ ] 评估是否需要在某个主版本中执行方案 A（全 UUID）
- [ ] 如需执行：使用 ID 抽象层确保代码层零影响 + 只迁移 DB 层

---

## 6. 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| `IngestJob.user_id` FK 类型不匹配导致运行时错误 | 高 | 中 | 阶段 0 立即修复 |
| API Schema 类型错误导致前端解析异常 | 中 | 中 | 阶段 0 立即修复 |
| 大量 `str()`/`int()` 转换散落导致维护困难 | 高 | 低 | 阶段 1-2 抽象层解决 |
| 未来 ID 数量耗尽 (Integer 自增) | 低 | 高 | 方案 A 长期解决 |
| 分布式场景下 ID 冲突 (Integer 自增) | 低 | 中 | 方案 A 长期解决 |
| DB 迁移失败导致数据丢失 | 低 | 极高 | 任何 DB 迁移前必须完整备份 + 回滚脚本 |

### 回滚方案

1. **阶段 0-2 的回滚**: 均为纯代码变更，通过 Git revert 即可回滚
2. **阶段 3 的 DB 迁移回滚**:
   - 迁移前创建完整 DB 备份 (pg_dump)
   - 编写反向 Alembic 迁移脚本
   - 在 staging 环境完整验证后再上生产
   - 设置观察期 (48h)，无异常后清理备份

---

## 7. 附录: 代码审计原始数据

### 7.1 BaseModel PK 定义 (`app/models/base.py:47-51`)

```python
class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id: Mapped[UUID] = mapped_column(
        String(36),       # <-- 注意: SQL 类型是 String(36)，但 Python 注解是 UUID
        primary_key=True,
        default=lambda: str(uuid4()),
    )
```

**值得注意**: `Mapped[UUID]` 注解与实际 `String(36)` 列类型不一致，但 SQLAlchemy 以 `mapped_column` 参数为准。

### 7.2 Project.id 覆盖 BaseModel.id (`app/models/project.py:16-21`)

```python
class Project(BaseModel, SoftDeleteMixin):
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
```

Project 明确覆盖了 BaseModel 的 UUID PK 为 Integer 自增。

### 7.3 GenerationTask.id 使用原生 Uuid (`app/models/generation_task.py:21-26`)

```python
class GenerationTask(Base, TimestampMixin, SoftDeleteMixin):  # 不继承 BaseModel
    id: Mapped[str] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
```

GenerationTask 不继承 BaseModel，避免 UUID PK 冲突，但使用了原生 `Uuid` 类型而非 `String(36)`。

### 7.4 IngestJob.user_id BUG (`app/ingest/models.py:28-32`)

```python
user_id: Mapped[int] = mapped_column(
    ForeignKey("users.id", ondelete="CASCADE"),  # users.id 是 String(36)!
    nullable=False,
)
```

`Mapped[int]` 声明与实际 FK 参照的 `String(36)` 类型不匹配。SQLAlchemy 会推断类型为 Integer，导致在数据库层面产生类型冲突。

### 7.5 Schema 层完整错误列表

| 文件 | Schema 类 | 错误字段 | 当前类型 | 正确类型 |
|------|----------|---------|---------|---------|
| `schemas/vault.py:159` | `CharacterResp` | `id` | `int` | `str` |
| `schemas/vault.py:159` | `CharacterResp` | `project_id` | `int` | ✅ 正确 |
| `schemas/vault.py:181` | `TimelineResp` | `id` | `str` | ✅ 正确 |
| `schemas/vault.py:181` | `TimelineResp` | `project_id` | `str` | `int` |
| `schemas/vault.py:197` | `PlotPromiseResp` | `id` | `int` | `str` |
| `schemas/vault.py:215` | `WorldResp` | `id` | `str` | ✅ 正确 |
| `schemas/vault.py:215` | `WorldResp` | `project_id` | `str` | `int` |
| `schemas/secret.py:14` | `SecretResp` | `id` | `int` | `str` |
| `schemas/secret.py:41` | `SecretItemUpdate` | `id` | `int` | `str` |
| `schemas/subscription.py:14` | Plan Resp | `id` | `int` | `str` |
| `schemas/phase4.py:36` | Phase4Task Resp | `id` | `int` | ✅ 正确 |

---

## 8. 结论

墨灵后端的 ID 类型混用问题已经在 3 个层面 (DB 层、Python 类型注解层、API Schema 层) 造成了一致性问题。但**这些问题目前尚未导致生产环境严重故障**（得益于 SQLAlchemy 的类型推断容错）。

**推荐行动:**
1. **立即** (阶段 0): 修复 2 个 FK bug + 7 个 Schema 错误
2. **短期** (阶段 1-2): 引入 ID 抽象层，统一代码风格
3. **长期** (阶段 3): 若业务需要，使用抽象层无缝迁移到全 UUID 方案
