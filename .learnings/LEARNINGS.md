# Learnings

Corrections, insights, and knowledge gaps captured during development.

---

## [LRN-20260614-001] best_practice

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
`from app.dao import user_dao` imports a singleton UserDAO **instance**, not the module. Calling `user_dao.UserDAO()` raises `'UserDAO' object has no attribute 'UserDAO'`.

### Details
In `app/dao/__init__.py`, `user_dao = UserDAO()` creates a singleton instance. When services do `from app.dao import user_dao`, they get the instance. Then `user_dao.UserDAO()` tries `.UserDAO` attribute on the instance, which doesn't exist. Fix: just use `user_dao` directly.

### Suggested Action
Search all service files for `user_dao.UserDAO()` pattern using grep.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: auth_service.py (lines 250, 293)
- **Notes**: Changed `dao = user_dao.UserDAO()` to `dao = user_dao`

### Metadata
- Source: runtime error
- Related Files: app/dao/__init__.py, app/service/auth_service.py
- Tags: dao, singleton, import, common_mistake

---

## [LRN-20260614-002] insight

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
Windows + aiosqlite + async SQLAlchemy has a known greenlet issue that cannot be fully patched. The `greenlet_spawn` monkey patch works for some operations but fails when `aiosqlite.connect()` (inherently async) is called from within the thread pool executor.

### Details
The greenlet patch in `dependencies.py` replaces `greenlet_spawn` with a thread pool executor. This works for sync-to-async bridging but fails for async-to-async calls like `aiosqlite` connection. The fix for `get_current_user` was to switch to `SyncSession` (sync DB), which completely avoids the async path.

### Suggested Action
For Windows development, either:
1. Switch all DB operations to sync sessions
2. Use a sync SQLite driver (e.g., pysqlite)
3. Document that production should run on Linux

### Metadata
- Source: runtime testing
- Related Files: app/dependencies.py, app/dao/base_dao.py
- Tags: windows, greenlet, aiosqlite, async

---

## [LRN-20260614-003] best_practice

**Logged**: 2026-06-14T16:20:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
Card service `get_draw_history()` method existed but router returned hardcoded `[]`. Router TODO comment said "implement get_draw_history in service" but the method was already implemented.

### Details
The router at `app/router/card.py:69` had `# TODO: implement get_draw_history in service` and returned `[]`. But `card_service.get_draw_history()` at `card_service.py:322` was fully implemented. Fix: simply call the service method.

### Suggested Action
Search for other routers with TODO comments that reference already-implemented service methods.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: app/router/card.py

### Metadata
- Source: code audit
- Related Files: app/router/card.py, app/service/card_service.py
- Tags: dead_code, router, stub

---

## [LRN-20260614-004] best_practice

**Logged**: 2026-06-14T17:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
Pydantic v2 `populate_by_name=True` + `from_attributes=True` causes SQLAlchemy ORM relation lists to be passed as field values, breaking field validation.

### Details
When `model_config = {"from_attributes": True, "populate_by_name": True}`, Pydantic tries both `validation_alias` and field name during population. For a field like `chapters: int` with `validation_alias="chapter_count"`, when the ORM object has a `chapters` relationship list but no `chapter_count` attribute, Pydantic falls back to passing the relationship list to the `chapters` field. This causes `ValidationError` because `list` is not `int`.

### Suggested Action
For MVP, remove `populate_by_name=True` and add a `@field_validator("chapters", mode="before")` to convert list→int. Also, never type ORM id fields as `str` when SQLAlchemy returns `int` — use `int`.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: app/schemas/project.py
- **Notes**: Removed `populate_by_name=True`, added field_validator for chapters, changed `id: str`→`id: int`

### Metadata
- Source: e2e testing (500 error on project creation)
- Related Files: app/schemas/project.py
- Tags: pydantic, schema, validation, common_mistake

---

## [LRN-20260614-005] pitfall

**Logged**: 2026-06-14T17:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
Frontend mock data (`mockTimelines`) uses a flat structure with `event: string` while the `VaultTimeline` interface expects `events: VaultTimelineEvent[]`. This mismatch causes TypeScript error when mock code tries `t.events`.

### Details
The mock timeline data at `src/mock/vault.ts:79` stores individual timeline entries with `event` (singular string), but `@/lib/types.ts:148` defines `VaultTimeline.events` as `VaultTimelineEvent[]`. When mock code at `index.ts:950` accesses `t.events`, TypeScript reports it doesn't exist because the mock data uses a different shape.

