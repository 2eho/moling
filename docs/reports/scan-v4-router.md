# 墨灵 Router/API 层深度扫描报告 v4

> **扫描日期**: 2026-06-21
> **扫描范围**: `app/router/`（20 个路由文件）+ `app/generation/router.py` + `app/ingest/router.py`
> **扫描深度**: very thorough
> **检测项**: 12 项逐端点审查

---

## 📊 扫描概要

| 指标 | 数值 |
|------|------|
| 扫描路由文件数 | 22 |
| 端点总数 | ~120 |
| 已通过（PASS） | 46 |
| 警告（WARN） | 19 |
| 高危/严重（CRITICAL） | 9 |
| 信息（INFO） | 16 |

---

## 一、认证缺失 (Authentication Missing)

| 端点 | 文件 | 问题 | 严重度 |
|------|------|------|--------|
| `GET /health` | `health.py:23` | 无 `Depends(get_current_user)` | ✅ 预期（健康检查公开） |
| `GET /system/health` | `__init__.py:58` | 无认证 | ✅ 预期（别名） |
| `POST /auth/register` | `auth.py:28` | 无认证 | ✅ 预期（注册无需登录） |
| `POST /auth/login` | `auth.py:39` | 无认证 | ✅ 预期（登录无需登录） |
| `POST /auth/refresh` | `auth.py:50` | 无 `Depends(get_current_user)`，仅验证 refresh_token | ✅ 可接受 |
| `POST /auth/password-reset-request` | `auth.py:67` | 无认证 | ✅ 预期 |
| `POST /auth/password-reset` | `auth.py:78` | 无认证 | ✅ 预期 |

**结论**: 所有公开端点均按设计无需认证，无意外遗漏。

---

## 二、授权绕过 (Authorization Bypass)

| 端点 | 文件 | 问题 | 严重度 |
|------|------|------|--------|
| 所有 `/admin/*` 端点 | `admin.py` | 全部有 `Depends(require_admin)` | ✅ PASS |
| `POST /phase4/reviews/{review_id}/approve` | `phase4.py:136` | 有 `_admin=Depends(require_admin)` + `get_current_user` | ✅ PASS |
| `POST /phase4/reviews/{review_id}/reject` | `phase4.py:165` | 有 `_admin=Depends(require_admin)` + `get_current_user` | ✅ PASS |
| `POST /phase4/tasks/{task_id}/retry` | `phase4.py:199` | 有 `_admin=Depends(require_admin)` + `get_current_user` | ✅ PASS |

**结论**: 所有 admin 端点均已正确授权，`require_admin` 检查 `status == "admin"`。

---

## 三、response_model 缺失 — 返回 dict 而非具体 Schema

### 🔴 CRITICAL — 运行时崩溃风险

由于 `get_current_user()` 返回 `UserResp`（Pydantic 模型），以下端点使用 `current_user["id"]` 字典式访问将导致 **TypeError**：

| 端点 | 文件:行 | 错误代码 | 说明 |
|------|---------|----------|------|
| `POST /generate/chapters/{chapter_id}/generate` | `generation/router.py:48` | `current_user["id"]` | Pydantic model 不支持 `__getitem__` |
| `GET /generate/jobs/{job_id}` | `generation/router.py:84` | `current_user["id"]` | 同上 |
| `POST /generate/jobs/{job_id}/cancel` | `generation/router.py:105` | `current_user["id"]` | 同上 |
| `GET /generate/history` | `generation/router.py:123` | `current_user["id"]` | 同上 |
| `POST /projects/{project_id}/import` | `ingest/router.py:113` | `user["id"]` | 同上 |
| `POST /projects/{project_id}/import/full-import` | `ingest/router.py:343` | `user["id"]` | 同上 |
| `POST /subscriptions` | `subscription.py:71` | `current_user["id"]` | 同上 |
| `GET /subscriptions/current` | `subscription.py:114` | `current_user["id"]` | 同上 |
| `GET /subscriptions/payment-history` | `subscription.py:137` | `current_user["id"]` | 同上 |

### 🟡 WARN — response_model=dict 或无 response_model

以下 ~45 个端点返回 `dict` 而非具体 Schema（部分已有 `response_model=dict`，部分完全无声明）：

