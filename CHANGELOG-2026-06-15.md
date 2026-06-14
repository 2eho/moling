# 墨灵项目 2026-06-15 完美修复变更日志

> **执行人**：6 代理并行修复团队  
> **范围**：后端 Service 实现 + 路由修复 + Worker 导入 + 前端 API 统一

---

## 一、路由与导入修复

### R1 [FIXED] - Secret 路由注册
**问题**：`app/router/secret.py` 存在且包含 4 个端点（list/get-by-character/update/update-by-character），但从未在 `app/router/__init__.py` 中注册，所有秘密矩阵 API 返回 404。

**修改文件**：
- `moling-server/app/router/__init__.py` — 第 92-96 行新增 secret router 注册块（prefix=/secrets, tags=["secrets"]）

### R2 [FIXED] - Card Service 导入错误
**问题**：`app/router/card.py:13` 执行 `from app.service import card_service`，但 `card_service` 未从 `app/service/__init__.py` 导出，导致 router 加载时静默 ImportError，card 路由组（4 个端点）全部不可访问。

**修改文件**：
- `moling-server/app/service/__init__.py` — 添加 `from app.service.card_service import card_service` 导出及 `__all__` 条目

---

## 二、新增 Service 实现

### S1 [NEW] - ImportService（文件导入服务）
**文件**：`moling-server/app/service/import_service.py`（631 行）

| 方法 | 功能 |
|------|------|
| `import_book(project_id, file_path, import_mode)` | 解析 txt/docx/epub 文件，按章节标记拆分（第X章/Chapter X），支持 replace（替换）/ append（追加）模式 |
| `analyze_content(project_id)` | 计算章节字数分布、平均句长、对话比、段落模式，生成导入建议 |

### S2 [NEW] - BookAnalysisService（书籍分析服务）
**文件**：`moling-server/app/service/book_analysis_service.py`（~320 行）

| 方法 | 功能 |
|------|------|
| `analyze_characters(project_id)` | 中英文角色提取 + 共现关系图谱 + 角色档案 |
| `analyze_plot(project_id)` | 幕结构识别 + 情节点检测 + 漏洞分析 |
| `detect_style(project_id)` | 句长/对话比/段落模式/高频短语统计 |

**技术决策**：同步 API（asyncio.run 桥接 async DAO），纯规则分析，无 LLM 依赖。

### S3 [NEW] - CardPoolService（卡池管理服务）
**文件**：`moling-server/app/service/card_pool_service.py`（267 行）

| 方法 | 功能 |
|------|------|
| `check_freshness(project_id)` | 计算卡牌新鲜度（draw_count/freshness_chapter），标记低分卡 |
| `retire_cards(project_id, card_ids)` | 退役指定卡牌（is_active=False），事务回滚 |
| `generate_replacements(project_id, count)` | 分析卡池类型缺口，生成 placeholder 新卡 |

### S4 [NEW] - Phase4Service.analyze_project
**文件**：`moling-server/app/service/phase4_service.py`

| 方法 | 功能 |
|------|------|
| `analyze_project(project_id)` | 分析卡池 → 提取角色/地点/物品/事件实体 → 置信度评分 |

### S5 [NEW] - VaultService.update_from_chapter
**文件**：`moling-server/app/service/vault_service.py`

| 方法 | 功能 |
|------|------|
| `update_from_chapter(project_id, chapter_id)` | 从章节文本提取实体（基于中文模式匹配），更新/创建保险库条目 |

---

## 三、Worker 修复

### W1 [FIXED] - 5 个 Worker 导入修复
**问题**：所有 Celery worker 使用 `from app.service import XxxService` 方式导入，但新 service 未在 `__init__.py` 的 `__all__` 中，导致所有后台任务静默失败。

**修改文件**：

| 文件 | 变更 |
|------|------|
| `app/worker/import_task.py` | `from app.service.import_service import ImportService` + `asyncio.run()` |
| `app/worker/book_analysis_task.py` | `from app.service.book_analysis_service import BookAnalysisService` |
| `app/worker/card_retire_task.py` | `from app.service.card_pool_service import CardPoolService` |
| `app/worker/phase4_task.py` | `from app.service.phase4_service import Phase4Service` + `from app.service.vault_service import VaultService` + `asyncio.run()` |
| `app/worker/tasks.py` | 无需修改（已有正确导入） |

### W2 [FIXED] - async/sync Worker 桥接
**问题**：`Phase4Service.analyze_project` 和 `VaultService.update_from_chapter` 是 async 方法，但 Celery worker 是同步调用，导致返回 coroutine 而非实际结果。

**修复**：在 worker 函数中使用 `asyncio.run()` 包裹 async 调用。

---

## 四、前端 API 统一

### F1 [FIXED] - 双 API 客户端统一到 @/lib/api
**问题**：`src/api/client.ts` 和 `src/lib/apiClient.ts` 是两套完全独立的 API 层——不同端口、不同 Token key、不同响应格式。6 个页面使用 @/api（缺功能），Mock 绑定在 @/lib/api（有功能）。

**修改文件**：

| 文件 | 变更 |
|------|------|
| `src/app/vaults/[id]/page.tsx` | 改用 `vaultApi.*` |
| `src/app/workspace/page.tsx` | 改用 `cardApi/generationApi/healthApi` |
| `src/app/notifications/page.tsx` | 改用 `notificationsApi.*` |
| `src/app/settings/page.tsx` | 改用 `settingsApi.*` |
| `src/app/import/page.tsx` | 改用 `importApi.*` |

### F2 [FIXED] - vault.ts 路径修复
`src/api/vault.ts` 所有 endpoint 缺少 `/vault/` 前缀，8 个 GET/POST 路径已修复。

### F3 [ADDED] - lib/api.ts 补充函数
为兼容旧 API 调用，在 `src/lib/api.ts` 新增：
- `vaultApi`: createTimelineEvent, updateTimelineEvent, deleteTimelineEvent, createPlotPromise 等 CRUD
- `settingsApi`: getSettings, updateGlobalSettings, updateProjectSettings, changePassword, updateProfile
- `notificationsApi`: getNotifications, getUnreadCount, deleteNotification, deleteAllRead
- `importApi`: uploadAndImport, getImportProgress, getImportResult, getImportHistory

---

## 五、Docker 部署配置修正（见昨日提交）

- 前端 Dockerfile: `npm ci` 移除 `--only=production`
- 后端 Dockerfile: 构建阶段补充 `COPY app/`
- docker-compose: 移除 PostgreSQL，切换 SQLite + 数据卷
- config.py/.env.example: DATABASE_URL 改为 SQLite

---

## 总结

| 类别 | 修复数 | 新增文件数 | 修改文件数 | 代码行数 |
|------|--------|-----------|-----------|---------|
| 路由修复 | 2 | 0 | 2 | ~30 |
| Service 实现 | 5 | 3 | 3 | ~1,200 |
| Worker 修复 | 5 | 0 | 4 | ~30 |
| 前端统一 | 7 页面 | 0 | 6 | ~200 |
| **总计** | **19** | **3** | **15** | **~1,460** |
