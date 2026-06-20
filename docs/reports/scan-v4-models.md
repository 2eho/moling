# 墨灵 Models/Schemas 深度扫描报告 (v4)

> **扫描日期**: 2026-06-21  
> **扫描范围**: 21 个 Models (含 1 个 ingest 额外模型) + 17 个 Schema 文件  
> **扫描引擎**: model-scanner  
> **Thoroughness**: very thorough

---

## 执行摘要

| 类别 | CRITICAL | HIGH | MEDIUM | LOW |
|------|----------|------|--------|-----|
| ORM 关系完整性 | 1 | 1 | 0 | 0 |
| FK 索引 | 0 | 2 | 1 | 1 |
| Model-Schema 一致性 | 2 | 4 | 6 | 5 |
| 主键类型 | 2 | 1 | 0 | 0 |
| TimestampMixin 覆盖 | 0 | 0 | 0 | 0 |
| 软删除覆盖 | 0 | 0 | 2 | 6 |
| 校验规则 | 0 | 1 | 4 | 5 |
| 响应 Schema 敏感字段 | 0 | 0 | 0 | 1 |
| 冗余/废弃字段 | 0 | 0 | 3 | 2 |
| `__init__.py` 导出 | 0 | 1 | 2 | 3 |
| Schema 版本提示 | 0 | 0 | 2 | 1 |
| Vault Schema ID | 0 | 0 | 0 | 0 |
| **合计** | **5** | **10** | **20** | **24** |

---

## 1. ORM 关系完整性 (Relationship Completeness)

### 逐模型审查

#### Phase4Task — **CRITICAL**
**文件**: `app/models/phase4_task.py:31-118`  
**问题**: 有 `project_id` (FK) 和 `chapter_id` (String(36)) 但没有定义任何 `relationship()`。  

| FK 列 | 目标表 | FK 约束 | relationship() | back_populates |
|-------|--------|---------|----------------|----------------|
| `project_id` | projects.id | YES (CASCADE) | **缺失** | Project 侧也缺失 `phase4_tasks` |
| `chapter_id` | chapters.id | **无 FK 约束** | **缺失** | Chapter 侧也缺失 |

**补充**: `chapter_id` 仅为 `String(36)` 列，无 `ForeignKey()` 约束，仅靠索引保证查询性能。

#### IngestJob — **CRITICAL (跨模块)**
**文件**: `app/ingest/models.py:17-97`  
**问题**: 与 Phase4Task 相同 — 有 `project_id` (FK) 和 `user_id` (FK) 但没有任何 `relationship()` 定义。

| FK 列 | 目标表 | FK 约束 | relationship() |
|-------|--------|---------|----------------|
| `project_id` | projects.id | YES (CASCADE) | **缺失** |
| `user_id` | users.id | YES (CASCADE) | **缺失** |

**注意**: Project 和 User 模型也缺少对应反向关系（如 `ingest_jobs`）。

#### 其他 19 模型 — **全部通过**
所有其余模型（User, Project, Chapter, DynamicLayer, GenerationTask, CardPool, DrawHistory, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld, VaultChangelog, HealthAlert, SystemConfig, Secret, Notification, Template, Plan, UserSubscription）均已完成双向 relationship 配对，`back_populates` 正确。

---

## 2. FK 索引 (Foreign Key Index)

### 缺失 index=True 的 FK 列

#### Notification.project_id — **HIGH**
**文件**: `app/models/notification.py:49-55`  
```python
project_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    ForeignKey("projects.id", ondelete="SET NULL"),
    nullable=True,
    # 缺少 index=True
)
```
**影响**: 按项目查询通知的性能较差。Notification 的 `user_id` 有 index=True，但 `project_id` 没有。

#### UserSubscription.plan_id — **HIGH**
**文件**: `app/models/subscription.py:68-72`  
```python
plan_id: Mapped[str] = mapped_column(
    String(36),
    ForeignKey("plans.id", ondelete="CASCADE"),
    nullable=False,
    # 缺少 index=True
)
```
**影响**: `user_id` 有 index=True，但 `plan_id` 没有。按套餐查询订阅需要全表扫描。