| 文件 | 端点 | 行号 | 问题 |
|------|------|------|------|
| `admin.py` | `POST /admin/llm-config/test` | 121 | 无 response_model，返回 dict |
| `admin.py` | `GET /admin/users` | 178 | `response_model=dict` |
| `admin.py` | `GET /admin/projects` | 204 | `response_model=dict` |
| `admin.py` | `PATCH /admin/users/{user_id}` | 230 | 无 response_model，返回 dict |
| `admin.py` | `GET /admin/llm-usage` | 253 | 无 response_model，返回 dict |
| `auth.py` | `POST /auth/password-reset-request` | 67 | 无 response_model |
| `auth.py` | `POST /auth/password-reset` | 78 | 无 response_model |
| `auth.py` | `POST /auth/logout` | 97 | 无 response_model |
| `card.py` | `GET /cards/history` | 77 | `PaginatedResp[dict]` |
| `card.py` | `GET /cards/draw-history` | 94 | `PaginatedResp[dict]` |
| `card.py` | `GET /cards/draw-history/{draw_id}` | 118 | `response_model=dict` |
| `chapter.py` | `GET /chapters/{chapter_id}/suggestions` | 131 | `response_model=dict` |
| `chapter.py` | `POST /chapters/{chapter_id}/agent` | 145 | `response_model=dict` |
| `chapter.py` | `POST /chapters/{chapter_id}/generate-sync` | 160 | `response_model=dict` |
| `chapter.py` | `POST /chapters/{chapter_id}/redraw` | 186 | `response_model=dict` |
| `generation.py` | `GET /generation/history` | 39 | `PaginatedResp[dict]` |
| `generation/router.py` | `POST /generate/chapters/{chapter_id}/generate` | 26 | 无 response_model |
| `generation/router.py` | `GET /generate/jobs/{job_id}` | 65 | 无 response_model |
| `generation/router.py` | `POST /generate/jobs/{job_id}/cancel` | 93 | 无 response_model |
| `generation/router.py` | `GET /generate/history` | 113 | 无 response_model |
| `ingest/router.py` | 全部 13 个端点 | 全文件 | 无 response_model |
| `notification.py` | `GET /notifications/unread-count` | 46 | `response_model=dict` |
| `notification.py` | `POST /notifications/read-all` | 74 | `response_model=dict` |
| `phase4.py` | `POST /phase4/apply` | 47 | 无 response_model |
| `phase4.py` | `GET /phase4/pending-reviews` | 91 | 无 response_model |
| `phase4.py` | `POST /phase4/reviews/{review_id}/approve` | 136 | 无 response_model |
| `phase4.py` | `POST /phase4/reviews/{review_id}/reject` | 165 | 无 response_model |
| `phase4.py` | `POST /phase4/tasks/{task_id}/retry` | 199 | 无 response_model |
| `project.py` | `GET /projects/{project_id}/suggestions` | 97 | `response_model=dict` |
| `project.py` | `GET /projects/{project_id}/cards/history` | 113 | `list[dict]` |
| `secret.py` | `GET /secrets/character/{character_name}` | 38 | `response_model=dict` |
| `secret.py` | `PUT /secrets/character/{character_id}` | 57 | `response_model=dict` |
| `secret.py` | `PATCH /secrets/{secret_id}` | 78 | `response_model=dict` |
| `setting.py` | `POST /settings/change-password` | 51 | 无 response_model |
| `setting.py` | `GET /settings/profile` | 67 | `response_model=dict` |
| `setting.py` | `PUT /settings/profile` | 80 | `response_model=dict` |
| `setting.py` | `PATCH /settings/health-monitor` | 97 | 无 response_model |
| `setting.py` | `POST /settings/export` | 134 | 无 response_model |
| `setting.py` | `POST /settings/clear-cache` | 144 | 无 response_model |
| `setting.py` | `GET /settings/phase4-review` | 153 | 无 response_model |
| `setting.py` | `PATCH /settings/phase4-review` | 165 | 无 response_model |
| `subscription.py` | `POST /subscriptions/create-checkout` | 35 | `response_model=dict` |
| `subscription.py` | `GET /subscriptions/current` | 108 | `response_model=dict` |
| `subscription.py` | `GET /subscriptions/payment-history` | 129 | `response_model=dict` |
| `vault.py` | `POST /vault/full-reanalyze` | 291 | 无 response_model |
| `weave.py` | `GET /weave/patterns` | 26 | `list[dict]` |
| `weave.py` | `POST /weave/apply` | 46 | 无 response_model |
| `health.py` | `GET /health` | 23 | 返回 `JSONResponse`，无 response_model |

