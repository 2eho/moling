# 墨灵前端推翻重做 — 技术设计

> 版本: v1.0 | 日期: 2026-06-19 | 状态: 待确认

---

## 1. 架构决策记录 (ADR)

### ADR-1: 纯 Tailwind CSS 4 + `--th-*` CSS 变量，零 CSS Module

**决策**：仅使用 Tailwind CSS 4 utility classes，所有颜色通过 `--th-*` CSS 变量族引用。删除所有 `.module.css` 文件。

**理由**：
- 当前 52 个 CSS Module 文件与 Tailwind 混用，导致样式碎片化、维护成本翻倍
- `--th-*` 变量 + `[data-theme]` 选择器实现 8 主题无缝切换，比 Tailwind `@theme` 令牌更灵活
- 统一的样式方案降低新成员上手成本

**2026-06-20 修正**：原设计中的 Tailwind `@theme` 令牌方案已被 `--th-*` CSS 变量替代。原因：`@theme` 无法实现运行时多主题切换，而 `[data-theme]` 选择器 + CSS 变量可以零 JS 开销切换。

**使用规则**：
- `globals.css` 负责 8 套 `[data-theme]` 变量定义 + `@layer base` 全局重置
- 组件中使用 `style={{ color: "var(--th-text)" }}` 或 `className="text-[var(--th-text)]"` 引用主题色
- 零硬编码色值，零 CSS Module

### ADR-2: Next.js Middleware 统一认证

**决策**：所有需认证路由通过单一 `middleware.ts` 保护，删除组件级 AuthGuard 和内联 useEffect。

**实现**：
```typescript
// middleware.ts
export const config = {
  matcher: [
    "/projects/:path*",
    "/workspace/:path*",
    "/admin/:path*",
    "/settings/:path*",
    "/history",
    "/import",
    "/notifications",
    "/pricing",
    "/vaults/:path*",
    "/weave",
  ],
};
```
- 未认证 → 302 重定向 `/auth?redirect=<原路径>`
- Token 已过期 → 尝试 refresh，失败则重定向
- 公开路由（`/`, `/auth`, `/landing`）不经过 middleware

### ADR-3: 按功能领域拆分，单文件 ≤300 行

**决策**：所有巨型文件按功能领域拆分。

| 原文件 | 拆分为 | 每文件行数 |
|--------|--------|-----------|
| `lib/api.ts` (940行) | `api/auth.ts` / `api/projects.ts` / `api/chapters.ts` / `api/cards.ts` / `api/generation.ts` / `api/vault.ts` / `api/health.ts` / `api/settings.ts` / `api/admin.ts` / `api/notifications.ts` / `api/subscription.ts` / `api/weave.ts` / `api/import.ts` / `api/phase4.ts` | ≤80 |
| `mock/index.ts` (964行) | `mock/handlers/auth.ts` / `mock/handlers/projects.ts` / ... (按领域) | ≤100 |
| `contexts/WorkspaceContext.tsx` (338行) | 拆分为 `WorkspaceProvider` + 多个专用 TanStack Query hooks | ≤200 |
| `globals.css` (771行) | `globals.css` (主题令牌+重置) + `components.css` (组件样式) | ≤400 |

### ADR-4: OpenAPI 自动生成类型，强制使用

**决策**：基于 `openapi.json` 使用 `openapi-typescript` 生成 `api-types.ts`，所有 API 函数强制使用。

**CI 集成**：`openapi:check` 脚本对比后端实际响应与前端类型，漂移时 CI 失败。

### ADR-5: TanStack Query 全量覆盖，删除旧 wrapper

**决策**：所有服务端数据状态由 TanStack Query 管理。删除 `useApi`、`usePolling` 以及 Context 中的兼容存根。

### ADR-6: 组件四态强制

**决策**：每个数据驱动组件必须覆盖四种状态，代码审查时验证：

1. **Loading** — Skeleton 骨架屏或 Spinner
2. **Empty** — EmptyState 组件，含操作引导
3. **Error** — ErrorState 组件，含重试按钮
4. **Normal** — 数据展示