#### Template.created_by — **MEDIUM**
**文件**: `app/models/template.py:36-41`  
```python
created_by: Mapped[Optional[str]] = mapped_column(
    String(36),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    # 缺少 index=True
)
```
**影响**: 按创建者查询模板时无索引优化，但模板数量通常较少。

#### IngestJob.user_id — **LOW**
**文件**: `app/ingest/models.py:29-34`  
`user_id` 有 FK 但缺少 index=True。

### 统计
| 总 FK 列数 | 有 index=True | 缺 index=True | 覆盖率 |
|-----------|---------------|---------------|-------|
| 31 | 27 | 4 | 87% |

---

## 3. Model-Schema 一致性 (Model ↔ Schema Field Mapping)

### SecretResp.id — **CRITICAL** (类型不匹配)
**文件**: `app/schemas/secret.py:14` vs `app/models/secret.py`  
```python
# Schema: id: int          ← 错误
# Model:  id: Mapped[UUID] = mapped_column(String(36), ...)  ← UUID 字符串
```
**影响**: Pydantic 验证会失败或数据截断。Secret 的 PK 是 String(36) UUID，但 Schema 声明为 int。

### PlanResp.id — **CRITICAL** (类型不匹配)
**文件**: `app/schemas/subscription.py:14` vs `app/models/subscription.py:12`  
```python
# Schema: id: int          ← 错误
# Model:  id: Mapped[UUID] = mapped_column(String(36), ...)  ← UUID 字符串
```
**影响**: 同 SecretResp — UUID PK 在 Schema 中错误声明为 int。

### IngestJob.project_id — **CRITICAL** (FK 类型不匹配，跨模块)
**文件**: `app/ingest/models.py:22-28`  
```python
project_id: Mapped[str] = mapped_column(
    String(36),                              # ← 声明为 String(36)
    ForeignKey("projects.id", ondelete="CASCADE"),  # ← 但 projects.id 是 Integer!
)
```
**影响**: 这是**已知 Bug** — String(36) FK 指向 Integer PK，数据库层面可能建表失败或数据不一致。

### CardResp.project_id — **HIGH** (类型不匹配)
**文件**: `app/schemas/card.py:36` vs `app/models/card_pool.py:20`  
```python
# Schema: project_id: str    ← 声明为 str
# Model:  project_id: Mapped[int] = mapped_column(ForeignKey("projects.id",...))  ← Integer FK
```
**影响**: CardPool 的 project_id 是 Integer FK（指向 Project 的 Integer PK），但 Schema 声明为 str。

### TimelineResp.project_id — **HIGH** (类型不匹配)
**文件**: `app/schemas/vault.py:182` vs `app/models/vault_timeline.py:16`  
```python
# Schema: project_id: str    ← 声明为 str  
# Model:  project_id: Mapped[int]  ← Integer FK
```

### WorldResp.project_id — **HIGH** (类型不匹配)
**文件**: `app/schemas/vault.py:216` vs `app/models/vault_world.py:16`  
```python
# Schema: project_id: str    ← 声明为 str
# Model:  project_id: Mapped[int]  ← Integer FK
```

### Phase4TaskResp.project_id — **HIGH** (类型不匹配)
**文件**: `app/schemas/phase4.py:38` vs `app/models/phase4_task.py:54`  
```python
# Schema: project_id: str    ← 声明为 str
# Model:  project_id: Mapped[int] = mapped_column(Integer, ...)  ← Integer
```

### Vault Schema 字段缺失（B5/B6/B8/B9 补充字段未在 Response 中呈现）

| Response 类 | Model 有但 Response 缺失的字段 | 严重级别 |
|------------|------------------------------|----------|
| `CharacterResp` | `location`, `appearance`, `personality`, `knowledge`, `confidence`, `chapter_hist`, `current_state`, `motivation` | **MEDIUM** (B5 补充字段) |
| `TimelineResp` | `day`, `title`, `precedes`, `confidence`, `source_chapter`, `importance`, `updated_at` | **MEDIUM** (B6 补充字段) |
| `PlotPromiseResp` | `title`, `redeem_window`, `confidence` | **MEDIUM** (B8 补充字段) |

