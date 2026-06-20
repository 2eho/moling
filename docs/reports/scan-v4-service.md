# Moling Service 层深度扫描报告

**扫描日期**: 2026-06-21
**扫描范围**: `app/service/` — 26 个 Python 文件，总约 ~17,000 行
**扫描深度**: very thorough（逐方法审查）
**检测清单**: 12 项

---

## 总体评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 1. 事务管理 | 🟡 需关注 | Service 层普遍直接 commit，缺少统一事务边界 |
| 2. 直接 SQL 绕过 DAO | ✅ 通过 | 未发现 select()/session.execute() 穿透 |
| 3. IDA 依赖 | 🟡 模式成立 | 全量直接 import DAO 实例，但符合项目单例模式 |
| 4. 异常处理 | 🟡 个别问题 | 主要使用 AppError，少数服务存在不一致 |
| 5. 幂等性 | 🟡 部分覆盖 | Phase4 有三层防护，但卡牌/章节等缺少 |
| 6. 循环依赖 | ✅ 已解决 | ServiceRegistry 打破循环，无直接循环 import |
| 7. 内存泄漏 | ✅ 无发现 | 缓存有 LRU 驱逐，大对象使用合理 |
| 8. 并发安全 | 🟡 部分保护 | Phase4 有分布式锁，其余服务无保护 |
| 9. N+1 查询 | 🔴 发现问题 | project_service.list_projects 存在 N+1 |
| 10. LLM 调用 | 🔴 需改进 | 无超时/重试，多处缺降级策略 |
| 11. 日志 | ✅ 基本合格 | 结构化日志，关键路径可追踪 |
| 12. 资源清理 | ✅ 基本合格 | 文件上传后清理，无明显泄漏 |

---

## 逐文件审查

### 1. `__init__.py`
- 导出 26 个单例实例
- 结构清晰，无问题

### 2. `algorithm_service.py` (Step 1-6 编排)

**事务**: ✅ 不直接操作 DB，仅编排子服务

**IDA**: ⚠️ 直接 `from app.dao import vault_dao`（line 16），且第 91 行有重复 `from app.service.vault_filter import vault_filter_service`

**幂等**: ❌ 各 step 方法无幂等保护

**并发**: ✅ 纯计算，无共享状态

**日志**: ✅ step 操作有日志

**建议**: 移除第 91 行的重复 import

### 3. `auth_service.py`

**事务**: 🔴 5 处直接 `await db.commit()`（lines 183, 220, 251, 299, 421, 516）。auth 操作独立提交正确，但当与其他操作组合时缺少 savepoint 保护

**直接 SQL**: ❌ `from app.auth.blacklist import add_to_blacklist`（lines 417, 444）— 直接调用黑名单模块而非通过 service 层

**异常**: ✅ 使用 AuthError, ConflictError, NotFoundError

**幂等**: ❌ register/login/refresh_tokens 无防重提交

**并发**: ⚠️ `_auth_service_instance` 全局变量（line 88）— 无锁保护但仅在模块加载时赋值

**日志**: ⚠️ 缺少关键操作结构化日志（登录/注册仅返回值，无 log）

### 4. `card_pool_service.py`

**事务**: ⚠️ `retire_cards` 直接 `await db.commit()`（line 133）

**异常**: ✅ 无异常场景

**日志**: ✅ `check_freshness`/`retire_cards` 有 info 日志

**幂等**: ❌ retire_cards 可重复执行

### 5. `card_retire_service.py`

**事务**: ✅ 使用 `await db.flush()`（line 159），由调用方 commit

**异常**: ✅ `check_and_retire` 错误降级返回 `RetireResult()`（line 182）

**日志**: ✅ 详细的分步日志和错误日志

**并发**: ⚠️ 无锁保护，多次调用可能产生重复退役

### 6. `card_service.py`

**事务**: 🔴 4 处 `await db.commit()`（lines 212, 253, 280, 426）

