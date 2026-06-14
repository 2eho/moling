# 墨灵 (Moling) 前后端 API 集成测试报告

**测试日期**: 2026-06-14  
**测试人员**: integration-tester  
**测试范围**: 前端 (Next.js) API 层与后端 (FastAPI) 路由的集成点

---

## 执行摘要

| 项目 | 状态 |
|------|------|
| 总 API 端点数 | 67 |
| 后端完全实现 | 5 (7.5%) |
| 后端部分实现 | 3 (4.5%) |
| 后端未实现 (存根) | 59 (88%) |
| **严重问题** | **后端大部分 API 未实现，前端调用将失败** |

---

## 1. 测试环境

### 前端
- **位置**: `C:/Users/Admin/Desktop/MolingProject/moling-web/`
- **API 层**: `src/lib/api.ts`, `src/lib/apiClient.ts`
- **基础 URL**: `http://localhost:8000/api/v1` (环境变量 `NEXT_PUBLIC_API_BASE_URL`)
- **响应格式**: 期望 `{ code, message, data, meta }` 包装格式

### 后端
- **位置**: `C:/Users/Admin/Desktop/MolingProject/moling-server/`
- **路由定义**: `app/router/*.py`
- **主应用**: `app/main.py` (挂载于 `/api/v1`)
- **响应格式**: 通过 `ResponseFormatMiddleware` 统一包装

---

## 2. 详细 API 对比

### 2.1 认证 API (Auth)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/auth/login` | `/auth/login` | POST | ✅ 匹配 | 完全实现 |
| `/auth/register` | `/auth/register` | POST | ✅ 匹配 | 完全实现 |
| `/auth/refresh` | `/auth/refresh` | POST | ✅ 匹配 | 完全实现 |
| `/auth/me` | `/auth/me` | GET | ✅ 匹配 | 完全实现 |
| `/auth/password-reset-request` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现密码重置 |

**问题**:
1. 前端定义了 `resetPassword(email)` 但后端没有对应端点
2. 前端期望响应格式 `{ sent: boolean; email: string }` 但后端未实现

---

### 2.2 项目 API (Project)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects` | `/projects` | GET | ❌ **未实现** | 路由存根 |
| `/projects` | `/projects` | POST | ❌ **未实现** | 路由存根 |
| `/projects/{id}` | `/projects/{id}` | GET | ❌ **未实现** | 路由存根 |
| `/projects/{id}` | `/projects/{id}` | PUT | ❌ **未实现** | 路由存根 |
| `/projects/{id}` | `/projects/{id}` | DELETE | ❌ **未实现** | 路由存根 |
| `/projects/{id}/stats` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现统计端点 |

**问题**:
1. 后端 `project.py` 是自动生成的存根，所有端点返回 404
2. 前端期望的 `Project` 类型与后端 `Project` 模型可能不匹配

---

### 2.3 章节 API (Chapter)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/chapters` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/chapters` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/chapters/{id}` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/chapters/{id}` | ❌ 未挂载 | PUT | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/chapters/current` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现获取当前章节 |

**问题**:
1. 后端 `chapter.py` 是存根
2. **路由挂载错误**: `__init__.py` 中 chapter 路由挂载在 `/chapters` 而不是 `/projects/{projectId}/chapters`
3. 前端期望嵌套资源路径，但后端路由挂载方式不支持

---

### 2.4 卡牌 API (Card)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/cards/pool` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/cards/draw` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根且挂载路径错误 |
| `/projects/{projectId}/chapters/{chapterId}/redraw` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现重抽接口 |

**问题**:
1. 后端 `card.py` 是存根
2. **路由挂载错误**: 同 chapter 问题，卡牌路由应该嵌套在 project 下

---