### TemplateResp 包含 Model 中不存在的字段 — **MEDIUM**
**文件**: `app/schemas/template.py:17-18` vs `app/models/template.py`  
```python
# TemplateResp 特有:
target_words: Optional[int]   # Template Model 无此字段
style: Optional[str]           # Template Model 无此字段
```
Model 仅有 `structure` (JSON) 存储模板结构，无 `target_words`/`style` 独立字段。

### WorldResp 额外字段 — **MEDIUM**
**文件**: `app/schemas/vault.py:220-221` vs `app/models/vault_world.py`  
```python
# WorldResp 特有:
change_type: Optional[str]     # VaultWorld Model 无此字段
rules: Optional[list]          # Model 用 constraint (Text) 而非 rules (list)
```
Model 有 `constraint` (Text) 字段但未在 WorldResp 中暴露。

### NotificationResp 额外字段 — **LOW**
**文件**: `app/schemas/notification.py:19`  
```python
message: Optional[str]    # Model 无此字段，由 model_validator 从 content 派生
```
这是兼容字段，由 `model_validator` 自动填充，功能正确。

### 类型不一致汇总

| Schema 类 | 字段 | Schema 类型 | Model 类型 | 严重级别 |
|-----------|------|-------------|-----------|----------|
| SecretResp | id | int | String(36)/UUID | **CRITICAL** |
| PlanResp | id | int | String(36)/UUID | **CRITICAL** |
| CardResp | project_id | str | int (Integer FK) | **HIGH** |
| TimelineResp | project_id | str | int (Integer FK) | **HIGH** |
| WorldResp | project_id | str | int (Integer FK) | **HIGH** |
| Phase4TaskResp | project_id | str | int (Integer) | **HIGH** |
| NotificationResp | project_id | str | Optional[int] | **MEDIUM** |
| IngestJob (model) | project_id | String(36) | 应为 Integer | **CRITICAL** |

---

## 4. 主键类型分析 (PK Types)

### 当前 PK 类型分布

| PK 类型 | 模型列表 | 数量 |
|---------|---------|------|
| `String(36)` (= UUID str) | User, Chapter, Secret, Template, Plan, CardPool, DynamicLayer, UserSubscription, VaultCharacter, VaultTimeline, VaultWorld, VaultChangelog, VaultPlotPromise, DrawHistory | 14 |
| `Integer` autoincrement | Project, Notification, HealthAlert, Phase4Task | 4 |
| `Uuid` native | GenerationTask | 1 |
| `String(128)` (key-value PK) | SystemConfig | 1 |

### FK 目标类型交叉引用

| FK 列 | 来源表 | 目标表 PK | 来源类型 | 目标类型 | 匹配？ |
|-------|-------|-----------|---------|----------|--------|
| project_id | Chapter | Project | Integer | Integer | ✓ |
| project_id | Secret | Project | Integer | Integer | ✓ |
| project_id | DynamicLayer | Project | Integer | Integer | ✓ |
| project_id | GenerationTask | Project | Integer | Integer | ✓ |
| project_id | CardPool | Project | Integer | Integer | ✓ |
| project_id | DrawHistory | Project | Integer | Integer | ✓ |
| project_id | VaultCharacter | Project | Integer | Integer | ✓ |
| project_id | VaultTimeline | Project | Integer | Integer | ✓ |
| project_id | VaultWorld | Project | Integer | Integer | ✓ |
| project_id | VaultChangelog | Project | Integer | Integer | ✓ |
| project_id | VaultPlotPromise | Project | Integer | Integer | ✓ |
| project_id | HealthAlert | Project | Integer | Integer | ✓ |
| project_id | Phase4Task | Project | Integer | Integer | ✓ |
| **project_id** | **IngestJob** | **Project** | **String(36)** | **Integer** | **✗ CRITICAL** |
| user_id | Project | User | String(36) | String(36) | ✓ |
| user_id | GenerationTask | User | String(36) | String(36) | ✓ |
| user_id | Notification | User | String(36) | String(36) | ✓ |
| user_id | DrawHistory | User | String(36) | String(36) | ✓ |
| user_id | UserSubscription | User | String(36) | String(36) | ✓ |
| user_id | IngestJob | User | String(36) | String(36) | ✓ |
| created_by | Template | User | String(36) | String(36) | ✓ |
| plan_id | UserSubscription | Plan | String(36) | String(36) | ✓ |
| chapter_id | DynamicLayer | Chapter | String(36) | String(36) | ✓ |
| chapter_id | GenerationTask | Chapter | String(36) | String(36) | ✓ |
| chapter_id | DrawHistory | Chapter | String(36) | String(36) | ✓ |
| chapter_id | VaultChangelog | Chapter | String(36) | String(36) | ✓ |

