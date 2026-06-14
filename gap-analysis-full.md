# 墨灵代码实现 vs 三份规格文档 — 全面差异分析

> 审计方法：将 3 份文档（012_后端设计文档、009_算法文档、015_前后端接口映射）逐条与实际后端代码和前端代码对比  
> 审计范围：后端路由 52 个 + 前端 API 28 个 + 前端页面 12 页 + 算法功能点 ~75 个  
> 审计日期：2026-06-13 | 审计员：audit-router + audit-frontend + audit-algo + audit-algo-2 并行作业

---

## 一、总览

### 1.1 覆盖度矩阵

| 维度 | 已实现 | 未实现 | 部分实现/路径不一致 |
|------|:------:|:------:|:------------------:|
| 015 映射文档端点 (63) | 25 (40%) | 24 (38%) | 14 (22%) |
| 后端设计文档功能点 (~80) | 42 (53%) | 30 (37%) | 8 (10%) |
| 算法文档功能点 (~75) | 40 (53%) | 32 (43%) | 3 (4%) |
| 前端 API 函数 (28) | 28 (100%)* | — | — |

> 注：前端 28 个 API 函数全部有定义，但其中 3 个是 mock 空列表（healthApi），2 个调用后端不存在的路径（confirm/revise）

### 1.2 路径差异 vs 功能缺失

项目中存在两种不同性质的 GAP：

1. **路径/方法不一致**（低风险）：功能代码已实现，但路径命名与文档不同。更新文档或统一路径即可。
2. **功能完全缺失**（高风险）：代码中不存在该功能，需要从零实现。

---

## 二、015 映射文档端点逐条审计

### ✅ 已实现且匹配 (25 个)

| # | 文档路径 | 后端状态 | 前端状态 |
|:-:|:---------|:--------:|:--------:|
| 1 | GET /api/v1/projects | ✅ | ✅ |
| 2 | GET /api/v1/projects/stats | ✅ | ✅ |
| 3 | POST /api/v1/projects | ✅ | ✅ |
| 4 | GET /api/v1/projects/:id | ✅ | ✅ |
| 5 | DELETE /api/v1/projects/:id | ✅ | ✅ |
| 6 | GET /api/v1/projects/:pid/chapters | ✅ | ✅ |
| 7 | GET /api/v1/projects/:pid/chapters/:id | ✅ | ✅ |
| 8 | POST /api/v1/projects/:pid/chapters | ✅ | ✅ |
| 9 | GET /api/v1/projects/:pid/chapters/current | ✅ | ✅ |
| 10 | POST /api/v1/auth/login | ✅ | ✅ |
| 11 | POST /api/v1/auth/register | ✅ | ✅ |
| 12 | POST /api/v1/auth/refresh | ✅ | ✅ |
| 13 | GET /api/v1/auth/me | ✅ | ✅ |
| 14 | GET /api/v1/projects/:pid/vault/characters | ✅ | ✅ |
| 15 | GET /api/v1/projects/:pid/vault/timeline | ✅ | ✅ |
| 16 | GET /api/v1/projects/:pid/vault/plot-promises | ✅ | ✅ |
| 17 | GET /api/v1/projects/:pid/vault/world | ✅ | ✅ |
| 18 | GET /api/v1/projects/:pid/cards/pool | ✅ (路径不同: `/cards/pool`) | ✅ (路径: `/cards/pool`) |
| 19 | POST /api/v1/projects/:pid/cards/draw | ✅ (路径不同: `/cards/draw`) | ✅ (路径: `/cards/draw`) |
| 20 | POST /api/v1/projects/:pid/chapters/:id/generate | ✅ (路径不同: `/generation/trigger`) | ✅ (路径: `/generation/trigger`) |
| 21 | GET /api/v1/generate/:task_id/status | ✅ (路径不同: `/generation/task/{id}`) | ✅ (路径: `/generation/task/{id}`) |
| 22 | GET /api/v1/projects/:pid/vault/characters/:id | ✅ | ❌ 前端 vaultApi 未调用 |
| 23 | POST /api/v1/projects/:pid/vault/characters | ✅ | ❌ 前端 vaultApi 未调用 |
| 24 | GET /api/v1/projects/:pid/vault/plot-promises/:id | ✅ | ❌ 前端 vaultApi 未调用 |
| 25 | POST /api/v1/projects/:pid/vault/plot-promises | ✅ | ❌ 前端 vaultApi 未调用 |

