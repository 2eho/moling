# 墨灵前端设计文档

> **版本**: 2.5.0 | **最后更新**: 2026-06-22
> 本文档是前端开发的唯一真相来源。合并了原 DESIGN.md / design-decisions.md / VIBE_WRITING_DESIGN.md / 前端重建方案.md 的关键内容。新增 Tauri 桌面端支持。

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

### 后端混合架构

墨灵后端支持 **Python (FastAPI)** 和 **Rust (Axum)** 双轨运行：

| 层 | Python 后端 | Rust 后端 (moling-server-rs) |
|----|-------------|------------------------------|
| 框架 | FastAPI 0.115+ | Axum 0.8 |
| ORM | SQLAlchemy 2.0 | SeaORM 1.1 |
| 异步 | Uvicorn + asyncio | Tokio 1.x |
| 任务队列 | Celery + Redis | moling-worker (Rust native) |
| LLM 客户端 | httpx + tenacity | Reqwest 0.12 + 内置重试 |
| JWT | python-jose 3.3 | jsonwebtoken 9 |
| 密码 | passlib + bcrypt | bcrypt 0.16 |
| 配置 | pydantic-settings | Figment 0.10 |
| 日志 | structlog | Tracing 0.3 |
| 部署 | Docker (python:3.12-slim) | Docker 多阶段 (rust:1.85-slim → scratch) |

Rust 后端共享同一 PostgreSQL/Redis 数据层，通过 Nginx 反向代理统一路由。
Rust Crate 架构详见 [ARCHITECTURE.md](./ARCHITECTURE.md) 技术栈说明章节。

**硬约束**：
- 所有组件 `"use client"`（当前阶段）
- 零 CSS Module，纯 Tailwind 4 + CSS 变量
- 颜色 100% 通过 `var(--th-*)` 引用，禁止硬编码色值
- API 代理：`/api/*` → `localhost:8000`（无需前端改 base URL）
  - Tauri 桌面端：跳过 Next.js 代理，客户端直接 HTTP 调用 `http://127.0.0.1:8000/api/v1`

### Tauri 桌面端 (v2)

**方案A**：同一套 Next.js 代码 → 双模式构建，Web 模式保持 SSR standalone，桌面模式用 static export + Tauri 包裹。

| 维度 | Web 模式 | Tauri 桌面模式 |
|------|----------|---------------|
| 构建命令 | `next build` | `npm run build:tauri` |
| 输出 | `output: "standalone"` | `output: "export"` → `out/` |
| basePath | `/moling` | 空（本地应用无需路径前缀） |
| API 调用 | Next.js rewrites 代理 | 客户端直连 `http://127.0.0.1:8000` |
| 认证守卫 | `middleware.ts` (SSR) | `AuthGuard` 组件 (CSR) |
| 部署 | Docker + Nginx | `tauri build` → .msi / .dmg / .AppImage |

**关键文件**：

| 文件 | 用途 |
|------|------|
| `src-tauri/tauri.conf.json` | Tauri v2 窗口配置、CSP、打包参数 |
| `src-tauri/Cargo.toml` | Rust 依赖 (tauri 2.x + tauri-plugin-opener) |
| `src-tauri/src/main.rs` | Rust 入口 |
| `src-tauri/src/lib.rs` | Tauri Builder 配置 + 自定义命令 |
| `src-tauri/capabilities/default.json` | 权限声明 |
| `src/app/AuthGuard.tsx` | 客户端认证守卫（替代 middleware） |
| `scripts/pre-tauri-build.js` | 构建前：禁用 middleware.ts |
| `scripts/post-tauri-build.js` | 构建后：恢复 middleware.ts |
| `.env.tauri` | Tauri 构建专用环境变量 |
| `next.config.ts` | 条件分支：`NEXT_PUBLIC_TAURI_BUILD=true` 触发 export 模式 |