**关键发现**: 仅 IngestJob.project_id 存在 `String(36) → Integer` 的类型不匹配。其他所有 FK 与其目标 PK 类型一致。

### 混合 PK 类型的影响 — **HIGH** (架构债务)
Project 使用 Integer PK 而 14 个模型使用 String(36) UUID PK，导致：
- FK 列类型不一致（有些 Integer，有些 String(36)）
- 需要人工追踪每个 FK 的目标类型
- `docs/id-type-unification-plan.md` 规划了统一方案但文件不存在，可能尚未开始执行

---

## 5. TimestampMixin 覆盖

所有 21 个模型均通过 `BaseModel` 或直接继承 `TimestampMixin` 获得 `created_at`/`updated_at`。

| 模型 | created_at | updated_at | 继承方式 |
|------|-----------|------------|----------|
| User | ✓ | ✓ | BaseModel (→TimestampMixin) |
| Project | ✓ | ✓ | BaseModel |
| Chapter | ✓ | ✓ | BaseModel |
| DynamicLayer | ✓ | ✓ | BaseModel |
| GenerationTask | ✓ | ✓ | Base + TimestampMixin |
| CardPool | ✓ | ✓ | BaseModel |
| DrawHistory | ✓ | ✓ | BaseModel |
| VaultCharacter | ✓ | ✓ | BaseModel |
| VaultTimeline | ✓ | ✓ | BaseModel |
| VaultPlotPromise | ✓ | ✓ | BaseModel |
| VaultWorld | ✓ | ✓ | BaseModel |
| VaultChangelog | ✓ | ✓ | BaseModel |
| HealthAlert | ✓ | ✓ | Base + TimestampMixin |
| SystemConfig | ✓ | ✓ | Base + TimestampMixin |
| Secret | ✓ | ✓ | BaseModel |
| Notification | ✓ | ✓ | Base + TimestampMixin |
| Template | ✓ | ✓ | BaseModel |
| Plan | ✓ | ✓ | BaseModel |
| UserSubscription | ✓ | ✓ | BaseModel |
| Phase4Task | ✓ | ✓ | Base + TimestampMixin |
| IngestJob | ✓ | ✓ | BaseModel (ingest) |

**结论**: 100% 覆盖，无需修复。SystemConfig 迁移到 TimestampMixin 已完成 ✓。

---

## 6. 软删除覆盖 (SoftDeleteMixin)

### 已有软删除
User, Project, Chapter, Secret, GenerationTask, CardPool, VaultCharacter, VaultTimeline, VaultPlotPromise, VaultWorld, Notification (11/21)

### 缺失软删除 — 需评估

#### DynamicLayer — **MEDIUM**
每个 Chapter 对应一条 DynamicLayer，类似 Chapter 的业务重要性。Chapter 有软删除而 DynamicLayer 没有，不一致。

#### VaultChangelog — **MEDIUM**
变更是不可变历史记录，但出于审计追查考虑，可能需要软删除标记而非物理删除。

#### Template — **LOW**
模板为共享资源，软删除可防止误操作。

#### Plan — **LOW**
订阅方案删除后，已有订阅的 plan_id 将失效。软删除更安全。

#### UserSubscription — **LOW**
订阅历史对账需要保留，不应物理删除。

#### DrawHistory — **LOW**
抽取历史为不可变记录，软删除意义有限。

#### HealthAlert — **LOW** (合理缺失)
告警为临时数据，解决后可直接物理删除。

#### SystemConfig — **LOW** (合理缺失)
Key-value 配置，直接删除即可。

#### Phase4Task — **LOW** (合理缺失)
任务记录为不可变幂等追踪数据。