### ⚠️ 路径/方法不一致 (14 个)

| # | 文档路径 (方法) | 实际后端 | 差异说明 |
|:-:|:---------------|:---------|:---------|
| 1 | PUT /api/v1/projects/:id | PATCH /{project_id} | PUT→PATCH（建议更新文档） |
| 2 | PUT /api/v1/projects/:pid/chapters/:id | PATCH /{chapter_id} | PUT→PATCH（建议更新文档） |
| 3 | GET /api/v1/projects/:pid/cards/pool?count=3 | /cards/pool?project_id=xxx | 路径结构不同 |
| 4 | POST /api/v1/projects/:pid/cards/draw | /cards/draw?project_id=xxx | 路径结构不同 |
| 5 | POST /api/v1/projects/:pid/chapters/:id/generate | /generation/trigger | 路径结构不同 |
| 6 | GET /api/v1/generate/:task_id/status | /generation/task/{task_id} | generate→generation |
| 7 | POST /api/v1/projects/:pid/import | /ingest/projects/{pid}/jobs | import→ingest |
| 8 | GET /api/v1/projects/:pid/import/:jobid | /ingest/jobs/{job_id} | import→ingest |
| 9 | POST /api/v1/projects/:pid/import/:jobid/phase1 | /ingest/jobs/{job_id}/phase1 | import→ingest |
| 10 | POST /api/v1/projects/:pid/import/:jobid/phase2 | /ingest/jobs/{job_id}/phase2 | import→ingest |
| 11 | POST /api/v1/projects/:pid/import/:jobid/confirm | /ingest/jobs/{job_id}/phase3 | 路径+名称不同 |
| 12 | GET /api/v1/projects/:pid/vault/timeline/:id | 后端不存在—无单条时间线详情 | 文档有，后端无 |
| 13 | GET /api/v1/projects/:pid/vault/world/:id | 后端不存在—无单条世界观详情 | 文档有，后端无 |
| 14 | PATCH /api/v1/settings (文档写 PUT) | 后端不存在整套 | 方法差异已无意义 |

### ❌ 后端完全缺失的端点 (24 个)

| # | 文档路径 | 前端状态 | 严重度 |
|:-:|:---------|:--------:|:------:|
| 1 | POST /api/v1/generate/:task_id/cancel | ✅ 已实现但后端无 | **严重** |
| 2 | GET /api/v1/weave-patterns | ❌ 不存在 | 中等 |
| 3 | PUT /api/v1/projects/:id/draft | ❌ 不存在 | 中等 |
| 4 | GET /api/v1/templates | ❌ 不存在 | 中等 |
| 5 | GET /api/v1/projects/suggestions | ❌ 不存在 | 低 |
| 6 | POST /api/v1/projects/:pid/chapters/:id/confirm | ✅ 前端有但后端无 | **严重** |
| 7 | POST /api/v1/projects/:pid/chapters/:id/revise | ✅ 前端有但后端无 | **严重** |
| 8 | GET /api/v1/projects/:pid/chapters/:id/suggestions | ❌ 不存在 | 中等 |
| 9 | POST /api/v1/projects/:pid/chapters/:id/agent | ❌ 不存在 | 低 |
| 10 | GET /api/v1/phase4/pending-reviews | ❌ 不存在 | 低 |
| 11 | GET /api/v1/projects/:pid/vault/summary | ❌ 不存在 | 中等 |
| 12 | PUT /api/v1/projects/:pid/vault/characters/:id | ❌ 不存在 | **严重** |
| 13 | PUT /api/v1/projects/:pid/vault/plot-promises/:id | ❌ 不存在 | 中等 |
| 14 | GET /api/v1/projects/:pid/secrets (全部 3 个) | ❌ 不存在 | 中等 |
| 15 | POST /api/v1/projects/:pid/vault/full-reanalyze | ❌ 不存在 | 低 |
| 16 | GET /api/v1/projects/:pid/health | ❌ (mock 空数组) | 中等 |
| 17 | POST /api/v1/projects/:pid/health/refresh | ❌ (mock 空数组) | 中等 |
| 18 | GET /api/v1/settings (全部 6 个 Settings 端点) | ❌ 不存在 | **严重** |
| 19 | PUT /api/v1/auth/me | ❌ 不存在 | 中等 |
| 20 | POST /api/v1/auth/password-reset-request | ✅ 前端有路径不同 | 中等 |
| 21 | POST /api/v1/auth/password-reset | ✅ 前端有路径不同 | 中等 |
| 22 | GET /api/v1/subscriptions/plans (全部 2 个) | ❌ 不存在 | 低 |
| 23 | GET /api/v1/notifications (全部 3 个) | ❌ 不存在 | 低 |
| 24 | GET /api/v1/projects?q=keyword | ❌ 不支持搜索 | 低 |

