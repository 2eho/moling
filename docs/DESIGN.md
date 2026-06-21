# 墨灵前端设计文档

> **版本**: 2.1.0 | **最后更新**: 2026-06-21
> 本文档是前端开发的唯一真相来源。合并了原 DESIGN.md / design-decisions.md / VIBE_WRITING_DESIGN.md / 前端重建方案.md 的关键内容。

---

## 1. 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 框架 | Next.js App Router | 15.x |
| UI | React + TypeScript | 19.x / 5.7 |
| 样式 | Tailwind CSS 4 | utility-first，零 CSS Module |
| 状态（客户端） | zustand | 按域拆分 store |
| 状态（服务端） | TanStack Query v5 | 缓存 + 自动刷新 |
| 图标 | lucide-react | — |
| 测试 | Vitest + Playwright | — |
| basePath | `/moling` | Nginx 反向代理统一前缀 |

**硬约束**：
- 所有组件 `"use client"`（当前阶段）
- 零 CSS Module，纯 Tailwind 4 + CSS 变量
- 颜色 100% 通过 `var(--th-*)` 引用，禁止硬编码色值
- API 代理：`/api/*` → `localhost:8000`（无需前端改 base URL）

---

## 2. 设计系统：8 主题

8 套经典主题，通过 `<html data-theme="moling">` 切换，每套定义 30+ `--th-*` CSS 变量。

| 分类 | 主题 ID | 基调 |
|------|---------|------|
| 暗色 | `moling`（默认） | 深靛蓝 + 琥珀金 |
| 暗色 | `nord` | 极地冷蓝，低饱和 |
| 暗色 | `onedark` | Atom 传承，钢蓝灰 |
| 暗色 | `dracula` | 暗紫霓虹，高对比 |
| 暗色 | `solarized-dark` | 青绿底，学术基准 |
| 亮色 | `solarized-light` | 暖纸白，蓝灰字 |
| 亮色 | `paper` | 纸张质感，暖米色 |
| 亮色 | `github-light` | 纯白底，蓝强调 |

**切换**: `Ctrl+Shift+T`，localStorage 持久化。完整 token 定义 → `moling-web/src/app/globals.css`。

---

## 3. Vibe Writing 交互模型

**核心原则**：Heavy Options, Light Input — 80% 选择 A/B/C，20% 自由输入 D。

```
                    ┌─────────────────────┐
                    │   用户 (写作者)        │
                    └──────────┬──────────┘
                A/B/C 选项选择  │  D: 自由输入
                    ┌──────────▼──────────┐
                    │   Coordinator Agent  │
                    │   - 理解写作意图      │
                    │   - 分配子代理任务    │
                    │   - 生成选项集合      │
                    └──┬───┬───┬───┬───┬──┘
          ┌────────────┘   │   │   │   └─────────────┐
          ▼                 ▼   ▼   ▼                 ▼
    Plot Agent    Character Agent  Dialogue Agent  Style Agent  World Agent
    (剧情)        (人物)          (对话)          (风格)       (世界观)
```

**Agent 协作**：Agent of Agents 模式 — 5 个专业 Agent（Plot/Character/Dialogue/Style/World）由 Coordinator 调度。每轮交互：用户选 A/B/C → Coordinator 分发 → Agent 并行生成 → 汇总返回。

**OptionsPanel**: A/B/C 三个预设方向 + D 自由输入入口。Workspace 三栏：左侧上下文 + 中央选项 + 右侧 Agent 面板（可开关）。

---

## 4. 路由结构

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Landing Page | 产品首页 |
| `/auth` | 登录/注册 | JWT 认证 |
| `/projects` | 项目列表 | 小说项目管理 |
| `/projects/new` | 新建项目 | 创建新小说 |
| `/workspace/[projectId]` | Vibe Writing 工作台 | 三栏：上下文+选项+Agent |
| `/settings` | 用户设置 | 主题切换、账户管理 |

---

## 5. 状态管理

| Store | 文件 | 职责 |
|-------|------|------|
| `useWritingStore` | `stores/writing.ts` | 多项目管理（projects[] / activeProjectId / expandedProjectId） |
| `useAuthStore` | `stores/auth.ts` | 认证状态（token / user） |
| `useThemeStore` | `stores/theme.ts` | 主题切换 |

**服务端状态**：TanStack Query 管理 API 数据缓存，自动失效和重新获取。

---

## 6. Sidebar 交互规则

- 点击小说名 → setActiveProject + toggleExpand + navigate
- 同一时间只有一个项目展开
- 非活跃项目章节 disabled + dimmed
- 章节目录倒序（最新章紧贴项目名）
- 连载中 vs 已完结分栏；已完结项目只读（Workspace 无 OptionsPanel）

---

## 7. 代码规范

- 所有组件 `"use client"`
- 零 CSS Module，纯 Tailwind 4 + CSS 变量 `var(--th-*)`
- Mock 数据先行，后端 API 对接后续
- 环境变量 `NEXT_PUBLIC_SKIP_AUTH=true` 跳过认证（开发模式）
- 组件分层：`ui/`（原子组件） → `business/`（业务组件） → `page/`（页面组件）

---

## 8. 废弃的旧决策

| 旧决策 | 原因 | 当前做法 |
|--------|------|----------|
| CSS Modules only | 开发效率低 | 纯 Tailwind 4 |
| 暗色 only | 用户需要亮色 | 8 主题（5暗+3亮） |
| `--color-brand-indigo` 命名 | 单主题无法覆盖多主题 | `--th-*` 通用语义变量 |
| 4 个 React Context 嵌套 | 重渲染、难调试 | zustand + TanStack Query |
| 双层 API 客户端 | 混乱、无类型安全 | 统一 apiClient + openapi-types |

---

## 文档版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 2.1.0 | 2026-06-21 | 🛠 前端错误边界+Mock数据补全 — 新建 8 个 `error.tsx` 错误边界（projects/new/projects/[projectId]/workspace/[projectId]/settings/auth 路由全覆盖），React Error Boundary 捕获渲染期异常并上报 Sentry；新建 Mock 数据文件（projects/chapters/users），前端可独立开发不依赖后端；settings 页面移除 `"use client"` 指令对齐 SSR 最佳实践 | Moling Team |
| 2.0.0 | 2026-06-21 | Agent 优化合并：吸收 VIBE_WRITING_DESIGN / design-decisions / 前端重建方案 / DESIGN.md 关键内容 |
| 1.0.0 | 2026-06-20 | 原始 DESIGN.md 设计系统文档 |
