# API 响应安全实施指南

**版本**: 1.0.0  
**日期**: 2026-06-16  
**状态**: ✅ 已实施

---

## 目录

1. [概述](#概述)
2. [三层防护体系](#三层防护体系)
3. [第一层：安全工具库](#第一层安全工具库)
4. [第二层：Zod 验证](#第二层zod-验证)
5. [第三层：ESLint 规则](#第三层eslint-规则)
6. [最佳实践](#最佳实践)
7. [反模式（禁止）](#反模式禁止)
8. [迁移指南](#迁移指南)

---

## 概述

### 问题

前端代码中直接处理 API 响应时，如果响应为 `undefined` 或 `null`，会导致运行时错误：

```
Cannot read properties of undefined (reading 'filter')
Cannot destructure property 'access_token' of '(intermediate value).data'
```

### 解决方案

实施**三层防护体系**，从代码、验证、规则三个层面防止不安全操作。

---

## 三层防护体系

| 层级 | 手段 | 作用 | 失败成本 |
|------|------|------|----------|
| **第一层（代码层）** | `apiSafety.ts` 工具函数 | 确保所有 API 响应都有安全的默认值 | 低（开发时发现） |
| **第二层（验证层）** | Zod Schema 验证 | 验证 API 响应格式是否符合预期 | 中（测试时发现） |
| **第三层（规则层）** | ESLint 规则 | 阻止不安全的代码提交到代码库 | 高（提交前发现） |

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│  开发者写代码                                               │
│  - 使用 apiSafety.ts 工具函数                              │
│  - 添加 Zod 验证（可选）                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Git commit                                              │
│  - ESLint 检查（阻止不安全代码）                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  CI/CD 流水线                                             │
│  - TypeScript 类型检查                                    │
│  - 单元测试                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  生产环境                                                  │
│  - 运行时错误监控（Sentry）                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 第一层：安全工具库

### 文件位置

`src/lib/apiSafety.ts`

### 提供的工具函数

#### 1. `safeArray()` - 安全获取数组

```typescript
// ✅ 安全：即使 res.data 是 undefined，也返回 []
const projects = safeArray(res.data);

// ✅ 可以指定默认值
const projects = safeArray(res.data, []);

// ❌ 不安全（可能崩溃）
const projects = res.data;
const filtered = projects.filter(p => p.title); // 如果 projects 是 undefined，崩溃！
```

#### 2. `safeObject()` - 安全获取对象

```typescript
// ✅ 安全：即使 res.data 是 undefined，也返回 null
const project = safeObject<Project>(res.data);

// ✅ 可以指定默认值
const project = safeObject<Project>(res.data, defaultProject);

// ❌ 不安全（可能崩溃）
const project = res.data;
console.log(project.title); // 如果 project 是 undefined，崩溃！
```

#### 3. `safeResponseData()` - 安全提取 API 响应数据

```typescript
// ✅ 安全：自动处理 { code, data, message } 格式
const projects = safeResponseData<Project[]>(res, []);

// ✅ 可以指定默认值
const projects = safeResponseData<Project[]>(res, defaultProjects);
```

#### 4. `safePaginatedData()` - 安全提取分页数据

```typescript
// ✅ 安全：自动提取 { items, total }
const { items, total } = safePaginatedData<Project>(res);

// 返回值：{ items: Project[], total: number }
```

#### 5. `safeAsync()` - 安全处理 Promise

```typescript
// ✅ 安全：永远不会 throw，而是返回 [data, error]
const [projects, error] = await safeAsync(projectApi.list(), []);

if (error) {
  console.error("加载项目失败:", error);
  // 使用默认值或显示错误提示
} else {
  // 使用 projects
}
```

#### 6. `useSafeFetch()` - React Hook 安全获取数据

```typescript
// ✅ 安全：自动处理 loading/error/data 状态
const { data: projects, loading, error } = useSafeFetch(
  () => projectApi.list(),
  []
);

// 在组件中
if (loading) return <Spinner />;
if (error) return <ErrorMessage error={error} />;
return <ProjectList projects={projects} />;
```

### 使用示例

#### 在页面文件中

```typescript
// app/projects/page.tsx
import { safeArray, safeAsync } from "@/lib/apiSafety";

export default function ProjectsPage() {
  const { projects, isLoading } = useProjects();
  
  // ✅ 安全：即使 projects 是 undefined，也不会崩溃
  const safeProjects = safeArray(projects);
  const filteredProjects = safeProjects.filter(
    (p) => p.title.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  return (
    <div>
      {filteredProjects.map(p => (
        <ProjectCard key={p.id} project={p} />
      ))}
    </div>
  );
}
```

#### 在 Context 文件中

```typescript
// contexts/ProjectContext.tsx
import { safeArray } from "@/lib/apiSafety";

const loadProjects = useCallback(async () => {
  try {
    const res = await projectApi.list();
    // ✅ 安全：确保 projects 始终是数组
    setProjects(safeArray(res.data));
  } catch (error) {
    console.error("加载项目失败:", error);
    // ✅ 安全：API 失败时保持 projects 为 []
    setProjects([]);
  }
}, []);
```

---

## 第二层：Zod 验证

### 文件位置

`src/lib/apiValidation.ts`

### 提供的 Schema

| Schema | 用途 | 示例 |
|--------|------|------|
| `baseResponseSchema` | 基础 API 响应格式 | `{ code, message, data }` |
| `paginatedResponseSchema` | 分页响应格式 | `{ items: [], total: number }` |
| `arrayResponseSchema` | 数组响应格式 | `data: [...]` |
| `objectResponseSchema` | 对象响应格式 | `data: {...}` |
| `projectSchema` | Project 数据类型验证 | - |
| `chapterSchema` | Chapter 数据类型验证 | - |

### 使用示例

#### 验证 API 响应

```typescript
import { validateResponse, arrayResponseSchema } from "@/lib/apiValidation";

const loadProjects = async () => {
  const res = await projectApi.list();
  
  // ✅ 验证响应格式
  const result = validateResponse(
    arrayResponseSchema(projectSchema),
    res
  );
  
  if (result.success) {
    // result.data 是类型安全的 Project[]
    setProjects(result.data);
  } else {
    console.error("响应格式错误:", result.error);
    setProjects([]);
  }
};
```

#### 自定义 Schema

```typescript
import { z } from "zod";

// 定义自定义 Schema
const userSettingsSchema = z.object({
  theme: z.enum(["light", "dark"]),
  auto_save_interval: z.number().min(0),
  nickname: z.string().optional(),
});

// 使用自定义 Schema 验证
const res = await settingsApi.get();
const result = validateResponse(
  objectResponseSchema(userSettingsSchema),
  res
);

if (result.success) {
  setSettings(result.data);
}
```

---

## 第三层：ESLint 规则

### 文件位置

`.eslintrc.json`

### 配置的规则

#### 1. 禁止直接访问可能 `undefined` 的属性

```json
{
  "rules": {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "MemberExpression[object.name='res'][property.name='data']",
        "message": "不要直接访问 res.data，使用 safeResponseData(res, defaultValue)"
      }
    ]
  }
}
```

**效果**：
```typescript
// ❌ ESLint 报错
const projects = res.data;

// ✅ ESLint 通过
const projects = safeResponseData(res, []);
```

#### 2. 禁止不安全的数组操作

```json
{
  "rules": {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "CallExpression[callee.property.name='filter'][arguments.length=1]",
        "message": "确保对象在调用 .filter() 前是数组，使用 safeArray(obj)"
      }
    ]
  }
}
```

**效果**：
```typescript
// ❌ ESLint 报错（如果 projects 可能是 undefined）
projects.filter(p => p.title);

// ✅ ESLint 通过
safeArray(projects).filter(p => p.title);
```

### 运行 ESLint

```bash
# 检查所有文件
npx eslint src/

# 自动修复可修复的问题
npx eslint src/ --fix

# 检查特定文件
npx eslint src/contexts/ProjectContext.tsx
```

---

## 最佳实践

### ✅ 推荐做法

#### 1. 在 Context 文件中

```typescript
import { safeArray, safeObject } from "@/lib/apiSafety";

const loadData = async () => {
  try {
    const res = await api.get();
    // ✅ 使用 safeArray / safeObject
    setData(safeArray(res.data));
  } catch (error) {
    console.error("加载失败:", error);
    // ✅ API 失败时也保持安全默认值
    setData([]);
  }
};
```

#### 2. 在页面文件中

```typescript
import { safeArray } from "@/lib/apiSafety";

const MyPage = () => {
  const { data } = useData();
  
  // ✅ 使用 safeArray 作为"安全带"
  const safeData = safeArray(data);
  
  return (
    <div>
      {safeData.map(item => (
        <ItemCard key={item.id} item={item} />
      ))}
    </div>
  );
};
```

#### 3. 处理分页数据

```typescript
import { safePaginatedData } from "@/lib/apiSafety";

const loadPaginatedData = async (page: number) => {
  const res = await api.list({ page, pageSize: 20 });
  
  // ✅ 安全提取分页数据
  const { items, total } = safePaginatedData<Item>(res);
  
  setItems(items);
  setTotal(total);
};
```

#### 4. 使用 safeAsync 处理并发请求

```typescript
import { safeAsync } from "@/lib/apiSafety";

const loadDashboardData = async () => {
  const [
    [projects, projectsError],
    [stats, statsError],
    [alerts, alertsError],
  ] = await Promise.all([
    safeAsync(projectApi.list(), []),
    safeAsync(projectApi.getStats(), null),
    safeAsync(healthApi.getAlerts(), []),
  ]);
  
  // ✅ 即使某个请求失败，其他请求的结果仍然可用
  if (!projectsError) setProjects(projects);
  if (!statsError) setStats(stats);
  if (!alertsError) setAlerts(alerts);
};
```

---

## 反模式（禁止）

### ❌ 反模式 1：直接访问 `res.data`

```typescript
// ❌ 禁止
const res = await api.get();
const data = res.data; // 如果 res.data 是 undefined，后续操作会崩溃

// ✅ 正确
const res = await api.get();
const data = safeResponseData(res, defaultValue);
```

### ❌ 反模式 2：不检查就调用数组方法

```typescript
// ❌ 禁止
const projects = res.data;
const filtered = projects.filter(p => p.title); // 如果 projects 是 undefined，崩溃！

// ✅ 正确
const projects = safeArray(res.data);
const filtered = projects.filter(p => p.title); // 永远不会崩溃
```

### ❌ 反模式 3：在 Context 中直接设置 `undefined`

```typescript
// ❌ 禁止
const loadData = async () => {
  const res = await api.get();
  setData(res.data); // 如果 res.data 是 undefined，状态变成 undefined
};

// ✅ 正确
const loadData = async () => {
  try {
    const res = await api.get();
    setData(safeArray(res.data));
  } catch (error) {
    setData([]); // API 失败时也保持安全默认值
  }
};
```

### ❌ 反模式 4：直接导入 `apiClient`

```typescript
// ❌ 禁止
import { apiClient } from "@/lib/apiClient";
const res = await apiClient.post("/auth/login", ...);

// ✅ 正确
import { authApi } from "@/lib/api";
const res = await authApi.login(email, password);
```

---

## 迁移指南

### 步骤 1：安装依赖

```bash
cd moling-web
npm install zod --save
```

### 步骤 2：添加安全工具库

将 `src/lib/apiSafety.ts` 和 `src/lib/apiValidation.ts` 复制到项目中。

### 步骤 3：更新 ESLint 配置

将 `.eslintrc.json` 中的 `rules` 部分更新为包含安全规则。

### 步骤 4：修复现有代码

#### 4.1 修复 Context 文件

```typescript
// contexts/MyContext.tsx

// 修改前
const loadData = async () => {
  const res = await api.get();
  setData(res.data);
};

// 修改后
import { safeArray, safeObject } from "@/lib/apiSafety";

const loadData = async () => {
  try {
    const res = await api.get();
    setData(safeArray(res.data));
  } catch (error) {
    console.error("加载失败:", error);
    setData([]);
  }
};
```

#### 4.2 修复页面文件

```typescript
// app/my-page/page.tsx

// 修改前
const { data } = useMyData();
const filtered = data.filter(...); // 可能崩溃

// 修改后
import { safeArray } from "@/lib/apiSafety";

const { data } = useMyData();
const safeData = safeArray(data);
const filtered = safeData.filter(...); // 永远不会崩溃
```

### 步骤 5：运行 ESLint 检查

```bash
npx eslint src/ --fix
```

### 步骤 6：测试验证

```bash
# TypeScript 类型检查
npx tsc --noEmit

# 构建生产版本
npm run build

# 运行单元测试
npm run test
```

---

## 常见问题

### Q1：`safeArray()` 会影响性能吗？

**A**：几乎不会。`safeArray()` 只是做了一个 `Array.isArray()` 检查，成本极低（< 1μs）。

### Q2：我应该在所有地方都使用 `safeArray()` 吗？

**A**：建议是的。即使你觉得"这里不可能为 undefined"，使用 `safeArray()` 作为"安全带"也是好习惯。

### Q3：Zod 验证会影响性能吗？

**A**：会一点点（每个验证 ~0.1ms）。建议只在关键 API（如登录、支付）使用 Zod 验证。

### Q4：ESLint 规则太严格了，能放宽吗？

**A**：可以。修改 `.eslintrc.json` 中的规则等级：
- `"error"`：禁止提交（推荐）
- `"warn"`：警告但允许提交
- `"off"`：关闭规则

---

## 参考资料

- [API 响应安全审计报告](./api-safety-audit-report-complete.md)
- [Zod 官方文档](https://zod.dev/)
- [ESLint 官方文档](https://eslint.org/docs/latest/)
- [TypeScript 严格模式](https://www.typescriptlang.org/tsconfig#strict)

---

**维护者**: 墨灵开发团队  
**更新日期**: 2026-06-16
