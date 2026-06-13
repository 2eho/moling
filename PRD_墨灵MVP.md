# 墨灵 · MVP 核心闭环 PRD

> 文档版本：v1.0  
> 创建人：许清楚（Alice, Product Manager）  
> 创建日期：2026-06-12  
> 数据来源：后端设计文档 v1.0、前后端接口映射文档、卡牌组合算法 v2.0、UI 机密文档、4 个 MVP 页面 HTML 原型

---

## 1. 产品定位与 MVP 范围

### 一句话定位

**墨灵**是一款 AI 小说创作平台，通过「抽卡获取灵感 → 组合卡片生成章节 → 四库维护故事一致性」的闭环流程，让创作者在 AI 辅助下高效、连贯地完成长篇小说创作。

### MVP 核心闭环

```
用户登录 → 项目列表 → 新建项目 → 工作台创作
                                    ├── 抽卡（获取灵感卡片）
                                    ├── 组合卡片 → AI 生成章节
                                    ├── 确认收纳 / 拒稿（含 Phase 4 异步同步）
                                    └── 侧栏四库查阅（角色/时间线/伏笔/世界观）
```

### MVP 边界

| 范围内（MVP v1.0） | 范围外（第二期） |
|:---|:---|
| Auth（登录/注册/密码重置） | Landing 首页营销页 |
| 项目列表（CRUD + 搜索 + 统计） | 四库独立管理页面 |
| 新建项目（表单 + 模板选择） | 设置页（全局/项目级别） |
| 工作台（核心创作全流程） | 导入功能（拆书引擎） |
| — | 定价/订阅 |
| — | 通知中心 |
| — | 管理后台 |

---

## 2. 用户角色

| 角色 | 描述 | 核心需求 |
|:----|:-----|:---------|
| **小说创作者（核心用户）** | 有长篇小说创作需求的写作者，可能缺乏写作灵感或时间 | 快速生成连贯章节、保持故事一致性、降低创作门槛 |
| **写作爱好者（轻量用户）** | 尝试 AI 写作的新手，探索创作可能性 | 简单直观的创作流程、获得灵感启发 |
| **专业作者** | 已有完整写作经验，使用 AI 辅助提速 | 精细控制创作方向、手动编辑+AI生成混合工作流 |

---

## 3. 用户故事（按页面分模块）

### 3.1 Auth（`/auth`）

| ID | 用户故事 | 优先级 |
|:---|:---------|:------:|
| US-AUTH-01 | As a **新用户**, I want to **注册账号**, so that **我可以开始使用墨灵创作** | P0 |
| US-AUTH-02 | As a **已有账号用户**, I want to **登录**, so that **我可以访问我的项目** | P0 |
| US-AUTH-03 | As a **忘记密码的用户**, I want to **重置密码**, so that **我可以重新访问我的账号** | P0 |
| US-AUTH-04 | As a **活跃用户**, I want to **刷新登录 token**, so that **无需反复登录即可持续使用** | P0 |

### 3.2 项目列表（`/projects`）

| ID | 用户故事 | 优先级 |
|:---|:---------|:------:|
| US-PRJ-01 | As a **用户**, I want to **查看我的所有项目概览**, so that **我可以快速了解创作进度和统计数据** | P0 |
| US-PRJ-02 | As a **用户**, I want to **创建新项目**, so that **我可以开始一部新的小说创作** | P0 |
| US-PRJ-03 | As a **用户**, I want to **搜索和过滤项目**, so that **我可以在众多项目中快速找到目标项目** | P1 |
| US-PRJ-04 | As a **用户**, I want to **删除不再需要的项目**, so that **我可以保持项目列表干净** | P1 |
| US-PRJ-05 | As a **用户**, I want to **查看项目详情**, so that **我可以了解项目的章节数量和字数统计** | P1 |
| US-PRJ-06 | As a **用户**, I want to **编辑项目基本信息**, so that **我可以修正标题或类型** | P1 |

