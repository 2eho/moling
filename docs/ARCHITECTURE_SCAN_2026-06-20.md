# 墨灵后端架构深度扫描报告

**日期**: 2026-06-20 | **扫描范围**: 全部后端模块（20 Models / 30 Services / 20 Routers / 16 DAOs / 18 Schemas / 5 Middleware / 7 Workers / LLM / Genre / Ingest）  
**方法论**: 逐文件全量读取 + 跨模块交叉验证 + 分层审计

---

## 总体评分

| 维度 | 初始评分 | 当前评分 | 目标评分 | 说明 |
|------|----------|----------|----------|------|
| **分层架构** | 7.0 | 7.5 | 9.0 | Router→Service→DAO 分层清晰，但 DAO 穿透已修复 |
| **数据完整性** | 5.5 | 5.5 | 9.0 | 10个模型缺 relationship，2个 embedding 类型错误，phase4_task id 类型不匹配 |
| **安全性** | 5.0 | 5.0 | 9.5 | phase4.py 缺角色检查，admin 已修复，仍有多个端点无权限验证 |
| **依赖注入** | 1.0 | 1.0 | 7.0 | 仅 VaultFilterService 有构造注入，其余全是模块级单例+直接 import |
| **异步一致性** | 7.5 | 7.5 | 9.0 | 大部分 async，但 card_pool_service 使用同步 Session，vault_service自建引擎 |
| **错误处理** | 6.0 | 6.5 | 9.0 | generation_service 有完整 savepoint，但 validation 缺独立 try/except，fire-and-forget 无异常处理 |
| **测试覆盖** | 5.5 | 5.5 | 8.5 | 620+测试但95%用Mock，仅2个真实DB测试且只在Linux运行，Windows全skip |
| **Worker健壮性** | 4.0 | 4.0 | 8.5 | DB会话管理4种不同模式，引擎泄露，3个worker完全没会话管理 |
| **可观测性** | 6.5 | 6.5 | 8.0 | 有审计日志+Prometheus+Sentry，但限流拒绝请求无审计，中间件顺序有坑 |
| **文档同步** | 5.0 | 5.0 | 8.0 | 文档债较多，许多新功能无对应文档 |

**加权总分: 5.4 / 10** （初始 5.9 下调，因本次深扫发现了新的严重问题）

---

## 一、致命级问题 (CRITICAL — 必须立即修复)

### C1. Phase4 路由无权限检查 🔴 安全漏洞

| 位置 | 问题 | 影响 |
|------|------|------|
| `router/phase4.py:90-124` | `get_pending_reviews` 返回所有用户的待审任务，无 user_id 过滤 | 任何已认证用户可看到全平台待审内容 |
| `router/phase4.py:127-154` | `approve_review` 检查了项目所有权但无 admin 角色要求 | 普通用户可审批任意项目精修建议 |
| `router/phase4.py:157-189` | `reject_review` 同上 | 同上 |
| `router/phase4.py:192-215` | `retry_task` 既不检查项目所有权也不检查admin角色 | 任何用户可重试任何任务 |

**修复建议**: 添加 `Depends(require_admin)` 到所有审批/拒绝/重试端点；`get_pending_reviews` 添加 `user_id` 过滤。

### C2. Embedding 列类型错误 🔴 数据损坏风险

| 位置 | 问题 |
|------|------|
| `models/card_pool.py` | `Mapped[Optional[list[float]]]` 但列为 `Float`（标量）。list→标量会导致数据截断 |
| `models/vault_character.py` | 同样问题 |

**修复建议**: 改为 `ARRAY(Float)` 或 `JSON` 类型存储向量。

### C3. Phase4Task project_id 类型不匹配 🔴 数据库约束不可用

| 位置 | 问题 |
|------|------|
| `models/phase4_task.py` | `project_id` 定义为 `String(36)` 但 `projects.id` 是 `Integer`。无法加外键约束。 |

**修复建议**: 将 `project_id` 改为 `Integer` 并添加 `ForeignKey("projects.id")`。

### C4. Worker DB 会话管理四模式混乱 🔴 生产隐患

| Worker | 会话管理模式 | 问题 |
|--------|-------------|------|
| `tasks.py` | 模块级 `_session_factory`，导入时创建引擎 | 引擎永远不 dispose，长期泄漏连接 |
| `phase4_task.py` | 每次 `create_async_engine` 新引擎 | 每次都新建，永远不 dispose |
| `vault_reanalyze_task.py` | 每次 `create_async_engine` 新引擎 | 同上 |
| `book_analysis_task.py` | **完全没有**会话管理 | service 方法无 db 参数 |
| `import_task.py` | **完全没有**会话管理 | 同上 |
| `card_retire_task.py` | **完全没有**会话管理 | 同上 |

