# 墨灵 (Moling) 项目完整结构梳理 v2

> **梳理日期**: 2026-06-21  
> **项目定位**: AI 辅助网文创作平台  
> **梳理范围**: 全栈 — 前端/后端/基础设施/文档  
> **vs v1**: 基于真实代码目录深度扫描，修正统计数字，补充最新模块

---

## 目录

1. [项目概览](#1-项目概览)
2. [顶层目录结构](#2-顶层目录结构)
3. [架构总览](#3-架构总览)
4. [前端架构 — moling-web](#4-前端架构--moling-web)
5. [后端架构 — moling-server](#5-后端架构--moling-server)
6. [部署与基础设施](#6-部署与基础设施)
7. [文档体系](#7-文档体系)
8. [关键发现与改进建议](#8-关键发现与改进建议)

---

## 1. 项目概览

| 维度 | 详情 |
|------|------|
| **项目名称** | 墨灵 (Moling) |
| **项目类型** | AI 辅助网文创作平台（全栈） |
| **仓库地址** | `2eho/moling` (GitHub) |
| **部署地址** | `http://124.222.163.79:8080/moling/` |
| **技术栈** | FastAPI 0.115+ + SQLAlchemy 2.0 async + PostgreSQL 17 + Alembic + Celery 5.5 + Next.js 15 + React 19 + TypeScript 5.7 + TailwindCSS 4 |
| **核心功能** | 灵感卡牌抽取、AI 章节生成、四库管理（角色/时间线/伏笔/世界观）、Phase 4 自动收纳、编织模式、秘密矩阵、连载书导入、拆书引擎 |

### 核心子项目

```
moling/
├── moling-web/       # 前端 — Next.js 15 App Router (24,700+ 文件)
├── moling-server/    # 后端 — FastAPI (4,800+ 文件)
├── docker/           # 生产级 Docker 编排 (9 服务)
├── docker-compose.yml# 开发级 Docker 编排 (4 服务)
├── deploy/           # 宿主机 Nginx 反向代理配置
├── docs/             # 项目文档 (3 核心 + 21 辅助 + 15 归档)
├── .github/          # CI/CD (7 个工作流)
├── novel_dissector/  # 拆书引擎 (独立 Python 工具)
└── scripts/          # 运维脚本
```

---

## 2. 顶层目录结构

```
moling/
│
├── moling-web/                          # 【前端】Next.js 15 + React 19 + TypeScript
│   ├── src/
│   │   ├── app/                         #   App Router 页面 (9 个路由)
│   │   ├── components/                  #   组件库 (14 个，按功能分 health/phase4/vibe)
│   │   ├── lib/                         #   工具库 + HTTP 客户端 + 类型定义
│   │   ├── mock/                        #   Mock 基础设施（架子已搭，数据待填）
│   │   └── __tests__/                   #   前端测试
│   ├── public/                          #   静态资源
│   ├── Dockerfile                       #   多阶段构建 (standalone 输出)
│   ├── nginx.conf                       #   前端容器 Nginx (子路径 /moling)
│   ├── next.config.ts                   #   Next.js 配置 (basePath: /moling)
│   └── package.json                     #   依赖管理 (pnpm)
│
├── moling-server/                       # 【后端】FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── router/                      #   API 路由层 (18 个模块, 150+ 端点)
│   │   ├── service/                     #   业务逻辑层 (28 个服务)
│   │   ├── dao/                         #   数据访问层 (15 个 DAO，含 base_dao)
│   │   ├── models/                      #   ORM 模型 (20 个表/模型文件)
│   │   ├── schemas/                     #   Pydantic Schema (17 个文件)
│   │   ├── middleware/                  #   中间件 (5 个)
│   │   ├── llm/                         #   LLM 集成 (客户端 + 密钥池 + 提示词)
│   │   ├── worker/                      #   Celery 后台任务 (9 个文件)
│   │   ├── generation/                  #   异步生成 (jobs_store + router)
│   │   ├── ingest/                      #   连载书导入管线 (Phase 0-3 + scraper)
│   │   ├── genre/                       #   拆书引擎 (A1-A5 五阶段管线)
│   │   ├── auth/                        #   JWT 黑名单
│   │   ├── core/                        #   核心框架 (依赖注入 + 服务注册)
│   │   ├── utils/                       #   工具函数
│   │   ├── config.py                    #   应用配置
│   │   ├── dependencies.py              #   FastAPI 依赖注入
│   │   ├── errors.py                    #   统一错误处理 (AppError 体系)
│   │   ├── limiter.py                   #   限流器
│   │   └── main.py                      #   应用入口
│   ├── alembic/                         #   数据库迁移 (3+ 版本)
│   ├── tests/                           #   后端测试 (875+ passed)
│   └── Dockerfile                       #   多阶段构建 (python:3.11-slim)
│
├── docker/                              # 【生产部署】9 服务完整编排
│   ├── docker-compose.yml               #   生产级编排
│   ├── docker-compose.prod.yml          #   CI/CD 自动化版 (GHCR 镜像 + 资源限制)
│   ├── .env.example                     #   飞书 Webhook / Grafana 配置模板
│   ├── deploy.sh                        #   Linux 手工部署脚本 (含 --rollback)
│   ├── deploy-remote.sh                 #   远程部署脚本 (CI/CD 调用，零停机滚动更新)
│   ├── deploy.bat                       #   Windows 部署脚本
│   ├── health-check.sh                  #   全面健康检查 (8 项，支持 --json)
│   ├── prometheus.yml                   #   Prometheus 抓取配置
│   ├── alert_rules.yml                  #   告警规则
│   ├── alertmanager.yml                 #   AlertManager 配置 (按 severity 路由)
│   ├── feishu-tmpl.go                   #   飞书消息模板
│   ├── feishu-alert-bridge.py           #   飞书告警桥接服务
│   ├── Dockerfile.feishu-bridge         #   飞书桥接 Dockerfile
│   ├── nginx/nginx.conf                 #   容器 Nginx (HTTPS + HSTS + CSP)
│   ├── nginx/ssl/README.md              #   SSL 证书说明
│   └── grafana/provisioning/            #   Grafana 自动配置 (仪表板 + 数据源)
│
├── docker-compose.yml                   # 【开发部署】4 服务快速编排 (db/redis/app/web)
├── deploy/nginx/moling.conf             #   宿主机 Nginx 反向代理配置 (端口 8080)
├── docs/                                #   项目文档
├── .github/workflows/                   #   CI/CD (7 个 pipeline)
├── novel_dissector/                     #   拆书引擎 (独立 Python 工具)
├── scripts/                             #   运维脚本
├── specs/                               #   技术规格
├── .githooks/                           #   Git hooks
├── openapi.json / openapi.yaml          #   API 规范
├── DESIGN.md                            #   设计文档 (根目录简版)
├── fe-specs.md                          #   前端技术规格
├── OPENAPI_MANAGEMENT.md                #   OpenAPI 管理规范
├── VIBE_WRITING_DESIGN.md               #   Vibe Writing 设计文档
└── README.md                            #   项目 README
```

---

## 3. 架构总览

### 3.1 分层架构

```
                        用户浏览器
              http://124.222.163.79:8080/moling/
                           │ HTTPS
           宿主机 Nginx (deploy/nginx/moling.conf)
        /moling → :3000    /moling/api/ → :8000
        SSE 流式支持 / 速率限制 100r/s / HSTS+CSP
              │ /moling              │ /moling/api/
  frontend 容器 (:3000)       app 容器 (:8000)
  Nginx + Next.js             FastAPI + Uvicorn
  standalone output           (4 workers)
                                  │
              PostgreSQL 17+pgvector  Redis 7    Celery Worker
                                  │
              监控栈 (可选，生产环境)
  Prometheus :9090 → AlertManager :9093
  → feishu-bridge :9094 → 飞书卡片通知
  Grafana :3001 → moling-overview 仪表板
```

### 3.2 技术选型矩阵

| 层次 | 技术 | 版本 | 职责 |
|------|------|------|------|
| **前端框架** | Next.js (App Router) | 15.x | SSR/SSG/路由/代码分割 |
| **前端UI** | React + TailwindCSS | 19.x + 4.x | 组件化 + 原子化样式 |
| **前端语言** | TypeScript | 5.7 | 类型安全 |
| **前端状态** | zustand + TanStack Query | v5 | UI 状态 + 服务端状态 |
| **后端框架** | FastAPI | 0.115+ | RESTful API + 自动文档 |
| **ORM** | SQLAlchemy (async) | 2.0.36+ | 异步数据库操作 |
| **数据库** | PostgreSQL + pgvector | 17 | 主存储 + 向量搜索 |
| **缓存/队列** | Redis | 7 | Token 黑名单 + Celery Broker |
| **任务队列** | Celery | 5.5+ | 异步 AI 生成/导入/Phase4 |
| **LLM** | DeepSeek (OpenAI 兼容) | V3 | AI 文本生成 |
| **监控** | Prometheus + Grafana + AlertManager | latest | 指标采集 + 可视化 + 告警 |
| **告警通知** | 飞书卡片消息 | — | AlertManager → feishu-bridge → 飞书 |
| **CI/CD** | GitHub Actions | — | 7 个自动化管道 |
| **容器化** | Docker Compose | — | 开发 4 服务 / 生产 9 服务 |
| **反向代理** | Nginx | — | /moling 子路径 + SSL 终结 |

### 3.3 数据流

```
用户操作 → React 组件 → zustand Store / TanStack Query
    → api.ts (src/lib/http/) → client.ts (Bearer Token + 自动刷新)
    → HTTP (JWT Bearer Token)
    → Nginx Proxy → FastAPI Router → Service → DAO → SQLAlchemy → PostgreSQL
                                              ↓
                                         Celery Worker → DeepSeek API
                                              ↓
                                         WebSocket/轮询通知前端
```

### 3.4 后端五层架构

```
Router (18 modules)
  │  请求验证 (Pydantic schemas)、路由分发、认证依赖
  ▼
Service (28 modules)
  │  业务逻辑、编排、事务管理
  ▼
DAO (15 modules, 基于 base_dao)
  │  数据库操作封装、查询构建、软删除过滤
  ▼
SQLAlchemy Models (20 tables)
  │  ORM 映射、relationship 关联
  ▼
PostgreSQL 17 + pgvector
```

---

## 4. 前端架构 — moling-web

### 4.1 路由地图 (9 个页面)

| 路由路径 | 认证 | 说明 |
|---------|------|------|
| `/` | 可选 | 首页/落地页 |
| `/auth` | 公开 | 登录/注册 |
| `/settings` | ✅ | 用户设置 |
| `/projects` | ✅ | 项目列表 |
| `/projects/new` | ✅ | 新建项目 |
| `/workspace/[projectId]` | ✅ | **核心**: Vibe Writing 工作台 |
| `/workspace/[projectId]/health` | ✅ | 项目健康面板 |
| `/workspace/[projectId]/phase4/tasks` | ✅ | Phase 4 任务详情 |
| `/vaults/[projectId]` | ✅ | 四库管理 |

> **vs v1**: 从 18 个路由精简到 9 个。路由重新设计，去掉了 landing/pricing/import/history/notifications/admin 等独立页面，核心功能收敛到 workspace 和 vaults。

### 4.2 组件体系 (14 个组件)

**健康仪表板**: `HealthDashboard`

**Phase 4 模块**: `CharacterLibrary`, `WorldviewLibrary`, `TimelineLibrary`, `ForeshadowingLibrary`, `CardManager`, `Phase4TaskPanel`

**Vibe Writing 核心**: `AgentPanel`, `Sidebar`, `ThemeSwitcher`, `ThemeInitializer`, `ProgressBar`, `PhaseNavigator`, `ContextPanel`, `ActionBar`, `OptionCard`, `FreeInput`, `QueryProvider`

### 4.3 HTTP 客户端架构

| 层 | 文件 | 功能 |
|----|------|------|
| **核心 HTTP** | `src/lib/http/client.ts` | Bearer Token 注入 + 401 自动刷新 + 请求去重缓存 + X-Request-ID 追踪 |
| **Token 管理** | `src/lib/http/auth.ts` | JWT 读写/过期检查/自动清理 |
| **业务 API** | `src/lib/http/api.ts` | 业务 API 模块封装 |
| **缓存** | `src/lib/http/cache.ts` | 请求去重缓存 |

### 4.4 工具库

| 文件 | 功能 |
|------|------|
| `src/lib/cn.ts` | className 合并工具 (clsx + tailwind-merge) |
| `src/lib/env.ts` | 环境变量管理 |
| `src/lib/format.ts` | 格式化工具 |
| `src/lib/constants.ts` | 全局常量 |
| `src/lib/types/domain.ts` | 领域类型定义 |

### 4.5 设计系统

8 套经典主题 (CSS 变量 `--th-*`)：
- **暗色 5**: moling (默认) / nord / onedark / dracula / solarized-dark
- **亮色 3**: solarized-light / paper / github-light
- 零硬编码色值，`Ctrl+Shift+T` 切换

### 4.6 Vibe Writing 交互模型

- **设计原则**: Heavy Options, Light Input
- **交互方式**: A/B/C 选项推进 + D 自由输入
- **Agent 理念**: Agent of Agents — Plot/Character/Dialogue/Style/World 5 Agent 协作
- **状态管理**: zustand (UI 状态) + TanStack Query v5 (服务端状态)

---

## 5. 后端架构 — moling-server

### 5.1 API 路由模块 (18 个模块, 150+ 端点)

| 路由模块 | 前缀 | 核心功能 |
|---------|------|---------|
| **auth** | `/auth` | 注册/登录/JWT 刷新/登出/密码重置/个人信息 |
| **project** | `/projects` | CRUD + 统计 + 建议 + 抽卡历史 + 健康告警 |
| **chapter** | `/projects/{id}` | CRUD + 排序 + 确认/修订 + AI 指令 + 生成 |
| **card** | `/projects/{id}` | 抽卡/重抽/退役/卡池/历史 |
| **vault** | `/projects/{id}/vault` | 四库 CRUD (角色/时间线/伏笔/世界观) + 总览 + 重分析 |
| **generation** | `/generate` | 异步生成/状态查询/取消/历史 |
| **health** | `/health` | 系统健康检查 |
| **project_health** | `/projects/{id}` | 项目健康告警/刷新 |
| **admin** | `/admin` | LLM 配置/统计/用户管理/LLM 用量 |
| **notification** | `/notifications` | 列表/未读数/标记已读/删除 |
| **setting** | `/settings` | 设置 CRUD/改密/导出/缓存/health-monitor/phase4-review |
| **template** | `/templates` | 模板 CRUD + 用模板创建项目 |
| **phase4** | `/phase4` | 精修建议/应用/任务状态/审核 |
| **subscription** | `/subscriptions` | 方案/结算/订阅/支付历史 |
| **weave** | `/weave` | 编织模式/建议/应用/分析 |
| **genre** | `/genre` | 冷启动预填/确认入库 |
| **secret** | `/projects/{id}/secrets` | 秘密矩阵查询/更新 |
| **ingest** | `/projects/{id}/import` | 导入任务/进度查询/分阶段执行 |

### 5.2 服务层 (28 个服务)

| 文件 | 职责 |
|------|------|
| `algorithm_service.py` | 卡牌组合算法 (8 维评分) |
| `auth_service.py` | 认证 + 密码复杂度 + 登录锁定 |
| `book_analysis_service.py` | 全书分析 |
| `card_pool_service.py` | 卡牌池管理 |
| `card_retire_service.py` | 卡牌退役逻辑 |
| `card_service.py` | 抽卡核心逻辑 |
| `chapter_service.py` | 章节 CRUD + 排序 |
| `coherence_service.py` | 连贯性检查 (3 组 LLM 分组调用) |
| `conflict_detection.py` | 冲突检测 |
| `direction_scoring.py` | 方向评分 |
| `generation_service.py` | AI 生成编排 + Prompt 组装 |
| `health_monitor.py` | 健康监控 |
| `health_service.py` | 健康检查服务 |
| `import_service.py` | 导入引擎 (批量写入 BULK_BATCH_SIZE=200) |
| `merge_service.py` | 合并服务 (savepoint 保护) |
| `notification_service.py` | 通知管理 |
| `phase4_scheduler.py` | Phase 4 调度器 |
| `phase4_service.py` | Phase 4 自动收纳 |
| `phase4_store.py` | Phase 4 状态存储 |
| `project_service.py` | 项目 CRUD + 统计 |
| `prompt_service.py` | 统一 Prompt 组装 |
| `secret_service.py` | 秘密矩阵管理 |
| `setting_service.py` | 用户设置 |
| `template_service.py` | 模板管理 |
| `validation_service.py` | 预生成验证 |
| `vault_filter.py` | 四库过滤 + 压缩 |
| `vault_service.py` | 四库核心逻辑 |
| `weave_service.py` | 编织模式识别 |
| `weaving_scheme.py` | 编织方案生成 |

### 5.3 DAO 层 (15 个 DAO)

| 文件 | 职责 |
|------|------|
| `base_dao.py` | 基础 DAO (CRUD + 分页 + 软删除 + limit 钳制 500) |
| `user_dao.py` | 用户数据访问 |
| `project_dao.py` | 项目数据访问 |
| `chapter_dao.py` | 章节数据访问 |
| `card_dao.py` | 卡牌数据访问 (含同步方法给 Worker) |
| `generation_dao.py` | 生成任务数据访问 |
| `dynamic_layer_dao.py` | 动态层数据访问 (含 JOIN 查询) |
| `vault_dao.py` | 四库数据访问 (含 8 个 count 方法) |
| `secret_dao.py` | 秘密矩阵数据访问 (含 debt 聚合) |
| `health_alert_dao.py` | 健康告警数据访问 |
| `notification_dao.py` | 通知数据访问 |
| `phase4_dao.py` | Phase 4 任务数据访问 |
| `template_dao.py` | 模板数据访问 |
| `system_config_dao.py` | 系统配置数据访问 |
| `subscription_dao.py` | 订阅数据访问 |

### 5.4 数据库模型 (20 个表)

| 模型 | 表名 | 用途 |
|-----|------|------|
| User | users | 用户账号 + 偏好设置 |
| Project | projects | 小说项目元数据 |
| Chapter | chapters | 章节内容 + 方向标记 |
| DynamicLayer | dynamic_layers | 每章动态事实层 (前情摘要/锚点/秘密矩阵) |
| GenerationTask | generation_tasks | AI 生成任务追踪 |
| CardPool | card_pool | 方向卡牌池 (含 8 维算法字段) |
| DrawHistory | draw_history | 抽卡历史快照 |
| VaultCharacter | vault_characters | 四库-角色 (含状态机) |
| VaultTimeline | vault_timeline | 四库-时间线事件 |
| VaultPlotPromise | vault_plot_promises | 四库-伏笔/情节承诺 |
| VaultWorld | vault_world | 四库-世界观规则 |
| VaultChangelog | vault_changelog | 四库变更日志 (审计追踪) |
| Secret | secrets | 秘密矩阵 |
| HealthAlert | health_alerts | 项目健康告警 |
| Notification | notifications | 用户通知 |
| Plan | plans | 订阅方案 |
| UserSubscription | user_subscriptions | 用户订阅 |
| Phase4Task | phase4_tasks | Phase 4 幂等任务 (10 状态机) |
| SystemConfig | system_config | 系统配置键值存储 |
| Template | templates | 项目模板 |

### 5.5 Pydantic Schema (17 个文件)

auth / project / chapter / card / vault / generation / health / notification / phase4 / secret / setting / subscription / template / weave / admin / coherence / common

### 5.6 中间件体系 (5 个)

| 中间件 | 功能 |
|--------|------|
| `request_id.py` | X-Request-ID 注入 (UUID 追踪) |
| `rate_limit.py` | 分布式限流 (Redis 1000 次/60s + IP 级别) |
| `audit_log.py` | 审计日志 (method/path/user/duration/body 10KB 上限/敏感数据过滤/100MB rollover) |
| `response_format.py` | 统一响应包装 `{code, message, data, meta}` + 流式透传 |
| `content_length_limit.py` | Content-Length 限制 (MAX_BODY_SIZE) |

> CORS 通过 FastAPI 原生 CORSMiddleware 处理（环境自适应）。

### 5.7 错误体系

- **ErrorCode 枚举**: 20+ 错误码 (`HTTP 状态码 * 100 + 序号`)
- **AppError 基类**: 继承 HTTPException，含中文错误消息
- **子类**: `NotFoundError`, `AuthError`, `PermissionError`, `ValidationError`, `RateLimitError`, `ConflictError`, `VaultNotFoundError`
- 所有异常处理统一到 AppError，替代直接 HTTPException

### 5.8 LLM 集成 (`app/llm/`)

| 文件 | 功能 |
|------|------|
| `client.py` | OpenAI 兼容 HTTP 客户端，流式/非流式，tenacity 自动重试，Token 计数 |
| `key_manager.py` | API 密钥池 (Pro Pool / Flash Pool)，LEAST_USAGE / ROUND_ROBIN 策略，自动冷却恢复 |
| `context_budget.py` | 上下文预算管理 |
| `prompts.py` | 提示词入口 |
| `prompts/generation.py` | 生成提示词模板 |

### 5.9 异步生成架构

```
用户请求生成
  → POST /chapters/{id}/generate
  → generation/jobs_store.py (任务状态存储)
  → Celery Worker (生产) / BackgroundTasks (开发)
  → DeepSeek API (流式调用)
  → 前端轮询 GET /generate/{task_id}/status
```

### 5.10 Worker 异步任务 (9 个文件)

| 文件 | 功能 |
|------|------|
| `celery_app.py` | Celery 实例配置 |
| `db.py` | Worker 数据库会话管理 (get_worker_session) |
| `idempotency.py` | 任务幂等性保障 |
| `tasks.py` | 主任务注册 |
| `book_analysis_task.py` | 全书分析任务 |
| `card_retire_task.py` | 卡牌退役任务 |
| `import_task.py` | 导入任务 |
| `phase4_task.py` | Phase 4 收纳任务 |
| `vault_reanalyze_task.py` | 四库重分析任务 |

### 5.11 业务引擎

| 引擎 | 目录 | 管线 |
|------|------|------|
| **拆书引擎** | `app/genre/` | A1 黄金三章 → A2 角色聚类 → A3 钩子密度 → A4 节奏曲线 → A5 套路归纳 |
| **导入引擎** | `app/ingest/` | Phase 0 分章预览 → Phase 1 全量四库 → Phase 2 动态层 → Phase 3 确认写入 |
| **卡牌系统** | `app/service/card_service.py` | 8 维算法评分 + 方向抽取 + 卡牌退役 |
| **Phase 4** | `app/service/phase4_*.py` | 自动收纳 (IDLE→QUEUED→LOCKING→EXTRACTING→VERIFYING→MERGING→COMMITTING→DONE) |
| **编织模式** | `app/service/weave_*.py` | 跨章节模式识别 + 编织建议 |
| **连贯性检查** | `app/service/coherence_service.py` | 3 组 LLM 分组调用 (叙事一致性/写作质量/连续性) |

### 5.12 导入引擎详细结构 (最复杂模块)

```
app/ingest/
├── __init__.py
├── models.py / router.py / service.py       # 入口层
├── phase1/                                   # 阶段 1: 提取
│   ├── extractor.py / merger.py / scheduler.py / schemas.py
├── phase2/                                   # 阶段 2: 分析
│   ├── analyzer.py / schemas.py
├── phase3/                                   # 阶段 3: 提交
│   ├── committer.py / conflict.py
└── scraper/                                  # 采集器
    ├── pipeline.py                           # 采集管线
    ├── core/                                 # 核心引擎
    │   ├── fetcher.py / cleaner.py / extractor.py
    │   ├── toc_crawler.py / style_analyzer.py / style_prompt_builder.py
    ├── splitter/                             # 文本分割
    │   ├── base.py / chapter.py / paragraph.py / strategies.py
    ├── models/schemas.py                     # 数据模型
    ├── config.py / export.py                 # 配置 + 导出
    └── example_usage.py / test_verify.py     # 示例 + 验证
```

### 5.13 Windows 兼容性

- `greenlet_spawn` 猴子补丁 (线程池替代 greenlet)
- `_get_exec_once_mutex` 补丁 (事件系统兼容)
- `_SyncAsyncSessionWrapper` 包装器 (同步 Session → 伪异步)
- 启动时自动检测并创建 SQLite 表 (绕过 Alembic)

---

## 6. 部署与基础设施

### 6.1 双层次 Docker 编排

| 属性 | 开发级 (`docker-compose.yml`) | 生产级 (`docker/docker-compose.yml`) |
|------|---------------------------|-----------------------------------|
| **服务数** | 4 | 9 |
| **数据库** | PostgreSQL 16-alpine (端口暴露) | PostgreSQL 17 + pgvector (内网) |
| **Redis** | 无密码 | 密码保护 |
| **Worker** | 无 | Celery Worker |
| **监控** | 无 | Prometheus + AlertManager + Grafana |
| **告警** | 无 | AlertManager + feishu-bridge → 飞书 |
| **Nginx** | 无 (直接 Next.js) | 安全加固版 (HTTPS + HSTS + CSP) |
| **安全** | 开发宽松 | 非 root 用户 + 最小端口暴露 |

### 6.2 Nginx 三套配置

| 配置 | 用途 | 关键特性 |
|------|------|---------|
| `docker/nginx/nginx.conf` | 生产 frontend 容器 | HTTPS 443 + HSTS + CSP + api 代理 → app:8000 |
| `moling-web/nginx.conf` | 前端 standalone 容器 | 子路径 /moling + WebSocket 300s |
| `deploy/nginx/moling.conf` | 宿主机 Nginx | 端口 8080 + /moling 路径转发 + SSE 流式 + Prometheus 内网限制 |

### 6.3 CI/CD 管道 (7 个 workflow)

| Workflow | 触发条件 | 核心动作 |
|----------|---------|---------|
| **deploy.yml** | push to main / workflow_dispatch | 完整 CI/CD: lint → test → build (GHCR) → deploy (SSH) → verify → auto-rollback |
| **ci-cd.yml** | push/PR main/master/develop + workflow_dispatch | lint (报告不阻断) → test → 前端构建 → Docker 构建 (仅手动) |
| **ci.yml** | push/PR develop, main | 后端测试 (pytest) + 前端构建 + lint + OpenAPI 校验 |
| **auto-update-openapi.yml** | push main + 修改 server/** | 自动生成 openapi.json 并 commit |
| **openapi-check.yml** | push/PR main | OpenAPI JSON 合法性校验 |
| **backup-test.yml** | 修改备份脚本/每周 cron/手动 | 全量备份 + 加密 + 灾备演练 |
| **database-migration-test.yml** | 修改 alembic/** 或 models/** | 迁移回滚幂等性测试 + 灾备 |

### 6.4 部署流程

```
开发者 git push main
  → GitHub Actions deploy.yml
  → lint + test + Docker build (GHCR)
  → SSH docker/deploy-remote.sh
  → 滚动更新 (横向扩展 → 健康检查 → 缩容)
  → 冒烟测试 (verify)
  → 失败自动回滚 + 飞书通知
```

### 6.5 备份策略

| 任务 | 频率 | 方式 |
|------|------|------|
| 全量备份 | 每天 02:00 | pg_dump + GPG 加密 |
| 增量备份 | 每 30 分钟 | WAL 归档 |
| 备份监控 | 每天 03:00 | 完整性验证 + 通知 |
| 灾备演练 | 每周日 04:00 | 完整恢复演练 + 报告 |

### 6.6 数据库三层策略

| 环境 | 数据库 | 连接字符串 |
|------|--------|-----------|
| 本地开发 | SQLite | `sqlite+aiosqlite:///./moling.db` |
| 开发 Docker | PostgreSQL 16 | `postgresql+psycopg://moling:moling@db:5432/moling` |
| 生产 MVP | SQLite | `sqlite+aiosqlite:///app/data/moling.db` |
| 生产推荐 | PostgreSQL 17+pgvector | 通过 DATABASE_URL 切换 |

### 6.7 监控与可观测性

| 组件 | 端口 | 功能 |
|------|------|------|
| Prometheus | 9090 | 指标采集 (15s 间隔) + 200h 保留 |
| AlertManager | 9093 | 告警路由 (按 severity: critical 即时 / warning 聚合) |
| feishu-bridge | 9094 | AlertManager → 飞书富文本卡片 |
| Grafana | 3001 | moling-overview 仪表板 (自动加载) |
| Health 端点 | /health | 服务健康检查 (R1/R2/R3 三级) |
| AuditLog | — | 请求/响应审计日志 |

---

## 7. 文档体系

### 7.1 核心文档 (3 份 — Agent 优化)

| 文档 | 版本 | 说明 |
|:-----|:----:|:-----|
| `docs/ARCHITECTURE.md` | 1.9.0 | **后端架构唯一真相来源** — 系统拓扑/数据流/部署/Worker 可靠性/DAO 规范/AppError 体系/健康检查/操作命令 |
| `docs/SPECIFICATIONS.md` | 2.4.0 | **功能规格唯一真相来源** — P0/P1 规格/卡牌算法/架构加固/质量门禁 (总分 87/100, A 级) |
| `docs/DESIGN.md` | 2.0.0 | **前端设计唯一真相来源** — 技术栈/8 主题/Vibe Writing/路由/状态管理/Sidebar 规则 |

### 7.2 辅助文档

| 类别 | 文件 |
|------|------|
| **运维** | DEPLOYMENT.md, ONBOARDING.md, RUNBOOK.md, BACKUP_STRATEGY.md, DISASTER_RECOVERY_LOG.md |
| **安全** | SECURITY_HARDENING.md |
| **监控** | MONITORING_SETUP.md |
| **性能** | PERFORMANCE_BASELINE.md, PERFORMANCE_TESTING_REPORT.md |
| **流程** | CI_CD_SETUP.md, GIT_WORKFLOW_GUIDE.md |
| **决策** | design-decisions.md |
| **扫描** | ARCHITECTURE_SCAN_2026-06-20.md, ARCHITECTURE_DEEP_SCAN_2026-06-21.md, reports/scan-v4-*.md (9 份) |
| **设计** | 前端重建方案.md |

### 7.3 归档 (docs/archive/ — 15 份)

历史算法设计、接口映射、审计报告、集成测试方案等，仅供人类查阅。

### 7.4 文档铁律

1. **禁止新建文档** — agent 不得在 docs/ 下创建新的 .md 文件
2. **禁止拆分文档** — 不得将核心文档拆分为子文档
3. **代码改动 → 立即回填** — 每次代码修改后同步更新对应核心文档
4. **archive/ 只进不出** — 历史文档放入后不再更新

---

## 8. 关键发现与改进建议

### 🔴 需优先处理

| 问题 | 影响 | 建议 |
|------|------|------|
| **前端路由大幅精简** | 从 18 个路由 → 9 个，landing/pricing/import/history/notifications/admin 等独立页面消失 | 确认是否为有意精简，缺失功能是否需补充 |
| **前端组件减至 14 个** | vs v1 报告的 "130+ 组件"，实际仅 14 个文件 | 大规模重构进行中，需确认交付里程碑 |
| **前端 contexts/hooks 不存在** | 状态管理迁移到 zustand + TanStack Query | 确认新方案是否完成迁移 |
| **前端 Mock 未实现** | mock/data/ 和 mock/handlers/ 空目录 | Mock 基础设施需填充数据 |
| **内存任务存储** | `jobs_store.py` 使用内存存储，重启丢失 | 迁移到 Redis/PostgreSQL 持久化 |
| **TypeScript 构建跳过错误** | `ignoreBuildErrors: true` 隐藏类型问题 | 逐步修复 TS 错误，最终启用严格构建 |

### 🟡 建议优化

| 项目 | 说明 |
|------|------|
| **前端 API 路径** | `src/lib/http/` 结构清晰，但需确保与后端 OpenAPI 规范严格对齐 |
| **Celery Worker 生产就绪** | Worker 模块完整 (9 文件)，但开发环境未启用 |
| **导入引擎 scraper** | `ingest/scraper/` 子模块复杂，含独立 requirements.txt，需确认依赖管理 |
| **生产默认 SQLite** | MVP 可用，但需计划 PostgreSQL 迁移路径 |
| **告警通知** | feishu-bridge 完整，但依赖飞书 Webhook 配置 |

### 🟢 做得好的地方

- ✅ 后端五层架构清晰 (Router→Service→DAO→Model→DB)
- ✅ DAO 层 15 个模块完整覆盖所有实体，含 base_dao 统一规范
- ✅ 中间件体系完善 (5 层) + 审计日志
- ✅ 统一错误码 + 中文消息 + AppError 体系
- ✅ CI/CD 7 个管道覆盖质量/部署/备份全流程
- ✅ 备份策略完整 (全量+增量+加密+灾备演练)
- ✅ LLM API 密钥池管理 (Pro/Flash 双池 + 冷却恢复)
- ✅ Docker 双层次编排 (开发 4 服务 / 生产 9 服务)
- ✅ 监控栈完整 (Prometheus + AlertManager + Grafana + 飞书告警)
- ✅ 部署零停机滚动更新 + 自动回滚
- ✅ Windows 兼容性处理到位
- ✅ 核心文档版本化管理 + Agent 优化索引

---

## 附录: 数量统计 (v2 vs v1)

| 维度 | v1 (2026-06-19) | v2 (2026-06-21) | 变化 |
|------|:---:|:---:|:---:|
| 前端路由 | 18 | **9** | -50% |
| 前端组件 | 130+ | **14** | 重构精简 |
| 前端 Context | 5 | **0** | 迁移到 zustand |
| 前端 Hooks | 8 | **0** | 迁移到 TanStack Query |
| 前端 Mock 端点 | 50+ | **0** (空目录) | 待实现 |
| 前端 API 目录 | `src/api/` + `src/lib/` | `src/lib/http/` | 统一 |
| 后端路由模块 | 18 | **18** | — |
| 后端服务 | 27 | **28** | +1 |
| 后端 DAO | 11 | **15** | +4 |
| 后端模型 | 17 | **20** | +3 |
| 后端 Schema | 14 | **17** | +3 |
| 后端中间件 | 6 | **5** (代码) | CORS 归 FastAPI 原生 |
| 后端 Worker | ~5 | **9** | +4 |
| 数据库迁移 | 3 | **3+** | — |
| CI/CD 工作流 | 6 | **7** | +1 (deploy.yml v2) |
| Docker 服务 (生产) | 7 | **9** | +alertmanager + feishu-bridge |
| Docker 服务 (开发) | 4 | **4** | — |
| Nginx 配置 | 3 | **3** | — |
| 核心文档 | 3 | **3** | 版本更新 |
| 辅助文档 | 33 | **21** | 精简归档 |