---

## 三、后端设计文档 vs 实际代码

### 3.1 架构差异

| 文档要求 | 实际代码 | 差异 |
|:---------|:---------|:-----|
| 6 层中间件链（RequestID/Auth/CORS/RateLimit/AuditLog/ResponseFormat） | 只有 CORSMiddleware | 缺失 5 个中间件 |
| 路由层在 `app/api/v1/` | 实际在 `app/router/` | 功能等价 |
| 统一的 `{code, message, data, request_id}` 响应格式 | 直接返回裸数据 | 无统一包装 |
| Service 层通过构造函数 DI 注入 DAO | 部分 Service 硬编码 DAO | **不一致** |
| `phase4_service.py` | **不存在** | 严重缺失 |
| `card_service.py` | **不存在** | 逻辑在 router 中 |
| `setting_service.py` | **不存在** | 严重缺失 |
| `vault_service.py` PUT/DELETE 端点 | **不存在** | 只有 GET/POST |
| `llm/gateway.py` (LLMGateway) | **不存在** | 只有 LLMClient |
| `llm/router.py` (模型路由) | **不存在** | 无 |
| `llm/context.py` (上下文管理) | **不存在** | 无 |
| `llm/prompts/` 目录 (独立 Prompt 文件) | `llm/prompts.py` 单文件 | 简化 |
| `middleware/` 目录 (独立中间件文件) | **不存在** | 严重缺失 |
| `tasks/` 目录 (独立 Celery 任务文件) | `worker/tasks.py` 单文件 | 只有 1 个任务 |
| Celery Beat 定时任务 | **不存在** | 无定时淘汰/检查 |
| `tests/` 目录 (按层测试) | **不存在** | **严重缺失** |
| Alembic 迁移 `alembic/` | **不存在** | 无迁移管理 |
| `docker/` | **不存在** | 无容器化 |
| `Dockerfile` | **不存在** | 无容器化 |

### 3.2 数据模型差异

| 文档定义的模型 | 代码状态 | 差异 |
|:--------------|:--------:|:-----|
| `DynamicLayer` (独立表) | ❌ 不存在 | 字段在 Chapter 的 JSONB 中 |
| `DrawHistory` (设计文档名) | ⚠️ | 代码中为 `DrawRecord` |
| `DynamicLayerSnapshot` (设计文档 §4.3 JSONB Schema) | ❌ 不存在 | 无独立验证结构 |
| `settings` 表 | ❌ 不存在 | 设置无后端存储 |
| `CardPoolHistory` (class diagram) | ❌ 不存在 | 无退役记录 |
| `vault_changelog` (class diagram) | ❌ 不存在 | 无变更日志 |
| VaultPlotPromise.event_type | ❌ 不存在 | 算法文档要求的字段 |
| `secrets` 表/模型 | ❌ 不存在 | 秘密矩阵无存储 |
| `weave_patterns` 表 | ❌ 不存在 | 编织模式无存储 |

### 3.3 API 差异

