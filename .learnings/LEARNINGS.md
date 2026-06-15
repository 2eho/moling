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