### 3.3 新建项目（`/projects/new`）

| ID | 用户故事 | 优先级 |
|:---|:---------|:------:|
| US-NEW-01 | As a **新用户**, I want to **填写项目基本信息（标题/作者/类型/世界观/角色）**, so that **AI 能基于设定生成连贯内容** | P0 |
| US-NEW-02 | As a **用户**, I want to **选择创作模式（从零创作/从模板创作）**, so that **我可以按自己的偏好开始创作** | P0 |
| US-NEW-03 | As a **用户**, I want to **保存项目草稿**, so that **我可以在后续继续完善设定** | P1 |
| US-NEW-04 | As a **用户**, I want to **获取创作建议（世界观/角色/故事钩子）**, so that **我可以获得灵感启发** | P1 |
| US-NEW-05 | As a **用户**, I want to **选择模板快速开始**, so that **我不需要从零填写所有设定** | P1 |

### 3.4 工作台（`/workspace/:projectId`）— 核心创作

| ID | 用户故事 | 优先级 |
|:---|:---------|:------:|
| US-WS-01 | As a **创作者**, I want to **在编辑器中撰写/编辑章节正文**, so that **我可以自由控制内容** | P0 |
| US-WS-02 | As a **创作者**, I want to **点击"抽卡"获取灵感卡片**, so that **我可以获得 AI 建议的创作方向** | P0 |
| US-WS-03 | As a **创作者**, I want to **选择卡片并调整权重后生成章节**, so that **AI 按我期望的方向创作内容** | P0 |
| US-WS-04 | As a **创作者**, I want to **查看生成进度**, so that **我知道系统正在工作** | P0 |
| US-WS-05 | As a **创作者**, I want to **确认收纳满意的生成结果**, so that **内容正式保存并同步到四库** | P0 |
| US-WS-06 | As a **创作者**, I want to **拒稿并重新生成**, so that **我可以获得更满意的内容** | P0 |
| US-WS-07 | As a **创作者**, I want to **查看侧栏四库（角色/时间线/伏笔/世界观）**, so that **我可以随时查阅故事设定一致性** | P0 |
| US-WS-08 | As a **创作者**, I want to **查看健康告警**, so that **我可以及时发现故事设定中的问题** | P1 |
| US-WS-09 | As a **创作者**, I want to **使用工具栏 AI 指令输入**, so that **我可以快速让 AI 处理特定任务** | P1 |
| US-WS-10 | As a **创作者**, I want to **切换到不同的章节**, so that **我可以在不同章节间编辑** | P0 |
| US-WS-11 | As a **创作者**, I want to **保存章节草稿**, so that **编辑内容不会丢失** | P0 |
| US-WS-12 | As a **创作者**, I want to **重抽不满意的卡片**, so that **我可以获得更符合预期的创作灵感** | P0 |

---

## 4. 需求池（P0 / P1 / P2）

### P0 — Must Have（MVP 必须完成）