| 设计文档要求的端点 | 实际代码 |
|:------------------|:---------|
| POST /auth/logout | ❌ 不存在 |
| GET /me (用户信息) | ✅ |
| PUT /me (更新资料) | ❌ |
| POST /projects/:id/draft | ❌ |
| GET /templates | ❌ |
| PUT /vault/characters/:id | ❌ (vault 无更新) |
| PUT /vault/plot-promises/:id | ❌ |
| DELETE /vault/characters/:id | ❌ |
| DELETE /vault/plot-promises/:id | ❌ |
| DELETE /vault/world/:id | ❌ |
| POST /cards/retire | ❌ |
| POST /generate (实时生文) | ⚠️ 实际为 /generation/trigger |
| POST /phase4/confirm | ❌ |
| GET /tasks/:task_id | ⚠️ 实际为 /generation/task/:id |
| GET /settings | ❌ |
| PUT /settings | ❌ |
| POST /import (文件上传) | ✅ (通过 /ingest) |

---

## 四、算法文档 vs 实际代码（关键差异）

### 4.1 算法引擎

| 算法步骤 | 文档位置 | 代码状态 |
|:---------|:---------|:--------:|
| [1] 权重分配 | §2.1 | ❌ |
| [2] 四库过滤 | §3.4 | ❌ |
| [3] 动态层冲突检测 | §3.3 | ❌ |
| [4] 方向冲突评分 | §3.3-3.4 | ❌ |
| [5] 编织方案匹配 | §3.6 | ❌ |
| [6] 大纲模板填充 | §3.6 | ❌ |
| [7] 叙事元素提取 (小模型) | §2.1 | ❌ |
| [8] 头脑风暴发散 (中模型) | §2.1 | ❌ |
| [9] 正文写作 (大模型) | §2.1 | ⚠️ 简化实现 |
| [10] 连贯性校验 | §5.2 | ❌ |
| [11] 动态层更新 | §2.1 Phase 3 | ❌ |
| [12] 前情摘要更新 | §2.1 | ❌ |
| [13] 动态层版本化 | §2.1 | ❌ |
| [14]-[22] Phase 4 整套 | §11 | ❌ 完全缺失 |
| 抽卡加权随机算法 | §6.2 | ❌ |
| 分层保底 | 后端设计§6.2.2 | ❌ |
| 新鲜期加权 | §4.0 | ⚠️ 有字段无逻辑 |
| 久未出现加成 | §4.0 | ❌ |
| LRU 淘汰检查 | §4.0 | ❌ |
| 重抽上限 (3次) | §2.2 P3 | ❌ |
| 方向相容性检测 | §3.3-3.4 | ❌ |
| 秘密矩阵生命周期 | §2.8 | ❌ |
| 秘密债务模型 | §2.8.2 | ❌ |
| R1/R2/R3 健康监控 | §5.3 | ❌ |
| 四层注入 prompt 架构 | §3.1-3.5 | ❌ |
| Phase 4 调度器 | §12 | ❌ |
| SourceText 验证 | §11.6 | ❌ |
| API Key Pool | §2.7 | ❌ |

### 4.2 已实现的算法

| 模块 | 状态 | 文件 |
|:-----|:----:|:-----|
| A1-A5 拆书引擎 | ✅ 全部 | `app/genre/` |
| Phase 0 分章预处理 | ✅ 全部 | `app/ingest/scraper/` |
| Phase 1 四库提取 | ✅ 全部 | `app/ingest/phase1/` |
| Phase 2 动态层分析 | ✅ 全部 | `app/ingest/phase2/` |
| Phase 3 导入审核 | ✅ 全部 | `app/ingest/phase3/` |
| 文风分析器 | ✅ | `scraper/core/style_analyzer.py` |

---

## 五、前端页面 vs API 后端匹配状态