**环境检测**：
- `env.isTauri`: 运行时检测 — `typeof window !== "undefined" && "__TAURI_INTERNALS__" in window`
- `env.isTauriBuild`: 构建时检测 — `process.env.NEXT_PUBLIC_TAURI_BUILD === "true"`

**开发命令**：
```bash
# Tauri 开发模式（热重载）
npm run tauri:dev

# Tauri 生产构建
npm run tauri:build

# 仅构建前端（不打包 Tauri）
npm run build:tauri
```

**CSP 策略**：`connect-src 'self' http://localhost:* http://127.0.0.1:*` — 允许 WebView 直连本地后端。

**ADM (Architecture Decision Mockup)**：
- **选择**：Next.js `output: "export"` + Tauri v2 包裹
- **理由**：复用 100% 现有代码，零 UI 改动，双模式构建同一代码库
- **拒绝**：单独 Vite SPA 重写（代码分裂，维护成本高）；Electron（体积大，Tauri 更轻量）
- **后果**：static export 不支持 middleware/rewrites，需客户端 AuthGuard + 直连 API 替代

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

## 10. 前端框架结构全览 (2026-06-21 梳理)

### 10.1 源码目录树

```
src/
├── app/                              # Next.js App Router 页面层
│   ├── layout.tsx                    # 根布局: ThemeInitializer + QueryProvider
│   ├── globals.css                   # 8主题CSS变量 + 全局样式 + 关键帧动画
│   ├── page.tsx                      # Landing Page
│   ├── loading.tsx / not-found.tsx   # 全局加载/404
│   ├── auth/                         # 登录/注册 + error.tsx + loading.tsx
│   ├── projects/                     # 项目列表
│   │   └── new/                      # 新建项目
│   ├── settings/                     # 用户设置
│   ├── vaults/[projectId]/          # Vault 四库(人物/时间线/伏笔/世界观)
│   └── workspace/[projectId]/        # ⭐ Vibe Writing 核心工作台
│       ├── health/                   # 健康监控面板
│       └── phase4/tasks/             # Phase4 任务管理
│
├── components/                        # 共享组件层
│   ├── QueryProvider.tsx              # TanStack Query 全局 Provider
│   ├── health/                        # HealthDashboard + 测试
│   ├── phase4/                        # Phase4 组件(CardManager/四库面板) + 测试
│   └── vibe/                          # Vibe Writing 专属组件
│       ├── Sidebar.tsx                # 侧栏: 项目列表 + 章节树 + 连载/完结分栏
│       ├── AgentPanel.tsx             # Agent 调度面板(右栏)
│       ├── ContextPanel.tsx           # 上下文面板(左栏)
│       ├── FreeInput.tsx              # D 自由输入
│       ├── OptionCard.tsx             # A/B/C 选项卡片
│       ├── ActionBar.tsx              # 操作栏
│       ├── PhaseNavigator.tsx         # 阶段导航
│       ├── ProgressBar.tsx            # 进度指示
│       ├── ThemeInitializer.tsx       # 主题恢复(SSR→CSR同步)
│       └── ThemeSwitcher.tsx          # 主题切换器
│
├── stores/                            # Zustand Store 层
│   ├── useTheme.ts                    # 主题状态 + persist(localStorage)
│   │   theme / setTheme / cycleNext / isDarkTheme
│   └── useWritingStore.ts             # 写作状态(核心 Store)
│       projects[] / activeProjectId / activeChapterId / expandedProjectId
│       options[] / selectedOption / customInput / agents[] / history[] / isGenerating
│       loadProjects / setActiveProject / toggleProjectExpand
│       selectOption / submitCustom / undo / generateOptions
│       addChapter / completeChapter
│
├── lib/                               # 工具库层
│   ├── cn.ts                          # clsx + tailwind-merge (cn函数)
│   ├── constants.ts                   # API端点 + UI标签常量
│   ├── env.ts                         # 环境变量封装(类型安全)
│   ├── format.ts                      # 日期/字数/时长格式化
│   ├── http/                          # HTTP 客户端子层
│   │   ├── client.ts                  # Fetch封装: apiGet/POST/PUT/PATCH/DELETE
│   │   │   ApiError类 + AbortController超时 + Bearer自动注入 + 204处理
│   │   ├── api.ts                     # 业务API函数(health/phase4/vault/cards)
│   │   ├── auth.ts                    # Token管理(access/refresh) + 刷新去重
│   │   └── cache.ts                   # DedupCache(TTL+并发去重+LRU淘汰)
│   └── types/
│       └── domain.ts                  # 领域模型: Project/HealthAlert/Phase4Task/
│                                      #   VaultCharacter/VaultTimeline/VaultForeshadowing/
│                                      #   VaultWorldview/CardPoolItem
│
├── mock/                              # Mock 数据(开发阶段)
│   ├── data/                          # projects / workspace / agent-outputs
│   └── handlers/                      # auth mock handler
│
├── hooks/                             # 自定义 Hooks(预留,当前空)
├── middleware.ts                      # Auth中间件(cookie/JWT校验 + 保护路由)
└── test-setup.ts                      # 测试Setup
```