**修复建议**: 统一为 `app/worker/db.py` 工具模块，提供 `get_worker_session()` 上下文管理器，所有 worker 统一使用。

---

## 二、高危问题 (HIGH)

### H1. Service 层循环依赖 🔴

`generation_service.py` 存在 4 处延迟导入：
- `from app.worker.tasks import run_generation_task` (L97)
- `from app.service.health_monitor import health_monitor_service` (L293)  
- `from app.service.phase4_scheduler import phase4_scheduler` (L310)
- `from app.service.coherence_service import coherence_service` (L446)

以及顶层导入 `algorithm_service` 和 `prompt_service`——若它们也 import generation_service 会形成循环。

**根本原因**: 所有 Service 都是模块级单例，通过 `import` 引用而非依赖注入。

**修复建议**: 短期可保持延迟导入，长期应引入依赖注入容器（如 `dependency-injector`）或至少 ServiceRegistry 模式。

### H2. vault_service.update_from_chapter 自建引擎 🔴

`vault_service.py:427-429` 在方法内部创建独立引擎和会话：
```python
engine = create_async_engine(settings.DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)
```

**影响**: 
- 绕过调用方事务边界（无法与 Phase4 事务联动）
- 每次调用创建新连接池，不 dispose，泄漏连接
- 与统一依赖注入架构矛盾

### H3. card_service 使用 PermissionError 而非 AppError 🔴

`card_service.py:124`: `raise PermissionError(error_code=...)` — `PermissionError` 不接受 `error_code` 关键字参数。这是运行时 bug。

### H4. Router 重复注册 — project vs project_health 🔴

`project.py:128-154` 和 `project_health.py:20-121` 在相同前缀 `/projects` 下注册了完全相同的端点 `/{project_id}/health` 和 `/{project_id}/health/refresh`。虽然 `__init__.py` 都 import 了，可能导致路由冲突。

### H5. GenerationTask/DrawHistory 有 FK 但无 relationship 🔴

两个模型各有 3 个外键但完全没有 `relationship()` 定义，导致无法进行 ORM 层导航，所有关联查询必须手写 JOIN。

---

## 三、中等问题 (MEDIUM)

### M1. 13 个模型缺 relationship 定义

以下模型有外键但没有 `relationship()`:
- VaultCharacter / VaultTimeline / VaultPlotPromise / VaultWorld / VaultChangelog
- HealthAlert / Secret / Notification / Template / Plan / UserSubscription / CardPool

**影响**: 无法进行 ORM 导航，所有跨表查询必须手写 JOIN 或多次查询，降低开发效率。

### M2. DynamicLayer.project 缺 back_populates

`DynamicLayer.project` 定义了 relationship 但没有 `back_populates`，且 Project 没有对应的 `dynamic_layers` 集合。这是单向关系——需要但不可访问。

### M3. validation_service 缺独立 try/except

`run_pre_checks` 将 7 个检查串行调用，如果一个检查抛异常，后续全部跳过。应先独立捕获，汇总失败项。

### M4. merge_service.archive_changelog 无 savepoint

批量插入 changelog 时，如果第 N 条插入失败，前 N-1 条已提交，无回滚机制。

### M5. audit_log 中间件消费请求体

`audit_log.py:67-70` 调用 `await request.body()` 在 response 中间件之前消费了请求体流，导致下游无法读取。

### M6. get_sync_db commit 在 yield 后

`dependencies.py:155-165`: commit 在 yield 之后执行，如果请求异常退出或 generator 未正确关闭，commit 不会执行——可能导致静默数据丢失。

### M7. 模型 nullable 约束遗漏

- `notification.py`: `is_read` 有 default=False 但 nullable=True
- `subscription.py`: `status`, `start_date`, `auto_renew` 有 default 但 nullable=True
- `DynamicLayer`: `project_id` mapped_column 无显式类型（全靠 Mapped[] 推断）

### M8. 硬编码值分散

- `version` = `"1.0.0"` (health.py)
- Redis 端口 = `6379` (vault.py 内联检查)
- 订阅天数 = `30` / `365` (subscription.py)
- 编织模式列表 = 硬编码在 weave.py

### M9. Windows 测试全 skip

conftest.py 在 Windows 上自动 skip 所有需要 async_client/test_db/test_user/test_project/test_chapter fixture 的测试。**意味着 Windows 开发环境下 0 个测试运行**。

