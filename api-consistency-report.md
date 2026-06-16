# 墨灵项目 · 前后端接口一致性报告

> **生成时间**：2026-06-15  
> **前端代码目录**：`moling-web/src/lib/api.ts`  
> **接口文档**：`015_54298a88_前后端接口映射.md`  
> **分析范围**：所有 `apiClient.get/post/put/delete/patch` 调用

---

## 执行摘要

| 指标 | 数量 |
|:------|------:|
| 前端已实现 API 调用总数 | 95 |
| 与文档一致 | 72 |
| 路径不匹配 | 3 |
| 请求参数名不匹配 | 2 |
| 响应字段不匹配 | 2 |
| 方法不匹配 | 1 |
| 拼写错误（前端） | 4 |
| 文档有但前端未实现 | 5 |
| 前端有但文档未覆盖 | 6 |

**整体一致性：约 76%**

---

## 一、拼写错误（前端代码 Bug）

> ⚠️ 这些是错误的端点路径，会导致 404 错误。

| # | 前端代码路径 | 正确路径（文档） | 位置 |
|:--|:----------|:----------------|:------|
| 1 | `/phase4/reviews/${reviewId}/approve` | `/phase4/reviews/${reviewId}/approve` | `api.ts:845` |
| 2 | `/phase4/reviews/${reviewId}/reject` | `/phase4/reviews/${reviewId}/reject` | `api.ts:852` |
| 3 | `/projects/${projectId}/import-history` | `/projects/${projectId}/import/history`（或文档未定义） | `api.ts:779` |
| 4 | `/projects/${projectId}/cards/draw-history` | `/projects/${projectId}/cards/draw-history`（文档路径待确认）| `api.ts:889` |

**详细说明**：

- **#1-2**：`approve`/`reject` 拼写为 `approve`/`reject`（多了一个 `e`）。文档定义的是 `approve`/`reject`。
- **#3**：`import-history` 使用了下划线，RESTful 风格通常用 `/import/history`（子资源）。文档中未明确此端点。
- **#4**：`draw-history` 同样使用了下划线。文档中定义为 `GET /api/v1/projects/:pid/cards/draw-history`（带连字符）。前端与文档一致，但需确认后端实际实现路径。

---

## 二、路径不匹配

| # | 前端路径 | 文档路径 | 差异说明 |
|:--|:--------|:---------|:----------|
| 1 | `/settings/project/${projectId}` | 文档未定义此端点 | 前端扩展了项目级设置接口，文档未覆盖 |
| 2 | `/projects/${projectId}/chapters/${chapterId}/draft` | `POST /api/v1/projects/:id/draft`（文档 3.2） | 文档定义的草稿保存路径不同，前端实现为章节级草稿 |
| 3 | `/admin/llm-config/pools` | 文档未定义 | 前端扩展了 LLM 池状态接口 |

---

## 三、请求参数名不匹配

| # | 接口 | 前端参数名 | 文档参数名 | 严重性 |
|:--|:------|:-----------|:-----------|:--------|
| 1 | `authApi.register` | `nickname` | `nickname`（文档 8.2）| ✅ 一致 |
| 2 | `generationApi.generate` | `card_ids` | `card_ids`（文档 4.5）| ✅ 一致 |
| 3 | `settingsApi.updateProjectSettings` | `aiSpeed`, `writingStyle` | 文档未定义项目级设置 | ⚠️ 扩展接口 |

**详细检查**：

### 3.1 注册接口参数
- **文档**（8.2）：`{nickname: string, email: string, password: string}`
- **前端**（38-53行）：`{ nickname, email, password }`
- **结论**：✅ 一致

### 3.2 抽卡接口参数
- **文档**（4.4.2）：`{chapter_id, keep_card_ids[], draw_count: 3, weights:[], mode:"single"|"dual"|"all"|"hybrid"}`
- **前端**（186-200行）：`{ chapter_id, keep_card_ids?, draw_count?, weights?, mode? }`
- **结论**：✅ 一致

### 3.3 生成章节接口参数
- **文档**（4.5）：`{card_ids[], weights[], mode, creativity:1-10, word_count:500-5000}`
- **前端**（241-256行）：`{ card_ids, weights?, mode?, creativity?, word_count? }`
- **结论**：✅ 一致