| 编号 | 模块 | 需求描述 | 关联 API（接口映射文档） |
|:----|:-----|:---------|:----------------------|
| R-001 | Auth | 邮箱+密码注册，含输入校验和防重复注册 | `POST /api/v1/auth/register` |
| R-002 | Auth | 邮箱+密码登录，返回 JWT（access + refresh） | `POST /api/v1/auth/login` |
| R-003 | Auth | JWT Token 自动刷新机制（401 → refresh → retry） | `POST /api/v1/auth/refresh` |
| R-004 | Auth | 密码重置请求（邮箱）和设置新密码 | `POST /api/v1/auth/password-reset-request`, `POST /api/v1/auth/password-reset` |
| R-005 | Auth | 路由级认证守卫（未登录跳转 `/auth`） | `GET /api/v1/auth/me` |
| R-006 | 项目列表 | 加载用户项目列表（含标题/类型/字数/状态） | `GET /api/v1/projects` |
| R-007 | 项目列表 | 显示项目统计概览（项目数/总字数/今日字数） | `GET /api/v1/projects/stats` |
| R-008 | 项目列表 | 点击项目卡片进入工作台，传递 projectId | — |
| R-009 | 新建项目 | 表单填写：标题、作者、类型、标签、简介、世界观、主角、配角、目标字数、更新频率、创作风格 | 见 3.1 字段映射 |
| R-010 | 新建项目 | 表单提交流程：校验 → API → 跳转工作台 | `POST /api/v1/projects` |
| R-011 | 新建项目 | 从零创作 / 从模板创作两种模式选择 | — |
| R-012 | 新建项目 | 模板列表加载 | `GET /api/v1/templates` |
| R-013 | 工作台 | 加载当前工作台章节数据和元信息 | `GET /api/v1/projects/:pid/chapters/current` |
| R-014 | 工作台 | 章节内容编辑（富文本/纯文本编辑器），支持保存草稿 | `PUT /api/v1/projects/:pid/chapters/:id` |
| R-015 | 工作台 | 章节切换（下拉选择器，加载对应章节内容） | `GET /api/v1/projects/:pid/chapters` + `GET /api/v1/projects/:pid/chapters/:id` |
| R-016 | 工作台 | 抽卡流程：打开抽卡模态框 → 展示 3 张候选卡 → 执行抽卡 | `GET /api/v1/projects/:pid/cards/pool?count=3` → `POST /api/v1/projects/:pid/cards/draw` |
| R-017 | 工作台 | 卡牌选择交互（单选/多选）、方向模式切换（不选/单卡/双卡/全选/Hybrid） | — |
| R-018 | 工作台 | 权重滑块（0-100）调整 | — |
| R-019 | 工作台 | 触发生成 → 展示进度动画（模糊化为 3 阶段：预处理中→生成中→校验中） | `POST /api/v1/projects/:pid/chapters/:id/generate` → 轮询 `GET /api/v1/generate/:task_id/status` |
| R-020 | 工作台 | 生成结果展示在编辑区 | — |
| R-021 | 工作台 | 确认收纳（触发 Phase 4 异步流程，按钮显示收纳状态） | `POST /api/v1/projects/:pid/chapters/:id/confirm` → 轮询 `GET /api/v1/generate/:task_id/status` |
| R-022 | 工作台 | 拒稿（点击拒稿 → 返回抽卡状态 / 显示修改建议） | `POST /api/v1/projects/:pid/chapters/:id/revise` |
| R-023 | 工作台 | 单卡重抽 / 全部重抽 | `POST /api/v1/projects/:pid/chapters/:id/redraw` |
| R-024 | 工作台 | 侧栏四库展示：人物库 Tab、时间线库 Tab、剧情承诺库 Tab、世界观库 Tab | `GET /api/v1/projects/:pid/vault/characters`, `GET /api/v1/projects/:pid/vault/timeline`, `GET /api/v1/projects/:pid/vault/plot-promises`, `GET /api/v1/projects/:pid/vault/world` |
| R-025 | 工作台 | 侧栏折叠/展开 | — |
| R-026 | 工作台 | 健康告警横幅展示 | `GET /api/v1/projects/:pid/health` |
| R-027 | UI 安全 | 生成进度模糊化为 3 阶段（不展示具体步骤名） | — |
| R-028 | UI 安全 | 不在 UI 展示动态层面板（移除；保留数据层+隐藏调试模式） | — |
| R-029 | UI 安全 | 模态框摘要使用「当前上下文已就绪」文案 | — |
| R-030 | UI 安全 | 无"Phase 4"、"四库收纳"等工程术语出现在用户界面 | — |

### P1 — Should Have（MVP 推荐包含）