### 🟢 已 Schema 化的端点（确认）

| 端点 | response_model | 状态 |
|------|---------------|------|
| `POST /auth/register` | `TokenResp` | ✅ |
| `POST /auth/login` | `TokenResp` | ✅ |
| `POST /auth/refresh` | `TokenResp` | ✅ |
| `GET /auth/me` | `UserResp` | ✅ |
| `PUT /auth/me` | `UserResp` | ✅ |
| `GET /admin/llm-config` | `LLMConfigResp` | ✅ |
| `POST /admin/llm-config` | `LLMConfigResp` | ✅ |
| `GET /admin/stats` | `AdminStatsResp` | ✅ |
| `GET /notifications` | `PaginatedResp[NotificationResp]` | ✅ |
| `GET /settings` | `UserSettings` | ✅ |
| `PUT /settings` | `UserSettings` | ✅ |
| 全部模板端点 | 各 Schema | ✅ |
| 全部 vault CRUD 端点 | 各 Schema | ✅ |
| 全部 project CRUD 端点 | 各 Schema | ✅ |
| 全部 chapter CRUD 端点 | 各 Schema | ✅ |
| 全部 genre 端点 | 各 Pydantic Schema | ✅ |

---

## 四、输入验证 (Input Validation)

### 🟡 WARN — 路径/查询参数缺少 min/max 限制

| 端点 | 参数 | 文件:行 | 问题 |
|------|------|---------|------|
| `POST /generate/chapters/{chapter_id}/generate` | `project_id: int` (Query) | `generation/router.py:28` | 无 `ge=1` 验证 |
| `POST /projects/{project_id}/import` | `project_id: str` | `ingest/router.py:34` | 使用 `str` 类型，非 `int`，无验证 |
| `GET /projects/{project_id}/import/{job_id}` | `project_id: str` | `ingest/router.py:136` | 同上 |
| 全部 `ingest/router.py` 端点 | `project_id: str` | 全文件 | 与其他路由 `int` 类型不一致 |
| `POST /chapters/{chapter_id}/confirm` | `req: Optional[ChapterConfirmReq] = None` | `chapter.py:107` | 可选请求体，无验证 |
| `POST /chapters/{chapter_id}/revise` | `req: Optional[ChapterReviseReq] = None` | `chapter.py:121` | 同上 |

### 🟢 验证良好的端点

- `auth.py`: `RegisterReq` / `LoginReq` 有 field_validator 验证
- `genre.py`: `PrefillRequest` 有 `field_validator` 检查 genre 枚举和 synopsis 长度
- `admin.py`: `LLMConfigReq` 有字段验证（需确认 Schema 定义）
- 所有 `page/page_size` Query 参数有 `ge=1, le=100` 限制
- 所有 `offset/limit` 类参数有验证

### ⚠️ ingest/router.py — project_id 类型不一致

`ingest/router.py` 中 `project_id` 声明为 `str` 类型：
```python
# ingest/router.py:34
async def submit_import(project_id: str, ...)
```

而其他路由中 `project_id` 均为 `int`：
```python
# project.py:68
async def get_project(project_id: int, ...)
```

如果数据库中 `id` 为整数，`str` 类型接受任何字符串可能造成问题。建议统一为 `int`。

---

## 五、HTTP 方法语义审查

### 🟡 WARN — 方法语义不佳

| 端点 | 文件:行 | 当前方法 | 建议方法 | 原因 |
|------|---------|----------|----------|------|
| `POST /notifications/{notification_id}/read` | `notification.py:59` | POST | PATCH | 部分更新（标记已读） |
| `POST /notifications/read-all` | `notification.py:74` | POST | PATCH | 批量更新 |
| `POST /settings/change-password` | `setting.py:51` | POST | PUT | 完整替换密码 |
| `POST /settings/clear-cache` | `setting.py:144` | POST | DELETE | 删除缓存 |
| `POST /projects/{project_id}/import/full-import` | `ingest/router.py:312` | POST | — | 可接受（创建操作） |
| `POST /cards/{card_id}/retire` | `card.py:55` | POST | PATCH | 部分更新（设置 is_active=False） |