**异常**: ❌ 使用 `PermissionError` 而非 `AppError`（lines 124, 352）⚠️ **会绕过全局异常处理器**

**幂等**: ❌ draw_cards/redraw_cards 无幂等保护，重复调用产生新记录

**并发**: ⚠️ 多用户并发抽卡时可能产生竞态（抽到同一张卡的边界情况）

**日志**: ⚠️ 缺少关键操作日志（创建卡牌、退役卡牌）

### 7. `chapter_service.py`

**事务**: 🔴 6 处 `await db.commit()`（lines 51, 120, 149, 175, 228, 396）

**异常**: ✅ 使用 NotFoundError，但 ❌ `PermissionError`（line 166, 384）

**幂等**: ✅ `confirm_chapter` 有 nonce 幂等保护（lines 212-226）

**并发**: ⚠️ confirm_chapter 创建 Phase4Task 后异步触发 — 如 Celery 不可用则同步执行，可能阻塞

**日志**: ✅ 关键步骤有日志

### 8. `coherence_service.py`

**事务**: ✅ 不直接操作 DB（query only）

**LLM**: 🔴 3 处 `json.loads(response)` 无 try/except（lines 293, 409, 548）— LLM 返回非 JSON 时崩溃

**LLM**: 🔴 无超时/重试配置

**异常**: ✅ 顶层 `validate_post_generation` 有异常兜底

**日志**: ✅ 详细的检查结果日志

**循环依赖**: ✅ 使用 ServiceRegistry 注册（line 627）

### 9. `conflict_detection.py`

**事务**: ✅ 不直接写 DB

**LLM**: ⚠️ `_parse_llm_response` 有健壮的 JSON 解析（line 492-521）

**LLM**: 🔴 `json.loads(response)` 在 `_llm_fallback_for_conflicts` 首次尝试可能失败但后面有恢复

**异常**: ✅ `detect_conflicts` 顶层有异常兜底（line 230-244）

**日志**: ✅ 详细的分步骤日志

### 10. `direction_scoring.py`

**事务**: ✅ 纯计算，无 DB 操作

**LLM**: ⚠️ `_llm_fallback` 有异常兜底（line 521-526），但 ❌ `json.loads(content[json_start:json_end])` 可能崩溃（line 515）

**异常**: ✅ `_llm_fallback` 双重 except

**日志**: ✅ 有信息级别日志

### 11. `generation_service.py`

**事务**: ✅ 使用 `async with db.begin_nested() as savepoint:` + `savepoint.rollback()`（lines 143, 348）— **优秀**

**异常**: ✅ 使用 AppError

**幂等**: ✅ 支持预分配 task_id（line 79）

**并发**: ⚠️ `asyncio.create_task(phase4_scheduler.schedule_phase4(...))`（line 320）— 创建后台任务但可能被垃圾回收导致静默丢失

**LLM**: 🔴 4 个 LLM 调用（steps 8, 9, 11, _adjust_content）无超时配置

**LLM**: ✅ step8有降级返回默认值（line 404），step9 抛出 AppError（line 439）

**日志**: ✅ 每个 step 都有日志

**N+1**: ✅ 单次查询

### 12. `health_monitor.py`

**事务**: ✅ 仅读/计算，不直接写 DB

**异常**: 🔴 `check_health` 使用 `except Exception: raise`（line 110-112）— 捕获后重新抛出，未做降级

**DAO 延迟导入**: ✅ `from app.dao import vault_dao as _vault_dao`（line 385）等 — 避免模块加载时的循环问题

**日志**: ✅ 详细日志

### 13. `health_service.py`

**事务**: 🔴 `await db.commit()`（line 94）在创建 HealthAlert 后

**LLM**: 🔴 无超时/重试

**异常**: ✅ R1/R2/R3 有独立异常兜底

**JSON**: ⚠️ `json.loads(response_text)` 有 try/except（line 157-181）

### 14. `import_service.py`

**事务**: 🔴 `await db.commit()`（line 357）