| 编号 | 模块 | 需求描述 | 关联 API |
|:----|:-----|:---------|:---------|
| R-031 | 项目列表 | 搜索项目（前端过滤 / API 搜索） | `GET /api/v1/projects?q=关键字` |
| R-032 | 项目列表 | 删除项目（含确认弹窗） | `DELETE /api/v1/projects/:id` |
| R-033 | 项目列表 | 查看项目详情弹窗 | `GET /api/v1/projects/:id` |
| R-034 | 项目列表 | 编辑项目基本信息 | `PUT /api/v1/projects/:id` |
| R-035 | 新建项目 | 保存草稿功能 | `POST /api/v1/projects?draft=true` / `PUT /api/v1/projects/:id/draft` |
| R-036 | 新建项目 | 创作建议（标题/类型输入时实时推荐世界观/角色/钩子） | `GET /api/v1/projects/suggestions` |
| R-037 | 工作台 | 健康告警"立即检查"刷新 | `POST /api/v1/projects/:pid/health/refresh` |
| R-038 | 工作台 | 工具栏 AI 指令（输入框 + 回车发送） | `POST /api/v1/projects/:pid/chapters/:id/agent` |
| R-039 | 工作台 | AI 建议右侧面板展开/收起 | `GET /api/v1/projects/:pid/chapters/:id/suggestions` |
| R-040 | 工作台 | 重抽用尽后 AI 推荐卡片 | `POST /redraw` 响应中附带的 `recommended` |
| R-041 | 工作台 | 生成中的取消按钮 | `POST /api/v1/generate/:task_id/cancel` |
| R-042 | 工作台 | 重新生成（生成完成后再次触发） | `POST /api/v1/projects/:pid/chapters/:id/generate`（同参数） |
| R-043 | 通用 | 全局 404 页面 | — |
| R-044 | 通用 | 空状态展示（无项目/无章节/无角色等） | — |
| R-045 | 通用 | 加载状态 skeleton / spinner | — |

### P2 — Nice to Have

| 编号 | 模块 | 需求描述 |
|:----|:-----|:---------|
| R-046 | 工作台 | 自动保存草稿（定时/失焦时） |
| R-047 | Auth | 记住密码/自动登录 |
| R-048 | 工作台 | 章节排序调整（拖拽） |
| R-049 | 项目列表 | 项目卡片封面自定义 |
| R-050 | 工作台 | 编辑器字号/主题切换（跟随全局设置） |

---

## 5. UI 设计稿

> 以下 4 个 HTML 原型文件位于 `C:\Users\Admin\Desktop\新建文件夹 (2)\`，每个页面均有**桌面端（Desktop Shell）**和**移动端（Mobile Shell）**两套布局，通过 `769px` 断点切换。

### 5.1 Auth（`010_d04ccd3d_moling-auth.html`）

**设计风格**：深色主题（`#0d0f1a` 背景），居中对齐表单卡片，品牌色靛蓝（`#6366f1`）。

**关键交互点**：
| 元素 | 描述 |
|:----|:-----|
| `.auth-card` | 居中表单卡片，max-width 420px |
| `#formLogin` | 登录表单：邮箱 + 密码 + 登录按钮 |
| `#formRegister` | 注册表单：昵称 + 邮箱 + 密码 + 确认密码 + 注册按钮 |
| `#formReset` / `#formSetPassword` | 密码重置流程：输入邮箱 → 发送重置链接 → 设置新密码 |
| Tab 切换 | 登录/注册/重置 三个 tab 切换（前端 JS 控制，无页面跳转） |
| 登录成功 | 保存 token 到 localStorage → 跳转 `/projects` |
| 注册成功 | 自动切回登录 tab 并填入邮箱 |

### 5.2 项目列表（`004_f05ef162_moling-projects.html`）

**设计风格**：顶部导航 + 网格/列表式项目卡片。

**关键交互点**：
| 元素 | 描述 |
|:----|:-----|
| `.stat-card` | 3 个统计数字卡片（项目数/总字数/今日字数） |
| `.project-card` | 项目卡片网格，桌面 6 张/行，移动 4 张/行 |
| `#dSearchInput` | 搜索输入框（oninput 前端过滤） |
| 新建项目按钮 | 跳转到 `/projects/new`（桌面右上角 / 移动右下角 FAB） |
| 项目卡片点击 | 跳转到 `/workspace/:id` |
| 详情弹窗 | 点击"查看详情"打开弹窗，显示项目完整信息 |
| 删除 | 详情弹窗中"删除"按钮 → 确认弹窗 → DELETE API |

