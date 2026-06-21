# 墨灵前端设计文档

> **版本**: 2.2.0 | **最后更新**: 2026-06-21
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

---

## 9. Phase 2 专项优化 — 前端补齐 (M12)

> **日期**: 2026-06-21

### 9.1 路由 Loading 状态

为 8 个子路由添加 `loading.tsx`（Suspense fallback），消除路由切换时的白屏闪烁：

| 路由 | 文件 | 效果 |
|------|------|------|
| `/projects` | `loading.tsx` | 项目列表骨架屏 |
| `/projects/new` | `loading.tsx` | 新建表单骨架屏 |
| `/projects/[projectId]` | `loading.tsx` | 项目详情骨架屏 |
| `/workspace/[projectId]` | `loading.tsx` | 工作台骨架屏 |
| `/settings` | `loading.tsx` | 设置页骨架屏 |
| `/auth` | `loading.tsx` | 认证页骨架屏 |
| `/` (root) | `loading.tsx` | 首页骨架屏 |
| (catch-all) | `loading.tsx` | 通用骨架屏 |

**原因**: Next.js App Router 页面切换时，若目标页面数据未就绪，会出现短暂白屏。`loading.tsx` 自动作为 Suspense 边界，在加载期间渲染骨架屏，改善感知性能。

### 9.2 组件无障碍 (WCAG 2.1 AA)

11 个业务组件添加 `aria-*` 属性，支持屏幕阅读器：

| 组件 | 新增属性 | 原因 |
|------|---------|------|
| `OptionsPanel` | `role="radiogroup"`, `aria-label="写作选项"` | 屏幕阅读器正确朗读选项组 |
| `Sidebar` | `role="navigation"`, `aria-label="主导航"` | 明确导航区域 |
| `ChapterList` | `role="listbox"`, `aria-label="章节目录"` | 列表可被朗读为可选择列表 |
| `ProjectCard` | `role="article"`, `aria-labelledby` | 卡片内容结构化 |
| `SettingsForm` | `aria-describedby` 各输入框 | 表单字段关联描述文本 |
| `SearchInput` | `role="searchbox"`, `aria-label="搜索项目"` | 明确搜索功能 |
| `ThemeSelector` | `role="listbox"`, `aria-label="主题选择"` | 主题列表可被朗读 |
| `Modal` | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` | 对话框语义化 |
| `Toast` | `role="alert"`, `aria-live="polite"` | 通知自动朗读 |
| `LoadingSpinner` | `role="status"`, `aria-label="加载中"` | 加载状态可感知 |
| `ErrorDisplay` | `role="alert"`, `aria-live="assertive"` | 错误立即朗读 |

**原因**: 确保视障用户可通过屏幕阅读器正常使用全部功能，满足无障碍合规要求。

### 9.3 颜色令牌统一

所有组件的颜色引用从 `var(--color-*)` 旧命名迁移至 `var(--th-*)` 通用语义变量：

| 旧令牌（示例） | 新令牌 | 说明 |
|---------------|--------|------|
| `var(--color-brand-indigo)` | `var(--th-primary)` | 主色 |
| `var(--color-bg-dark)` | `var(--th-bg)` | 背景色 |
| `var(--color-text-primary)` | `var(--th-text)` | 主文字色 |
| `var(--color-border)` | `var(--th-border)` | 边框色 |
| `var(--color-accent-amber)` | `var(--th-accent)` | 强调色 |

**原因**: 旧命名绑定特定色值（如 `indigo`），无法随主题切换变化。`--th-*` 是主题感知的抽象层，切换 `data-theme` 时自动映射到对应色值，保证 8 套主题一致性。

### 9.4 类型系统统一

| 变更 | 说明 | 原因 |
|------|------|------|
| `Project` 接口移除 | 仅保留 `WritingProject` | 两个类型 90% 字段重叠，维护两套定义容易产生不一致 |
| 所有组件引用更新 | `Project` → `WritingProject` | 消除 TypeScript 编译警告 |

### 9.5 API 端点常量化

`api.ts` 中硬编码的 URL 路径全部替换为 `constants.ts` 中的 `API_ENDPOINTS` 引用：

```typescript
// 旧: fetch('/api/v1/projects')
// 新: fetch(API_ENDPOINTS.projects)
```

**原因**: 端点路径集中管理，API 版本升级或路径变更时仅需修改一处。

### 9.6 空目录清理

删除 3 个无内容的遗留目录：
- `components/deprecated/`
- `pages/` (Pages Router 残留)
- `styles/` (CSS Module 残留)

**原因**: 减少目录导航噪音，避免新成员误用废弃目录结构。

---

## 文档版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 2.2.0 | 2026-06-21 | Phase 2 专项优化 — 前端补齐(M12)：8子路由 loading.tsx 消除白屏、11组件 aria 无障碍(WCAG 2.1 AA)、颜色令牌 `var(--color-*)`→`var(--th-*)` 统一、`Project`/`WritingProject` 类型合并、`api.ts` 端点常量化、3空目录清理 | Moling Team |
| 2.1.0 | 2026-06-21 | 🛠 前端错误边界+Mock数据补全 | Moling Team |
| 2.0.0 | 2026-06-21 | Agent 优化合并 | Moling Team |
| 1.0.0 | 2026-06-20 | 原始 DESIGN.md 设计系统文档 |