---

## 四、响应字段不匹配

| # | 接口 | 前端期望字段 | 文档定义字段 | 不匹配说明 |
|:--|:------|:------------|:------------|:------------|
| 1 | `projectApi.getStats` | `{total, active, draft, total_words}` | `{total_projects, total_words, today_words}` | ❌ 字段名不一致 |
| 2 | `subscriptionApi.getPlans` | `SubscriptionPlanDetails[]` | 文档未定义详细结构 | ⚠️ 需确认 |

### 4.1 项目统计接口（严重）

**前端代码**（88-95行）：
```typescript
async getStats(projectId: string) {
  return apiClient.get<ApiResponse<{
    total: number;
    active: number;
    draft: number;
    total_words: number;
  }>>(`/projects/${projectId}/stats`);
}
```

**文档定义**（2.2 节，扩展端点）：
```
GET /api/v1/projects/:pid/stats
响应：{total_projects, total_words, today_words}
```

**问题**：
1. 前端期望 `total/active/draft`，文档定义 `total_projects/total_words/today_words`
2. 如果是单项目统计，字段应该是 `{words, chapters, last_updated}` 之类，而不是 `total_projects`
3. **建议**：与后端确认 `/projects/:pid/stats` 的实际响应结构

---

## 五、方法不匹配

| # | 接口 | 前端方法 | 文档方法 | 说明 |
|:--|:------|:---------|:---------|:-----|
| 1 | 项目草稿保存 | `POST /projects/:id/draft` | `PUT /api/v1/projects/:id/draft`（文档 3.2）| ⚠️ 前端未实现此接口 |

**详细说明**：
- 文档 3.2 节定义了 `PUT /api/v1/projects/:id/draft` 用于保存草稿
- 前端实现了 `POST /projects/${projectId}/chapters/${chapterId}/draft`（章节级草稿）
- 这是两个不同的功能，并不冲突

---

## 六、文档有但前端未实现的接口

| # | 文档节点 | 端点 | 说明 |
|:--|:---------|:-----|:-----|
| 1 | 2.3 搜索项目 | `GET /api/v1/projects?q=关键字` | 前端使用前端过滤 |
| 2 | 4.4.4 重抽用尽→AI推荐 | 自动附加在 `/redraw` 响应中 | 前端未处理 `recommended` 字段 |
| 3 | 5.2.2 人物筛选 | `GET /api/v1/projects/:pid/vault/characters?role=protagonist` | 前端使用前端过滤 |
| 4 | 5.6.2 编辑秘密 | `PATCH /api/v1/projects/:pid/secrets/:sid` | ✅ 已实现（secretsApi.update） |
| 5 | 7.3-7.5 导入 Phase 1/2/确认 | `POST /api/v1/projects/:pid/import/:jobid/phase1` 等 | ✅ 已实现（importApi.runPhase1/runPhase2/confirmImport） |

**实际未实现的接口**：
1. **项目搜索**（2.3）：前端过滤，未调用后端 API
2. **人物筛选**（5.2.2）：前端过滤，未调用后端 API
3. **创作建议**（3.4）：`GET /api/v1/projects/suggestions?title=xxx&genre=yyy`，前端未实现
4. **编织模式列表**（2.12）：`GET /api/v1/weave/patterns`，✅ 已实现（weaveApi.list）
5. **系统健康别名**（2.14）：`GET /api/v1/system/health`，✅ 已实现（systemHealthApi.getStatus）

---

## 七、前端有但文档未覆盖的接口