### Suggested Action
Use `map()` to convert mock data to the correct shape rather than `flatMap()`, since each mock entry IS a single event.

### Resolution
- **Resolved**: 2026-06-14
- **Files Fixed**: src/mock/index.ts

### Metadata
- Source: tsc type checking
- Related Files: src/mock/vault.ts, src/mock/index.ts, src/lib/types.ts
- Tags: typescript, mock, type_mismatch

---

## [LRN-20260615-001] insight

**Logged**: 2026-06-15T15:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra | docker

### Summary
Debian Trixie (the testing branch) renamed `libffi7` to `libffi8`. When using `python:3.11-slim` or newer as base image, always check the actual package names in the Debian package repository.

### Details
The `python:3.11-slim` image is based on Debian. As Debian upgrades from Bookworm (stable) to Trixie (testing), package names may change. The `libffi` runtime package was renamed from `libffi7` (Bookworm) to `libffi8` (Trixie). This broke our Docker build.

**Lesson**: Don't hardcode package names in Dockerfiles. Either:
1. Use a specific Debian version (e.g., `python:3.11-slim-bookworm`)
2. Check the actual package name dynamically (e.g., `apt-cache search libffi | head -5`)

### Suggested Action
For production Dockerfiles, pin the base image to a specific Debian version to avoid surprises.

### Metadata
- Source: Docker build failure
- Related Files: moling-server/Dockerfile
- Tags: debian, docker, package-management

---

## [LRN-20260615-002] best_practice

**Logged**: 2026-06-15T15:15:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend | deps

### Summary
When specifying version constraints in `pyproject.toml` (or `requirements.txt`), always specify both lower and upper bounds. Single-bound constraints (e.g., `<4.1` or `>=4.0`) will break when the latest version exceeds the upper bound or when the oldest version satisfying the lower bound is no longer available.

### Details
We had `bcrypt<4.1` in `pyproject.toml`. This worked fine until bcrypt 4.1.0 was released, at which point pip couldn't find any version that satisfies `<4.1`. The fix was to specify both bounds: `bcrypt>=4.0,<5.0`.

**Lesson**: Always use `">=min,<max"` format for version constraints.

### Suggested Action
Audit all version constraints in `pyproject.toml` to ensure they have both lower and upper bounds.

### Metadata
- Source: pip install failure
- Related Files: moling-server/pyproject.toml
- Tags: python, dependencies, versioning

---

## [LRN-20260615-003] best_practice

**Logged**: 2026-06-15T15:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | docker

### Summary
In Dockerfiles, `ENV NODE_ENV=production` must be set AFTER `npm ci` (or `npm install`), otherwise npm will skip devDependencies. This is a common mistake that causes build failures for Next.js and other frameworks that require devDependencies at build time.

### Details
Our Dockerfile had:
```dockerfile
ENV NODE_ENV=production
RUN npm ci
```
This caused `npm ci` to skip devDependencies (including `typescript`), which caused Next.js build to fail with "Cannot find module 'typescript'".

The correct order is:
```dockerfile
RUN npm ci
ENV NODE_ENV=production
```

**Lesson**: Always install dependencies before setting `NODE_ENV=production`.

### Suggested Action
Audit all Dockerfiles to ensure `ENV NODE_ENV=production` is set after `npm ci` / `npm install`.

### Metadata
- Source: Next.js build failure
- Related Files: moling-web/Dockerfile
- Tags: docker, nodejs, npm, common_mistake

---

## [LRN-20260615-004] pitfall

**Logged**: 2026-06-15T15:45:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | cross-platform

### Summary
Windows is case-insensitive for filenames, but Linux is case-sensitive. This causes code that works on Windows to fail in Docker Linux containers (or on CI/CD). Always ensure import statements exactly match the filename (including case).

### Details
We had `import styles from './Settings.module.css'` in the code, but the actual file was `settings.module.css` (lowercase `s`). On Windows, this works fine because Windows doesn't distinguish case. But in Docker (Linux), the import fails because Linux distinguishes case.