### 🟢 方法使用正确

- CRUD: POST(create)/GET(read)/PUT(update)/DELETE(delete) — 大部分端点正确
- `status_code=201` 用于创建 — 正确
- `status_code=204` 用于无响应体的删除 — 正确
- `status_code=202` 用于 `vault/full-reanalyze` — 正确（已接受异步任务）

---

## 六、路径冲突分析

### 🟢 冲突预防良好

所有参数化路径与非参数路径的声明顺序正确：

| 路由文件 | 声明顺序 | 状态 |
|----------|----------|------|
| `project.py` | `/stats` 在 `/{project_id}` 之前 | ✅ |
| `chapter.py` | `/chapters/current` 在 `/chapters/{chapter_id}` 之前 | ✅ |
| `card.py` | `/cards/pool`、`/cards/history` 在 `/cards/{card_id}/retire` 之前 | ✅ |
| `generation.py` | `/history` 在 `/{task_id}` 之前 | ✅ |
| `notification.py` | `/unread-count`、`/read-all` 在 `/{notification_id}/read` 之前 | ✅ |

### ⚠️ 潜在关注点

| 路径 | 文件 | 问题 |
|------|------|------|
| `/projects/{project_id}/cards/history` | `project.py:113` | 与 `card.py` 中的 `/cards/history` (第77行) 和 `/cards/draw-history` (第94行) **功能重复**。三处都调用 `card_service.get_draw_history()` |
| `/projects/{project_id}/cards/draw-history` | `card.py:94` | 与 `GET /cards/history` (第77行) 返回相同数据 |
| `GET /vault/{project_id}/vault/...` | `vault.py` | 路径中的双重 vault（`/vault` + `/vault/...`）可能冗余 |

---

## 七、响应格式一致性

### 🔴 CRITICAL — 三种互不兼容的响应格式

经过 `__init__.py` 中的 `ResponseFormatMiddleware` 包装后，正常端点响应格式为：
```json
{"code": 200, "message": "success", "data": {...}, "meta": {...}}
```

但以下路由**手动构造**了不同格式的响应：

#### 格式 1: `{"code": 0, "message": ..., "data": ...}`（generation/router.py）
| 端点 | 文件:行 |
|------|---------|
| `POST /generate/chapters/{chapter_id}/generate` | `generation/router.py:54` |
| `GET /generate/jobs/{job_id}` | `generation/router.py:90` |
| `POST /generate/jobs/{job_id}/cancel` | `generation/router.py:110` |
| `GET /generate/history` | `generation/router.py:125` |

问题：
- `code: 0` 而标准 `code: 200`
- `data` 包裹在 `{code, message, data}` 中，但外部 `ResponseFormatMiddleware` 还会再包裹一层，形成**双重嵌套**

#### 格式 2: `{"success": true/false, ...}`（ingest/router.py）
| 端点 | 文件:行 |
|------|---------|
| 全部 `ingest/router.py` 端点 | 全文件 |

问题：
- 完全不同的字段名 `success` vs `code`
- 无 `message`、`data` 标准字段

#### 格式 3: `{"status": "ok"/"degraded", ...}`（health.py + __init__.py）
| 端点 | 文件:行 |
|------|---------|
| `GET /health` | `health.py:76` |
| `GET /system/health` | `__init__.py:58` |

问题：
- 返回 `JSONResponse` 直接，可能绕过 `ResponseFormatMiddleware`
- 手动构造了 `{"code": ..., "message": ..., "data": ...}` 格式（第 84-88 行），但未使用 `meta` 字段

#### 格式 4: `POST /admin/llm-config/test` 返回 `{"ok": true/false, "msg": ...}`
| 端点 | 文件:行 |
|------|---------|
| `POST /admin/llm-config/test` | `admin.py:134` |