| 页面 | 路由 | 前端实现 | 需调用的 API 后端状态 | 综合状态 |
|:-----|:-----|:--------:|:--------------------:|:--------:|
| Landing | `/` | 静态页，无 API | — | ✅ |
| Auth | `/auth` | ✅ 完整 | 4/7 端点已实现 | ⚠️ 密码重置缺失 |
| Projects | `/projects` | ✅ 完整 | 5/7 端点已实现 | ⚠️ 搜索/draft 缺失 |
| New Project | `/projects/new` | ✅ 完整 | 1/4 端点已实现 | ❌ 模板/建议缺失 |
| Workspace | `/workspace/[id]` | ✅ 前端骨架 | 6/13 端点已实现 | **❌** confirm/revise 缺失 |
| Vault | `/vaults/[id]` | ✅ UI 完整 | 6/12 端点已实现 | ⚠️ 编辑/秘密缺失 |
| Settings | `/settings` | ✅ UI mock | 0/6 端点已实现 | **❌** 完全 mock |
| Import | `/projects/[id]/import` | ✅ UI mock | 后端已有(路径不同) | ⚠️ 前端未接入 |
| Pricing | `/pricing` | 硬编码数据 | 0/2 端点已实现 | ❌ 完全 mock |
| Notifications | `/notifications` | mock 数据 | 0/3 端点已实现 | ❌ 完全 mock |
| Admin | `/admin` | LLM 配置功能 | 2/6 端点已实现 | ⚠️ 部分实现 |
| 404 | `/*` | 静态页 | — | ✅ |

---

## 六、前端 API 调用 vs 后端实际路由

| 前端函数 | 方法+路径 | 后端匹配 | 备注 |
|:---------|:---------|:--------:|:-----|
| authApi.login | POST /auth/login | ✅ | |
| authApi.register | POST /auth/register | ✅ | |
| authApi.refreshToken | POST /auth/refresh | ✅ | |
| authApi.getMe | GET /auth/me | ✅ | |
| projectApi.list | GET /projects | ✅ | |
| projectApi.getStats | GET /projects/stats | ✅ | |
| projectApi.create | POST /projects | ✅ | |
| projectApi.getById | GET /projects/:id | ✅ | |
| projectApi.update | PATCH /projects/:id | ✅ | 文档写 PUT |
| projectApi.delete | DELETE /projects/:id | ✅ | |
| chapterApi.getCurrent | GET /projects/:pid/chapters/current | ✅ | |
| chapterApi.list | GET /projects/:pid/chapters | ✅ | |
| chapterApi.create | POST /projects/:pid/chapters | ✅ | |
| chapterApi.getById | GET /projects/:pid/chapters/:cid | ✅ | |
| chapterApi.update | PATCH /projects/:pid/chapters/:cid | ✅ | 文档写 PUT |
| chapterApi.deleteChapter | DELETE /projects/:pid/chapters/:cid | ✅ | |
| cardApi.getPool | GET /cards/pool?project_id=x | ✅ | 路径与文档不同 |
| cardApi.drawCards | POST /cards/draw | ✅ | 路径与文档不同 |
| cardApi.redraw | POST /cards/draw | ⚠️ 复用 draw 端点 | 无独立 redraw |
| generationApi.generate | POST /generation/trigger | ✅ | |
| generationApi.getStatus | GET /generation/task/:id | ✅ | |
| **generationApi.cancel** | POST /generation/task/:id/cancel | ❌ **后端缺失** | **严重** |
| **generationApi.confirm** | POST /chapters/:cid/confirm | ❌ **后端缺失** | **严重** |
| **generationApi.revise** | POST /chapters/:cid/revise | ❌ **后端缺失** | **严重** |
| vaultApi.getCharacters | GET /projects/:pid/vault/characters | ✅ | |
| vaultApi.getTimeline | GET /projects/:pid/vault/timeline | ✅ | |
| vaultApi.getPlotPromises | GET /projects/:pid/vault/plot-promises | ✅ | |
| vaultApi.getWorld | GET /projects/:pid/vault/world | ✅ | |
| healthApi.getAlerts | — (mock) | ❌ 返回空数组 | |
| healthApi.refreshCheck | — (mock) | ❌ 返回空数组 | |

---

## 七、优先级修复计划

### P0 — 必须优先修复（核心流程断裂）

