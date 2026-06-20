# 墨灵项目 DAO 层深度扫描报告 v4

> **扫描日期**: 2026-06-21
> **扫描范围**: `moling-server/app/dao/` — 全部 15 个 DAO 文件（16 个类，2337 行代码）
> **扫描深度**: very thorough — 逐方法审查 10 项检测清单
> **前置报告**: scan-v3-dao.md（软删除专项扫描）

---

## 一、文件清单与架构概览

### 1.1 实际 DAO 文件（与预估的差异）

| 序号 | 文件 | 类 | 行数 | 基类 | 对应模型 |
|------|------|-----|------|------|----------|
| 1 | base_dao.py | BaseDAO[ModelT] | 354 | - | 通用泛型基类 |
| 2 | user_dao.py | UserDAO | 92 | BaseDAO[User] | User (有软删除) |
| 3 | project_dao.py | ProjectDAO | 134 | BaseDAO[Project] | Project (有软删除) |
| 4 | chapter_dao.py | ChapterDAO | 118 | BaseDAO[Chapter] | Chapter (有软删除) |
| 5 | vault_dao.py | VaultCharacterDAO | 392 | BaseDAO[VaultCharacter] | VaultCharacter (有软删除) |
| | | VaultTimelineDAO | | BaseDAO[VaultTimeline] | VaultTimeline (有软删除) |
| | | VaultPlotPromiseDAO | | BaseDAO[VaultPlotPromise] | VaultPlotPromise (有软删除) |
| | | VaultWorldDAO | | BaseDAO[VaultWorld] | VaultWorld (有软删除) |
| | | VaultDAO (Facade) | | - | 组合以上4个DAO |
| 6 | card_dao.py | CardDAO | 282 | BaseDAO[CardPool] | CardPool (有软删除), DrawHistory |
| 7 | dynamic_layer_dao.py | DynamicLayerDAO | 106 | BaseDAO[DynamicLayer] | DynamicLayer (无软删除) |
| 8 | secret_dao.py | SecretDAO | 148 | BaseDAO[Secret] | Secret (有软删除) |
| 9 | health_alert_dao.py | HealthAlertDAO | 122 | BaseDAO[HealthAlert] | HealthAlert (无软删除) |
| 10 | generation_dao.py | GenerationDAO | 103 | BaseDAO[GenerationTask] | GenerationTask (有软删除) |
| 11 | notification_dao.py | NotificationDAO | 109 | BaseDAO[Notification] | Notification (有软删除) |
| 12 | template_dao.py | TemplateDAO | 49 | BaseDAO[Template] | Template (无软删除) |
| 13 | phase4_dao.py | Phase4DAO | 91 | BaseDAO[Phase4Task] | Phase4Task (无软删除) |
| 14 | subscription_dao.py | PlanDAO + UserSubscriptionDAO | 92 | BaseDAO[Plan] / BaseDAO[UserSubscription] | Plan, UserSubscription (无软删除) |
| 15 | system_config_dao.py | SystemConfigDAO | 69 | **独立类** | SystemConfig (无软删除) |

**与 team-lead 预估的差异**：
- `character_dao` / `plot_dao` / `world_dao` → 实际是 `vault_dao.py` 内的 `VaultCharacterDAO` / `VaultPlotPromiseDAO` / `VaultWorldDAO`，不存在独立文件
- `invoice_dao` → 项目中**不存在**，无此 DAO
- 实际比预估多出: `generation_dao`, `notification_dao`, `template_dao`, `phase4_dao`, `subscription_dao`, `system_config_dao`

### 1.2 模型软删除状态矩阵