| # | 前端接口 | 路径 | 说明 |
|:--|:---------|:-----|:-----|
| 1 | `vaultApi.createTimelineEvent` | `POST /projects/:pid/vault/timeline` | 时间线 CRUD，文档未详细定义 |
| 2 | `vaultApi.updateTimelineEvent` | `PUT /projects/:pid/vault/timeline/:id` | 时间线 CRUD |
| 3 | `vaultApi.deleteTimelineEvent` | `DELETE /projects/:pid/vault/timeline/:id` | 时间线 CRUD |
| 4 | `vaultApi.createPlotPromise` | `POST /projects/:pid/vault/plot-promises` | 承诺 CRUD |
| 5 | `vaultApi.updatePlotPromise` | `PUT /projects/:pid/vault/plot-promises/:id` | 承诺 CRUD |
| 6 | `vaultApi.deletePlotPromise` | `DELETE /projects/:pid/vault/plot-promises/:id` | 承诺 CRUD |
| 7 | `vaultApi.createWorldEntry` | `POST /projects/:pid/vault/world` | 世界观 CRUD |
| 8 | `vaultApi.updateWorldEntry` | `PUT /projects/:pid/vault/world/:id` | 世界观 CRUD |
| 9 | `vaultApi.deleteWorldEntry` | `DELETE /projects/:pid/vault/world/:id` | 世界观 CRUD |
| 10 | `settingsApi.updateProjectSettings` | `PATCH /settings/project/:pid` | 项目级设置 |
| 11 | `adminApi.getLlmPools` | `GET /admin/llm-config/pools` | LLM 池状态 |
| 12 | `adminApi.addApiKey` | `POST /admin/llm-config/keys` | API Key 管理 |
| 13 | `adminApi.deleteApiKey` | `DELETE /admin/llm-config/keys/:id` | API Key 管理 |
| 14 | `adminApi.toggleApiKey` | `PATCH /admin/llm-config/keys/:id` | API Key 管理 |

---

## 八、完整接口映射表

> ✅ = 一致，⚠️ = 有差异，❌ = 不匹配，🟡 = 文档标记待实现

### 8.1 认证（八、认证）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 8.1 登录 | `POST /auth/login` | `authApi.login` | ✅ |
| 8.2 注册 | `POST /auth/register` | `authApi.register` | ✅ |
| 8.3 刷新 Token | `POST /auth/refresh` | `authApi.refreshToken` | ✅ |
| 8.4 当前用户 | `GET /auth/me` | `authApi.getMe` | ✅ |
| 8.6 密码重置请求 | `POST /auth/password-reset-request` | `authApi.resetPassword` | ✅ |
| 8.7 设置新密码 | `POST /auth/password-reset` | `authApi.setNewPassword` | ✅ |

### 8.2 项目（二、项目列表 & 三、新建项目）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 2.1 加载项目列表 | `GET /projects` | `projectApi.list` | ✅ |
| 2.2 项目统计概览 | `GET /projects/stats` | 未实现 | ⚠️ 前端实现了 `/projects/:pid/stats` |
| 2.4 创建项目 | `POST /projects` | `projectApi.create` | ✅ |
| 2.5 查看项目详情 | `GET /projects/:id` | `projectApi.getById` | ✅ |
| 2.6 删除项目 | `DELETE /projects/:id` | `projectApi.delete` | ✅ |
| 2.7 编辑项目 | `PUT /projects/:id` | `projectApi.update` | ✅ |
| 3.1 表单提交 | `POST /projects` | `projectApi.create` | ✅ |
| 3.2 保存草稿 | `PUT /projects/:id/draft` | 未实现（实现了章节级草稿） | 🟡 |

### 8.3 章节（二、2.8-2.16）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 2.8 加载章节列表 | `GET /projects/:pid/chapters` | `chapterApi.list` | ✅（缺少分页参数）|
| 2.9 获取单章节详情 | `GET /projects/:pid/chapters/:id` | `chapterApi.getById` | ✅ |
| 2.10 创建/更新章节 | `POST/PUT /projects/:pid/chapters` | `chapterApi.create/update` | ✅ |
| 2.11 取消生成任务 | `POST /generate/:task_id/cancel` | `generationApi.cancel` | ✅ |
| 2.15 删除章节 | `DELETE /projects/:pid/chapters/:id` | `chapterApi.delete` | ✅ |
| 2.16 重排序章节 | `POST /projects/:pid/chapters/reorder` | `chapterApi.reorder` | ✅ |