### 10.2 认证中间件

```
middleware.ts
  ├── PROTECTED_PATTERNS: /projects /workspace /admin /settings /history
  │                       /import /notifications /pricing /vaults /weave
  ├── isProtectedRoute() → 路径前缀匹配
  ├── NEXT_PUBLIC_SKIP_AUTH=true → 全部放行(开发模式)
  ├── 检查 cookie.access_token || header.Authorization
  └── 无token → 302重定向 /moling/auth?redirect=<原路径>
```

### 10.3 HTTP 客户端层

```
业务层 (api.ts)
  getProjectHealth / refreshProjectHealth
  getProjectPhase4Tasks / getPhase4Task / getChapterPhase4Tasks
  getVaultCharacters / getVaultTimeline / getVaultForeshadowing / getVaultWorldview / getVaultSummary
  getCardPool / retireCard
        ↓
传输层 (client.ts)
  apiGet<T> / apiPost<T> / apiPut<T> / apiPatch<T> / apiDelete<T>
    → request<T>(method, path, body?, options?)
      → fetch(url, { headers + Bearer, signal, body })
      → 超时: AbortController → ApiError(408)
      → 错误: response.ok? → response.json() : ApiError(status, message, data)
      → 204: 返回 undefined
        ↓
缓存层 (cache.ts)
  DedupCache: TTL(30s) + maxSize(50) + 并发去重(dedupe方法)
  apiCache: 模块级单例
        ↓
认证层 (auth.ts)
  getAccessToken / getRefreshToken → localStorage
  setTokens / clearTokens
  refreshAccessToken → 去重(同一时间只有一个刷新请求)
```

### 10.4 构建与部署