---

## 7. 校验规则 (Schema Field Constraints)

### 缺少或不足的约束

#### UpdateChapterReq.content — **HIGH**
**文件**: `app/schemas/chapter.py:22`  
`content` 字段无 min_length/max_length 约束，可能接受超大文本导致性能问题。

#### SecretResp & UpdateSecretReq — **MEDIUM**
**文件**: `app/schemas/secret.py:11-35`  
**所有字段均无 Field() 约束** — 使用裸类型声明而非 `Field(...)`。
- `description` 无 max_length
- `known_by`, `unknown_to` 列表项无验证
- `secrecy_level` 无 pattern 约束
- `debt` 无 ge=0 约束

#### PlanResp — **MEDIUM**
**文件**: `app/schemas/subscription.py:11-22`  
裸类型声明，无 Field() 约束：
- `price` 无 ge=0
- `currency` 无 max_length
- `interval` 无 pattern (应为 month/year)

#### LoginReq.password — **MEDIUM**
**文件**: `app/schemas/auth.py:26-27`  
`password` 无 min_length 约束（RegisterReq 有 min_length=8）。

#### SubscriptionResp — **MEDIUM**
**文件**: `app/schemas/subscription.py:32-44`  
裸类型声明，无 Field() 约束。

### 校验良好的 Schema
`CreateProjectReq`, `UpdateProjectReq`, `RegisterReq`, `PasswordResetReq`, `DrawCardReq`, `GenerateReq`, `SyncGenerateReq`, `RedrawCardsReq`, `CharacterCreate`, `TimelineCreate`, `PlotPromiseCreate`, `WorldCreate` 均有适当的 Field 约束。

---

## 8. 响应 Schema 敏感字段暴露审查

| Schema | 敏感字段 | 是否暴露 | 状态 |
|--------|---------|----------|------|
| UserResp | password_hash | 否 | ✓ 安全 |
| UserResp | reset_token | 否 | ✓ 安全 |
| UserResp | reset_token_expires | 否 | ✓ 安全 |
| UserManageResp | password_hash | 否 | ✓ 安全 |
| UserManageResp | reset_token | 否 | ✓ 安全 |
| NotificationResp | content | 是 | ✓ 正常（通知内容） |
| LLMConfigResp | api_key | api_key_masked (遮蔽) | ✓ 安全 |
| LLMConfigReq | api_key | 输入用，正常 | ✓ 安全 |
| SystemConfig | value | 仅在管理端 | ✓ 安全 |

### UserResp 暴露 bio — **LOW**
`bio` 字段在 `auth.py:UserResp` 中不存在，但在 `setting.py:UserSettings` 和 `UpdateProfileReq` 中公开。UserResp 正确排除了 bio。

**结论**: 所有敏感字段（password_hash, reset_token, api_key 明文）均未在响应 Schema 中暴露。

---

## 9. 冗余/废弃字段

### Project.template_id — **MEDIUM**
**文件**: `app/models/project.py:102-106`  
注释为"预留"，当前未在业务逻辑中实际使用。CreateProjectReq 包含 `template_id` 但后端未实现模板创建功能。

### WorldResp.rules + change_type — **MEDIUM** (疑似废弃命名)
**文件**: `app/schemas/vault.py:220-221`  
- `rules: Optional[list]` — Model 中对应为 `constraint` (单个 Text)，看起来是旧版多规则命名
- `change_type: Optional[str]` — Model `VaultWorld` 无此字段
- WorldCreate/WorldUpdate 中也包含 `change_type` 和 `rules`

### SyncGenerateReq — **MEDIUM** (已废弃端点)
**文件**: `app/schemas/chapter.py:63`  
注释明确标记为"deprecated sync generation endpoint"。Schema 保留但功能已迁移到异步 GenerationTask。

### ChapterResp 缺失生成相关字段 — **LOW**
`used_card_ids`, `generation_mode`, `generation_prompt`, `generation_weights`, `generation_result`, `error_message`, `retry_count`, `generation_duration` 均在 Model 中存在但 ChapterResp 中不暴露。可能这些字段通过 GenerationTaskResp 单独返回。