### 2.5 生成 API (Generation)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/chapters/{chapterId}/generate` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |
| `/generation/{taskId}/status` | `/generation/{taskId}/status` | GET | ❌ **未实现** | 路由存根 |
| `/generation/{taskId}/cancel` | `/generation/{taskId}/cancel` | POST | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/chapters/{chapterId}/confirm` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现确认接口 |
| `/projects/{projectId}/chapters/{chapterId}/revise` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现修订接口 |

**问题**:
1. 后端 `generation.py` 是存根
2. 生成相关的确认和修订端点完全缺失

---

### 2.6  Vault API (知识库)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/vault/characters` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/vault/characters` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/vault/characters/{characterId}` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/vault/characters/{characterId}` | ❌ 未挂载 | PUT | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/vault/characters/{characterId}` | ❌ 未挂载 | DELETE | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/vault/timeline` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现时间线 |
| `/projects/{projectId}/vault/plot-promises` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现剧情承诺 |
| `/projects/{projectId}/vault/world` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现世界观 |
| `/projects/{projectId}/vault/summary` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现摘要 |

**问题**:
1. 后端 `vault.py` 是存根
2. Vault 相关的大部分端点完全缺失

---

### 2.7 健康监控 API (Health)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/health/alerts` | ❌ 不存在 | GET | ❌ **缺失** | 后端只实现了基础健康检查 |
| `/projects/{projectId}/health/refresh` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现刷新检查 |

**后端实现**:
```python
# health.py 只实现了基础健康检查
@router.get("")  # 挂载后为 /health
async def health_check(request: Request):
    return {"status": "ok", ...}
```

**问题**:
1. 后端只实现了基础健康检查 `/health`，不包含项目级别的健康监控
2. 前端期望的项目级健康告警完全缺失

---

### 2.8 设置 API (Settings)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/settings` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/settings` | ❌ 未挂载 | PUT | ❌ **未实现** | 路由存根 |
| `/settings/health-monitor` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |
| `/settings/phase4-review` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |
| `/settings/export` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现 |
| `/settings/clear-cache` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现 |

**问题**:
1. 后端 `setting.py` 是存根
2. 所有设置相关端点完全缺失

---

### 2.9 通知 API (Notifications)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/notifications` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/notifications/{notificationId}/read` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |
| `/notifications/read-all` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |

**问题**:
1. 后端 `notification.py` 是存根
2. 通知系统完全未实现

---

### 2.10 订阅 API (Subscription)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/subscriptions/plans` | `/subscriptions/plans` | GET | ⚠️ **部分实现** | 返回计划列表 |
| `/subscriptions/create-checkout` | `/subscriptions/create-checkout` | POST | ⚠️ **存根** | 返回 "Coming soon" |
| `/subscriptions/current` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现获取当前订阅 |
| `/subscriptions/cancel` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现取消订阅 |

**后端实现**:
```python
@router.get("/plans", response_model=list[PlanResp])
async def list_plans(...):
    # 完全实现
    
@router.post("/create-checkout", response_model=dict)
async def create_checkout(...):
    # 存根 - 返回 {"checkout_url": None, "message": "Coming soon"}
```

**问题**:
1. `create-checkout` 是存根，不可用
2. 获取当前订阅和取消订阅端点缺失

---

### 2.11 秘密矩阵 API (Secrets)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/secrets` | `/secrets` | GET | ⚠️ **路径不匹配** | 后端挂载在 `/secrets`，期望 `/projects/{projectId}/secrets` |
| `/projects/{projectId}/secrets/character/{characterId}` | `/secrets/character/{character_name}` | GET | ⚠️ **路径不匹配** | 后端使用 character_name，前端使用 characterId |
| `/projects/{projectId}/secrets/character/{characterId}` | `/secrets/character/{character_id}` | PUT | ⚠️ **路径不匹配** | 同上 |

**后端实现**:
```python
# secret.py 挂载在 /secrets (需要项目级前缀)
@router.get("", response_model=list[SecretResp])  # 需要 project_id 作为 query param
@router.get("/character/{character_name}")  # 使用 name 而不是 id
@router.put("/character/{character_id}")  # 这个存在
```

**问题**:
1. **路径不匹配**: 后端挂载在 `/secrets`，但前端期望 `/projects/{projectId}/secrets`
2. **参数不匹配**: 后端 GET 使用 `character_name`，前端使用 `characterId`
3. 路由注册 `__init__.py` 中可能没有包含 secret 路由