| 配置项 | 值 | 说明 |
|--------|-----|------|
| basePath | `/moling` | 子路径部署 |
| output | `standalone` | Docker 独立部署 |
| reactStrictMode | true | 严格模式 |
| poweredByHeader | false | 隐藏框架标识 |
| compiler.removeConsole | 仅保留 error/warn | 生产环境去除日志 |
| images.unoptimized | true | standalone 模式禁用优化 |
| httpAgentOptions.keepAlive | true | HTTP 连接复用 |
| generateEtags | false | 配合 Nginx 强缓存 |
| rewrites | /api/* → localhost:8000 | 开发代理 |
| eslint.ignoreDuringBuilds | false | 构建时检查 |

### 10.5 测试体系

| 层级 | 工具 | 位置 | 覆盖 |
|------|------|------|------|
| Client 层测试 | Vitest | `src/lib/http/__tests__/` | HTTP client + cache |
| Store 测试 | Vitest | `src/stores/__tests__/` | useWritingStore |
| 组件测试 | Vitest + Testing Library | `src/components/**/__tests__/` | Health/Phase4 组件 |
| E2E | Playwright | `e2e/` | auth.spec / project.spec / workspace.spec |

### 10.6 代码品控

| 工具 | 配置 | 说明 |
|------|------|------|
| TypeScript | strict: true | 全量类型检查 |
| ESLint | next/core-web-vitals | React hooks + no-console(warn) |
| Sentry | @sentry/nextjs 10.58 | 客户端+服务端错误监控, tracesSampleRate 0.2(prod) |

### 10.7 组件间数据流

```
WorkspacePage (page.tsx)
  ├── 读: useWritingStore (project/activeChapterId/projects)
  ├── 读: useTheme (theme)
  ├── 写: loadProjects / setActiveProject / setActiveChapter / completeChapter
  │
  ├── <Sidebar>
  │     └── 读: projects/activeProjectId/expandedProjectId/activeChapterId
  │     └── 写: setActiveProject/setActiveChapter/toggleProjectExpand
  │     └── 路由: router.push
  │
  ├── <ThemeSwitcher>
  │     └── 读/写: useTheme
  │
  ├── <OptionsPanel>
  │     └── Mock: MOCK_OPTIONS → A/B/C 选项卡片
  │     └── 模式切换: options/custom
  │     └── 回调: onDraftStep → setDraftStepCount++
  │
  └── <AgentPanel>
        └── 读: useWritingStore(agents)
        └── 5 Agent 状态卡片(Plot/Character/Dialogue/Style/World)
```

### 10.8 组件注册表

| 组件文件 | 类型 | 依赖 Store | 依赖库 |
|---------|------|-----------|--------|
| `QueryProvider.tsx` | Provider | — | @tanstack/react-query |
| `ThemeInitializer.tsx` | Utility | useTheme | — |
| `ThemeSwitcher.tsx` | UI | useTheme | lucide-react |
| `Sidebar.tsx` | Navigation | useWritingStore | lucide-react, next/navigation |
| `AgentPanel.tsx` | Panel | useWritingStore | lucide-react |
| `ContextPanel.tsx` | Panel | useWritingStore | lucide-react |
| `FreeInput.tsx` | Form | — | lucide-react |
| `OptionCard.tsx` | Form | — | lucide-react |
| `ActionBar.tsx` | Toolbar | useWritingStore | lucide-react |
| `PhaseNavigator.tsx` | Navigation | useWritingStore | lucide-react |
| `ProgressBar.tsx` | Indicator | useWritingStore | — |
| `HealthDashboard.tsx` | Data | — | lib/http/api |
| `CardManager.tsx` | Data | — | lib/http/api |
| `CharacterLibrary.tsx` | Data | — | lib/http/api |
| `TimelineLibrary.tsx` | Data | — | lib/http/api |
| `ForeshadowingLibrary.tsx` | Data | — | lib/http/api |
| `WorldviewLibrary.tsx` | Data | — | lib/http/api |
| `Phase4TaskPanel.tsx` | Data | — | lib/http/api |

---

## 文档版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| 2.3.0 | 2026-06-21 | 前端框架结构全览(§10)：源码目录树/认证中间件/HTTP客户端层/构建部署/测试体系/代码品控/组件数据流/组件注册表 | Lead |
| 2.2.0 | 2026-06-21 | Phase 2 专项优化 — 前端补齐(M12)：8子路由 loading.tsx 消除白屏、11组件 aria 无障碍(WCAG 2.1 AA)、颜色令牌 `var(--color-*)`→`var(--th-*)` 统一、`Project`/`WritingProject` 类型合并、`api.ts` 端点常量化、3空目录清理 | Moling Team |
| 2.1.0 | 2026-06-21 | 🛠 前端错误边界+Mock数据补全 | Moling Team |
| 2.0.0 | 2026-06-21 | Agent 优化合并 | Moling Team |
| 1.0.0 | 2026-06-20 | 原始 DESIGN.md 设计系统文档 |