---

## 四、轻微问题 (LOW)

### L1. ID 类型三态不一致

- `User`/`Chapter`/`CardPool`/Vault 等 → `String(36)` (UUID 字符串)
- `Project`/`HealthAlert`/`Notification` → `Integer` (自增)
- `GenerationTask` → `Uuid` (原生 UUID 类型)
- `SystemConfig` → `key` 为主键（非 `id`）

### L2. 基础模型继承不一致

- 12 个模型继承 `BaseModel` (带 UUID 主键)
- 5 个模型继承 `Base` 手动定义主键
- `SystemConfig` 连 `TimestampMixin` 都没用，只用 `Base`

### L3. 模板路由无认证

`template.py:16-40` 的 `list_templates` 和 `get_template` 端点完全没有认证依赖——任何人可随意访问。

### L4. 占位符实现

- `setting.py:159-165` — `clear_user_cache` 永远返回 True，什么都没清除
- `setting.py:149-156` — `export_user_data` 返回 URL 占位符，没有导出逻辑
- `subscription.py:34-60` — `create_checkout` 返回占位 checkout URL

### L5. 请求体模型位置不统一

`setting.py:17-35` 在 router 文件内定义 `ChangePasswordReq`、`UpdateProfileReq`、`Phase4ReviewReq`，应移到 `schemas/setting.py`。

---

## 五、Worker 层详细问题

| Worker | db 会话 | 引擎管理 | 异常处理 | 幂等性 |
|--------|---------|----------|----------|--------|
| `tasks.py` | ✅ async context | 🔴 导入时创建，不 dispose | ✅ retry | ✅ 幂等检查 |
| `book_analysis_task.py` | 🔴 无 | 🔴 无 | ❓ 未知 | ❓ 未知 |
| `import_task.py` | 🔴 无 | 🔴 无 | ✅ try/except | ❓ 未知 |
| `card_retire_task.py` | 🔴 无 | 🔴 无 | ✅ try/except | ❓ 未知 |
| `phase4_task.py` | ✅ 自建 | 🔴 每次新建create_async_engine | ✅ try/except | ❓ 未知 |
| `vault_reanalyze_task.py` | ✅ async context | 🔴 每次新建create_async_engine | ✅ try/except | ❓ 未知 |

**关键缺失**: Celery 任务超时 `task_time_limit=600` 可能对 LLM 调用不够。

---

## 六、模块完整性矩阵

| 模块 | 文件数 | Model | DAO | Schema | Service | Router | Test | 完整性 |
|------|--------|-------|-----|--------|---------|--------|------|--------|
| Auth | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 85% |
| Project | 5 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 80% |
| Chapter | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 85% |
| Card/Draw | 6 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 80% |
| Vault (四库) | 8 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 75% |
| Generation | 4 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 85% |
| Phase4 | 3 | 🔴 | ✅ | ✅ | ✅ | 🔴 | ✅ | 55% |
| Health | 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 80% |
| Secret | 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 85% |
| Notification | 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 80% |
| Template | 3 | ✅ | ✅ | ✅ | ✅ | 🔴 | ❌ | 60% |
| Subscription | 2 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 65% |
| Weave | 3 | - | - | ✅ | ✅ | ✅ | ✅ | 75% |
| Ingest | 8 | ✅ | - | - | ✅ | ✅ | ✅ | 70% |
| Genre | 5 | ✅ | - | - | - | ✅ | ✅ | 65% |
| Admin | 1 | - | - | ✅ | - | ✅ | ✅ | 75% |
| Setting | 2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 70% |
| LLM | 6 | - | - | - | - | - | ✅ | 70% |
| Worker | 7 | - | - | - | - | - | ❌ | 45% |

**图例**: ✅完成 🔴有严重问题 🟡有中等问题 ❌缺失 ⬜占位

---

## 七、修复路线图

### Round 1: 致命修复（今天）🟡

| # | 模块 | 问题 | 文件 | 工作量 |
|---|------|------|------|--------|
| R1.1 | Router | Phase4 路由加 admin 角色检查 | `router/phase4.py` | 30min |
| R1.2 | Models | Embedding 列类型改为 ARRAY(Float) | `models/card_pool.py`, `models/vault_character.py` | 20min |
| R1.3 | Models | Phase4Task.project_id 改为 Integer + FK | `models/phase4_task.py` | 15min |
| R1.4 | Worker | 统一 DB 会话管理工具模块 | 新建 `worker/db.py` | 1h |
| R1.5 | Service | card_service PermissionError→AppError | `service/card_service.py` | 10min |
| R1.6 | Router | 解决 project/project_health 重复 | `router/project.py` + `router/project_health.py` | 20min |