### TemplateResp 的 target_words/style — **LOW**
Model 无对应字段，可能源自旧版结构设计，或预留用于模板增强。

---

## 10. `__init__.py` 导出完整性

### Models `__init__.py` — **完整** ✓
21 个模型 + 3 个 Base 类全部导出。

### Schemas `__init__.py` — **缺失** (部分)

#### 未导出但可能被路由使用的 Schema — **HIGH**

| Schema 类 | 所在文件 | 用途 |
|-----------|---------|------|
| `UpdateProfileReq` | auth.py | 更新用户资料（与 setting.py 中的同名类不同） |
| `PasswordResetRequestReq` | auth.py | 密码重置步骤1 |
| `PasswordResetReq` | auth.py | 密码重置步骤2 |
| `LogoutReq` | auth.py | 用户登出 |
| `SubscriptionResp` | subscription.py | 订阅详情响应 |
| `CreateSubscriptionReq` | subscription.py | 创建订阅请求 |
| `CharacterCreate`/`TimelineCreate`/`PlotPromiseCreate`/`WorldCreate` | vault.py | 四库创建请求 |
| `CharacterUpdate`/`TimelineUpdate`/`PlotPromiseUpdate`/`WorldUpdate` | vault.py | 四库更新请求 |
| `TaskCancelResp` | generation.py | 任务取消响应 |
| `VaultSummaryResp`/`VaultSummaryData` | vault.py | 四库总览 |

#### 未导出但可能是内部使用的 Schema — **MEDIUM**

| Schema 类 | 所在文件 | 用途 |
|-----------|---------|------|
| `ChapterConfirmReq` | chapter.py | 章节确认 |
| `ChapterReviseReq` | chapter.py | 章节修订 |
| `AgentInstructionReq` | chapter.py | AI 指令 |
| `RedrawCardsReq` | chapter.py | 重抽卡片 |
| `ProjectListResp` | project.py | 项目列表 |
| `SingleProjectStatsResp` | project.py | 单项目统计 |
| `CardPoolListResp` | card.py | 卡池列表 |
| `HealthAlertItem`/`HealthCheckResp` | health.py | 健康检查 |
| `CreateTemplateReq`/`UpdateTemplateReq`/`TemplateListResp`/`CreateProjectFromTemplateResp` | template.py | 模板管理 |
| `SecretItemUpdate`/`UpdateSecretsByCharacterReq` | secret.py | 秘密批量更新 |

#### 未导出但为内部逻辑使用的 Schema — **LOW**

| Schema 类 | 所在文件 | 用途 |
|-----------|---------|------|
| `CoherenceCheckItem` 等 coherence schemas | coherence.py | 内部连贯性检查 |
| `HealthMonitorReq`/`Phase4ReviewReq`/`Phase4ModeReq`/`ChangePasswordReq`/`UpdateProfileReq` | setting.py | 用户设置 |
| `ApplyPhase4Req`/`RejectReviewReq` | phase4.py | Phase 4 操作 |
| `WeaveSuggestionResp`/`ApplyWeaveReq`/`WeaveAnalysisResp` | weave.py | 编织功能 |

**建议**: 将路由实际使用的 Schema 全部加入 `__init__.py` 的 `__all__` 列表，避免在其他模块中通过直接文件路径导入。

---

## 11. Schema 版本提示/废弃字段

### WorldResp/WorldCreate/WorldUpdate 的 rules 字段 — **MEDIUM**
`rules` 存在于 Schema 但 Model 使用 `constraint` (单个 Text 而非 list)，表明存在 API 版本更迭。旧版可能使用 `rules: list`，新版改为 `constraint: str`。

### WorldResp/WorldCreate/WorldUpdate 的 change_type 字段 — **MEDIUM**
`change_type` 在 Schema 中存在但 Model `VaultWorld` 无此字段。看起来像从 VaultChangelog 混入的字段名。

### SyncGenerateReq — **LOW**
明确标记为 deprecated，建议在当前版本中移除或添加 DeprecationWarning。

---

## 12. Vault Schema UUID 修正

| Schema | id 类型 | 状态 |
|--------|---------|------|
| `CharacterResp.id` | str | **已修正** ✓ |
| `PlotPromiseResp.id` | str | **已修正** ✓ |
| `TimelineResp.id` | str | **已修正** ✓ |
| `WorldResp.id` | str | **已修正** ✓ |