**内存**: ⚠️ 大文件可能全局加载到内存（无流式处理）

**资源清理**: ✅ 导入后删除临时文件（line 361-364）

**异常**: ✅ 使用 ValidationError, NotFoundError

**日志**: ✅ 有导入进度日志

### 15. `merge_service.py`

**事务**: ✅ 不直接 commit，由调用方控制

**异常**: ✅ 使用 ValueError（合理，属于假设违反）

**置信度系统**: ✅ P1-4 置信度降级策略完善（ConfidenceLevel 四级）

**日志**: ✅ 有变更日志

**重复代码**: ⚠️ `_calc_edit_distance` 与 `phase4_scheduler._levenshtein` 重复实现

### 16. `notification_service.py`

**事务**: 🔴 `await db.commit()`（lines 95, 117）

**异常**: ✅ 使用 NotFoundError

### 17. `phase4_scheduler.py`

**幂等**: ✅ 三层幂等保护（内存 + DB + UNIQUE 约束）— **最佳实践**

**并发**: ✅ 分布式锁 + asyncio.Lock（lines 102, 397-466, 411-466）

**事务**: ✅ 由调用方管理

**日志**: ✅ 详细的状态流转日志

**内存**: ⚠️ LRU 缓存 1000 条（line 63）合理，但 `_nonce_set` 无限增长无清理机制

**LLM**: ⚠️ `_llm_judge` 当前是模拟实现（line 949-1011），依赖关键词匹配

### 18. `phase4_service.py`

**事务**: ✅ 使用 savepoint + rollback + 主事务 commit 三步模式（lines 1148-1272）— **优秀**

**幂等**: ✅ `confirm_storage` 有 nonce 检查（line 145）

**LLM**: 🔴 无超时配置（lines 459, 1417）

**LLM**: ✅ `_call_extraction_llm` 有降级策略（line 1427-1438），`_analyze_chapter_content` 有兜底（line 488-495）

**重复代码**: ⚠️ `_calc_edit_distance`（line 1521）与 merge_service 重复

**N+1**: ⚠️ `_merge_plot_promises` 对每个 action 循环内查询（lines 1876, 1913, 1949）

**日志**: ✅ 详细的 step 日志

### 19. `prompt_service.py`

**事务**: ✅ 无 DB 操作，纯字符串处理

**异常**: ✅ 无异常场景

**日志**: ⚠️ 无日志（纯工具类，可接受）

### 20. `secret_service.py`

**事务**: ⚠️ `await db.flush()`（lines 139, 188, 224, 299）— 由调用方 commit

**LLM**: 🔴 无超时/重试

**JSON**: ⚠️ `json.loads(json_str)` 有 try/except（line 121）

**日志**: ✅ 操作有日志记录

### 21. `setting_service.py`

**事务**: 🔴 `await db.commit()`（lines 76, 113, 175）

**异常**: ✅ 使用 AuthError, NotFoundError, ValidationError

**安全**: ✅ 密码修改需验证旧密码（line 98）

### 22. `template_service.py`

**事务**: 🔴 `await db.commit()`（lines 70, 91, 111, 153）

**异常**: ✅ 使用 NotFoundError

**注意**: ❌ `error_code=ErrorCode.VAULT_ENTRY_NOT_FOUND`（lines 57, 86, 108, 127）— 语义不匹配，应使用 `TEMPLATE_NOT_FOUND`

### 23. `validation_service.py`

**事务**: ✅ 不直接操作 DB

**日志**: ✅ 有结果日志

### 24. `vault_filter.py`

**设计**: ✅ 支持依赖注入 DAO（line 46）— **良好实践**

**分层压缩**: ✅ §3.4 层级压缩实现

**事务**: ✅ 不直接 commit

### 25. `vault_service.py`

**事务**: 🔴 多处 `await db.commit()`（lines 47, 74, 92, etc.）

**异常**: ✅ 使用 NotFoundError

### 26. `weave_service.py`