| 模型 | SoftDeleteMixin | is_deleted | 说明 |
|------|:---:|:---:|------|
| User | ✅ | ✅ | 用户软删除 |
| Project | ✅ | ✅ | 项目软删除 |
| Chapter | ✅ | ✅ | 章节软删除 |
| VaultCharacter | ✅ | ✅ | 角色库软删除 |
| VaultTimeline | ✅ | ✅ | 时间线软删除 |
| VaultPlotPromise | ✅ | ✅ | 伏笔软删除 |
| VaultWorld | ✅ | ✅ | 世界观软删除 |
| CardPool | ✅ | ✅ | 卡池软删除 |
| Secret | ✅ | ✅ | 秘密矩阵软删除 |
| GenerationTask | ✅ | ✅ | 生成任务软删除 |
| Notification | ✅ | ✅ | 通知软删除 |
| DynamicLayer | ❌ | ❌ | 无软删除 |
| HealthAlert | ❌ | ❌ | 无软删除 |
| Phase4Task | ❌ | ❌ | 无软删除 |
| Template | ❌ | ❌ | 无软删除 |
| Plan | ❌ | ❌ | 订阅计划 |
| UserSubscription | ❌ | ❌ | 用户订阅 |
| SystemConfig | ❌ | ❌ | KV配置 |
| DrawHistory | ❌ | ❌ | 抽卡记录 |

### 1.3 BaseDAO 契约（8 个标准方法 + 辅助方法）

| 方法 | 签名 |
|------|------|
| `get(id, *, include_deleted)` | 按主键获取 |
| `get_sync(db, id)` | 同步版 get |
| `get_multi(*, skip, limit, filters, order_by, descending, include_deleted)` | offset/limit 分页 |
| `list_cursor(*, cursor, cursor_field, limit, filters, order, include_deleted)` | 游标分页 |
| `count(filters, *, include_deleted)` | 计数 |
| `create(obj_in)` | 创建（flush，不 commit） |
| `update(db_obj, obj_in)` | 更新（flush，不 commit） |
| `delete(id, *, soft)` | 软/硬删除 |
| `restore(id)` | 恢复软删除 |
| `_apply_filters(stmt, filters)` | 过滤条件构建器 |

**契约规则**：
1. 禁止 DAO 内部 commit() — 事务由调用方管理
2. 禁止 DAO 内部创建 Session/Engine — 接受 db 参数
3. **所有 DAO 方法必须有 try/except 并记录日志**
4. 子类使用模块级单例 (xxx_dao = XxxDAO())

---

## 二、10 项检测结果

### 2.1 SQL 注入风险 — ✅ 无风险

| 检查项 | 结果 |
|--------|------|
| raw SQL 拼接 | **未发现** — 所有查询使用 SQLAlchemy ORM (select/where/func) |
| text() 未参数化 | **未发现** — 全代码库无 `text()` 调用 |
| _apply_filters 动态字段 | **安全** — 使用 `getattr()` 获取 Column 对象后通过 `==` 操作符，SQLAlchemy 自动参数化 |
| contains() 模糊匹配 | **安全** — `VaultPlotPromiseDAO.find_by_description()` 和 `find_by_type_and_char()` 使用 `.contains()` 方法，SQLAlchemy 自动参数化 |
| in_() 批量 ID | **安全** — 多个 DAO 使用 `.in_(list)`，参数化执行 |

**结论**: 零 SQL 注入风险。全部使用 SQLAlchemy ORM 参数化查询。

---

### 2.2 N+1 查询 — ⚠️ 1 处可优化

| 严重度 | 文件:行号 | 方法 | 问题 |
|--------|-----------|------|------|
| 🟡 LOW | `project_dao.py:94-134` | `get_stats()` | **4 次独立查询**（total count + active count + draft count + total words），可合并为 1 个 GROUP BY 查询 |

```python
# 当前实现 — 4 次 db.execute()
total = await self.count_by_user(db, user_id)        # 查询 1
active_result = await db.execute(active_stmt)         # 查询 2
draft_result = await db.execute(draft_stmt)           # 查询 3
words_result = await db.execute(words_stmt)           # 查询 4
```

**建议优化**: 使用单次 `select(func.count(), ...).group_by(Project.status)` + 条件聚合。

**其他 DAO 均无循环内查询**。`dynamic_layer_dao.get_latest_by_project()` 调用 `get_recent_by_project(limit=1)` 仅发 1 次查询，正确。

---

### 2.3 事务边界 — ✅ 全部合规

| 检查项 | 结果 |
|--------|------|
| DAO 方法内调用 commit() | **零发现** — 全部 15 个 DAO 文件扫描完毕 |
| 使用 flush() | ✅ base_dao 的 create/update/delete/restore 在所有变更后调用 flush() |
| 子类 flush() 使用 | ✅ card_dao, secret_dao, health_alert_dao, notification_dao, system_config_dao 中的自定义方法正确使用 flush() |