### 5.3 新建项目（`003_1e4d402c_moling-new-project.html`）

**设计风格**：步骤式折叠表单（Step Card），左侧表单 + 右侧空区域（预留展示区）。

**关键交互点**：
| 元素 | 描述 |
|:----|:-----|
| `.d-step-card` | 折叠式步骤卡片（基本信息 → 世界观设定 → 角色设定 → 创作偏好） |
| `.d-creation-mode-card` | 创作模式选择（从零创作 / 从模板创作） |
| `.d-template-item` | 模板卡片网格（6 个模板） |
| `#dSynopsis` | 故事简介文本域 |
| `#dWorldview` | 世界观设定文本域 |
| `#dProtagonist` / `.d-form-input`(supporting) | 主角 / 配角设定 |
| `#dWordCountGroup` | 目标字数选择 |
| `#dFrequencyGroup` | 更新频率选择 |
| `#dStyleGroup` | 创作风格选择 |
| 保存草稿按钮 | 保存当前表单为草稿 |
| "开始创作"按钮 | 提交 → API → 跳转工作台 |

### 5.4 工作台（`008_8e2010d7_moling-workspace.html`）— 最复杂页面

**设计风格**：三栏布局（左侧四库面板 → 中间编辑器 → 右侧 AI 建议面板）。

**全局布局**：
```
┌─────────────────────────────────────────────────────────┐
│ Header: Logo | 章节选择器 | 保存状态 | 头像/通知        │
├──────┬──────────────────────────────────┬───────────────┤
│      │                                  │               │
│ Left │     Editor (中间编辑区)           │ Right Panel   │
│ Panel│  ┌─────────────────────────┐     │ (AI 建议)     │
│ (四库)│  │ 编辑区 (.editor-area)   │     │               │
│      │  │                         │     │               │
│ Tab  │  └─────────────────────────┘     │               │
│ 切换 │                                  │               │
│      │  ┌─────────────────────────┐     │               │
│      │  │ 底部: 健康告警横幅       │     │               │
│      │  │       生成进度条(模态)    │     │               │
│      │  └─────────────────────────┘     │               │
├──────┴──────────────────────────────────┴───────────────┤
│ 底部工具栏: | 抽卡 | 生成 | 确认收纳 | 拒稿 | AI指令    │
└─────────────────────────────────────────────────────────┘
```

**关键交互点**：
| 元素 | 描述 |
|:----|:-----|
| `.left-panel` | 左侧四库侧栏（`width: 280px`），4 个 Tab：人物/时间线/承诺/世界观 |
| `.panel-tab-btn` | Tab 按钮，点击切换显示对应库内容 |
| `.panel-collapse-btn` | 侧栏折叠按钮（折叠后宽 `56px`） |
| `.editor-area` | 章节编辑区（富文本/纯文本），支持直接输入 |
| `.header-chapter` | 章节选择器（下拉），选择后加载对应章节 |
| 抽卡按钮 → `#cardModal` | 抽卡模态框：展示 3 张灵感卡片（稀有度 ⚪🔵🟣🟠），含重抽按钮 |
| `.mode-btn` | 编织模式选择（不选/单卡/双卡/全选/Hybrid） |
| `.weight-slider` | 3 个权重滑块（0-100），调整各卡片影响程度 |
| 生成按钮 | 触发 AI 生成 → 显示进度动画（3 阶段） |
| `#confirmBtn` | 确认收纳按钮 → 触发 Phase 4 异步 → 状态反馈 |
| `#rejectBtn` | 拒稿按钮 → 返回抽卡状态或显示修改建议 |
| `.health-alert-bar` | 健康告警横幅（顶部/底部），含"立即检查"按钮 |
| `#toolbarInput` | AI 指令输入框（底部工具栏） |