### ADR-7: 单例模式 API 客户端重构

**决策**：`apiClient` 拆分为三个独立模块：
- `lib/http/client.ts` — 纯净 HTTP 请求（fetch wrapper）
- `lib/http/cache.ts` — GET 去重 + 响应缓存
- `lib/http/auth.ts` — Token 管理与自动刷新

---

## 2. 目录结构设计

```
moling-web/src/
├── app/                            # Next.js App Router
│   ├── layout.tsx                  # 根布局（Server Component）
│   ├── page.tsx                    # 首页（Server Component）
│   ├── not-found.tsx               # 404
│   ├── error.tsx                   # 全局错误
│   ├── globals.css                 # @theme 令牌 + @layer base
│   ├── components.css              # @layer components 样式
│   │
│   ├── (public)/                   # 公开路由组（无认证）
│   │   ├── landing/page.tsx
│   │   └── auth/
│   │       ├── layout.tsx
│   │       └── page.tsx
│   │
│   └── (app)/                      # 需认证路由组（middleware保护）
│       ├── layout.tsx              # App Shell（含侧边栏、顶栏）
│       ├── projects/
│       │   ├── page.tsx
│       │   ├── new/page.tsx
│       │   └── [projectId]/
│       │       ├── edit/page.tsx
│       │       └── import/page.tsx
│       ├── workspace/
│       │   └── [projectId]/
│       │       ├── layout.tsx
│       │       ├── page.tsx
│       │       ├── health/page.tsx
│       │       └── phase4/
│       │           ├── page.tsx
│       │           └── tasks/page.tsx
│       ├── admin/page.tsx
│       ├── settings/page.tsx
│       ├── history/page.tsx
│       ├── import/page.tsx
│       ├── notifications/page.tsx
│       ├── pricing/page.tsx
│       ├── vaults/[projectId]/page.tsx
│       └── weave/page.tsx
│
├── components/
│   ├── ui/                         # 原子UI组件
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── textarea.tsx
│   │   ├── select.tsx
│   │   ├── modal.tsx
│   │   ├── toast.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── skeleton.tsx
│   │   ├── spinner.tsx
│   │   ├── empty-state.tsx
│   │   ├── error-state.tsx
│   │   ├── badge.tsx
│   │   ├── card.tsx
│   │   ├── tabs.tsx
│   │   ├── tooltip.tsx
│   │   └── resizable-handle.tsx
│   │
│   ├── layout/                     # 布局组件
│   │   ├── app-shell.tsx
│   │   ├── sidebar.tsx
│   │   ├── navbar.tsx
│   │   └── bottom-nav.tsx
│   │
│   ├── auth/                       # 认证组件
│   │   ├── login-form.tsx
│   │   ├── register-form.tsx
│   │   ├── reset-password-form.tsx
│   │   └── auth-tabs.tsx
│   │
│   ├── projects/                   # 项目组件
│   │   ├── project-card.tsx
│   │   ├── project-form.tsx
│   │   ├── project-stats.tsx
│   │   ├── creation-mode-card.tsx
│   │   └── template-selector.tsx
│   │
│   ├── workspace/                  # 工作台组件
│   │   ├── editor.tsx
│   │   ├── left-panel.tsx
│   │   ├── right-panel.tsx
│   │   ├── library-panel.tsx
│   │   ├── chapter-selector.tsx
│   │   ├── card-modal.tsx
│   │   ├── ai-toolbox.tsx
│   │   ├── generation-progress.tsx
│   │   ├── inspiration-card.tsx
│   │   └── toolbar.tsx
│   │
│   ├── vault/                      # 四库组件
│   │   ├── character-list.tsx
│   │   ├── character-detail.tsx
│   │   ├── timeline-list.tsx
│   │   ├── plot-promise-list.tsx
│   │   ├── world-list.tsx
│   │   └── vault-tabs.tsx
│   │
│   ├── health/                     # 健康监控组件
│   │   ├── health-dashboard.tsx
│   │   └── health-banner.tsx
│   │
│   ├── phase4/                     # Phase 4 组件
│   │   ├── card-manager.tsx
│   │   ├── task-panel.tsx
│   │   └── safety-indicator.tsx
│   │
│   ├── landng/                     # 落地页组件
│   │   └── landing-page.tsx
│   │
│   ├── notifications/              # 通知组件
│   │   ├── notification-item.tsx
│   │   └── notification-list.tsx
│   │
│   ├── import/                     # 导入组件
│   │   ├── import-wizard.tsx
│   │   └── import-progress.tsx
│   │
│   └── providers/                  # Provider 组件
│       ├── providers.tsx           # Provider 组合器
│       ├── theme-provider.tsx
│       └── error-boundary.tsx
│
├── lib/
│   ├── api/                        # API 函数（按领域拆分）
│   │   ├── index.ts                # 统一导出
│   │   ├── auth.ts
│   │   ├── projects.ts
│   │   ├── chapters.ts
│   │   ├── cards.ts
│   │   ├── generation.ts
│   │   ├── vault.ts
│   │   ├── health.ts
│   │   ├── settings.ts
│   │   ├── admin.ts
│   │   ├── notifications.ts
│   │   ├── subscription.ts
│   │   ├── weave.ts
│   │   ├── import.ts
│   │   ├── phase4.ts
│   │   └── chapter-agent.ts
│   │
│   ├── http/                       # HTTP 客户端
│   │   ├── client.ts               # fetch wrapper
│   │   ├── cache.ts                # GET去重+缓存
│   │   ├── auth.ts                 # Token管理+自动刷新
│   │   ├── errors.ts               # ApiError 类
│   │   └── types.ts                # HTTP 通用类型
│   │
│   ├── validation/                 # Zod 验证
│   │   ├── schemas.ts              # 所有 Zod schema
│   │   ├── response.ts            # 响应验证 middleware
│   │   └── types.ts                # 从 schema 导出的类型
│   │
│   ├── types/                      # 类型定义
│   │   ├── api-types.ts            # OpenAPI 自动生成（不手动编辑）
│   │   ├── domain.ts               # 领域类型补充
│   │   └── common.ts               # 通用类型（ApiResponse等）
│   │
│   ├── hooks/                      # 自定义 Hooks
│   │   ├── queries/                # TanStack Query hooks
│   │   │   ├── use-auth.ts
│   │   │   ├── use-projects.ts
│   │   │   ├── use-chapters.ts
│   │   │   ├── use-cards.ts
│   │   │   ├── use-generation.ts
│   │   │   ├── use-vault.ts
│   │   │   ├── use-health.ts
│   │   │   ├── use-settings.ts
│   │   │   ├── use-admin.ts
│   │   │   ├── use-notifications.ts
│   │   │   ├── use-subscription.ts
│   │   │   ├── use-weave.ts
│   │   │   ├── use-import.ts
│   │   │   ├── use-chapter-agent.ts
│   │   │   └── use-phase4.ts
│   │   ├── use-debounce.ts
│   │   ├── use-resizable-panel.ts
│   │   └── use-touch-gesture.ts
│   │
│   ├── context/                    # Context (仅UI状态)
│   │   ├── theme-context.tsx
│   │   └── workspace-ui.tsx         # 仅UI状态（抽屉展开、面板宽度等）
│   │
│   ├── constants.ts                # 路由/API常量（已存在，增强）
│   ├── cn.ts                       # clsx + tailwind-merge 工具
│   ├── format.ts                   # 日期/数字格式化
│   └── env.ts                      # 环境变量类型封装
│
├── mock/                           # Mock 系统
│   ├── index.ts                    # Mock 注册入口
│   ├── registry.ts                 # Mock 注册表（从 apiClient 迁出）
│   ├── utils.ts                    # ok/paginate/findItem 等 helper
│   ├── state.ts                    # Mock 可变状态（Map 存储，替代全局变量）
│   ├── data/                       # Mock 种子数据
│   │   ├── projects.ts
│   │   ├── chapters.ts
│   │   ├── cards.ts
│   │   ├── vault.ts
│   │   ├── health.ts
│   │   └── system-health.ts
│   └── handlers/                   # Mock handlers（按领域拆分）
│       ├── auth.ts
│       ├── projects.ts
│       ├── chapters.ts
│       ├── cards.ts
│       ├── generation.ts
│       ├── vault.ts
│       ├── health.ts
│       ├── settings.ts
│       ├── admin.ts
│       ├── notifications.ts
│       ├── subscription.ts
│       ├── weave.ts
│       ├── import.ts
│       ├── phase4.ts
│       └── chapter-agent.ts
│
├── middleware.ts                    # 统一认证守卫
├── instrumentation.ts              # Sentry 初始化
└── sentry.*.config.ts              # Sentry 配置
```