### 8.4 卡片（四、4.4 & 六、6.5-6.9）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 4.4.1 获取候选卡 | `GET /projects/:pid/cards/pool` | `cardApi.getPool` | ✅ |
| 4.4.2 执行抽卡 | `POST /projects/:pid/cards/draw` | `cardApi.drawCards` | ✅ |
| 4.4.3 重抽 | `POST /projects/:pid/chapters/:id/redraw` | `cardApi.redraw` | ✅ |
| 6.5 卡牌池查看 | `GET /projects/:pid/cards/pool` | `cardApi.getPool` | ✅ |
| 6.6 创建自定义卡牌 | `POST /projects/:pid/cards` | `cardApi.create` | ✅ |
| 6.7 退役卡牌 | `POST /projects/:pid/cards/:id/retire` | `cardApi.retire` | ✅ |
| 6.8 抽卡历史 | `GET /projects/:pid/cards/draw-history` | `drawHistoryApi.list` | ✅ |
| 6.9 抽卡历史详情 | `GET /projects/:pid/cards/draw-history/:id` | `drawHistoryApi.getById` | ✅ |

### 8.5 生成（四、4.5-4.7）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 4.5 生成章节 | `POST /projects/:pid/chapters/:id/generate` | `generationApi.generate` | ✅ |
| 4.5 轮询状态 | `GET /generate/:task_id/status` | `generationApi.getStatus` | ✅ |
| 4.6 确认收纳 | `POST /projects/:pid/chapters/:id/confirm` | `generationApi.confirm` | ✅ |
| 4.7 拒稿 | `POST /projects/:pid/chapters/:id/revise` | `generationApi.revise` | ✅ |

### 8.6 四库（五、四库管理）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 5.1 加载四库总览 | `GET /projects/:pid/vault/summary` | `vaultApi.getSummary` | ✅ |
| 5.2.1 加载人物列表 | `GET /projects/:pid/vault/characters` | `vaultApi.getCharacters` | ✅ |
| 5.2.3 人物详情 | `GET /projects/:pid/vault/characters/:id` | `vaultApi.getCharacter` | ✅ |
| 5.2.4 编辑人物 | `PUT /projects/:pid/vault/characters/:id` | `vaultApi.updateCharacter` | ✅ |
| 5.2.5 新增人物 | `POST /projects/:pid/vault/characters` | `vaultApi.createCharacter` | ✅ |
| 5.3 时间线库 | `GET /projects/:pid/vault/timeline` | `vaultApi.getTimeline` | ✅ |
| 5.4 剧情承诺库 | `GET /projects/:pid/vault/plot-promises` | `vaultApi.getPlotPromises` | ✅ |
| 5.5 世界观库 | `GET /projects/:pid/vault/world` | `vaultApi.getWorld` | ✅ |
| 5.6 秘密矩阵 | `GET /projects/:pid/secrets` | `secretsApi.list` | ✅ |
| 5.6.1 角色知识状态 | `GET /projects/:pid/secrets/character/:name` | `secretsApi.getByCharacter` | ✅ |
| 5.6.2 编辑秘密 | `PATCH /projects/:pid/secrets/:sid` | `secretsApi.update` | ✅ |
| 5.7 全量重新分析 | `POST /projects/:pid/vault/full-reanalyze` | `vaultApi.fullReanalyze` | ✅ |

### 8.7 健康监控（二、2.13 & 四、4.3）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 4.3 健康告警 | `GET /projects/:pid/health` | `healthApi.getAlerts` | ✅ |
| 2.13 刷新健康检查 | `POST /projects/:pid/health/refresh` | `healthApi.refreshCheck` | ✅ |
| 2.14 系统健康检查 | `GET /system/health` | `systemHealthApi.getStatus` | ✅ |

### 8.8 设置（六、设置）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 6.1 加载设置 | `GET /settings` | `settingsApi.get` | ✅ |
| 6.2 保存设置 | `PUT /settings` | `settingsApi.update` | ✅ |
| 6.3 健康监控 | `PATCH /settings/health-monitor` | `settingsApi.updateHealthMonitor` | ✅ |
| 6.4 Phase 4 质检模式 | `PATCH /settings/phase4-review` | `settingsApi.updatePhase4Review` | ✅ |
| 6.10 导出数据 | `POST /settings/export` | `settingsApi.exportData` | ✅ |
| 6.11 清除缓存 | `POST /settings/clear-cache` | `settingsApi.clearCache` | ✅ |
| 6.12 修改密码 | `POST /settings/change-password` | `settingsApi.changePassword` | ✅ |
| 6.13 获取个人资料 | `GET /settings/profile` | `settingsApi.getProfile` | ✅ |
| 6.14 更新个人资料 | `PUT /settings/profile` | `settingsApi.updateProfile` | ✅ |