**UI 安全约束**（参见 `001_e24ff30d_UI机密文档.md`）：
- 生成进度必须模糊化为 3 阶段：**预处理中… → 生成中… → 校验中…**（不能展示 12 步具体步骤名）
- **不得**展示动态层面板
- 模态框动态层摘要改为：**「当前上下文已就绪」**
- 冲突警告文案改为 **「组合偏好提示」**
- 收纳进度提示使用 **「草稿已确认，正在同步世界设定…」**，不使用"Phase 4"、"四库收纳"等术语
- 重抽次数使用友好文案：**「今日可重抽 {2}/{3} 次」**

---

## 6. 非功能性需求

### 6.1 性能

| 需求 | 指标 |
|:----|:-----|
| 页面加载 | 首屏渲染 < 2s（Next.js SSR/SSG） |
| API 响应 | 常规 CRUD < 200ms（P95），生文请求 < 30s |
| 章节生成 | 单章生成（500-5000字）< 15s（含 LLM 调用时间） |
| 并发支持 | 支持 100 并发用户（初期） |
| 数据库查询 | 列表分页查询 < 100ms（加索引），慢查询日志记录 > 500ms |

### 6.2 安全

| 需求 | 说明 |
|:----|:-----|
| JWT 认证 | Access Token 15min 过期，Refresh Token 7 天过期 |
| 密码策略 | 最少 8 位，含字母+数字，bcrypt 哈希存储 |
| 登录限流 | 同一 IP 5 分钟内错误超过 5 次 → 429 |
| API 访问 | 所有 `/api/v1/projects/*` 需 `Authorization: Bearer` |
| Token 刷新 | 401 自动调用 `/api/v1/auth/refresh`，失败则跳转登录 |
| UI 信息保护 | 参考 UI 机密文档隐藏算法架构细节（进度步骤/动态层/Phase 4术语） |

### 6.3 兼容性

| 需求 | 说明 |
|:----|:-----|
| 浏览器支持 | Chrome 90+, Firefox 90+, Safari 15+, Edge 90+ |
| 响应式设计 | 769px 断点切换桌面/移动布局（双壳设计） |
| 移动端适配 | 支持 safe area、触摸交互、底部导航栏 |

### 6.4 可用性

| 需求 | 说明 |
|:----|:-----|
| 加载状态 | 所有数据加载展示 skeleton 或 spinner |
| 空状态 | 项目列表/四库/搜索结果等无数据时显示友好空状态提示 |
| 错误状态 | API 失败时展示 toast 提示（统一错误处理，参考接口映射 9.3） |
| 表单校验 | 实时校验（输入时） + 提交校验（提交时），错误位置内联显示 |
| 防重复提交 | 抽卡/生成/确认收纳等操作需前端按钮 loading 状态 + 后端 nonce |

---

## 7. 技术约束与已确定决策

以下技术选型已由架构师/技术负责人确定，PRD 阶段不做变更：

| 层面 | 选型 | 版本 |
|:----|:-----|:----:|
| 前端框架 | Next.js (App Router) | 19 |
| 前端语言 | TypeScript | ≥5.5 |
| 前端样式 | CSS Modules | — |
| 后端框架 | FastAPI | ≥0.115 |
| 后端语言 | Python | ≥3.12 |
| 数据库 | PostgreSQL + pgvector | 17 |
| 异步任务 | Celery + Redis | — |
| LLM 网关 | DeepSeek V4（通过 LiteLLM） | — |
| 部署 | Docker（本地 dev 模式直跑） | — |

### 7.1 前端关键约束

- **路由**：Next.js App Router 文件路由，4 个页面一一映射
- **状态管理**：React Context + useReducer（初期够用）
- **API 请求**：fetch 原生（52 个端点均为 REST）
- **认证**：localStorage 存储 token，请求头注入 `Authorization: Bearer`
- **401 处理**：全局拦截 → 自动 refresh → 失败跳转 `/auth`