**Lesson**: Use linting rules (e.g., ESLint's `import/no-unresolved`) to catch case mismatches early. Or use a case-sensitive filesystem for development (e.g., WSL2 on Windows).

### Suggested Action
Add ESLint rule to enforce correct import paths. Consider using WSL2 for development on Windows.

### Metadata
- Source: Docker build failure
- Related Files: moling-web/src/app/settings/page.tsx
- Tags: windows, linux, case-sensitivity, common_mistake

---

## [LRN-20260615-005] best_practice

**Logged**: 2026-06-15T16:00:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | nextjs

### Summary
When deploying Next.js to a subpath (e.g., `/moling`), use the `basePath` config option in `next.config.ts`. This automatically prefixes all routes and static asset paths with the subpath, so you don't need to manually rewrite paths in the reverse proxy.

### Details
We configured `basePath: "/moling"` in `next.config.ts`. This caused Next.js to:
1. Prefix all routes with `/moling` (e.g., `/` becomes `/moling/`, `/api/health` becomes `/moling/api/health`)
2. Prefix all static asset paths with `/moling` (e.g., `/_next/static/...` becomes `/moling/_next/static/...`)

This made the Nginx configuration much simpler: we just needed to proxy `/moling` to the Next.js container, and Next.js handled the rest.

**Lesson**: Use Next.js built-in `basePath` and `assetPrefix` options for subpath deployments. Don't try to manually rewrite paths in the reverse proxy.

### Suggested Action
Document the `basePath` configuration in the deployment guide.

### Metadata
- Source: deployment experience
- Related Files: moling-web/next.config.ts
- Tags: nextjs, deployment, subpath

---

## [LRN-20260615-006] best_practice

**Logged**: 2026-06-15T16:15:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend | deps

### Summary
Pydantic's `EmailStr` type requires the `email-validator` package, but this is not installed by default. Always add `email-validator` to your dependencies when using `EmailStr`.

### Details
We got `ImportError: email-validator is not installed, run pip install 'pydantic[email]'` when starting the backend. The fix was to add `email-validator>=2.2.0` to `pyproject.toml`.

**Lesson**: When using pydantic's special types (EmailStr, UrlStr, etc.), check if they require additional dependencies. The pydantic documentation lists these requirements.

### Suggested Action
Audit all pydantic schemas to ensure all required dependencies are installed.

### Metadata
- Source: backend startup failure
- Related Files: moling-server/pyproject.toml
- Tags: pydantic, dependencies, gotcha

---

## [LRN-20260615-007] pitfall

**Logged**: 2026-06-15T16:30:00+08:00
**Priority**: high
**Status**: resolved
**Area**: infra | nginx

### Summary
In Nginx, `location /moling/` (with trailing slash) only matches paths that exactly have the trailing slash (or paths below it). If you want to match `/moling` without trailing slash AND `/moling/...` with trailing slash, use `location /moling` (without trailing slash).

### Details
We had `location /moling/ { ... }` in the Nginx config. This caused a redirect loop because:
1. User visits `/moling` (no trailing slash)
2. Next.js redirects to `/moling/` (adds trailing slash)
3. Nginx doesn't match `/moling` (without trailing slash), so it doesn't proxy to Next.js
4. The redirect happens again, causing a loop

The fix was to change to `location /moling` (without trailing slash), which matches all paths starting with `/moling`.

**Lesson**: Be careful with trailing slashes in Nginx `location` directives. Use `location /path` (without trailing slash) to match all paths starting with `/path`.

### Suggested Action
Document Nginx configuration best practices in the deployment guide.

### Metadata
- Source: deployment experience
- Related Files: /etc/nginx/conf.d/moling.conf
- Tags: nginx, reverse-proxy, gotcha

---

## [LRN-20260615-008] best_practice

**Logged**: 2026-06-15T16:45:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: infra | docker

### Summary
When building Docker images from China, always configure domestic mirrors for apt and pip. This can reduce build time from 17+ minutes to 3-5 minutes.

### Details
We added the following to our Dockerfiles:
```dockerfile
# apt 使用阿里云镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends ...

# pip 使用阿里云镜像
RUN pip install --upgrade pip && \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir .
```

This reduced the build time significantly.

**Lesson**: For teams in China, always configure domestic mirrors in Dockerfiles. For teams outside China, make the mirror configurable (e.g., via build args).

### Suggested Action
Add build args to Dockerfiles to make mirrors configurable.

### Metadata
- Source: deployment experience
- Related Files: moling-server/Dockerfile, moling-web/Dockerfile
- Tags: docker, mirrors, china, performance

## [LRN-20260615-009] best_practice

**Logged**: 2026-06-15T18:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | react

### Summary
React 性能优化三大模式：React.memo 防止组件重渲染、useMemo 稳定 Context value 引用、useRef 避免闭包过期和依赖重建。

### Details
在墨灵前端优化中，发现以下关键模式：

1. **React.memo 包裹纯展示组件**：Button、Input、Modal、Toast 等 UI 组件用 React.memo 包裹后，
   只有 props 变化时才重渲染。注意：React.memo 是浅比较，如果传递了对象/函数引用（每次渲染都新建），
   则 memo 失效。

2. **Context value 用 useMemo 稳定**：`createContext(defaultValue)` 的 value 每次渲染都是新对象，
   导致所有 Consumer 重渲染。必须用 `useMemo(() => ({...}), [deps])` 包裹 value。

3. **useRef 保存可变值**：`useState` 的值每次渲染都不同（触发依赖更新），
   `useRef` 的 `.current` 是可变引用，不触发重渲染。适合保存：
   - 定时器 ID
   - 前一个 state 的引用（避免依赖）
   - 任何需要在 effect 中读取最新值但不想触发重渲染的变量

### Suggested Action
在新组件开发时，默认用 React.memo 包裹；Context 的 value 必须用 useMemo 稳定。

### Metadata
- Source: frontend-optimization
- Related Files: src/contexts/WorkspaceContext.tsx, src/contexts/AuthContext.tsx, src/components/ui/Button.tsx
- Tags: react, performance, memo, useMemo, useRef, best_practice

---

## [LRN-20260615-010] pitfall

**Logged**: 2026-06-15T18:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | react

### Summary
useEffect 依赖数组中放对象/数组引用（如 `currentChapter`，每次渲染都是新对象），
导致 effect 每次渲染都执行（无限触发 API 调用）。

### Details
`RightPanel.tsx` 中有 `useEffect(() => { fetchCards() }, [currentChapter])`，
但 `currentChapter` 是对象，每次渲染 `WorkspaceContext` 提供的都是新引用，
导致 `fetchCards()` 在每次按键时都执行。

**修复方案**：只依赖对象的具体字段，而非整个对象：
```tsx
// ❌ 错误：对象引用作为依赖
useEffect(() => { ... }, [currentChapter]);

// ✅ 正确：具体字段作为依赖
useEffect(() => { ... }, [currentChapter?.id, currentChapter?.project_id]);
```

同理，`LandingPage.tsx` 的 IntersectionObserver 回调中用了 `setVisibleElements(visibleElements + 1)`，
但 `visibleElements` 在依赖数组中，每次状态变化都触发 effect 重建（无限循环）。
修复：用函数式更新 `setVisibleElements(prev => prev + 1)`，并从依赖数组中移除 `visibleElements`。

### Suggested Action
永远不要将对象/数组直接放入 useEffect 依赖数组。使用 `obj?.id`、`arr?.length` 等原始值，
或用 `JSON.stringify(obj)` 做深比较（仅限小对象）。

### Metadata
- Source: frontend-optimization
- Related Files: src/components/workspace/RightPanel.tsx, src/components/landing/LandingPage.tsx
- Tags: react, useEffect, dependency, common_mistake, pitfall

---

## [LRN-20260615-011] best_practice

**Logged**: 2026-06-15T18:10:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | nextjs

### Summary
Next.js 生产环境配置优化：SWC 压缩、移除 X-Powered-By 头、移除 console、HTTP keep-alive、
禁用 ETag，可显著提升构建速度和运行时性能。

### Details
在 `next.config.ts` 中添加以下优化：

```typescript
const nextConfig: NextConfig = {
  reactStrictMode: true,
  swcMinify: true,              // SWC 压缩（默认开启，显式声明）
  poweredByHeader: false,        // 移除 X-Powered-By 头
  compress: true,                // 启用 gzip 压缩
  productionBrowserSourceMaps: false,  // 生产环境不生成 source map
  
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      config.optimization.minimize = true;
    }
    return config;
  },

  env: {
    NEXT_PUBLIC_BUILD_TIME: new Date().toISOString(),
  },
};
```

同时，在 `next.config.ts` 的 `webpack` 配置中，可以用 `terserMinifyOptions` 移除 console：
（实际是在 `next.config.mjs` 的 `compress` 选项，或 `swc` 配置中）

**注意**：Next.js 15+ 的 SWC 配置方式可能不同，需查阅最新文档。

### Suggested Action
每次创建新 Next.js 项目时，从这份配置模板开始。

### Metadata
- Source: frontend-optimization
- Related Files: moling-web/next.config.ts
- Tags: nextjs, configuration, performance, production

---

## [LRN-20260615-012] best_practice

**Logged**: 2026-06-15T18:15:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | api

### Summary
API 客户端优化三板斧：请求去重（同一 URL 并发请求合并为一个）、
响应缓存（GET 请求缓存 5 秒）、Token 刷新防并发（多个 401 只刷新一次）。

### Details
在 `src/lib/apiClient.ts` 中实现：

1. **请求去重**：用 `Map<string, Promise>` 记录进行中的 GET 请求，
   相同 URL 的并发请求复用同一个 Promise。

2. **响应缓存**：用 `Map<string, {data, expiry}>` 缓存 GET 响应，
   TTL 5 秒，最多缓存 50 条。缓存 key 是 URL + 请求参数。

3. **Token 刷新去重**：用 `refreshPromise` 变量记录进行中的刷新操作，
   多个 401 响应只触发一次 token 刷新。

### Suggested Action
将这个 `apiClient.ts` 作为模板，在新项目中复用。

### Metadata
- Source: frontend-optimization
- Related Files: src/lib/apiClient.ts
- Tags: api, performance, cache, deduplication, template

---

## [LRN-20260615-013] pitfall

**Logged**: 2026-06-15T18:20:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend | react

### Summary
列表渲染使用 `key={idx}`（数组索引作为 key），当列表顺序变化时，
React 无法正确识别哪些元素变了，导致状态混乱或性能下降。

### Details
在 `WorldList.tsx`、`CharacterList.tsx`、`TimelineList.tsx` 中，
列表渲染用了 `key={idx}`：

```tsx
// ❌ 错误：用索引作为 key
{items.map((item, idx) => <Component key={idx} ... />)}

// ✅ 正确：用唯一标识作为 key
{items.map(item => <Component key={item.id} ... />)}

// ✅ 如果确实没有唯一标识，用多个字段组合：
{rules.map((rule, idx) => <Component key={`${rule}-${idx}`} ... />)}
{factions.map((f, idx) => <Component key={`${f.name || `faction-${idx}`}`} ... />)}
```

**何时可以用索引作为 key**：
- 列表是静态的（永远不会重新排序或过滤）
- 列表项没有状态（如输入框的内容）
- 你确定列表顺序永远不变

### Suggested Action
用 ESLint 规则 `react/no-array-index-key` 禁止用索引作为 key。

### Metadata
- Source: frontend-optimization
- Related Files: src/components/workspace/WorldList.tsx, CharacterList.tsx, TimelineList.tsx
- Tags: react, list, key, pitfall, common_mistake

---

## [LRN-20260615-014] best_practice

**Logged**: 2026-06-15T18:25:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | css

### Summary
CSS 性能优化：用 `content-visibility: auto` 跳过视口外元素的渲染、
`scrollbar-gutter: stable` 防止滚动条出现时布局偏移、
`@media (prefers-reduced-motion: reduce)` 禁用动画（无障碍）。

### Details
在 `src/app/globals.css` 中添加：

```css
/* 跳过视口外元素的渲染（提升滚动性能） */
.content-section {
  content-visibility: auto;
  contain-intrinsic-size: 0 500px; /* 预估高度，避免布局偏移 */
}

/* 防止滚动条出现时布局偏移 */
html {
  scrollbar-gutter: stable;
}

/* 无障碍：允许用户禁用动画 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Suggested Action
在所有长列表页面中使用 `content-visibility: auto`。

### Metadata
- Source: frontend-optimization
- Related Files: src/app/globals.css
- Tags: css, performance, accessibility, best_practice

---

## [LRN-20260615-015] insight

**Logged**: 2026-06-15T18:30:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend | nextjs

### Summary
Next.js 动态导入（Dynamic Import）可以显著减少首屏 JavaScript 体积，
特别是对于大型第三方库或稀有使用的组件。

### Details
在 `src/app/workspace/[projectId]/page.tsx` 中，将重型组件改为动态导入：

```tsx
import dynamic from 'next/dynamic';

const LeftPanel = dynamic(() => import('@/components/workspace/LeftPanel'), {
  loading: () => <div className={styles.panelPlaceholder}>加载中...</div>,
  ssr: false,  // 如果组件依赖浏览器 API（如 window），禁用 SSR
});

const Editor = dynamic(() => import('@/components/workspace/Editor'), {
  loading: () => <div className={styles.editorPlaceholder}>加载中...</div>,
});
```

**注意**：
- 动态导入会增加网络请求数（每个 `dynamic()` 一个单独的文件）
- 不要对小型组件（< 5KB）使用动态导入
- 用 `loading` 属性提供加载状态，避免布局偏移

### Suggested Action
审计所有页面，对首屏不需要的组件使用动态导入。

### Metadata
- Source: frontend-optimization
- Related Files: src/app/workspace/[projectId]/page.tsx
- Tags: nextjs, dynamic-import, performance, code-splitting

---


