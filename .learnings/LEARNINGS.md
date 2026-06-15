# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20250615-001] best_practice

**Logged**: 2026-06-15T19:36:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend | frontend | process

### Summary
多代理协作修复 API 问题时，必须按照用户使用频率排序优先级（认证 > 项目 > 章节 > 卡牌 > 四库），而非技术优先级。

### Details
初始修复计划按技术优先级（高/中/低）排序，但用户指出应该按**常用操作排列**（登录注册最常用）。
- 错误做法：先修复技术上的"高优先级"问题
- 正确做法：先修复80-90%用户会使用的功能（章节管理、Phase 4路径）

### Suggested Action
在制定修复计划时，先分析用户使用频率，再排序修复顺序。

### Metadata
- Source: user_feedback
- Related Files: api-fix-plan.md
- Tags: prioritization, user_centric, multi_agent
- Pattern-Key: process.user_centric_prioritization
- Recurrence-Count: 1
- First-Seen: 2026-06-15
- Last-Seen: 2026-06-15

### Resolution
- **Resolved**: 2026-06-15T19:36:00+08:00
- **Notes**: 重新排序修复计划，按用户使用频率：认证(100%) > 项目(90%) > 章节(80%) > 卡牌(60%) > 四库(40%)

---

## [LRN-20250615-002] correction

**Logged**: 2026-06-15T19:36:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: backend | frontend

### Summary
前端 API 响应处理：实际后端返回统一格式 `{code, message, data, meta}`，前端必须用 `res.data` 获取实际数据，而非 `res` 直接。

### Details
初始分析误判前端代码有 bug（使用了 `.data` 链式访问），但实际：
1. 后端 `ResponseFormatMiddleware` 包装响应为 `{code: 0, message: "success", data: {...}, meta: {...}}`
2. 前端 `apiClient` 返回完整响应 JSON
3. 前端代码用 `res.data` 获取 `data` 字段 ✅ 正确

**错误假设**：认为后端直接返回数据，不包 `data` 包裹层。

### Suggested Action
在分析前后端对接问题时，先检查中间件/拦截器的实际行为，不要假设响应格式。

### Metadata
- Source: conversation | error
- Related Files: moling-web/src/lib/apiClient.ts, moling-server/app/middleware/response_format.py
- Tags: api_response, middleware, frontend_backend_integration

### Resolution
- **Resolved**: 2026-06-15T19:36:00+08:00
- **Notes**: 确认前端代码正确，无需修改 ProjectContext.tsx

---

## [LRN-20250615-003] best_practice

**Logged**: 2026-06-15T19:36:00+08:00
**Priority**: high
**Status**: resolved
**Area**: process | multi_agent

### Summary
多代理协作时，必须确保闭环更新：修复 → 测试 → 验证 → 记录学习。

### Details
用户提醒"要注意闭环更新"，参照 self-improvement skill。
- 修复完成后，必须记录到 `.learnings/LEARNINGS.md`
- 记录内容包括：做了什么、为什么、如何验证、后续建议
- 便于未来会话复用经验

### Suggested Action
每次多代理协作任务完成后，立即更新学习日志。

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md
- Tags: self_improvement, closed_loop, multi_agent
- Pattern-Key: process.closed_loop_updates
- Recurrence-Count: 1
- First-Seen: 2026-06-15
- Last-Seen: 2026-06-15

### Resolution
- **Resolved**: 2026-06-15T19:36:00+08:00
- **Notes**: 已创建 .learnings/ 目录并更新 LEARNINGS.md

---

## [LRN-20250615-004] best_practice

**Logged**: 2026-06-15T19:50:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | design | responsive

### Summary
响应式布局设计：移动端和Web端双端可用，使用统一布局管理器（AppShell）根据屏幕尺寸自动切换导航方式。

### Details
**问题**：`/moling/projects` 页面出现双重标题栏（两个"AI小说操作平台"）。

**根因**：Next.js App Router 的布局嵌套规则 - Root Layout (`app/layout.tsx`) 包含 `<AppShell>`（含 Navbar），Projects Layout (`app/projects/layout.tsx`) 又包含了一个 `<Navbar>`，导致重复渲染。

**解决方案**：
1. **统一布局管理**：使用 `AppShell` 作为唯一布局管理器
2. **响应式设计**：
   - Web端（> 768px）：侧边栏导航（可折叠）
   - 移动端（≤ 768px）：顶部导航 + 底部导航
3. **移除子布局重复组件**：所有子布局不重复 Navbar/Sidebar

**关键代码**：
- `AppShell.tsx`：检测屏幕尺寸（`useEffect` + `window.addEventListener("resize")`）
- `Sidebar.tsx`：Web端侧边栏（280px / 56px 可折叠）
- `BottomNav.tsx`：移动端底部导航（56px 高度，适配 iPhone X+ 安全区）

### Suggested Action
1. 在设计布局时，明确哪一层是"布局管理层"
2. 子布局只负责数据提供（如 `ProjectProvider`），不负责导航渲染
3. 使用 CSS Media Query (`@media (max-width: 768px)`) 实现响应式

### Metadata
- Source: user_feedback | error
- Related Files: app/projects/layout.tsx, components/layout/AppShell.tsx, components/layout/Sidebar.tsx, components/layout/BottomNav.tsx
- Tags: responsive_design, nextjs_app_router, layout_nesting, mobile_first
- Pattern-Key: design.responsive_layout_management
- Recurrence-Count: 1
- First-Seen: 2026-06-15
- Last-Seen: 2026-06-15

### Resolution
- **Resolved**: 2026-06-15T19:50:00+08:00
- **Notes**: 创建响应式布局系统，支持移动端+Web端双端可用，移除子布局重复 Navbar

---