| DAO | flush 位置 | 是否正确 |
|-----|-----------|:---:|
| base_dao.create() | `db.add()` → `db.flush()` → `db.refresh()` | ✅ |
| base_dao.update() | `setattr` → `db.flush()` → `db.refresh()` | ✅ |
| base_dao.delete() | `db.delete()` or `setattr` → `db.flush()` | ✅ |
| base_dao.restore() | `setattr` → `db.flush()` | ✅ |
| card_dao.create_draw_record() | `db.add()` → `db.flush()` → `db.refresh()` | ✅ |
| card_dao.batch_update_is_active_sync() | `db.execute()` → `db.flush()` | ✅ |
| secret_dao.update_by_id() | `setattr` → `db.flush()` → `db.refresh()` | ✅ |
| secret_dao.batch_create() | `db.add_all()` → `db.flush()` | ✅ |
| secret_dao.batch_update() | 循环 `db.execute(update)` → 最后 `db.flush()` | ✅ |
| health_alert_dao.create_alert() | `db.add()` → `db.flush()` → `db.refresh()` | ✅ |
| health_alert_dao.resolve_alerts_by_rule() | `db.execute()` → `db.flush()` | ✅ |
| health_alert_dao.update_checked_at() | `db.execute()` → `db.flush()` | ✅ |
| notification_dao.delete_by_user() | `db.delete()` → `db.flush()` | ✅ |
| system_config_dao.upsert() | `db.add()` or `setattr` → `db.flush()` | ✅ |

**结论**: 铁律严格执行 — DAO 层零 commit()，事务控制权完全在 Service/Router 层。

---

### 2.4 软删除遗漏 — ✅ 全覆盖

> **重要修正**: v3 报告中标记为"遗漏"的 DynamicLayerDAO、HealthAlertDAO、Phase4DAO、TemplateDAO 实际对应的模型 **不含 SoftDeleteMixin**，因此不需要 is_deleted 过滤。

**有软删除模型 × DAO 检查全覆盖矩阵**:

| 模型 | DAO | 查询方法数 | is_deleted 过滤 | 状态 |
|------|-----|:---:|:---:|:---:|
| User | UserDAO | 6 | ✅ 全部 | 通过 |
| Project | ProjectDAO | 8 (含 get_stats 内部) | ✅ 全部 | 通过 |
| Chapter | ChapterDAO | 6 | ✅ 全部 | 通过 |
| VaultCharacter | VaultCharacterDAO | 5 | ✅ 全部 (含委托 base) | 通过 |
| VaultTimeline | VaultTimelineDAO | 2 | ✅ 全部 | 通过 |
| VaultPlotPromise | VaultPlotPromiseDAO | 7 | ✅ 全部 | 通过 |
| VaultWorld | VaultWorldDAO | 4 | ✅ 全部 | 通过 |
| CardPool | CardDAO (CardPool部分) | 8 (含 sync) | ✅ 全部 | 通过 |
| DrawHistory | CardDAO (DrawHistory部分) | 3 | N/A (无软删除) | 通过 |
| Secret | SecretDAO | 7 | ✅ 全部查询; batch_update 按 id ✅ | 通过 |
| GenerationTask | GenerationDAO | 5 | ✅ 全部 | 通过 |
| Notification | NotificationDAO | 5 | ✅ get/count 过滤; update 按 id ✅ | 通过 |

**`include_deleted` 参数**: 在 base_dao 的 `get()`, `get_multi()`, `count()`, `list_cursor()` 中均作为可选参数生效。子类通过委托基类方法继承此能力。

**结论**: 所有有软删除的模型在 DAO 查询中均正确过滤 `is_deleted=False`。无遗漏。

---

### 2.5 Limit 钳制 — ⚠️ 5 处高危，10 处中危

#### 2.5.1 基类钳制

| 方法 | 钳制逻辑 | 上限 |
|------|----------|:---:|
| `base_dao.get_multi()` | `limit = min(limit, DEFAULT_MAX_LIMIT)` | 500 |
| `base_dao.list_cursor()` | `limit = min(max(limit, 1), _CURSOR_MAX_LIMIT)` | 200 |

#### 2.5.2 子类自定义查询 — 未钳制清单

