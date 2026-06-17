# 墨灵全功能交互审计报告

> 审计时间: 2026-06-17 18:31
> 范围: 前端 19 个 API 模块(114 方法) vs 后端 ~101 路由
> 方法: 多 Agent 并行探索 → 交叉比对 → 批量修复

---

## 批处理结果

### P0 —— 已修复（会导致功能崩溃）

| 问题 | 根因 | 修复 |
|------|------|------|
| **生成功能全挂** | `generationApi.getJobStatus` 前端路径 `/generate/${taskId}/status` 后端不存在（实际是 `/generate/jobs/${job_id}` | 前端改为 `/generate/jobs/${taskId}` |
| **无法取消生成** | 后端 `generation/router.py` 没有 cancel 端点，`jobs_store` 也没有 `cancelled` 状态 | 新增 `POST /generate/jobs/{job_id}/cancel` + `JobStatus.cancelled` |
| **生成历史404** | 历史端点只存在旧版 `app/router/generation.py`，但注册的是新版 `app/generation/router.py` | 新版 router 合并 `/history` 端点 |
| **admin 面板零认证** | admin.py 6 个路由全没有 `get_current_user` 依赖 | 全部加上 `current_user=Depends(get_current_user)` |
| **generation 导入被改错** | Agent 错误地把导入从 `app.generation.router` 改成了 `app.router.generation`（旧版同步） | 恢复为新版异步 router |

### P1 —— 需手动排查（不会崩但会有问题）

| 问题 | 位置 | 说明 |
|------|------|------|
| **secret.py 未注册** | `app/router/secret.py` 定义了 4 个路由但未在 `__init__.py` 引入 | 前端有 `secretsApi`(3方法)，前端调用的路径是 `/projects/{projectId}/secrets`，而后端 `project.py` 有内联 secrets 路由，可能能覆盖 |
| **try-catch 缺失** | workspace 页面的 `handleDrawCards`/`handleRedraw`、ToolBar 的 `handleGenerate`/`handleConfirm`/`handleRevise` | 调用在 context 内已有 catch，但外层调用点没有，出错时无 toast |
| **通知页错误静默** | notify page 的 `markAsRead`/`markAllAsRead`/`delete` 的 catch 只写 `console.error` | 用户看不到错误提示 |
| **设置页重复保存函数** | Profile/Theme/Defaults 三个标签的"保存"按钮都绑定了同一个 `handleSaveGlobalSettings` | 每次保存都全量更新，后端无副作用但冗余 |
| **四库管理页功能缺失** | "添加角色"是 toast 占位，世界观编辑/删除按钮无 onClick | 这些是二期功能，当前无后端端点 |

### P2 —— 功能正常（已验证路径匹配）

以下核心链路的 API 路径已验证前后端一致：
- ✅ authApi (login/register/refresh/me/reset) 
- ✅ projectApi (list/create/update/delete/stats)
- ✅ chapterApi (create/list/get/update/delete/confirm/revise/reorder)
- ✅ cardApi (pool/draw/redraw/create/retire)
- ✅ vaultApi (characters/timeline/plot-promises/world/summary)
- ✅ healthApi (alerts/refresh)
- ✅ settingsApi (大部分端点)
- ✅ notificationsApi (list/read/read-all/delete)

---

## 完整计数

| 类别 | 数量 |
|------|:----:|
| 前端 API 模块 | 19 |
| 前端 API 方法 | 114 |
| 后端已注册路由 | ~101 |
| P0 已修复 | **5个** |
| P1 待确认 | **5个** |
| 本次改动文件数 | **4个**（+ 上次 7个 = 本轮共 11个） |