### 7.2 后端关键约束

- **服务分层**：Route → Service → DAO → PostgreSQL
- **API 格式**：统一 `{code, message, data, request_id}` 格式
- **异步任务**：用户点击确认收纳后 → Celery 异步执行 Phase 4 → 前端轮询结果
- **分布式锁**：Phase 4 写入使用 Redis SET NX EX 防并发
- **Token 预算**：LLM 调用受限流和 Token 预算控制

---

## 8. 数据流摘要

### 8.1 核心创作流水线

```
抽卡阶段
  Step 1: 用户点击"抽卡"
  Step 2: GET /cards/pool?count=3 → 展示3张候选卡
  Step 3: 用户保留/重抽（最多3次） → 最终选定卡牌
  Step 4: 调整权重（三个滑块0-100）
  
生成阶段
  Step 5: POST /generate → 返回task_id
  Step 6: 前端轮询 GET /tasks/:task_id/status → 展示进度动画
  Step 7: 生成完成 → 结果展示在编辑区
  
收纳阶段
  Step 8: 用户点击"确认收纳" → POST /confirm
  Step 9: 展示"收纳中🔄" → 轮询 Phase 4 状态
  Step 10: 完成 → "已收纳✅" → 四库/卡牌池已更新（后台异步完成）
```

### 8.2 拒稿分支

```
用户点击"拒稿" → POST /revise → 返回修改建议
    ├── 返回抽卡状态（重新选卡/重抽）
    └── 显示修改建议（AI 给出的改进方向）
```

---

## 9. 待确认问题（Open Questions）

> 以下为编写 PRD 过程中发现的需要澄清或进一步讨论的事项：

| # | 问题 | 建议决策方 | 影响范围 |
|:--|:-----|:----------|:---------|
| OQ-01 | **编辑器类型**：章节编辑器采用纯文本 (textarea) 还是富文本 (Tiptap/Quill)？原型中无明确富文本组件，接口映射文档也未指定。建议 MVP 使用纯文本 + Markdown 渲染，降低实现复杂度。 | 技术负责人 | 工作台编辑器实现 |
| OQ-02 | **移动端工作台布局**：工作台 HTML 原型中对移动端布局的支持程度不如桌面端完整。移动端是否需要完整的抽卡/生成/四库流程，还是 MVP 先只支持桌面端？ | 产品负责人 | MVP 范围 |
| OQ-03 | **自动保存机制**：接口映射文档提及 `auto_save_draft` 设置（设置页），但工作台原型中未明确自动保存行为的 UI 反馈。MVP 是否需要自动保存（如 30s 间隔 / 失焦时）？ | 产品负责人 | 工作台体验 |
| OQ-04 | **生成结果分段展示**：LLM 生成 500-5000 字内容后，是直接替换编辑器全部内容，还是追加/插入在光标位置？是否允许用户选择替换模式？ | 产品负责人 | 工作台交互 |
| OQ-05 | **侧栏四库的编辑能力**：工作台侧栏的四库面板是"只读查阅"还是允许"直接编辑"（如修改角色描述）？接口映射文档有 PUT API 但 UX 设计未明确。 | 产品负责人 | 工作台功能边界 |
| OQ-06 | **模板数据来源**：新建项目的 6 个模板是后端返回（`GET /api/v1/templates`）还是前端硬编码？MVP 阶段建议先硬编码 3-5 个通用模板。 | 技术负责人 | 新建项目功能 |
| OQ-07 | **创作建议的 Mock 策略**：创作建议 API 的后端尚未实现（接口映射标注为 mock 规则引擎）。MVP 是保留前端 mock，还是先移除该功能？ | 技术负责人 | 新建项目功能 |
| OQ-08 | **Token 刷新策略**：接口映射文档描述 401 → 自动调用 refresh → 重试原请求。但在 fetch 原生实现中，需要全局拦截器机制。是否需要封装统一的 `apiClient` 函数处理？ | 前端开发 | Auth 实现 |
| OQ-09 | **非ce 防重复**：确认收纳和生成接口需要 nonce 防重复提交。nonce 的生成规则是前端 UUID 还是后端下发？ | 技术负责人 | API 设计 |
| OQ-10 | **密码重置的邮件发送**：密码重置涉及邮件发送，MVP 是使用第三方邮件服务（SendGrid/阿里云邮件）还是先返回重置链接到前端（仅开发环境）？ | 技术负责人 | Auth 功能 |