| # | 修复项 | 影响 | 预估工作量 |
|:-:|:-------|:-----|:----------|
| 1 | 后端实现 `POST /chapters/:id/confirm` | 工作台确认收纳流程断裂 | 2 天 |
| 2 | 后端实现 `POST /chapters/:id/revise` | 工作台拒稿重写流程断裂 | 1 天 |
| 3 | 后端实现 `POST /generation/task/:id/cancel` | 生成任务无法取消 | 0.5 天 |
| 4 | 后端实现 Settings 全套 6 个端点 | 设置页面完全是 mock | 3 天 |
| 5 | 后端实现 `PUT /vault/characters/:id` | 角色信息无法编辑保存 | 1 天 |

### P1 — 高优先级（功能不完整）

| # | 修复项 | 影响 | 预估工作量 |
|:-:|:-------|:-----|:----------|
| 6 | 后端实现 `PUT /vault/plot-promises/:id` | 伏笔无法编辑 | 1 天 |
| 7 | 后端实现 `GET /vault/summary` | 四库总览不可用 | 0.5 天 |
| 8 | 后端实现密码重置全套流程 | 密码无法重置 | 2 天 |
| 9 | 后端实现项目级健康告警 `GET /health` | 健康监控不可用 | 1 天 |
| 10 | 前端 cardApi + vaultApi 补齐缺失方法 | 详情/创建功能未连接 | 2 天 |
| 11 | 前端章节操作路径加 project_id 前缀 | 路径规范化 | 1 天 |
| 12 | 导入页面前端接入后端 `/ingest` 路由 | 导入功能完全未连接 | 3 天 |

### P2 — 中等优先级（体验优化）

| # | 修复项 | 预估工作量 |
|:-:|:-------|:----------|
| 13 | 实现抽卡加权算法（加权随机+保底+重抽限制） | 3 天 |
| 14 | 实现 6 层中间件链（RequestID + RateLimit + Auth + Logging + Format） | 2 天 |
| 15 | 统一 `{code, message, data}` 响应格式 | 1 天 |
| 16 | 统一路径命名规范（cards/import/generation 路径标准化） | 1 天 |
| 17 | 实现四库搜索 `?q=` 和角色过滤 `?role=` | 1 天 |
| 18 | 实现 secrets 秘密矩阵端点 (3 个) | 2 天 |
| 19 | 实现 CardService 抽卡历史 `GET /cards/history` | 1 天 |
| 20 | 实现生成历史 `GET /generation/history` | 1 天 |
| 21 | 实现编织模式 `GET /weave-patterns` | 0.5 天 |

### P3 — 长期优化（算法功能完整）

| # | 修复项 | 预估工作量 |
|:-:|:-------|:----------|
| 22 | 实现 Phase 4 全流程收纳调度器 | 5-7 天 |
| 23 | 实现生成流水线算法步骤 [1]-[12] | 5-7 天 |
| 24 | 实现连贯性校验 (Pre + Post 7-step) | 3-4 天 |
| 25 | 实现秘密矩阵生命周期 + 债务模型 | 3 天 |
| 26 | 实现 R1/R2/R3 健康监控 | 2 天 |
| 27 | 实现四层注入 Prompt 架构 | 2 天 |
| 28 | 实现 API Key Pool + Fallback 链 | 2 天 |
| 29 | 添加 Alembic 迁移管理 | 1 天 |
| 30 | 添加 Docker 容器化 | 1 天 |
| 31 | 添加测试覆盖（tests/ 目录） | 5 天 |

---

## 八、文档同步建议

1. **015 映射文档路径更新**：将 import→ingest, generate→generation, cards 路径结构统一
2. **012 设计文档架构图同步**：实际路由在 `router/` 而非 `api/v1/`
3. **009 算法文档 direction_type 同步**：中文分类 vs 代码英文分类，统一为英文
4. **为已实现模块补文档**：Admin LLM Config、Style Analyzer 在文档中未提及
5. **添加实现状态标记**：在每节开头标注 "✅ 已实现 / ⚠️ 部分实现 / ❌ 待实现"