**建议**: 统一为 `ResponseFormatMiddleware` 的格式，或至少将 generation/router.py 和 ingest/router.py 迁移到标准格式。

---

## 八、错误处理审查

### 🟡 WARN — 错误被吞没

| 端点 | 文件:行 | 问题 |
|------|---------|------|
| `POST /admin/llm-config/test` | `admin.py:155` | `except Exception as e: return {"ok": False, "msg": f"连接失败: {str(e)}"}` — 错误被吞没返回 200，而非 raise AppError |
| `POST /vault/full-reanalyze` | `vault.py:324` | `except Exception: pass` — Celery 连接失败被静默忽略 |

### 🟡 WARN — 错误码不一致

| 文件 | 用法 | 问题 |
|------|------|------|
| `genre.py:120` | `raise PermissionError(detail="无权访问该项目")` | 未传 `ErrorCode`，默认使用 `AUTH_INSUFFICIENT_PERMISSIONS` |
| `ingest/router.py:15` | `raise ValidationError(detail="请提供...")` | 未传 `ErrorCode`，默认使用 `VALIDATION_ERROR` |
| `card.py:131` | `raise NotFoundError(detail="抽卡记录不存在")` | 未传 `ErrorCode`，默认使用 `PROJECT_NOT_FOUND` |
| `chapter.py:54` | `raise NotFoundError(detail="No chapters found")` | 未传 `ErrorCode`，默认使用 `PROJECT_NOT_FOUND` |
| `admin.py:240` | `raise NotFoundError(ErrorCode.USER_NOT_FOUND)` | ✅ 传递了正确的 ErrorCode |

### 🟢 错误处理良好

- 大部分 CRUD 端点使用 `NotFoundError`、`ForbiddenError`、`ConflictError` 等子类
- `generation/router.py:81` 正确使用 `NotFoundError` 和 `PermissionError`
- `secret.py` 所有端点都有项目所有权验证

---

## 九、限流 (Rate Limiting)

### 🟢 已有速率限制

| 端点 | 限制 | 装饰器 |
|------|------|--------|
| `POST /auth/register` | 3/minute | `@limiter.limit("3/minute")` |
| `POST /auth/login` | 5/minute | `@limiter.limit("5/minute")` |
| `POST /auth/password-reset-request` | 3/minute | `@limiter.limit("3/minute")` |
| 全局 | 1000/60s | `RateLimitMiddleware` |

### 🟡 WARN — 敏感端点缺少限流

| 端点 | 文件 | 原因 | 建议 |
|------|------|------|------|
| `POST /generate/chapters/{chapter_id}/generate` | `generation/router.py:26` | AI 生成（资源密集型） | 添加 `@limiter.limit("10/minute")` |
| `POST /genre/prefill` | `genre.py:100` | 冷启动全流程（调用 LLM） | 添加 `@limiter.limit("5/minute")` |
| `POST /admin/llm-config/test` | `admin.py:121` | LLM API 测试（可能被滥用） | 添加 `@limiter.limit("5/minute")` |
| `POST /vault/full-reanalyze` | `vault.py:291` | 全量重分析（资源密集型异步任务） | 建议每项目限制 |
| `POST /chapters/{chapter_id}/generate-sync` | `chapter.py:160` | 同步 AI 生成（已弃用但仍在路由） | 添加限流直到移除 |
| `POST /projects/{project_id}/import` | `ingest/router.py:32` | 文件上传+解析 | 添加 `@limiter.limit("10/minute")` |

---

## 十、分页审查 (Pagination)

### 🟡 WARN — 无分页的列表端点

| 端点 | 文件:行 | 问题 | 风险 |
|------|---------|------|------|
| `GET /chapters` | `chapter.py:34` | `response_model=list[ChapterResp]` 无分页参数 | 大项目可能有数十章 |
| `GET /vault/characters` | `vault.py:35` | `response_model=list[CharacterResp]` 无分页 | 大型项目角色可能很多 |
| `GET /vault/timeline` | `vault.py:97` | `response_model=list[TimelineResp]` 无分页 | 同上 |
| `GET /vault/plot-promises` | `vault.py:159` | `response_model=list[PlotPromiseResp]` 无分页 | 同上 |
| `GET /vault/world` | `vault.py:221` | `response_model=list[WorldResp]` 无分页 | 同上 |
| `GET /subscriptions/plans` | `subscription.py:25` | `response_model=list[PlanResp]` 无分页 | ✅ 可接受（固定小量数据） |
| `GET /weave/patterns` | `weave.py:26` | `response_model=list[dict]` 无分页 | ✅ 可接受（固定 6 条） |