---

### 2.12 模板 API (Templates)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/templates` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/templates/{templateId}` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/templates` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |
| `/templates/{templateId}` | ❌ 未挂载 | DELETE | ❌ **未实现** | 路由存根 |

**问题**:
1. 后端 `template.py` 是存根
2. 模板系统完全未实现

---

### 2.13 编织 API (Weave)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/weave/patterns` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/weave/patterns/{patternId}` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/projects/{projectId}/weave/apply` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现应用编织模式 |

**问题**:
1. 后端 `weave.py` 是存根
2. 编织系统完全未实现

---

### 2.14 导入 API (Import/Ingest)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/ingest/projects/{projectId}/jobs` | `/api/v1/ingest/projects/{projectId}/jobs` | POST | ⚠️ **路径不匹配** | 后端有 `/api/v1` 前缀 |
| `/ingest/projects/{projectId}/jobs` | `/api/v1/ingest/projects/{projectId}/jobs` | GET | ⚠️ **路径不匹配** | 同上 |
| `/ingest/projects/{projectId}/jobs/{jobId}` | `/api/v1/ingest/jobs/{jobId}` | GET | ⚠️ **路径不匹配** | 后端路径不同 |

**后端实现**:
```python
# ingest/router.py - 注意它有自己单独的 prefix
router = APIRouter(prefix="/api/v1/ingest", tags=["Ingest"])

# 但主应用已经挂载了 /api/v1，所以这会导致重复前缀 /api/v1/api/v1/ingest
```

**问题**:
1. **路径重复**: `ingest/router.py` 定义了自己的 `prefix="/api/v1/ingest"`，但主应用已经挂载了 `/api/v1`，导致实际路径变成 `/api/v1/api/v1/ingest/...`
2. **路径不匹配**: 前端期望 `/ingest/...`，但实际后端路径是 `/api/v1/ingest/...` (或错误的 `/api/v1/api/v1/ingest/...`)
3. **路由未注册**: `ingest/router.py` 可能没有被包含在主 `api_router` 中

---

### 2.15 草稿 API (Draft)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/chapters/{chapterId}/draft` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现草稿保存 |
| `/projects/{projectId}/chapters/{chapterId}/draft` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现草稿获取 |

**问题**:
1. 后端完全没有实现草稿系统

---

### 2.16 章节智能体 API (Chapter Agent)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/chapters/{chapterId}/suggestions` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现建议接口 |
| `/projects/{projectId}/chapters/{chapterId}/agent` | ❌ 不存在 | POST | ❌ **缺失** | 后端未实现智能体接口 |

**问题**:
1. 后端完全没有实现章节智能体

---

### 2.17 Phase 4 审核 API

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/phase4/pending-reviews` | ❌ 未挂载 | GET | ❌ **未实现** | 路由存根 |
| `/phase4/reviews/{reviewId}/approve` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |
| `/phase4/reviews/{reviewId}/reject` | ❌ 未挂载 | POST | ❌ **未实现** | 路由存根 |

**问题**:
1. 后端 `phase4.py` 是存根
2. Phase 4 审核系统完全未实现

---

### 2.18 抽卡历史 API (Draw History)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/projects/{projectId}/draw-history` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |
| `/projects/{projectId}/draw-history/{drawId}` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |

**问题**:
1. 后端完全没有实现抽卡历史

---

### 2.19 管理 API (Admin)

| 前端调用 | 后端路由 | HTTP 方法 | 状态 | 备注 |
|---------|---------|----------|------|------|
| `/admin/stats` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |
| `/admin/users` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |
| `/admin/users/{userId}` | ❌ 不存在 | PUT | ❌ **缺失** | 后端未实现 |
| `/admin/projects` | ❌ 不存在 | GET | ❌ **缺失** | 后端未实现 |

**问题**:
1. 后端完全没有实现管理接口

---

## 3. 关键问题汇总