**🔴 高危 — 无任何 limit**:

| 严重度 | 文件:行号 | 方法 | 风险 |
|--------|-----------|------|------|
| 🔴 CRITICAL | `secret_dao.py:30-42` | `list_by_project()` | **无 limit** — 项目秘密可能很多 |
| 🔴 CRITICAL | `secret_dao.py:44-61` | `list_by_secrecy_level()` | **无 limit** — 同级别秘密可能很多 |
| 🔴 CRITICAL | `health_alert_dao.py:23-35` | `list_by_project()` | **无 limit** — 告警历史可累积 |
| 🔴 CRITICAL | `health_alert_dao.py:37-52` | `list_active_by_project()` | **无 limit** — 活跃告警可能很多 |
| 🔴 CRITICAL | `health_alert_dao.py:54-70` | `list_by_severity()` | **无 limit** — 同严重度告警可能很多 |

**🟡 中危 — 有 limit 但未钳制（可能 > 500）**:

| 严重度 | 文件:行号 | 方法 | 默认 limit | 调用方可传值 |
|--------|-----------|------|:---:|:---:|
| 🟡 MEDIUM | `project_dao.py:20-36` | `get_by_user()` | 100 | ✅ 可传任意值 |
| 🟡 MEDIUM | `project_dao.py:38-54` | `get_all_active()` | 200 | ❌ 固定 |
| 🟡 MEDIUM | `project_dao.py:56-78` | `get_recently_active()` | 200 | ❌ 固定 |
| 🟡 MEDIUM | `chapter_dao.py:20-36` | `get_by_project()` | 100 | ✅ 可传任意值 |
| 🟡 MEDIUM | `card_dao.py:24-49` | `get_active_cards()` | 20 | ❌ 固定 |
| 🟡 MEDIUM | `card_dao.py:51-68` | `get_by_rarity()` | **无** | **无 limit** |
| 🟡 MEDIUM | `card_dao.py:72-90` | `get_draw_history()` | 50 | ✅ 可传任意值 |
| 🟡 MEDIUM | `generation_dao.py:24-40` | `get_by_project()` | 50 | ✅ 可传任意值 |
| 🟡 MEDIUM | `generation_dao.py:61-75` | `get_by_status()` | 20 | ✅ 可传任意值 |
| 🟡 MEDIUM | `dynamic_layer_dao.py:59-102` | `get_health_check_history()` | 20 | ❌ 固定 |

**结论**: 基类钳制机制完善，但**子类自定义查询完全绕过了钳制**。SecretDAO 和 HealthAlertDAO 中的无限制查询是最大的风险点。

**修复建议**: 所有子类的自定义 list/get_multi 型方法应在查询前执行 `limit = min(limit, DEFAULT_MAX_LIMIT)`。

---

### 2.6 游标分页 — ⚠️ 已实现但未被使用

#### 2.6.1 BaseDAO 实现分析

`base_dao.py:291-354` 的 `list_cursor()` 实现：

| 特性 | 实现 | 正确性 |
|------|------|:---:|
| limit 钳制 | `limit = min(max(limit, 1), 200)` | ✅ |
| 多取一条判断下一页 | `limit + 1`，然后 `items = rows[:limit]` | ✅ |
| next_cursor 提取 | `getattr(items[-1], cursor_field)` | ✅ |
| 降序游标 | `column < cursor` (desc) | ✅ |
| 升序游标 | `column > cursor` (asc) | ✅ |
| 软删除过滤 | `include_deleted` 参数生效 | ✅ |
| 错误处理 | `try/except (SQLAlchemyError, ValueError)` | ✅ |

#### 2.6.2 复合排序限制

```python
# 当前实现 — 仅支持单字段排序
stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
```

**不支持复合排序场景**（如 `order_by(created_at DESC, id ASC)`）。当 cursor_field 是第一个排序字段时，复合排序的次要字段会导致结果不准确。

#### 2.6.3 使用率

| 状态 | DAO |
|------|-----|
| 基类实现 | BaseDAO ✅ |
| 子类使用 | **0 个 DAO** 使用 list_cursor |
| offset 分页仍在使用 | 全部子类使用 skip/limit |