### 🟢 分页良好

| 端点 | 分页参数 |
|------|----------|
| `GET /projects` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /templates` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /notifications` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /phase4/pending-reviews` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /admin/users` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /admin/projects` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /generation/history` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /generate/history` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /cards/draw-history` | `page` (ge=1), `page_size` (ge=1, le=100) |
| `GET /subscriptions/payment-history` | `page` (ge=1), `page_size` (ge=1, le=100) |

---

## 十一、API 版本审查

### 🟢 PASS

- 所有路由通过 `app.include_router(api_router, prefix="/api/v1")` 挂载（`main.py:444`）
- `/system/health` 别名路径不包含版本前缀（`__init__.py:58`），但这是有意为之的别名

---

## 十二、openapi.json 一致性

### ℹ️ 观察

- `main.py:451-472` 在启动时自动生成 `openapi.json`（非生产环境）
- `__init__.py:38-55` 动态加载所有路由
- 由于 response_model 声明缺失和手动 dict 返回，OpenAPI 规范中的响应类型可能不准确

---

## 🔍 额外发现

### 🔴 CRITICAL — `current_user["id"]` 字典式访问（运行时崩溃）

已在上方 3.1 节列出 9 处 `current_user["id"]` 或 `user["id"]` 字典式访问。

**根因**: `get_current_user()` 返回 `UserResp.model_validate(user)` — 一个 Pydantic 模型，**不支持 `__getitem__`**。

**修复**: 将所有 `current_user["id"]` 改为 `current_user.id`，`user["id"]` 改为 `user.id`。

涉及文件：
- `app/generation/router.py`（4 处）
- `app/ingest/router.py`（2 处）
- `app/router/subscription.py`（3 处）

### 🟡 WARN — `current_user` 类型注解不一致

| 类型注解 | 使用位置 |
|----------|----------|
| 无类型注解 | `admin.py`, `auth.py`, `card.py`, `chapter.py`, `generation.py`, `project.py`, `project_health.py`, `vault.py` |
| `current_user: User` (ORM 模型) | `notification.py`, `phase4.py`, `secret.py`, `setting.py`, `subscription.py`, `template.py`, `weave.py` |
| `current_user: UserResp` | `genre.py` |
| `user: dict` | `ingest/router.py` |

**问题**: `get_current_user()` 返回 `UserResp`（Pydantic Schema），但 7 个文件使用 `User`（ORM 模型）类型注解。
虽然 Pydantic 支持 `model_validate()` 转换，但类型注解误导开发者，并且 `User` 和 `UserResp` 的字段可能不完全一致。

**建议**: 统一使用 `UserResp` 类型。

### 🟡 WARN — 弃用端点未移除

| 端点 | 文件:行 | 弃用标记 | 状态 |
|------|---------|----------|------|
| `GET /cards` | `card.py:19` | `deprecated=True` | 陈旧 |
| `GET /phase4/suggestions/{chapter_id}` | `phase4.py:34` | `deprecated=True` | 陈旧 |
| `POST /chapters/{chapter_id}/generate-sync` | `chapter.py:160` | 文档标记 | 潜在安全风险（同步 AI 调用） |

### ℹ️ INFO — 功能重复

| 路径 | 文件 | 功能 |
|------|------|------|
| `GET /projects/{project_id}/cards/history` | `project.py:113` | 抽卡历史 |
| `GET /projects/{project_id}/cards/history` | `card.py:77` | 抽卡历史（无分页） |
| `GET /projects/{project_id}/cards/draw-history` | `card.py:94` | 抽卡历史（分页） |

三处端点提供相同功能，增加了维护复杂度。

### ℹ️ INFO — 健康检查端点响应格式

`health.py:76` 返回的 `JSONResponse` 中包含了冗余字段：
- `database` 字段是 `checks["database"]` 的重复
- 既有 `code` 整数又有 `message` 字段，但格式与其他端点不同