---

## 3. 路由与布局设计

### 3.1 路由分组

```
/                          → 首页（公开）
/landing                   → 落地页（公开）
/auth                      → 认证页（公开，已登录重定向到 /projects）
───────────────────── ⬆ middleware 边界 ⬆ ─────────────────────
/projects                  → 项目列表
/projects/new              → 新建项目
/projects/[id]/edit        → 编辑项目
/projects/[id]/import      → 导入已有
/workspace/[projectId]     → 工作台（三栏布局）
/workspace/[projectId]/health    → 健康仪表盘
/workspace/[projectId]/phase4    → Phase 4 概览
/workspace/[projectId]/phase4/tasks → Phase 4 任务列表
/admin                     → 管理面板
/settings                  → 用户设置
/history                   → 生成历史
/import                    → 导入管理
/notifications             → 通知中心
/pricing                   → 订阅定价
/vaults/[projectId]        → 四库独立视图
/weave                     → Weave 编织
```

### 3.2 布局嵌套

```
RootLayout (globals.css, Providers)
├── (public)/layout       — 极简布局（无侧边栏）
│   ├── /landing
│   └── /auth
├── / (首页)              — 特殊布局
├── (app)/layout           — App Shell（侧边栏 + 顶栏 + 底部导航）
│   ├── /projects/**
│   ├── /workspace/**      — 工作台三栏自定义布局
│   ├── /admin
│   ├── /settings
│   ├── /history
│   ├── /import
│   ├── /notifications
│   ├── /pricing
│   ├── /vaults/**
│   └── /weave
└── not-found
```