**结论**: 游标分页在基类中正确实现，但**无任何子类使用**。所有分页仍使用传统的 offset/limit 模式。这不是 bug，但可能需要考虑是否将其引入 Service 层。

---

### 2.7 异常处理 — 🔴 违规严重（契约违反）

> **DAOS 契约**: "所有 DAO 方法必须有 try/except 并记录日志"

#### 2.7.1 覆盖率统计

| 层级 | 方法总数 | 有 try/except | 缺失 | 覆盖率 |
|------|:---:|:---:|:---:|:---:|
| BaseDAO 基类 | 9 | 9 | 0 | 100% |
| 子类自定义方法 | ~50 | 0 | ~50 | **0%** |

#### 2.7.2 缺失异常处理的方法清单

```
user_dao.py:
  get_by_email(), get_by_username(), get_by_reset_token()
  get_by_email_sync(), get_by_username_sync(), create_sync()

project_dao.py:
  get_by_user(), get_all_active(), get_recently_active()
  count_by_user(), get_stats()

chapter_dao.py:
  get_by_project(), get_by_number(), get_current()
  get_max_chapter_number(), get_content(), count_by_project()

vault_dao.py (VaultCharacterDAO):
  get_by_project(), count_by_project(), count_by_status()
  get_by_ids(), get_by_name()

vault_dao.py (VaultTimelineDAO):
  get_by_project(), count_by_project()

vault_dao.py (VaultPlotPromiseDAO):
  get_by_project(), count_by_project(), count_by_status()
  get_by_ids(), find_by_description(), find_by_type_and_char()

vault_dao.py (VaultWorldDAO):
  get_by_project(), count_by_project(), get_by_ids(), get_by_term()

card_dao.py:
  get_active_cards(), get_by_rarity(), get_draw_history()
  get_latest_draw(), create_draw_record(), list_active_by_project()
  get_by_ids(), get_by_ids_any()
  list_active_by_project_sync(), get_active_cards_sync()
  list_by_project_sync(), get_by_ids_sync()
  batch_update_is_active_sync()

dynamic_layer_dao.py:
  get_by_chapter(), get_recent_by_project()
  get_latest_by_project(), get_health_check_history()

secret_dao.py:
  list_by_project(), list_by_secrecy_level()
  update_by_id(), batch_create(), batch_update()
  calculate_debt_by_project(), count_by_project()

health_alert_dao.py:
  list_by_project(), list_active_by_project(), list_by_severity()
  create_alert(), resolve_alerts_by_rule(), update_checked_at()

generation_dao.py:
  get_by_project(), get_by_chapter(), get_by_status()
  get_by_chapter_and_type(), get_by_id()

notification_dao.py:
  get_by_user(), count_by_user(), mark_as_read()
  mark_all_as_read(), delete_by_user()

template_dao.py:
  get_by_genre(), count_by_genre()

phase4_dao.py:
  get_by_nonce(), get_by_chapter(), get_by_project()
  list_by_status(), count_by_status()

subscription_dao.py (PlanDAO):
  get_active_plans()

subscription_dao.py (UserSubscriptionDAO):
  get_by_user(), get_by_user_and_plan(), list_by_user()

system_config_dao.py:
  get_by_key(), get_by_keys(), upsert(), upsert_batch()
```

**结论**: 🔴 这是本次扫描最严重的发现。**全部 15 个子类 DAO 的 ~50 个自定义方法均缺少 try/except**，直接违反 DAO 层契约。当 SQLAlchemy 抛出异常时，异常将直接传播到 Service/Router 层，失去 DAO 层的上下文日志。

---

### 2.8 类型安全 — ⚠️ 轻度问题

| 检查项 | 状态 |
|--------|:---:|
| 泛型传递 | ✅ BaseDAO[User], BaseDAO[Project] 等正确 |
| 返回类型注解 | ✅ 主要方法均有完整注解 |
| Optional 使用 | ✅ 单条返回使用 `Optional[X]` 或 `X \| None` |
| list/dict 泛型 | ✅ `list[ModelT]`, `dict[str, str]` 等 |

**2 处轻微问题**:

| 文件:行号 | 方法 | 问题 | 建议 |
|-----------|------|------|------|
| `project_dao.py:94` | `get_stats()` | 返回 `dict` 无 TypedDict | 定义 `ProjectStats` TypedDict |
| `dynamic_layer_dao.py:59` | `get_health_check_history()` | 返回 `list[dict]` 无 TypedDict | 定义 `HealthCheckHistoryItem` TypedDict |

---

### 2.9 事务效率 — ⚠️ 3 处优化机会

| 严重度 | 文件:行号 | 方法 | 问题 | 建议 |
|--------|-----------|------|------|------|
| 🟡 MEDIUM | `secret_dao.py:95-115` | `batch_update()` | 循环内逐条 `UPDATE` | 使用单次批量 UPDATE（对每个 status 值用一条语句） |
| 🟢 LOW | `system_config_dao.py:61-69` | `upsert_batch()` | 循环调用 `upsert()` | data 量小时可接受；大数据量时考虑 `INSERT ... ON DUPLICATE KEY UPDATE` |
| 🟢 LOW | `health_alert_dao.py:74-84` | `create_alert()` | 重复 `base_dao.create()` 逻辑 | 委托给 `self.create(db, obj_in)` |

**其他效率分析**:
- `card_dao.create_draw_record()` 重复 create 逻辑但参数类型不同（dict vs schema），可保留
- `secret_dao.batch_create()` 使用 `db.add_all()` — 正确使用批量添加 ✅
- `card_dao.batch_update_is_active_sync()` 使用单条 `update()` — 正确 ✅
- `health_alert_dao.resolve_alerts_by_rule()` 使用单条 `update()` — 正确 ✅

---

### 2.10 方法完整性 — BaseDAO 契约对照

| BaseDAO 契约方法 | 基类实现 | 子类继承 | 子类重写/扩充 |
|------------------|:---:|:---:|------|
| `get()` | ✅ | ✅ | user_dao 等通过 get_by_* 委托 ✅ |
| `get_sync()` | ✅ | ✅ | 少数子类实现特定 sync 方法 |
| `get_multi()` | ✅ | ✅ | vault 子 DAO 通过 filters 参数使用 |
| `list_cursor()` | ✅ | ✅ | **无子类使用** |
| `count()` | ✅ | ✅ | 广泛通过委托使用 |
| `create()` | ✅ | ✅ | health_alert 重复实现而未委托 ⚠️ |
| `update()` | ✅ | ✅ | secret_dao 实现了 update_by_id |
| `delete()` | ✅ | ✅ | notification_dao 实现了 delete_by_user |
| `restore()` | ✅ | ✅ | 子类不需重写 |
| `batch_create()` | ❌ 空 | - | **仅 SecretDAO 实现** |

**SystemConfigDAO 独立实现**: 此 DAO 未继承 BaseDAO（因主键是 `key` 而非 `id`），设计合理。但缺少完整的 CRUD 方法（无 delete、无 count），需要 Service 层补充或在此实现。

---

## 三、严重度汇总

| # | 检测项 | 最高严重度 | 问题数 |
|---|--------|:---:|:---:|
| 1 | SQL 注入风险 | 🟢 PASS | 0 |
| 2 | N+1 查询 | 🟡 LOW | 1 |
| 3 | 事务边界 (commit) | 🟢 PASS | 0 |
| 4 | 软删除遗漏 | 🟢 PASS | 0 (v3 的 24 处已修复) |
| 5 | Limit 钳制 | 🔴 CRITICAL | 5 (高危) + 10 (中危) |
| 6 | 游标分页 | 🟡 INFO | 1 (未使用) + 1 (复合排序限制) |
| 7 | 异常处理 | 🔴 CRITICAL | ~50 (全部子类方法缺失) |
| 8 | 类型安全 | 🟢 PASS | 2 (轻微) |
| 9 | 事务效率 | 🟡 LOW | 3 |
| 10 | 方法完整性 | 🟡 INFO | 2 |

---

## 四、优先修复建议

### P0 — 立即修复