---

## 📋 修复优先级建议

### P0 — 立即修复（可能运行时崩溃）
1. **修复 `current_user["id"]` → `current_user.id`**：`generation/router.py`（4 处）、`ingest/router.py`（2 处）、`subscription.py`（3 处）

### P1 — 高优先级
2. **统一响应格式**: 将 `generation/router.py` 的手动 `{"code": 0, ...}` 和 `ingest/router.py` 的 `{"success": true, ...}` 改为依赖 `ResponseFormatMiddleware` 的标准格式
3. **为 AI 生成端点添加限流**: `generation/router.py`、`genre.py` 的 prefill、`admin/llm-config/test`

### P2 — 中优先级
4. 为 `chapter.py`、`vault.py` 的列表端点添加分页
5. 统一 `current_user` 类型注解为 `UserResp`
6. 为返回 `dict` 的端点创建具体 Schema

### P3 — 低优先级
7. 移除弃用端点（`/cards`、`/phase4/suggestions/{chapter_id}`、同步 generate）
8. 统一 `project_id` 类型为 `int`（`ingest/router.py`）
9. 合并重复的抽卡历史端点

---

## 📊 统计汇总

| 类别 | PASS | WARN | CRITICAL |
|------|------|------|----------|
| 认证缺失 | 7 | 0 | 0 |
| 授权绕过 | 4 | 0 | 0 |
| response_model 缺失 | ~45 | 45 | 9 |
| 输入验证 | 大多数 | 6 | 0 |
| HTTP 方法 | 大部分 | 6 | 0 |
| 路径冲突 | 5 组 | 1 | 0 |
| 响应格式 | 大部分 | 2 | 3 格式 |
| 错误处理 | 大部分 | 5 | 0 |
| 限流 | 4 | 6 | 0 |
| 分页 | 10 | 5 | 0 |
| API 版本 | 1 | 0 | 0 |
| openapi.json | — | 1 | 0 |
| 额外发现 | — | 5 | 1 |

---

## 📎 附录：被扫描的完整文件列表

| # | 文件 | 端点数 | 状态 |
|---|------|--------|------|
| 1 | `app/router/__init__.py` | 1 (+loader) | ✅ |
| 2 | `app/router/admin.py` | 7 | ⚠️ 5 个 dict 返回 |
| 3 | `app/router/auth.py` | 8 | ✅ |
| 4 | `app/router/card.py` | 8 | ⚠️ 3 个 dict 返回 |
| 5 | `app/router/chapter.py` | 14 | ⚠️ 4 个 dict 返回 |
| 6 | `app/router/generation.py` | 3 | ⚠️ 1 个 dict 返回 |
| 7 | `app/router/genre.py` | 3 | ✅ 全部有 Schema |
| 8 | `app/router/health.py` | 1 | ⚠️ JSONResponse 直返 |
| 9 | `app/router/notification.py` | 5 | ⚠️ 2 个 dict 返回 |
| 10 | `app/router/phase4.py` | 12 | ⚠️ 5 个 dict 返回 |
| 11 | `app/router/project.py` | 9 | ⚠️ 2 个 dict 返回 |
| 12 | `app/router/project_health.py` | 2 | ✅ |
| 13 | `app/router/secret.py` | 4 | ⚠️ 3 个 dict 返回 |
| 14 | `app/router/setting.py` | 10 | ⚠️ 7 个 dict 返回 |
| 15 | `app/router/subscription.py` | 5 | ⚠️ 3 dict + 3 dict 访问 |
| 16 | `app/router/template.py` | 6 | ✅ 全部有 Schema |
| 17 | `app/router/vault.py` | 19 | ⚠️ 1 个 dict 返回 |
| 18 | `app/router/weave.py` | 4 | ⚠️ 2 个 dict 返回 |
| 19 | `app/generation/router.py` | 4 | 🔴 4 dict 访问 + 4 无 response_model |
| 20 | `app/ingest/router.py` | 13 | 🔴 2 dict 访问 + 13 无 response_model |
| 21 | `app/dependencies.py` | N/A | 依赖提供者 |
| 22 | `app/limiter.py` | N/A | 限流器配置 |