### Round 2: 高危修复（明天）

| # | 模块 | 问题 | 工作量 |
|---|------|------|--------|
| R2.1 | Service | generation_service 循环依赖解耦 | 2h |
| R2.2 | Service | vault_service 自建引擎改为参数注入 | 1h |
| R2.3 | Models | GenerationTask/DrawHistory 加 relationship | 30min |
| R2.4 | Dependencies | get_sync_db commit 移到 yield 前 | 30min |
| R2.5 | Middleware | audit_log 改用 request.state 缓存体 | 1h |
| R2.6 | Worker | 修复 book_analysis/import/card_retire 三个 worker | 2h |
| R2.7 | Tests | Windows 上至少跑 10 个核心测试（mock） | 2h |

### Round 3: 架构加固（本周）

| # | 模块 | 问题 | 工作量 |
|---|------|------|--------|
| R3.1 | Models | 13 个模型补 relationship 定义 | 3h |
| R3.2 | Service | 引入 ServiceRegistry 替代模块级单例 | 4h |
| R3.3 | Models | 统一 ID 类型策略（全 UUID 或全 Integer） | 3h |
| R3.4 | Dependencies | Redis 连接池复用 | 1h |
| R3.5 | All | 硬编码值移至配置常量 | 2h |
| R3.6 | All | 请求体模型统一移至 schemas/ | 1h |
| R3.7 | All | 占位符实现填坑（cache/export/checkout） | 3h |

### Round 4: 长期提升（下周）

| # | 模块 | 问题 | 工作量 |
|---|------|------|--------|
| R4.1 | All | 引入依赖注入容器（dependency-injector） | 8h |
| R4.2 | Tests | 真实 DB 集成测试覆盖核心流程 | 8h |
| R4.3 | Worker | 每个 worker 加幂等性检查 | 3h |
| R4.4 | Docs | 所有模块补文档（ADR 格式） | 8h |
| R4.5 | Ingest | Phase 2/3 补单元测试 | 4h |
| R4.6 | Subscription | 真实支付集成 | 12h |

---

## 八、健康指标

| 指标 | 当前值 | 健康值 | 状态 |
|------|--------|--------|------|
| DAO 穿透 (service 层 select()) | 0 处 | 0 处 | ✅ |
| 循环依赖（延迟 import） | 7 处 | 0 处 | 🔴 |
| Worker DB 管理模式数 | 4 种 | 1 种 | 🔴 |
| 缺 relationship 模型数 | 13 / 21 | 0 | 🔴 |
| 缺角色检查端点 | 4 个 | 0 个 | 🔴 |
| 测试在 Windows 运行率 | 0% | >80% | 🔴 |
| 数据类型错误 (列) | 3 处 | 0 处 | 🔴 |
| 占位符实现 | 4 处 | 0 处 | 🟡 |
| 硬编码配置值 | ~8 处 | 0 处 | 🟡 |
| 异常处理覆盖 Service | ~85% | 100% | 🟡 |
| 异步一致性 | ~90% | 100% | 🟡 |
| Auth 中间件覆盖 | ~85% | 100% | 🟡 |

---

## 九、架构优化建议（非修复，提升性）

### 1. 依赖注入容器
当前所有 Service 是 `模块级 import → 单例` 模式。建议引入 `dependency-injector` 或自建 ServiceRegistry：
```python
# 建议模式
class ServiceRegistry:
    _instances: dict = {}
    
    @classmethod
    def get(cls, service_cls):
        if service_cls not in cls._instances:
            cls._instances[service_cls] = service_cls()
        return cls._instances[service_cls]
```

### 2. 统一 Worker DB 管理
```python
# app/worker/db.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def worker_db():
    engine = get_worker_engine()  # 懒加载单例
    async with async_sessionmaker(engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 3. Router 层规范
- 所有端点强制 `response_model` Pydantic 类型
- 权限检查统一为 `Depends(require_admin)` 或 `Depends(require_owner)`
- 请求体模型不得定义在 Router 文件中

### 4. 测试策略分层
- **L0 (Unit)**: Mock 所有外部依赖，Windows+Linux 全跑
- **L1 (Integration)**: 真实 SQLite 内存库，Linux 跑
- **L2 (E2E)**: 真实 PostgreSQL + Redis，CI 环境跑