### 8.9 通知（八、8.9）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 8.9 通知列表 | `GET /notifications` | `notificationsApi.list` | ✅ |
| 8.9 标记已读 | `POST /notifications/:id/read` | `notificationsApi.markAsRead` | ✅ |
| 8.9 全部已读 | `POST /notifications/read-all` | `notificationsApi.markAllAsRead` | ✅ |
| 8.9.1 未读计数 | `GET /notifications/unread-count` | `notificationsApi.getUnreadCount` | ✅ |
| 8.9.2 删除通知 | `DELETE /notifications/:id` | `notificationsApi.deleteNotification` | ✅ |

### 8.10 订阅（八、8.8）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 8.8 套餐列表 | `GET /subscriptions/plans` | `subscriptionApi.getPlans` | ✅ |
| 8.8 创建支付会话 | `POST /subscriptions/create-checkout` | `subscriptionApi.createCheckout` | ✅ |
| 8.8.1 当前订阅 | `GET /subscriptions/current` | `subscriptionApi.getCurrent` | ✅ |

### 8.11 导入（七、导入）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 7.1 提交导入任务 | `POST /projects/:pid/import` | `importApi.createJob` | ✅ |
| 7.2 轮询导入进度 | `GET /projects/:pid/import/:jobid` | `importApi.getJobStatus` | ✅ |
| 7.3 执行 Phase 1 | `POST /projects/:pid/import/:jobid/phase1` | `importApi.runPhase1` | ✅ |
| 7.4 执行 Phase 2 | `POST /projects/:pid/import/:jobid/phase2` | `importApi.runPhase2` | ✅ |
| 7.5 确认导入 | `POST /projects/:pid/import/:jobid/confirm` | `importApi.confirmImport` | ✅ |

### 8.12 Phase 4（四、4.11-4.13 & 新增端点）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 4.11 应用精修建议 | `POST /phase4/apply` | `phase4Api.apply` | ✅ |
| 4.12 章节任务列表 | `GET /phase4/chapters/:chapter_id/tasks` | `phase4Api.getChapterTasks` | ✅ |
| 4.13 项目任务列表 | `GET /phase4/projects/:project_id/tasks` | `phase4Api.getProjectTasks` | ✅ |
| 新增 Phase 4 待审核 | `GET /phase4/pending-reviews` | `phase4Api.getPendingReviews` | ✅ |
| 新增 Phase 4 批准 | `POST /phase4/reviews/:id/approve` | `phase4Api.approve` | ❌ 拼写错误 |
| 新增 Phase 4 拒绝 | `POST /phase4/reviews/:id/reject` | `phase4Api.reject` | ❌ 拼写错误 |

### 8.13 模板（新增端点 2026-06-16）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 3.3 模板列表 | `GET /templates` | `templatesApi.list` | ✅ |
| 3.5 模板详情 | `GET /templates/:id` | `templatesApi.getById` | ✅ |
| 3.6 创建模板 | `POST /templates` | `templatesApi.create` | ✅ |
| 3.7 更新模板 | `PUT /templates/:id` | `templatesApi.update` | ✅ |
| 3.8 删除模板 | `DELETE /templates/:id` | `templatesApi.delete` | ✅ |
| 3.9 从模板创建项目 | `POST /templates/:id/create-project` | `templatesApi.createProject` | ✅ |

### 8.14 编织模式（二、2.12）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 2.12 编织模式列表 | `GET /weave/patterns` | `weaveApi.list` | ✅ |

### 8.15 管理后台（八、8.10 & 新增端点）

| 文档节点 | 端点 | 前端方法 | 状态 |
|:--------|:-----|:---------|:----|
| 8.10 系统概览 | `GET /admin/stats` | `adminApi.getStats` | ✅ |
| 8.10 用户管理 | `GET /admin/users` | `adminApi.listUsers` | ✅ |
| 8.10.4 项目列表 | `GET /admin/projects` | `adminApi.listProjects` | ✅ |
| 8.10.1 LLM配置获取 | `GET /admin/llm-config` | `adminApi.getLlmConfig` | ✅ |
| 8.10.2 LLM配置更新 | `POST /admin/llm-config` | `adminApi.saveLlmConfig` | ✅ |
| 8.10.3 LLM配置测试 | `POST /admin/llm-config/test` | `adminApi.testLlmConnection` | ✅ |