**LLM**: 🔴 无超时/重试（line 54）

**异常**: ✅ 使用 NotFoundError, ValidationError

---

## 重点发现汇总

### 🔴 严重问题

| ID | 文件 | 问题 | 严重度 | 修复建议 |
|----|------|------|--------|---------|
| S1 | `card_service.py:124,352` | 使用 `PermissionError` 而非 `AppError` 子类 | 高 | 替换为 `AppError(error_code=ErrorCode.INVALID_REQUEST, ...)` |
| S2 | `chapter_service.py:166,384` | 同上，使用 `PermissionError` | 高 | 替换为 AppError |
| S3 | `coherence_service.py:293,409,548` | `json.loads(response)` 无异常处理，LLM 返回非 JSON 时崩溃 | 高 | 添加 try/except 包装 |
| S4 | `project_service.py:77-78` | N+1 查询：循环中 `chapter_dao.count_by_project()` | 高 | 使用聚合查询或预加载 |
| S5 | `template_service.py:57,86,108,127` | 错误码语义不对应（VAULT_ENTRY_NOT_FOUND） | 中 | 使用 TEMPLATE_NOT_FOUND |
| S6 | `health_monitor.py:110-112` | `except Exception: raise` — 捕获后无降级直接重新抛出 | 中 | 添加降级 logic |
| S7 | `generation_service.py:320` | `asyncio.create_task()` 可能被 GC 静默丢弃 | 中 | 保存 task 引用或使用 task_group |

### 🟡 建议改进

| ID | 文件 | 问题 | 修复建议 |
|----|------|------|---------|
| S8 | `generation_service.py, coherence_service.py, health_service.py, phase4_service.py, secret_service.py, weave_service.py` | **所有 LLM 调用无 timeout 配置** | 添加 `timeout=30` 参数到 `llm_client.chat()` |
| S9 | 同上 | **所有 LLM 调用无自动重试** | 添加 exponential backoff 重试（max 3 次） |
| S10 | `card_service.py` draw_cards/redraw_cards | **缺少幂等保护** | 添加 nonce 或 based-on-previous-state 检查 |
| S11 | `merge_service.py` 和 `phase4_service.py` | **Levenshtein 编辑距离重复实现** | 提取到 `app/utils/text.py` 作为公共函数 |
| S12 | `phase4_scheduler.py` `_nonce_set` | 无限增长无清理 | 添加定期清理或使用 `OrderedDict` with maxlen |
| S13 | 多数 service | **Service 层直接 commit()** 模式 | 考虑在路由层统一控制事务边界，service 仅 flush |
| S14 | `import_service.py` | 大文件全量加载到内存 | 添加文件大小上限检查或流式处理 |
| S15 | `auth_service.py` | 缺少关键操作结构化日志 | 添加 login/register 事件日志（不含敏感信息） |

### ✅ 良好实践

1. **phase4_scheduler.py 三层幂等性**: 内存 → DB → UNIQUE 约束，业界最佳实践
2. **phase4_service.py 事务模式**: savepoint → merge → commit → rollback 三步模式完整
3. **generation_service.py savepoint**: 使用 `begin_nested()` + rollback 保护长事务
4. **merge_service.py 置信度系统**: P1-4 四级置信度 + 自动入库策略，设计完善
5. **conflict_detection.py U-curve 置信度模型**: §2.4 数学模型计算，设计细致
6. **vault_filter.py 依赖注入 DAO**: 构造函数支持注入，便于测试
7. **card_retire_service.py 错误降级**: 失败时返回空结果而非崩溃

### ℹ️ 结论

- **无直接 SQL 穿透 DAO 层**: 62 处历史清理后，本次扫描确认无新引入
- **循环依赖已解决**: ServiceRegistry Sentinel 模式有效打破循环
- **最需改进**: LLM 调用超时/重试 + ErrorCode 语义修正 + N+1 查询优化
- **整体架构健康**: Service 层职责清晰，DAO 访问规范，事务管理基本正确
