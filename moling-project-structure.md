# 墨灵 (Moling) 项目完整结构梳理

> **梳理日期**: 2026-06-19  
> **项目定位**: AI 辅助网文创作平台  
> **版本**: v0.1.0

---

## 目录

1. [项目概览](#1-项目概览)
2. [顶层目录结构](#2-顶层目录结构)
3. [架构总览](#3-架构总览)
4. [前端架构 - moling-web](#4-前端架构---moling-web)
5. [后端架构 - moling-server](#5-后端架构---moling-server)
6. [部署与基础设施](#6-部署与基础设施)
7. [监控与运维](#7-监控与运维)
8. [关键发现与改进建议](#8-关键发现与改进建议)

---

## 1. 项目概览

| 维度 | 详情 |
|------|------|
| **项目名称** | 墨灵 (Moling) |
| **项目类型** | AI 辅助网文创作平台（全栈） |
| **仓库地址** | `2eho/moling` (GitHub) |
| **部署地址** | `http://124.222.163.79:8080/moling/` |
| **技术栈** | FastAPI + SQLAlchemy async + PostgreSQL + Alembic + Next.js 15 + TypeScript + Tailwind CSS 4 |
| **核心功能** | 灵感卡牌抽取、AI 章节生成、四库管理（角色/时间线/伏笔/世界观）、Phase 4 自动收纳、编织模式、秘密矩阵、连载书导入 |

### 核心子项目

```
moling/                            # 项目根目录
├── moling-web/                    # 前端 — Next.js 15 App Router (18500+文件)
├── moling-server/                 # 后端 — FastAPI (4600+文件)
├── docker/                        # 生产级 Docker 编排（7服务）
├── docker-compose.yml             # 开发级 Docker 编排（4服务）
├── deploy/                        # 宿主机 Nginx 配置
├── docs/                          # 项目文档（36份）
├── novel_dissector/               # 拆书引擎（独立Python工具）
├── .github/workflows/             # 6个 CI/CD 工作流
└── tests/                         # 测试文档与计划
```

---

## 2. 顶层目录结构

```
C:\Users\Admin\Desktop\work\moling/
│
├── moling-web/                          # 【前端】Next.js 15 + React 19 + TypeScript
│   ├── src/
│   │   ├── app/                         #   App Router 页面 (18个路由)
│   │   ├── components/                  #   组件库 (130+组件)
│   │   ├── contexts/                    #   5个Context提供者
│   │   ├── hooks/                       #   8个自定义Hook
│   │   ├── lib/                         #   工具库 + API客户端
│   │   ├── mock/                        #   Mock开发系统 (50+端点)
│   │   └── __tests__/                   #   前端测试
│   ├── Dockerfile                       #   多阶段构建 (standalone)
│   ├── nginx.conf                       #   前端容器 Nginx
│   ├── next.config.ts                   #   basePath: /moling
│   └── package.json                     #   依赖管理
│
├── moling-server/                       # 【后端】FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── router/                      #   API路由层 (18个模块, 150+端点)
│   │   ├── models/                      #   ORM模型 (17个表)
│   │   ├── schemas/                     #   Pydantic模式 (14个文件)
│   │   ├── service/                     #   业务逻辑层 (27个服务)
│   │   ├── dao/                         #   数据访问层 (11个DAO)
│   │   ├── middleware/                  #   中间件 (5个)
│   │   ├── llm/                         #   LLM集成 (DeepSeek + API密钥池)
│   │   ├── genre/                       #   拆书引擎 (A1-A5管线)
│   │   ├── ingest/                      #   连载书导入 (Phase 0-3)
│   │   ├── worker/                      #   Celery后台任务
│   │   ├── generation/                  #   异步AI生成
│   │   └── auth/                        #   JWT黑名单
│   ├── alembic/                         #   数据库迁移 (3个版本)
│   ├── tests/                           #   后端测试
│   ├── scripts/                         #   运维脚本 (备份/灾备/性能)
│   └── Dockerfile                       #   多阶段构建 (python:3.11-slim)
│
├── docker/                              # 【生产部署】7服务编排
│   ├── docker-compose.yml               #   frontend + app + worker + db + redis + prometheus + grafana
│   ├── nginx/nginx.conf                 #   HTTPS + HSTS + 安全头
│   ├── prometheus.yml                   #   监控指标采集
│   ├── grafana/provisioning/            #   Grafana自动配置
│   ├── deploy.sh                        #   Linux部署脚本
│   └── deploy.bat                       #   Windows部署脚本
│
├── docker-compose.yml                   # 【开发部署】4服务快速编排
├── deploy/nginx/moling.conf             #   宿主机 Nginx (子路径 /moling)
├── docs/                                # 项目文档 (36份)
├── .github/workflows/                   # CI/CD (6个pipeline)
├── .githooks/                           # Git hooks
├── novel_dissector/                     # 拆书引擎 (独立工具)
├── src/                                 # 前端辅助模块
├── openapi.json / openapi.yaml          # API规范
├── DESIGN.md                            # 设计文档
├── OPENAPI_MANAGEMENT.md                # OpenAPI管理规范
├── fe-specs.md                          # 前端技术规格
└── README.md                            # 项目README
```

---

## 3. 架构总览

### 3.1 分层架构

项目采用经典的**四层架构**：表示层（Next.js + Nginx）→ 应用层（FastAPI）→ 数据层（PostgreSQL + Redis）→ 基础设施层（Docker + Prometheus + Grafana）。

```
┌──────────────────────────────────────────────────────────────┐
│                        用户浏览器                               │
│              http://124.222.163.79:8080/moling/                │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼───────────────────────────────────┐
│           宿主机 Nginx (deploy/nginx/moling.conf)              │
│        /moling → :3000    /moling/api → :8000                 │
└──────┬─────────────────────────────────┬─────────────────────┘
       │ /moling                         │ /api
┌──────▼──────────────────┐  ┌───────────▼─────────────────────┐
│  frontend 容器 (:3000)   │  │    app 容器 (:8000)             │
│  Nginx + Next.js         │  │    FastAPI + Uvicorn            │
│  standalone              │  │    (4 workers)                   │
└──────────────────────────┘  └───────────┬─────────────────────┘
                                          │
                      ┌───────────────────┼───────────────────┐
                      │                   │                    │
              ┌───────▼──────┐   ┌────────▼────────┐  ┌───────▼──────┐
              │  PostgreSQL  │   │     Redis 7     │  │   Celery     │
              │  17+pgvector │   │  cache+queue    │  │   Worker     │
              └──────────────┘   └─────────────────┘  └──────────────┘
```

### 3.2 技术选型矩阵

| 层次 | 技术 | 版本 | 职责 |
|------|------|------|------|
| **前端框架** | Next.js (App Router) | 15.x | SSR/SSG/路由/代码分割 |
| **前端UI** | React + TailwindCSS | 19.x + 4.x | 组件化 + 原子化样式 |
| **前端语言** | TypeScript | 5.7 | 类型安全 |
| **后端框架** | FastAPI | 0.115+ | RESTful API + 自动文档 |
| **ORM** | SQLAlchemy (async) | 2.0.36+ | 异步数据库操作 |
| **数据库** | PostgreSQL + pgvector | 17 | 主存储 + 向量搜索 |
| **缓存** | Redis | 7 | Token黑名单 + Celery |
| **任务队列** | Celery | 5.5+ | 异步AI生成/导入 |
| **LLM** | DeepSeek (OpenAI兼容) | V3 | AI文本生成 |
| **监控** | Prometheus + Grafana | latest | 指标 + 可视化 |
| **CI/CD** | GitHub Actions | — | 6个自动化管道 |
| **容器化** | Docker Compose | — | 7服务编排 |
| **子路径部署** | Nginx | — | /moling 路径转发 |

### 3.3 数据流

```
用户操作 → React组件 → Context/Hook → api.ts → apiClient.ts
    → HTTP (JWT Bearer Token)
    → Nginx Proxy → FastAPI Router → Service → DAO → SQLAlchemy → PostgreSQL
                                              ↓
                                         Celery Worker → DeepSeek API
                                              ↓
                                         WebSocket/轮询通知前端
```

---

## 4. 前端架构 - moling-web

### 4.1 路由地图 (18个页面)

| 路由路径 | 认证 | 说明 |
|---------|------|------|
| `/` | 可选 | 已登录→项目列表，未登录→落地页 |
| `/auth` | 公开 | 登录/注册/重置密码（Auth Group隔离布局） |
| `/landing` | 公开 | 产品落地页 |
| `/pricing` | 公开 | 定价页面 |
| `/projects` | ✅ | 项目管理列表 |
| `/projects/new` | ✅ | 新建项目（从零/模板/导入） |
| `/projects/[id]/edit` | ✅ | 编辑项目 |
| `/projects/[id]/import` | ✅ | 导入项目内容 |
| `/workspace/[id]` | ✅ | **核心**: 三栏工作台 |
| `/workspace/[id]/health` | ✅ | 项目健康检查 |
| `/workspace/[id]/phase4` | ✅ | Phase 4 收纳状态 |
| `/workspace/[id]/phase4/tasks` | ✅ | Phase 4 任务详情 |
| `/vaults/[id]` | ✅ | 四库管理概览 |
| `/weave` | ✅ | 编织模式总览 |
| `/history` | ✅ | 生成历史 |
| `/import` | ✅ | 导入管理 |
| `/notifications` | ✅ | 通知中心 |
| `/settings` | ✅ | 个人设置 |
| `/admin` | 🔒 管理员 | 管理后台（用户/LLM配置/统计） |

### 4.2 组件体系 (130+组件)

**布局组件**: `AppShell` (响应式三模式切换: 简单页/桌面/移动端), `Sidebar` (280px/56px折叠), `Navbar`, `BottomNav`

**认证组件**: `AuthGuard` (路由守卫), `LoginForm`, `RegisterForm`, `ResetPasswordForm`

**工作台核心**: `Editor` (动态导入), `ChapterSelector`, `LibraryPanel` (四库参考), `AIToolbox` (AI工具箱), `CardModal` (抽卡动画), `GenerationProgress`

**Provider树**: `ThemeProvider → AuthProvider → ProjectProvider → SystemHealthProvider → WorkspaceProvider`

### 4.3 API客户端架构

| 层 | 文件 | 功能 |
|----|------|------|
| **核心HTTP** | `src/lib/apiClient.ts` | Bearer Token注入 + 401自动刷新 + 请求去重缓存 + X-Request-ID追踪 |
| **Token管理** | `src/lib/auth.ts` | JWT读写/过期检查/自动清理 |
| **业务API** | `src/lib/api.ts` (~900行) | 30+业务API模块 (auth/project/chapter/card/generation/vault/health/phase4/weave/admin…) |
| **遗留API** | `src/api/` | 早期fetch封装（待迁移） |
| **Mock** | `src/mock/` | 50+端点完整Mock (离线开发) |

### 4.4 状态管理

- **AuthContext**: 登录/注册/登出/密码重置/DEV MODE免登
- **WorkspaceContext**: 章节/抽卡/AI生成(2秒轮询)/四库数据/健康告警
- **ProjectContext**: 项目CRUD + 统计
- **SystemHealthContext**: 30秒轮询，R1/R2/R3三级健康状态
- **ThemeContext**: 深色/亮色主题持久化

### 4.5 类型系统

`src/lib/types.ts` 约500行完整定义：User, Project, Chapter, CardPool, GenerationTask, 四库实体(Vault*), Notification(7种类型), Phase4Task(9状态机), SecretMatrix, WeavePattern, Template, AdminStats 等。

---

## 5. 后端架构 - moling-server

### 5.1 API路由模块 (18个模块, 150+端点)

| 路由模块 | 前缀 | 端点数量 | 核心功能 |
|---------|------|---------|---------|
| **auth** | `/auth` | 8 | 注册/登录/JWT刷新/登出/密码重置/个人信息 |
| **project** | `/projects` | 10 | CRUD + 统计 + 建议 + 抽卡历史 + 健康告警 |
| **chapter** | `/projects/{id}` | 13 | CRUD + 排序 + 确认/修订 + AI指令 + 生成 |
| **card** | `/projects/{id}` | 8 | 抽卡/重抽/退役/卡池/历史 |
| **vault** | `/projects/{id}/vault` | 22 | 四库CRUD(角色/时间线/伏笔/世界观) + 总览 + 重分析 |
| **generation** | `/generate` | 8 | 异步生成/状态查询/取消/历史 |
| **health** | `/health` | 2 | 系统健康检查 |
| **project_health** | `/projects/{id}` | 2 | 项目健康告警/刷新 |
| **admin** | `/admin` | 8 | LLM配置/统计/用户管理/LLM用量 |
| **notification** | `/notifications` | 5 | 列表/未读数/标记已读/删除 |
| **setting** | `/settings` | 9 | 设置CRUD/改密/导出/缓存/health-monitor/phase4-review |
| **template** | `/templates` | 6 | 模板CRUD + 用模板创建项目 |
| **phase4** | `/phase4` | 10 | 精修建议/应用/任务状态/审核 |
| **subscription** | `/subscriptions` | 5 | 方案/结算/订阅/支付历史 |
| **weave** | `/weave` | 4 | 编织模式/建议/应用/分析 |
| **genre** | `/genre` | 4 | 冷启动预填/确认入库 |
| **secret** | `/projects/{id}/secrets` | 4 | 秘密矩阵查询/更新 |
| **ingest** | `/projects/{id}/import` | 10 | 导入任务/进度查询/分阶段执行 |

### 5.2 数据库模型 (17张表)

| 模型 | 表名 | 用途 |
|-----|------|------|
| User | users | 用户账号 + 偏好设置 |
| Project | projects | 小说项目元数据 |
| Chapter | chapters | 章节内容 + 方向标记 |
| DynamicLayer | dynamic_layers | 每章动态事实层（前情摘要/锚点/秘密矩阵） |
| GenerationTask | generation_tasks | AI生成任务追踪 |
| CardPool | card_pool | 方向卡牌池（含8维算法字段） |
| DrawHistory | draw_history | 抽卡历史快照 |
| VaultCharacter | vault_characters | 四库-角色（含状态机） |
| VaultTimeline | vault_timeline | 四库-时间线事件 |
| VaultPlotPromise | vault_plot_promises | 四库-伏笔/情节承诺 |
| VaultWorld | vault_world | 四库-世界观规则 |
| VaultChangelog | vault_changelog | 四库变更日志（审计追踪） |
| HealthAlert | health_alerts | 项目健康告警 |
| Secret | secrets | 秘密矩阵 |
| Notification | notifications | 用户通知 |
| Plan / UserSubscription | plans / user_subscriptions | 订阅管理 |
| Phase4Task | phase4_tasks | Phase4幂等任务 (10状态机) |
| SystemConfig | system_config | 系统配置键值存储 |
| Template | templates | 项目模板 |

### 5.3 三层架构

```
Router (18 modules)
  │  请求验证 (Pydantic schemas)、路由分发
  ▼
Service (27 modules)
  │  业务逻辑、编排、事务管理
  ▼
DAO (11 modules)
  │  数据库操作封装、查询构建
  ▼
SQLAlchemy Models (17 models)
  │  ORM映射
  ▼
PostgreSQL 17 + pgvector
```

### 5.4 中间件体系 (5层)

```
RequestIDMiddleware      → X-Request-ID 注入（UUID追踪）
CORSMiddleware           → 跨域策略（环境自适应）
SlowAPIMiddleware        → 端点级速率限制
RateLimitMiddleware      → IP级请求频率控制（1000次/60秒）
AuditLogMiddleware       → 审计日志（method/path/user/duration）
ResponseFormatMiddleware → 统一响应包装 {code, message, data, meta}
```

### 5.5 错误体系

- **ErrorCode枚举**: 20个错误码（`HTTP状态码 * 100 + 序号`）
- **AppError基类**: 继承HTTPException，含中文错误消息
- **子类**: NotFoundError, AuthError, PermissionError, ValidationError, RateLimitError, ConflictError, VaultNotFoundError

### 5.6 LLM集成 (`app/llm/`)

- **client.py**: OpenAI兼容HTTP客户端，流式/非流式，自动重试(tenacity)，Token计数
- **key_manager.py**: API密钥池（Pro Pool / Flash Pool），LEAST_USAGE/ROUND_ROBIN策略，自动冷却恢复
- **prompts/**: 提示词模板库

### 5.7 异步生成架构

```
用户请求生成
  → FastAPI BackgroundTasks
  → generation/jobs_store.py (内存任务存储，MVP)
  → Celery Worker (生产环境)
  → DeepSeek API (流式调用)
  → 前端轮询 GET /generate/{task_id}/status (2秒间隔)
```

### 5.8 业务引擎

| 引擎 | 目录 | 管线 |
|------|------|------|
| **拆书引擎** | `app/genre/` | A1黄金三章 → A2角色聚类 → A3钩子密度 → A4节奏曲线 → A5套路归纳 |
| **导入引擎** | `app/ingest/` | Phase 0分章预览 → Phase 1全量四库 → Phase 2动态层 → Phase 3确认写入 |
| **卡牌系统** | `app/service/card_service.py` | 8维算法评分 + 方向抽取 + 卡牌退役 |
| **Phase 4** | `app/service/phase4_service.py` | 自动收纳（IDLE→QUEUED→LOCKING→EXTRACTING→VERIFYING→MERGING→COMMITTING→DONE） |
| **编织模式** | `app/service/weave_service.py` | 跨章节模式识别 + 编织建议 |

### 5.9 Windows兼容性

后端通过以下机制兼容Windows环境：

- `greenlet_spawn` 猴子补丁（线程池替代greenlet）
- `_get_exec_once_mutex` 补丁（事件系统兼容）
- `_SyncAsyncSessionWrapper` 包装器（同步Session → 伪异步）
- 启动时自动检测并创建SQLite表（绕过Alembic）

---

## 6. 部署与基础设施

### 6.1 双层次Docker编排

| 属性 | 开发级 (docker-compose.yml) | 生产级 (docker/docker-compose.yml) |
|------|---------------------------|-----------------------------------|
| **服务数** | 4 | 7 |
| **数据库** | PostgreSQL 16 (端口暴露) | PostgreSQL 17 + pgvector (内网) |
| **Redis** | 无密码 | 密码保护 |
| **监控** | 无 | Prometheus + Grafana |
| **Worker** | 无 | Celery Worker |
| **Nginx** | 无（直接Next.js） | 安全加固版（HTTPS + HSTS + CSP） |
| **安全** | 宽松 | 非root用户 / 最小端口暴露 |

### 6.2 Nginx三套配置

| 配置 | 用途 | 关键特性 |
|------|------|---------|
| `docker/nginx/nginx.conf` | 生产frontend容器 | HTTPS 443 + HSTS + CSP + api代理到app:8000 |
| `moling-web/nginx.conf` | 前端standalone容器 | 子路径 /moling + WebSocket 300s |
| `deploy/nginx/moling.conf` | 宿主机Nginx | 端口8080 + /moling路径转发 |

### 6.3 CI/CD管道 (6个workflow)

| Workflow | 触发条件 | 核心动作 |
|----------|---------|---------|
| **ci.yml** | Push/PR develop, main | 后端测试(pytest) + 前端构建 + lint + OpenAPI校验 |
| **ci-cd.yml** | Push/PR main, workflow_dispatch | 宽松测试 + Docker构建推送 |
| **auto-update-openapi.yml** | Push main + 修改server/** | 自动生成openapi.json并commit |
| **openapi-check.yml** | Push/PR main | OpenAPI JSON合法性校验 |
| **backup-test.yml** | 修改备份脚本/每周cron/手动 | 全量备份+加密+灾备演练 |
| **database-migration-test.yml** | 修改alembic/**或models/** | 迁移回滚幂等性测试 + 灾备 |

### 6.4 备份策略

| 任务 | 频率 | 方式 |
|------|------|------|
| 全量备份 | 每天 02:00 | pg_dump + GPG加密 |
| 增量备份 | 每30分钟 | WAL归档 |
| 备份监控 | 每天 03:00 | 完整性验证 + 通知 |
| 灾备演练 | 每周日 04:00 | 完整恢复演练 + 报告 |

### 6.5 数据库三层策略

| 环境 | 数据库 | 连接字符串 |
|------|--------|-----------|
| 本地开发 | SQLite | `sqlite+aiosqlite:///./moling.db` |
| 开发Docker | PostgreSQL 16 | `postgresql+psycopg://moling:moling@db:5432/moling` |
| 生产MVP | SQLite | `sqlite+aiosqlite:///app/data/moling.db` |
| 生产推荐 | PostgreSQL 17+pgvector | 通过DATABASE_URL切换 |

---

## 7. 监控与运维

### 7.1 可观测性

| 组件 | 端口 | 功能 |
|------|------|------|
| Prometheus | 9090 | 指标采集(15s间隔) + 200h保留 |
| Grafana | 3001 | 可视化仪表板 (moling-overview.json) |
| Sentry | — | 错误监控 + 性能追踪 |
| AuditLog | — | 请求/响应审计日志 |
| Health端点 | /health | 服务健康检查 |

### 7.2 日志策略

- **应用日志**: structlog (结构化日志)
- **审计日志**: AuditLogMiddleware (method/path/user/duration/status)
- **日志轮转**: 自动 10MB 轮转
- **错误日志**: 增强日志(user_id/request_body/IP/traceback)

---

## 8. 关键发现与改进建议

### 🔴 需优先处理

| 问题 | 影响 | 建议 |
|------|------|------|
| **双层API代码** | `src/api/` 与 `src/lib/api.ts` 功能重叠，维护成本高 | 统一迁移到 `src/lib/api.ts`，移除遗留层 |
| **前端API URL不一致** | `.env.example` 无 `/api/v1` 后缀，`.env.local` 有后缀 | 统一规范，在 apiClient 中集中处理 baseURL 拼接 |
| **TypeScript构建跳过错误** | `ignoreBuildErrors: true` 隐藏类型问题 | 逐步修复TS错误，最终启用严格构建 |
| **内存任务存储** | `jobs_store.py` 使用内存存储，重启丢失 | 迁移到 Redis/PostgreSQL 持久化 |

### 🟡 建议优化

| 项目 | 说明 |
|------|------|
| **Token命名不统一** | 旧API用 `moling_token`，新lib用 `access_token`/`refresh_token` |
| **Zod验证闲置** | `apiValidation.ts` 已定义但API调用未使用验证 |
| **Auth方式** | 纯客户端路由守卫(无Next.js Middleware)，可增加服务端保护 |
| **前端全客户端渲染** | 18个路由均为Client Component，可引入RSC优化首屏 |
| **生产默认SQLite** | MVP可用，但需计划PostgreSQL迁移路径 |

### 🟢 做得好的地方

- ✅ 130+组件体系完整，工业级UI架构
- ✅ Mock系统50+端点覆盖，离线开发能力强
- ✅ 防御性编程 (`apiSafety.ts`: safeArray/safeObject)
- ✅ API客户端: Token自动刷新+请求去重+缓存
- ✅ 后端三层架构清晰 (Router→Service→DAO)
- ✅ 中间件体系完善 (6层)
- ✅ 统一错误码 + 中文消息
- ✅ CI/CD 6个管道覆盖质量/部署/备份全流程
- ✅ 备份策略完整 (全量+增量+加密+灾备演练)
- ✅ LLM API密钥池管理 (双池+冷却恢复)
- ✅ Docker多阶段构建 + 非root用户

---

## 附录：数量统计

| 维度 | 数量 |
|------|------|
| 前端路由 | 18个页面 |
| 前端组件 | 130+ |
| 前端Context | 5个 |
| 前端Custom Hooks | 8个 |
| 前端Mock端点 | 50+ |
| 后端路由模块 | 18个 |
| 后端API端点 | 150+ |
| 后端服务 | 27个 |
| 后端DAO | 11个 |
| 后端模型 | 17个 |
| 后端中间件 | 5个 |
| 数据库迁移 | 3个版本 |
| CI/CD工作流 | 6个 |
| Docker服务(生产) | 7个 |
| Docker服务(开发) | 4个 |
| Nginx配置 | 3套 |