### 3.1 严重问题 (Critical)

1. **后端大部分 API 未实现** (88% 的端点是存根)
   - 影响: 前端几乎所有功能都无法正常工作
   - 建议: 优先实现核心功能 (项目、章节、生成)

2. **路由挂载错误**
   - `chapter.py` 和 `card.py` 挂载在 `/chapters` 和 `/cards`，但前端期望嵌套在 `/projects/{id}/...` 下
   - 建议: 重新设计路由结构或使用动态路由参数

3. **ingest 路由前缀重复**
   - `ingest/router.py` 定义了自己的 `/api/v1/ingest` 前缀，但主应用已经挂载了 `/api/v1`
   - 建议: 移除 ingest 路由中的 `/api/v1` 前缀

### 3.2 重要问题 (High)

1. **路径不匹配**
   - Secrets API: 后端 `/secrets`，前端期望 `/projects/{projectId}/secrets`
   - Ingest API: 路径结构不一致

2. **参数不匹配**
   - Secrets API: 后端使用 `character_name`，前端使用 `characterId`

3. **缺失的端点** (部分列表)
   - `/auth/password-reset-request`
   - `/projects/{id}/stats`
   - 所有 Vault 相关端点
   - 所有 Health 项目级端点
   - 所有 Settings 端点
   - 所有 Notifications 端点
   - 所有 Admin 端点

### 3.3 中等问题 (Medium)

1. **响应格式可能不匹配**
   - 前端期望 `ApiResponse<T>` 格式: `{ code, message, data, meta }`
   - 后端使用 `ResponseFormatMiddleware` 包装，但需要验证格式是否完全一致

2. **错误处理不一致**
   - 前端期望特定的错误消息格式
   - 后端需要检查所有异常是否都被正确捕获并格式化为统一格式

---

## 4. 建议的修复优先级

### P0 (立即修复)
1. 实现 `project.py` 路由 (项目 CRUD)
2. 实现 `chapter.py` 路由 (章节 CRUD)
3. 修复路由挂载问题 (chapter, card 的嵌套路径)
4. 修复 ingest 路由前缀重复问题

### P1 (高优先级)
1. 实现 `generation.py` 路由 (生成功能)
2. 实现 `card.py` 路由 (卡牌池和抽卡)
3. 实现 `vault.py` 路由 (知识库核心功能)
4. 添加缺失的认证端点 (`/auth/password-reset-request`)

### P2 (中优先级)
1. 实现 `notification.py` 路由
2. 实现 `setting.py` 路由
3. 完善 `subscription.py` 路由
4. 修复 `secret.py` 路径和参数不匹配

### P3 (低优先级)
1. 实现 `template.py` 路由
2. 实现 `weave.py` 路由
3. 实现 `phase4.py` 路由
4. 实现草稿、智能体、抽卡历史、管理接口

---

## 5. 测试用例建议

由于后端大部分 API 未实现，目前无法进行有效的集成测试。建议：

1. **先完成后端实现**，然后编写端到端测试
2. **使用 Mock 模式**: 前端已经支持 `NEXT_PUBLIC_MOCK_ENABLED=true` 来模拟 API 响应
3. **推荐测试工具**:
   - 后端: `pytest` + `httpx` (已经配置在 `moling-server/tests/`)
   - 前端: Jest + MSW (Mock Service Worker)
   - 集成: Cypress 或 Playwright E2E 测试

---

## 6. 结论

当前墨灵项目的前后端的集成状态**不可用于生产**。后端大部分 API 端点都是自动生成的存根，无法提供实际功能。前端代码定义了完整的 API 调用层，但无法成功调用后端。

**建议**:
1. 后端团队优先实现 P0 和 P1 功能的 API 端点
2. 修复路由挂载和路径匹配问题
3. 实现后，运行完整的集成测试套件
4. 考虑使用契约测试 (Contract Testing) 来确保前后端 API 一致性

---

**报告生成时间**: 2026-06-14  
**下一步**: 等待后端 API 实现完成后，重新运行集成测试
