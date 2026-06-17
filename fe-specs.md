# 前端 Phase 4 & 健康监控 — 生产级规格

> 2026-06-17 | 基于现有架构，连接真实 API 替换 Mock 数据

---

## 架构总览

```
Workspace（工作台）
├── HealthAlertBanner（已有）→ 连接到真实 API
├── Phase 4 Task Panel（新建）→ 任务状态机可视化
└── Vault Tabs（已有→改造）→ 替换 Mock 为真实 API
    ├── CharacterLibrary（已有→连接API）
    ├── TimelineLibrary（已有→连接API）
    ├── ForeshadowingLibrary（已有→连接API）
    ├── WorldviewLibrary（已有→连接API）
    └── CardManager（已有→连接API + 退役状态）

独立页面
├── /workspace/[projectId]/health（新建）→ 完整健康监控仪表盘
└── /workspace/[projectId]/phase4/tasks（新建）→ 任务历史

后端 API
├── GET /projects/{pid}/health              — 健康告警
├── POST /projects/{pid}/health/refresh     — 刷新健康
├── GET /phase4/projects/{pid}/tasks        — 任务列表
├── GET /phase4/tasks/{tid}                 — 任务详情
├── GET /projects/{pid}/vault/{type}        — 四库 CRUD
├── POST /projects/{pid}/vault/{type}       — 四库 CRUD
└── GET /projects/{pid}/vault/summary       — 四库统计
```

---

## Agent 1: 健康监控仪表盘（`health-dashboard-pro`）

### 目标
在 workspace 中实现完整的子情节健康监控仪表盘，连接真实 API，展示 R1/R2/R3 告警。

### 现有资源
- `components/health/SystemHealthBanner.tsx` — 系统级健康横幅
- `components/workspace/HealthAlertBanner.tsx` — 项目级健康告警横幅
- `contexts/SystemHealthContext.tsx` — 系统健康轮询
- `lib/api.ts` — 项目健康 API
- `lib/types.ts` — HealthAlert, HealthCheckResp 类型

### 新文件

**1. `components/health/HealthDashboard.tsx`** — 完整仪表盘组件
```
- 告警概览卡片：R1(黄色) / R2(橙色) / R3(红色) 计数
- 告警列表：按严重程度排序，可折叠/展开详情
- 每个告警显示：规则、子情节名称、当前章节、告警原因、建议操作
- 防疲劳标记：展示同一告警是否被抑制（灰色 + "3章内重复" 标注）
- 刷新按钮：手动触发健康检查
- 空状态：无告警时显示绿色勾 "所有子情节健康"
- 加载状态：Skeleton 骨架屏
- 错误状态：EmptyState + 重试按钮
```

**2. `app/workspace/[projectId]/health/page.tsx`** — 健康仪表盘独立页面
```
- 左侧：告警概览 + 图表（R1/R2/R3 分布饼图或柱状图）
- 右侧：告警详情列表
- 顶部：最后检查时间 + 刷新按钮
- 使用 WorkspaceProvider 的项目 ID
```

**3. `lib/api.ts` 新增方法**
```typescript
// 已有: getProjectHealth, refreshProjectHealth
// 新增:
getProjectHealthAlerts: (projectId) => GET /projects/{pid}/health
refreshProjectHealth: (projectId) => POST /projects/{pid}/health/refresh
```

### 修改文件

**`components/workspace/HealthAlertBanner.tsx`** — 增强
```
- 连接真实 API（当前可能是 mock）
- 添加告警数量徽标
- 点击跳转到健康仪表盘
- 支持多告警轮播
```

### 测试要求（≥8）

| # | 测试 |
|---|------|
| 1 | 健康仪表盘渲染告警列表 |
| 2 | R1/R2/R3 颜色正确 |
| 3 | 空状态显示 |
| 4 | 刷新按钮触发 API 调用 |
| 5 | 防疲劳告警显示灰色标记 |
| 6 | 加载状态骨架屏 |
| 7 | 错误状态+重试 |
| 8 | 告警计数正确 |

---

## Agent 2: Phase 4 Task 状态面板（`phase4-task-pro`）

### 目标
在 workspace 中实现 Phase 4 任务状态面板，展示任务状态机流转（QUEUED→LOCKING→EXTRACTING→VERIFYING→MERGING→COMMITTING→DONE）。

### 现有资源
- `lib/api.ts` — Phase 4 任务 API（getPhase4Task, getProjectPhase4Tasks）
- `lib/types.ts` — Phase4Task 类型
- 后端 `Phase4Task` 模型包含 state/retry_count/retry_at/last_error/safety_check 字段

### 新文件

**1. `components/phase4/Phase4TaskPanel.tsx`** — 任务状态面板
```
- 当前任务状态：状态机流程图（高亮当前步骤）
- 最近任务列表：按时间倒序
- 每个任务显示：任务ID、状态、开始时间、耗时、重试次数
- 状态颜色映射：
  IDLE=灰色, QUEUED=蓝色, LOCKING=橙色, EXTRACTING=紫色,
  VERIFYING=青色, MERGING=粉色, COMMITTING=黄色,
  DONE=绿色, FAILED=红色, RETRY=橙色(闪烁)
- 失败任务：显示 last_error + 重试按钮
- 空状态：无任务时的提示
- 自动轮询：每 5 秒刷新当前任务状态
```