### 3.3 工作台布局

```
┌─────────────────────────────────────────────────┐
│  [Navbar: 项目名 ▾  |  ChapterSelector ▾  |  ...]  │ Height: 56px
├──────────┬──────────────────────┬───────────────┤
│ LeftPanel│     Editor            │  RightPanel   │
│ (四库)    │   (主编辑器)          │  (AI工具箱)    │
│          │                      │               │
│ 角色库    │   ProseMirror        │  WeightSlider │
│ 时间线    │   或 Textarea        │  DrawButton   │
│ 伏笔库    │                      │  Progress     │
│ 世界观    │                      │               │
│          │                      │               │
│ Resizable│          Resizable   │               │
│ 220-400px│          60%         │  280-400px    │
└──────────┴──────────────────────┴───────────────┘
|                BottomNav (mobile)               | Height: 56px
```

---

## 4. 数据流设计

### 4.1 架构分层

```
┌─────────────────────────────────────────────────────┐
│                   React Components                   │
│  (仅关注渲染和用户交互)                               │
├─────────────────────────────────────────────────────┤
│              TanStack Query Hooks                     │
│  (数据获取缓存/同步/乐观更新)                          │
├─────────────────────────────────────────────────────┤
│                  API Layer (lib/api/)                 │
│  (HTTP请求封装/类型安全)                               │
├─────────────────────────────────────────────────────┤
│              HTTP Client (lib/http/)                  │
│  (fetch/token/缓存/去重)                              │
├─────────────────────────────────────────────────────┤
│              Zod Validation Layer                     │
│  (响应验证/类型收窄)                                  │
├─────────────────────────────────────────────────────┤
│               Backend API / Mock                      │
└─────────────────────────────────────────────────────┘
```