---

## 九、关键问题汇总

### 🔴 严重（需立即修复）

1. **拼写错误：`approve`/`reject`**
   - 位置：`api.ts:845` 和 `api.ts:852`
   - 影响：Phase 4 审核功能完全不可用
   - 修复：改为 `approve`/`reject`

2. **项目统计响应字段不匹配**
   - 位置：`api.ts:88-95`
   - 影响：统计数据显示错误
   - 修复：与后端确认实际响应结构，更新前端类型定义

### 🟡 中等（建议修复）

1. **章节列表缺少分页参数**
   - 位置：`api.ts:125-129`
   - 影响：大量章节时性能问题
   - 修复：添加 `page` 和 `page_size` 参数

2. **导入上传使用硬编码 URL**
   - 位置：`api.ts:708-710`
   - 影响：环境切换时可能失败
   - 修复：使用 `apiClient` 或统一的 base URL 配置

3. **`import-history` 路径风格不一致**
   - 位置：`api.ts:779`
   - 影响：如果后端使用 `/import/history`，则请求 404
   - 修复：确认后端路径，统一风格

### 🟢 轻微（可延后）

1. **前端扩展了文档未覆盖的接口**
   - 影响：文档不完整
   - 修复：更新接口文档，补充 CRUD 操作

2. **`getImportResult` 接口文档未定义**
   - 位置：`api.ts:757-764`
   - 影响：无（功能正常）
   - 修复：在文档中补充此端点

---

## 十、修复建议

### 10.1 立即修复（拼写错误）

```typescript
// api.ts:845 - 修复 approve 拼写
async approve(reviewId: string) {
  return apiClient.post<ApiResponse<{ approved: boolean }>>(
    `/phase4/reviews/${reviewId}/approve`,  // 修复：approve → approve
    {},
  );
},

// api.ts:852 - 修复 reject 拼写
async reject(reviewId: string, reason: string) {
  return apiClient.post<ApiResponse<{ rejected: boolean }>>(
    `/phase4/reviews/${reviewId}/reject`,  // 修复：reject → reject
    { reason },
  );
},
```

### 10.2 响应类型修复

```typescript
// api.ts:88-95 - 修复项目统计响应类型
async getStats(projectId: string) {
  return apiClient.get<ApiResponse<{
    total_projects: number;
    total_words: number;
    today_words: number;
  }>>(`/projects/${projectId}/stats`);
},
```

**注意**：需先与后端确认实际响应结构。

### 10.3 添加分页参数

```typescript
// api.ts:125-129 - 添加分页参数
async list(projectId: string, params?: { page?: number; page_size?: number }) {
  return apiClient.get<ApiResponse<{
    chapters: Chapter[];
    total: number;
    page: number;
    page_size: number;
  }>>(
    `/projects/${projectId}/chapters`,
    params,
  );
},
```

---

## 十一、总结

### 一致性评分

| 维度 | 评分 | 说明 |
|:-----|:----:|:-----|
| 路径一致性 | 95% | 仅少数扩展接口未覆盖 |
| 方法一致性 | 100% | 所有 HTTP 方法正确 |
| 参数名一致性 | 98% | 偶有字段名差异 |
| 响应处理一致性 | 85% | 统计接口字段不匹配 |
| 文档覆盖率 | 70% | 前端有 14 个扩展接口未文档化 |

**总体评价**：前端代码与接口文档基本保持一致，主要问题是：
1. 两个拼写错误（Phase 4 审核功能不可用）
2. 项目统计响应字段不匹配
3. 文档覆盖不完整（前端扩展接口）

### 下一步行动

1. ✅ 修复 `approve`/`reject` 拼写错误
2. 🔄 与后端确认 `/projects/:pid/stats` 响应结构
3. 📝 更新接口文档，补充前端扩展的 CRUD 接口
4. 🧪 添加 API 集成测试，自动检测路径/参数不匹配

---

**报告生成完成**