**2. `app/workspace/[projectId]/phase4/tasks/page.tsx`** — 任务历史页面
```
- 任务历史列表（分页，每页 20 条）
- 状态过滤：全部/进行中/完成/失败
- 时间范围过滤
- 点击任务查看详情
```

### 修改文件

**`lib/api.ts` 新增方法**
```typescript
// 已有: getPhase4Task, getProjectPhase4Tasks
// 新增:
getChapterPhase4Tasks: (chapterId) => GET /phase4/chapters/{cid}/tasks
```

**`lib/types.ts` 新增类型**
```typescript
export interface Phase4TaskStatus {
  id: string;
  projectId: string;
  chapterId: string;
  state: Phase4State;
  nonce: string;
  retryCount: number;
  retryAt?: string;
  lastError?: string;
  safetyCheck?: SafetyCheckResult;
  createdAt: string;
  updatedAt: string;
}

export enum Phase4State {
  IDLE = "idle",
  QUEUED = "queued",
  LOCKING = "locking",
  EXTRACTING = "extracting",
  VERIFYING = "verifying",
  MERGING = "merging",
  COMMITTING = "committing",
  DONE = "done",
  FAILED = "failed",
  RETRY = "retry",
}
```

### 测试要求（≥8）

| # | 测试 |
|---|------|
| 1 | 任务面板渲染状态列表 |
| 2 | 状态颜色映射正确 |
| 3 | 空状态无任务 |
| 4 | 失败任务显示错误信息 |
| 5 | 任务历史分页 |
| 6 | 状态过滤 |
| 7 | 自动轮询间隔 |
| 8 | 状态机流程图高亮当前状态 |

---

## Agent 3: Vault 四库 + 卡牌池 API 集成（`vault-api-pro`）

### 目标
将 `components/phase4/` 中四个库组件从 Mock 数据迁移到真实 API 调用。替换 `app/vaults/[projectId]/page.tsx` 中 80% 的 Mock 数据。

### 现有资源
- `components/phase4/CharacterLibrary.tsx` — 角色库（mock 数据）
- `components/phase4/TimelineLibrary.tsx` — 时间线（mock 数据）
- `components/phase4/ForeshadowingLibrary.tsx` — 伏笔库/承诺（mock 数据）
- `components/phase4/WorldviewLibrary.tsx` — 世界观（mock 数据）
- `components/phase4/CardManager.tsx` — 卡牌管理（已有 CardPool 调用）
- `lib/api.ts` — vaultApi CRUD 方法（已有）
- `lib/types.ts` — Vault* 类型
- 后端 P0-4 新增 `card_retire_service` 卡牌淘汰 API

### 修改文件

**`components/phase4/CharacterLibrary.tsx`**
```
- 替换 mock 数据为 useQuery/getVaultCharacters
- 保持现有的 UI 结构不变
- 添加 loading/error/empty state
- 添加分页（如果后端支持）
- 添加搜索/过滤功能
```

**`components/phase4/TimelineLibrary.tsx`**
```
- 替换 mock 数据为 useQuery/getVaultTimeline
- 保持时间线可视化结构
- 添加日期处理
```

**`components/phase4/ForeshadowingLibrary.tsx`**
```
- 替换 mock 数据为 useQuery/getVaultPlotPromises
- 保持伏笔/承诺展示结构
- 添加 status 过滤（active/redeemed/canceled）
```

**`components/phase4/WorldviewLibrary.tsx`**
```
- 替换 mock 数据为 useQuery/getVaultWorld
- 保持世界观展示结构
- 添加 category 过滤（geography/history/system/faction/event）
```

**`components/phase4/CardManager.tsx`**
```
- 后端 P0-4 新增了退役状态 → 前端展示退役标记
- 添加退役卡牌过滤（活跃/已退役/全部）
- 显示退休原因和退役章节
- 添加新鲜期指示器
```

**`app/vaults/[projectId]/page.tsx`**
```
- 替换 80% 的 mock 数据为真实 API 调用
- 复用与 workspace Phase4Tab 相同的 API 调用模式
- 保持 Desktop + Mobile 自适应布局
```

**`lib/api.ts` 和 `lib/types.ts`**
```
- 确保所有 vault API 方法返回正确类型
- 添加卡牌退役相关 API（如果后端有）
```

### 测试要求（≥12）

| # | 测试 |
|---|------|
| 1 | 角色库加载真实 API 数据 |
| 2 | 角色库空状态 |
| 3 | 角色库错误状态+重试 |
| 4 | 时间线加载真实 API 数据 |
| 5 | 承诺库 status 过滤 |
| 6 | 世界观 category 过滤 |
| 7 | 卡牌管理加载真实数据 |
| 8 | 卡牌退役状态显示 |
| 9 | 卡牌新鲜期指示器 |
| 10 | 卡牌过滤（活跃/已退役/全部） |
| 11 | Vault 独立页面 Desktop 布局 |
| 12 | Vault 独立页面 Mobile 布局 |

---

## 质量门禁

```bash
# 构建检查
cd C:\Users\Admin\Desktop\MolingProject\moling-web
npx next build 2>&1 | findstr "error"

# 类型检查
npx tsc --noEmit 2>&1 | findstr "error"

# 已有测试
npx vitest run --reporter=verbose 2>&1
```