### 4.2 状态归属决策表

| 状态类型 | 存放位置 | 示例 |
|---------|---------|------|
| 服务端数据 | TanStack Query | 项目列表、章节内容、四库数据、卡牌池 |
| 认证状态 | `AuthContext` (轻量级) | user, isAuthenticated, logout() |
| 主题偏好 | `ThemeContext` | theme, setTheme |
| 工作台UI状态 | `WorkspaceUIContext` | 面板宽度、抽屉展开、当前选中Tab |
| 表单状态 | 组件局部 `useState` | 输入值、验证错误 |
| 路由状态 | URL params | projectId, chapterId |

### 4.3 TanStack Query 键设计

```typescript
// 查询键工厂
export const queryKeys = {
  projects: {
    all:     ["projects"] as const,
    list:    (filters?: ProjectFilters) => ["projects", "list", filters] as const,
    detail:  (id: string) => ["projects", "detail", id] as const,
    stats:   (id: string) => ["projects", "stats", id] as const,
  },
  chapters: {
    list:    (projectId: string) => ["chapters", "list", projectId] as const,
    detail:  (projectId: string, chapterId: string) =>
             ["chapters", "detail", projectId, chapterId] as const,
  },
  vault: {
    all:     (projectId: string) => ["vault", "all", projectId] as const,
    byType:  (projectId: string, type: VaultType) =>
             ["vault", "detail", projectId, type] as const,
  },
  cards: {
    pool:    (projectId: string) => ["cards", "pool", projectId] as const,
  },
  generation: {
    job:     (taskId: string) => ["generation", "job", taskId] as const,
    history: (projectId: string) => ["generation", "history", projectId] as const,
  },
  health: {
    project: (projectId: string) => ["health", "project", projectId] as const,
    system:  () => ["health", "system"] as const,
  },
  // ... 其他领域同理
} as const;
```

---

## 5. API 层设计

### 5.1 HTTP Client 模块化

```typescript
// lib/http/client.ts — 纯净 fetch wrapper
async function request<T>(method: string, url: string, options?: RequestOptions): Promise<T>

// lib/http/cache.ts — 缓存与去重
const cache = new DedupCache({ ttl: 30_000, maxSize: 50 });
// 通过 request() 包装器自动注入

// lib/http/auth.ts — Token 管理
let tokenRefresher: Promise<string> | null = null; // 去重
async function refreshToken(): Promise<string>
function getAccessToken(): string | null
```

### 5.2 API 函数模式

```typescript
// lib/api/projects.ts
import type { paths } from "@/lib/types/api-types";  // OpenAPI 生成

type ProjectListResponse = paths["/projects"]["get"]["responses"]["200"]["content"]["application/json"];

export async function listProjects(params?: {
  status?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}): Promise<ProjectListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  // ...
  return apiGet(`/projects?${searchParams.toString()}`);
}
```

### 5.3 Zod 响应验证

```typescript
// lib/validation/response.ts
import { z } from "zod";

// 开发模式下验证所有API响应
export function validateResponse<T>(schema: z.ZodSchema<T>, data: unknown): T {
  if (process.env.NODE_ENV === "development") {
    const result = schema.safeParse(data);
    if (!result.success) {
      console.error("[API Validation]", result.error.format());
    }
    return data as T;
  }
  return data as T;
}
```

```typescript
// hooks/queries/use-projects.ts
import { projectSchema } from "@/lib/validation/schemas";

export function useProjectDetail(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: async () => {
      const res = await projectApi.getById(projectId);
      return validateResponse(projectSchema, res.data);
    },
  });
}
```

---

## 6. Mock 系统设计

### 6.1 注册机制