所有 Vault Schema 的 id 字段已从 `int` 修正为 `str`，与 BaseModel 的 `String(36)` UUID PK 一致。**修复已完成**。

---

## 已知问题快速修复指南

### CRITICAL (应立即修复)

1. **IngestJob.project_id 类型错误** — `app/ingest/models.py:22-28`  
   将 `String(36)` 改为 `Integer`，匹配 `projects.id`

2. **SecretResp.id 类型错误** — `app/schemas/secret.py:14`  
   将 `id: int` 改为 `id: str`（或使用 Field）

3. **PlanResp.id 类型错误** — `app/schemas/subscription.py:14`  
   将 `id: int` 改为 `id: str`

4. **Phase4Task/IngestJob 缺少 relationship()** — 添加 `relationship()` 并补充反向关系

### HIGH (计划修复)

5. CardResp.project_id: str → int
6. TimelineResp.project_id: str → int
7. WorldResp.project_id: str → int
8. Phase4TaskResp.project_id: str → int
9. Notification.project_id 添加 index=True
10. UserSubscription.plan_id 添加 index=True
11. UpdateChapterReq.content 添加 max_length
12. Schema `__init__.py` 补充缺失导出

---

## 附录 A: 模型清单

| # | 模型 | 表名 | PK 类型 | TimestampMixin | SoftDeleteMixin |
|---|------|------|---------|----------------|-----------------|
| 1 | User | users | String(36) | ✓ | ✓ |
| 2 | Project | projects | Integer | ✓ | ✓ |
| 3 | Chapter | chapters | String(36) | ✓ | ✓ |
| 4 | DynamicLayer | dynamic_layers | String(36) | ✓ | — |
| 5 | GenerationTask | generation_tasks | Uuid | ✓ | ✓ |
| 6 | CardPool | card_pool | String(36) | ✓ | ✓ |
| 7 | DrawHistory | draw_history | String(36) | ✓ | — |
| 8 | VaultCharacter | vault_characters | String(36) | ✓ | ✓ |
| 9 | VaultTimeline | vault_timeline | String(36) | ✓ | ✓ |
| 10 | VaultPlotPromise | vault_plot_promises | String(36) | ✓ | ✓ |
| 11 | VaultWorld | vault_world | String(36) | ✓ | ✓ |
| 12 | VaultChangelog | vault_changelog | String(36) | ✓ | — |
| 13 | HealthAlert | health_alerts | Integer | ✓ | — |
| 14 | SystemConfig | system_config | String(128) | ✓ | — |
| 15 | Secret | secrets | String(36) | ✓ | ✓ |
| 16 | Notification | notifications | Integer | ✓ | ✓ |
| 17 | Template | templates | String(36) | ✓ | — |
| 18 | Plan | plans | String(36) | ✓ | — |
| 19 | UserSubscription | user_subscriptions | String(36) | ✓ | — |
| 20 | Phase4Task | phase4_tasks | Integer | ✓ | — |
| 21 | IngestJob | ingest_jobs | String(36) | ✓ | — |

## 附录 B: Schema 文件清单

| # | 文件 | 导出类数 | 约束完整性 |
|---|------|---------|-----------|
| 1 | auth.py | 8 | 良好 |
| 2 | project.py | 7 | 良好 |
| 3 | chapter.py | 8 | 良好 |
| 4 | card.py | 4 | 良好 |
| 5 | vault.py | 15 | 良好 |
| 6 | generation.py | 4 | 良好 |
| 7 | health.py | 3 | 良好 |
| 8 | template.py | 5 | 一般 |
| 9 | secret.py | 4 | **差** |
| 10 | notification.py | 1 | 良好 |
| 11 | subscription.py | 3 | 一般 |
| 12 | coherence.py | 5 | 良好 |
| 13 | admin.py | 10 | 良好 |
| 14 | phase4.py | 4 | 一般 |
| 15 | setting.py | 6 | 一般 |
| 16 | weave.py | 3 | 良好 |
| 17 | common.py | 3 | 良好 |