1. **异常处理补全** (检查项 #7)
   - 为所有 ~50 个子类自定义方法添加 `try/except SQLAlchemyError`
   - 使用 `logger.error(f"DAO {method_name} failed: {e}")` 记录上下文
   - 统一抛出 `AppError(ErrorCode.INTERNAL_ERROR, detail=str(e))`

2. **Limit 钳制** (检查项 #5)
   - `secret_dao.list_by_project()` + `list_by_secrecy_level()` — 添加 limit 参数及钳制
   - `health_alert_dao.list_by_project()` + `list_active_by_project()` + `list_by_severity()` — 添加 limit 参数及钳制
   - `card_dao.get_by_rarity()` — 添加 limit 参数及钳制
   - 所有子类 list 方法统一执行 `limit = min(limit, DEFAULT_MAX_LIMIT)`

### P1 — 建议修复

3. **get_stats() 查询合并** (检查项 #2)
   - 项目统计 4 次查询合并为 1 次 GROUP BY

4. **SecretDAO batch_update 优化** (检查项 #9)
   - 循环内逐条 UPDATE 改为按 status 分组的批量 UPDATE

### P2 — 可选优化

5. **游标分页推广** (检查项 #6)
   - 在 Service 层推广 cursor 分页替代 offset 分页

6. **TypedDict 补充** (检查项 #8)
   - `get_stats()` 和 `get_health_check_history()` 返回类型精确化

---

## 五、与 v3 报告的差异与进展

| 项目 | v3 状态 | v4 状态 | 说明 |
|------|---------|---------|------|
| 软删除实现数 | 6 DAO / 24 处 | 11 模型 (全部) | 已全部覆盖 |
| 标注为"遗漏"的 DAO | DynamicLayer, HealthAlert, Phase4, Template | 确认无误 | 这些模型不含 SoftDeleteMixin |
| BaseDAO 契约定义 | 8 方法 | 9 + 辅助方法 | 新增 restore, _apply_filters |
| 游标分页 | 已实现 | 已实现但未使用 | 新增发现 |

---

## 六、完整 DAO 方法清单（用于审计跟踪）

```
BaseDAO         (9): get, get_sync, get_multi, list_cursor, count,
                      create, update, delete, restore
UserDAO         (6): get_by_email, get_by_username, get_by_reset_token,
                      get_by_email_sync, get_by_username_sync, create_sync
ProjectDAO      (5): get_by_user, get_all_active, get_recently_active,
                      count_by_user, get_stats
ChapterDAO      (6): get_by_project, get_by_number, get_current,
                      get_max_chapter_number, get_content, count_by_project
VaultCharacter  (5): get_by_project, count_by_project, count_by_status,
                      get_by_ids, get_by_name
VaultTimeline   (2): get_by_project, count_by_project
VaultPlotPromise(7): get_by_project, count_by_project, count_by_status,
                      get_by_ids, find_by_description, find_by_type_and_char
VaultWorld      (4): get_by_project, count_by_project, get_by_ids, get_by_term
VaultDAO facade (28): 委托方法
CardDAO         (13): get_active_cards, get_by_rarity, get_draw_history,
                      get_latest_draw, create_draw_record, list_active_by_project,
                      get_by_ids, get_by_ids_any,
                      list_active_by_project_sync, get_active_cards_sync,
                      list_by_project_sync, get_by_ids_sync,
                      batch_update_is_active_sync
DynamicLayer    (4): get_by_chapter, get_recent_by_project, get_latest_by_project,
                      get_health_check_history
SecretDAO       (7): get_by_id→委托, list_by_project, list_by_secrecy_level,
                      update_by_id, batch_create, batch_update,
                      calculate_debt_by_project, count_by_project
HealthAlert     (6): list_by_project, list_active_by_project, list_by_severity,
                      create_alert, resolve_alerts_by_rule, update_checked_at
GenerationDAO   (5): get_by_project, get_by_chapter, get_by_status,
                      get_by_chapter_and_type, get_by_id→委托
NotificationDAO (5): get_by_user, count_by_user, mark_as_read,
                      mark_all_as_read, delete_by_user
TemplateDAO     (2): get_by_genre, count_by_genre
Phase4DAO       (5): get_by_nonce, get_by_chapter, get_by_project,
                      list_by_status, count_by_status→委托
PlanDAO         (1): get_active_plans
UserSubscripDAO (3): get_by_user, get_by_user_and_plan, list_by_user
SystemConfigDAO (4): get_by_key, get_by_keys, upsert, upsert_batch
───────────────────────────────────────────────────────────────
总计自定义方法: ~115 (含 sync 版本和委托方法)
```