```typescript
// mock/registry.ts
type MockHandler = (
  method: string,
  path: string,
  body?: unknown
) => Promise<ApiResponse<unknown>>;

class MockRegistry {
  private handlers = new Map<string, MockHandler>();

  register(method: string, pathPattern: string, handler: MockHandler): void {
    this.handlers.set(`${method}:${pathPattern}`, handler);
  }

  match(method: string, path: string): MockHandler | undefined {
    // 精确匹配 + 路径参数解析（如 /projects/:id → /projects/abc123）
    return this.handlers.get(`${method}:${path}`);
  }
}
```

### 6.2 路径一致性保证

```typescript
// mock/handlers/projects.ts
import { API_ENDPOINTS } from "@/lib/constants";

export function registerProjectMocks(registry: MockRegistry) {
  registry.register("GET", API_ENDPOINTS.PROJECTS.LIST, handleListProjects);
  registry.register("GET", "/projects/:id", handleGetProject); // 使用通配符匹配
  registry.register("POST", API_ENDPOINTS.PROJECTS.CREATE, handleCreateProject);
}
```

**关键**：Mock handler 直接引用 `API_ENDPOINTS` 常量，确保路径永远与实际 API 一致。

### 6.3 状态隔离

```typescript
// mock/state.ts — 替代全局可变变量
class MockState {
  private data = new Map<string, unknown>();

  get<T>(key: string): T { return this.data.get(key) as T; }
  set<T>(key: string, value: T): void { this.data.set(key, value); }
  reset(): void { this.data.clear(); }  // 支持重置
}

export const mockState = new MockState();
```

---

## 7. 组件设计规范

### 7.1 四态契约

```typescript
interface DataComponentProps<T> {
  data: T | undefined;
  isLoading: boolean;
  error: Error | null;
  onRetry?: () => void;
}

// 组件内部：
function VaultCharacterList({ data, isLoading, error, onRetry }: DataComponentProps<Character[]>) {
  if (isLoading) return <CharacterListSkeleton />;
  if (error) return <ErrorState message="加载角色库失败" onRetry={onRetry} />;
  if (!data || data.length === 0) return <EmptyState title="暂无角色" description="创建第一个角色..." />;
  return <CharacterItems characters={data} />;
}
```

### 7.2 组件 Props 设计原则

- 数据组件：使用 `{ data, isLoading, error, onRetry }` 四元组
- UI 组件：受控优先（value + onChange），支持非受控变体
- 所有组件导出 Props 类型供外部使用
- 组件不直接调用 API hook，由页面层组装数据 → 组件接收 props

### 7.3 UI 组件目录

| 组件 | 基于 | 变体 | 状态 |
|------|------|------|------|
| `Button` | `<button>` | primary / secondary / ghost / danger | loading / disabled / active |
| `Input` | `<input>` | text / password / number / search | error / disabled / readonly |
| `Modal` | Radix Dialog | — | open / close 动画 |
| `Toast` | 自定义 portal | success / error / warning / info | enter / exit 动画 |
| `Dropdown` | Radix DropdownMenu | — | nested items |
| `Select` | Radix Select | — | open / close |
| `Tabs` | Radix Tabs | — | active / disabled |
| `Skeleton` | 自定义 | text / circle / rect | shimmer 动画 |
| `EmptyState` | 自定义 | compact / full | — |
| `ErrorState` | 自定义 | compact / full | retry button |
| `Badge` | `<span>` | default / success / warning / danger | — |
| `Card` | `<div>` | flat / elevated / interactive | hover |
| `Tooltip` | Radix Tooltip | — | — |
| `Spinner` | 自定义 | sm / md / lg | — |

---

## 8. 渐进交付计划

### Batch 0: 基础设施 (预估 ~3天)

- [ ] `moling-web/src/` 清空，保留 `package.json`/`next.config.ts`/`Dockerfile`
- [ ] 新目录结构搭建
- [ ] `globals.css` + `components.css`（主题令牌 + 基础样式）
- [ ] `lib/http/` HTTP 客户端三模块
- [ ] `lib/validation/` Zod schema + 响应验证
- [ ] `lib/cn.ts` / `lib/format.ts` / `lib/constants.ts` / `lib/env.ts`
- [ ] `middleware.ts` 统一认证
- [ ] `instrumentation.ts` Sentry 初始化
- [ ] `providers/` 提供者组合器
- [ ] CI: `openapi:generate` → `api-types.ts`