---

## 附录：API 端点汇总（MVP 范围）

基于 `015_54298a88_前后端接口映射.md`，MVP 涉及的 API 端点共 **34 个**：

| 模块 | 端点 | 方法 | 用途 | 优先级 |
|:----|:-----|:----:|:-----|:------:|
| Auth | `/auth/register` | POST | 注册 | P0 |
| Auth | `/auth/login` | POST | 登录 | P0 |
| Auth | `/auth/refresh` | POST | 刷新 Token | P0 |
| Auth | `/auth/me` | GET | 当前用户信息 | P0 |
| Auth | `/auth/password-reset-request` | POST | 请求密码重置 | P0 |
| Auth | `/auth/password-reset` | POST | 设置新密码 | P0 |
| 项目 | `/projects` | GET | 项目列表 | P0 |
| 项目 | `/projects/stats` | GET | 项目统计 | P0 |
| 项目 | `/projects` | POST | 创建项目 | P0 |
| 项目 | `/projects/:id` | GET | 项目详情 | P1 |
| 项目 | `/projects/:id` | PUT | 更新项目 | P1 |
| 项目 | `/projects/:id` | DELETE | 删除项目 | P1 |
| 项目 | `/templates` | GET | 模板列表 | P1 |
| 项目 | `/projects/suggestions` | GET | 创作建议 | P1 |
| 章节 | `/projects/:pid/chapters/current` | GET | 当前章节 | P0 |
| 章节 | `/projects/:pid/chapters` | GET | 章节列表 | P0 |
| 章节 | `/projects/:pid/chapters/:id` | GET | 章节详情 | P0 |
| 章节 | `/projects/:pid/chapters` | POST | 创建章节 | P0 |
| 章节 | `/projects/:pid/chapters/:id` | PUT | 更新章节 | P0 |
| 卡牌 | `/projects/:pid/cards/pool` | GET | 候选卡池 | P0 |
| 卡牌 | `/projects/:pid/cards/draw` | POST | 执行抽卡 | P0 |
| 卡牌 | `/projects/:pid/chapters/:id/redraw` | POST | 重抽 | P0 |
| 生成 | `/projects/:pid/chapters/:id/generate` | POST | 触发生成 | P0 |
| 生成 | `/generate/:task_id/status` | GET | 生成状态轮询 | P0 |
| 生成 | `/generate/:task_id/cancel` | POST | 取消生成 | P1 |
| 收纳 | `/projects/:pid/chapters/:id/confirm` | POST | 确认收纳 | P0 |
| 收纳 | `/projects/:pid/chapters/:id/revise` | POST | 拒稿修改 | P0 |
| 四库 | `/projects/:pid/vault/characters` | GET | 角色列表 | P0 |
| 四库 | `/projects/:pid/vault/timeline` | GET | 时间线 | P0 |
| 四库 | `/projects/:pid/vault/plot-promises` | GET | 剧情承诺 | P0 |
| 四库 | `/projects/:pid/vault/world` | GET | 世界观 | P0 |
| 健康 | `/projects/:pid/health` | GET | 健康告警 | P0 |
| 健康 | `/projects/:pid/health/refresh` | POST | 刷新检查 | P1 |
| AI指令 | `/projects/:pid/chapters/:id/agent` | POST | AI 指令 | P1 |

> 总计：P0 端点 24 个，P1 端点 10 个
>
> *注意：以上未包含设置页的 6 个端点（settings 模块属于第二期）*
