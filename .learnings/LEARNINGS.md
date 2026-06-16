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

## [LRN-20250616-001] best_practice

**Logged**: 2026-06-16T22:00:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: frontend | process | reliability

### Summary
API 响应安全处理必须建立**三层防护体系**（代码层 + 验证层 + 规则层），防止 `Cannot read properties of undefined` 类型错误。

### Details
**问题**：`projects/page.tsx` 中对 `projects` 数组调用 `.filter()` 时崩溃，因为 `projects` 状态变成了 `undefined`。

**根因分析**：
1. `ProjectContext.tsx` 的 `loadProjects` 直接 `setProjects(res.data)`，没有处理 `res.data` 为 `undefined` 的情况
2. 其他页面和 Context 文件也有类似问题
3. TypeScript 编译时无法捕获运行时 `undefined` 错误

**三层防护方案**：
1. **第一层（代码层）**：创建 `apiSafety.ts` 工具库（6个安全函数）
2. **第二层（验证层）**：创建 `apiValidation.ts` Zod 验证 + TypeScript 严格模式
3. **第三层（规则层）**：配置 `.eslintrc.json` 禁止不安全操作

### Suggested Action
1. 所有 API 响应处理必须使用 `apiSafety.ts` 工具函数
2. 关键 API 响应使用 Zod 验证格式
3. 提交代码前必须通过 ESLint 检查

### Metadata
- Source: error | user_feedback
- Related Files: src/lib/apiSafety.ts, src/lib/apiValidation.ts, .eslintrc.json
- Tags: api_safety, three_layer_protection, runtime_validation
- Pattern-Key: process.api_response_safety
- Recurrence-Count: 1
- First-Seen: 2026-06-16
- Last-Seen: 2026-06-16

### Resolution
- **Resolved**: 2026-06-16T22:00:00+08:00
- **Notes**: 创建三层防护体系，修复 7 个文件（3个Context + 4个页面），安装 Zod 依赖，配置 ESLint 规则

---

## [LRN-20250616-002] correction

**Logged**: 2026-06-16T22:00:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: frontend | auth

### Summary
`AuthContext.tsx` 直接使用 `apiClient` 导致登录/注册失败，必须通过 `api.ts` 包装器调用。

### Details
**问题**：登录时报错 `Cannot destructure property 'access_token' of '(intermediate value).data'`

**根因**：
1. `AuthContext.tsx` 直接导入 `apiClient` 并调用 `apiClient.post("/auth/login", ...)`
2. `apiClient` 返回完整响应 `{code, message, data, meta}`
3. 代码试图直接解构 `res.access_token`，但实际在 `res.data.access_token`

**正确做法**：
- 所有 API 调用通过 `api.ts` 包装器（如 `authApi.login()`）
- `api.ts` 包装器已经正确处理了响应格式

**修复**：
```typescript
// ❌ 错误
import { apiClient } from "@/lib/apiClient";
const res = await apiClient.post<LoginResponse>("/auth/login", ...);

// ✅ 正确
import { authApi } from "@/lib/api";
const res = await authApi.login(email, password);
```

### Suggested Action
1. 禁止在 Context 和页面文件中直接导入 `apiClient`
2. 所有 API 调用必须通过 `api.ts` 中的包装器
3. 如果 `api.ts` 中没有对应的包装器，先添加再使用

### Metadata
- Source: error | code_review
- Related Files: contexts/AuthContext.tsx, lib/api.ts
- Tags: api_wrapper, auth_flow, import_rules
- Pattern-Key: frontend.api_wrapper_only
- Recurrence-Count: 1
- First-Seen: 2026-06-16
- Last-Seen: 2026-06-16

### Resolution
- **Resolved**: 2026-06-16T22:00:00+08:00
- **Notes**: 修改 AuthContext.tsx 使用 authApi 包装器，登录/注册功能恢复正常

---

## [LRN-20250616-003] best_practice

**Logged**: 2026-06-16T22:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: process | documentation | closed_loop

### Summary
代码修复完成后，必须立即更新文档实现闭环：修复 → 测试 → 验证 → 记录学习 → 更新技术文档。

### Details
**用户要求**："改动写回文档，完成闭环"

**闭环流程**：
1. **修复代码**：修改源代码文件
2. **生成审计报告**：记录所有修改和测试结果
3. **更新学习日志**：将经验记录到 `.learnings/LEARNINGS.md`
4. **更新技术文档**：将实施方案记录到项目文档
5. **提交代码**：Git commit 包含文档更新

**本次实施**：
- ✅ 修复 7 个文件（3个Context + 4个页面）
- ✅ 创建 `api-safety-audit-report-complete.md`（审计报告）
- ✅ 更新 `.learnings/LEARNINGS.md`（添加 3 条学习）
- ✅ 创建 `api-safety-implementation.md`（技术实施文档）
- ✅ Git commit 消息包含文档更新说明

### Suggested Action
1. 每次修复完成后，立即更新 `.learnings/LEARNINGS.md`
2. 重大修复（影响 > 3 个文件）必须生成审计报告
3. 技术方案必须记录到项目文档（便于未来复用）

### Metadata
- Source: user_feedback
- Related Files: .learnings/LEARNINGS.md, api-safety-audit-report-complete.md
- Tags: closed_loop, documentation, process
- Pattern-Key: process.closed_loop_documentation
- Recurrence-Count: 2
- First-Seen: 2026-06-15
- Last-Seen: 2026-06-16

### Resolution
- **Resolved**: 2026-06-16T22:00:00+08:00
- **Notes**: 完成三层防护体系的文档闭环，包括审计报告、学习日志、技术文档

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