### Batch 1: UI 组件库 (预估 ~2天)

- [ ] 全部 `components/ui/` 组件（14个）
- [ ] 每个组件包含 Loading/Empty/Error/Normal 四态
- [ ] Design token 验证（深色/浅色主题切换）
- [ ] 组件 Storybook 或测试页面验证
- [ ] 布局组件：AppShell / Sidebar / Navbar / BottomNav

### Batch 2: 认证 + 项目 (预估 ~2天)

- [ ] 公开路由：/ /landing /auth
- [ ] 认证页面：LoginForm / RegisterForm / ResetPasswordForm / AuthTabs
- [ ] 认证 API + hooks + mock
- [ ] 项目列表页 + 项目新建/编辑/导入
- [ ] 项目组件：ProjectCard / ProjectForm / TemplateSelector
- [ ] 项目 API + hooks + mock

### Batch 3: 工作台核心 (预估 ~3天)

- [ ] 工作台三栏布局 + ResizableHandle
- [ ] 编辑器组件（ProseMirror 集成）
- [ ] 章节选择器
- [ ] 左面板 + 四库组件
- [ ] 右面板 + AI 工具箱 + 权重滑块
- [ ] 卡牌系统 + 抽卡动画
- [ ] 生成进度
- [ ] 工作台 API + hooks + mock

### Batch 4: 四库 + Phase 4 (预估 ~2天)

- [ ] 四库管理：角色库 / 时间线 / 伏笔库 / 世界观
- [ ] Phase 4 概览页 + 任务面板
- [ ] Phase 4 API + hooks + mock

### Batch 5: 其余模块 (预估 ~2天)

- [ ] 管理面板 (/admin)
- [ ] 设置 (/settings)
- [ ] 通知中心 (/notifications)
- [ ] 生成历史 (/history)
- [ ] 导入管理 (/import)
- [ ] 定价 (/pricing)
- [ ] Weave (/weave)
- [ ] 健康仪表盘 (/workspace/[id]/health)
- [ ] 各自 API + hooks + mock

### Batch 6: 收尾 (预估 ~1天)

- [ ] 移动端适配全量验证
- [ ] Lighthouse 性能优化（≥90 目标）
- [ ] ESLint strict 全量通过，`ignoreBuildErrors: false`
- [ ] Vitest 测试覆盖 ≥80%
- [ ] Playwright E2E 关键流程覆盖
- [ ] `openapi:check` 类型漂移检测通过

**总计预估：~15天**

---

## 9. 质量保证

### 9.1 ESLint 规则（严格模式）

```json
{
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/strict-boolean-expressions": "error",
  "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
  "react-hooks/exhaustive-deps": "error",
  "no-console": "warn",
  "import/no-cycle": "error"
}
```

### 9.2 测试策略

| 层级 | 工具 | 覆盖目标 | 覆盖内容 |
|------|------|---------|---------|
| 单元 | Vitest | ≥80% | UI 组件渲染、API 函数、Zod Schema |
| 集成 | Vitest + MSW | 核心流程 | TanStack Query + Mock 完整流程 |
| E2E | Playwright | 3条关键流程 | 登录→创建项目→工作台→生成 / 登录→抽卡→写章节 / 登录→四库管理 |

### 9.3 性能目标

| 指标 | 目标 |
|------|------|
| FCP (First Contentful Paint) | < 1.5s |
| LCP (Largest Contentful Paint) | < 2.5s |
| TBT (Total Blocking Time) | < 200ms |
| CLS (Cumulative Layout Shift) | < 0.1 |
| 组件渲染帧率 | ≥60fps |

---

*待确认后进入 Phase 3: Tasks*
