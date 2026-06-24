# 墨灵(Moling) 系统架构说明

> **文档版本**: 2.0.0  
> **最后更新**: 2026-06-24  
> **维护者**: Moling Team  
> **适用人员**: 开发人员、运维人员、架构师

---

## 目录

1. [系统概述](#系统概述)
2. [系统架构图](#系统架构图)
3. [数据流图](#数据流图)
4. [技术栈说明](#技术栈说明)
5. [部署架构](#部署架构)
6. [第三方服务](#第三方服务)
7. [目录结构](#目录结构)
8. [Phase 4 核心架构](#phase-4-核心架构)
9. [安全架构](#安全架构)

---

## 系统概述

**墨灵(Moling)** 是一个 AI 辅助小说创作平台，帮助用户通过 AI 能力进行小说创作、角色设定、情节设计等。

### 核心功能

- 📝 **小说创作**：提供 AI 辅助的小说写作功能
- 👤 **角色管理**：创建和管理小说角色
- 📚 **项目管理**：管理多个小说项目
- 🤖 **AI 生成**：基于 LLM 的内容生成（情节、对话、描述等）
- 📊 **知识库**：存储和管理创作素材

### 架构特点

- **前后端分离**：前端（React 19 + Vite）+ 后端（Rust Axum）+ 桌面壳（Tauri 2）
- **全 Rust 后端**：8 crate workspace，编译为单二进制，零运行时依赖
- **双数据库后端**：SQLite（桌面端 / 单机部署）和 PostgreSQL（生产 / 高并发），SeaORM 抽象层统一访问
- **原生异步**：Tokio 全异步 I/O，无 GIL 限制，原生并发
- **异步任务处理**：Rust 原生 Worker（moling-worker），基于 Redis 任务队列 + Cron 调度器，替代 Celery
- **缓存优化**：Redis 缓存热点数据（bb8-redis 连接池）
- **监控告警**：Tracing 结构化日志（JSON 输出）+ Prometheus + Sentry

---

## 系统架构图

### 整体架构

```mermaid
graph TB
    subgraph "用户层"
        A[用户浏览器]
        B[Tauri 桌面端<br/>Windows / macOS / Linux]
    end

    subgraph "接入层"
        C[Nginx<br/>反向代理<br/>端口:80/443]
    end

    subgraph "应用层 — Rust 8 Crate Workspace"
        D[前端 React 19 + Vite<br/>端口:3000<br/>容器:moling-web]
        E[后端 Rust Axum<br/>端口:8000<br/>二进制:moling-server]
        F[moling-worker<br/>7 Workers<br/>Redis 任务队列 + Cron]
    end

    subgraph "Rust Crate 内部结构"
        subgraph "moling-server (入口)"
            ENTRY[main.rs — 启动 + 优雅关闭]
        end
        subgraph "moling-api (路由层)"
            API[Axum Router 16 模块<br/>8 中间件栈<br/>AppState]
        end
        subgraph "moling-services (业务层)"
            SVC[31 服务模块<br/>merge / card / vault / phase4 / import]
        end
        subgraph "moling-llm (AI 层)"
            LLM[DeepSeek 客户端<br/>Key 轮换器<br/>RateLimitTracker<br/>Prompt 构建]
        end
        subgraph "moling-worker (任务层)"
            WRK[10 Workers<br/>BRPOPLPUSH 队列<br/>3 级优先级<br/>指数退避重试]
        end
        subgraph "moling-auth (认证层)"
            AUTH[JWT + bcrypt<br/>黑名单 + 锁仓<br/>Auth 中间件]
        end
        subgraph "moling-db (数据层)"
            DB_CRATE[SeaORM 实体 22+ 表<br/>DAO 层<br/>迁移脚本]
        end
        subgraph "moling-core (基础层)"
            CORE[配置 / 错误类型<br/>Redis 客户端<br/>日志 / Tracing]
        end
    end

    subgraph "数据层"
        G[(SQLite / PostgreSQL<br/>容器/文件)]
        H[(Redis 7<br/>端口:6379)]
    end

    subgraph "监控层"
        I[Prometheus<br/>指标收集<br/>端口:9090]
        J[Grafana<br/>可视化仪表板<br/>端口:3001]
        K[Sentry<br/>错误追踪<br/>SaaS]
    end

    subgraph "第三方服务"
        L[DeepSeek API<br/>主 LLM]
        M[其他 LLM API<br/>兼容 OpenAI 接口]
    end

    A -->|HTTPS| C
    B -->|直连 HTTP| E
    B -->|WebView| D
    C -->|/| D
    C -->|/api/| E
    D -->|API 请求| E
    E -->|SeaORM| G
    E -->|bb8-redis| H
    E -->|发布任务| F
    F -->|SeaORM| G
    F -->|Redis 队列| H
    F -->|HTTP 请求| L
    F -->|HTTP 请求| M
    E -->|Tracing 指标| I
    I -->|抓取指标| J
    E -->|错误上报| K
    D -->|错误上报| K
```

### 网络拓扑

```mermaid
graph LR
    subgraph "Docker Network: moling-network"
        A[moling-web<br/>3000]
        B[moling-server<br/>8000]
        C[moling-worker<br/>内部]
        D[moling-db<br/>5432 / 文件]
        E[moling-redis<br/>6379]
    end

    A -->|API 请求| B
    B -->|SeaORM| D
    B -->|bb8-redis| E
    C -->|SeaORM| D
    C -->|Redis 队列| E
```

> **SQLite 模式 (桌面端)**: db 为本地文件 `moling.db`，无需独立容器。PostgreSQL 模式（生产）使用独立 `moling-db` 容器。
> **Tauri 桌面端**: 前端 WebView 直连 `http://127.0.0.1:8000`，跳过 Nginx。

### 8 Crate Workspace 依赖图

```mermaid
graph TB
    SERVER[moling-server<br/>二进制入口] --> API[moling-api]
    SERVER --> CORE[moling-core]
    API --> SVC[moling-services]
    API --> AUTH[moling-auth]
    API --> LLM[moling-llm]
    API --> CORE
    SVC --> DB[moling-db]
    SVC --> LLM
    SVC --> AUTH
    SVC --> CORE
    LLM --> CORE
    AUTH --> DB
    AUTH --> CORE
    WRK[moling-worker] --> SVC
    WRK --> DB
    WRK --> LLM
    WRK --> CORE
    DB --> CORE

    style SERVER fill:#e8f5e9,stroke:#4caf50
    style API fill:#e3f2fd,stroke:#2196f3
    style SVC fill:#fff3e0,stroke:#ff9800
    style LLM fill:#f3e5f5,stroke:#9c27b0
    style WRK fill:#fce4ec,stroke:#e91e63
    style AUTH fill:#e0f7fa,stroke:#00bcd4
    style DB fill:#f1f8e9,stroke:#8bc34a
    style CORE fill:#eceff1,stroke:#607d8b
```

---

## 数据流图

### 用户请求流程

```mermaid
sequenceDiagram
    participant U as 用户浏览器 / Tauri 桌面
    participant N as Nginx (80)
    participant W as 前端 (3000)
    participant A as Rust Axum 后端 (8000)
    participant D as SQLite / PostgreSQL
    participant R as Redis
    participant L as DeepSeek API

    U->>N: 1. 请求 / (前端页面)
    N->>W: 2. 反向代理到 :3000
    W->>U: 3. 返回 HTML/JS/CSS

    U->>N: 4. API 请求 /api/v1/...
    N->>A: 5. 反向代理到 :8000
    A->>R: 6. 查询缓存
    alt 缓存命中
        R-->>A: 7a. 返回缓存数据
    else 缓存未命中
        A->>D: 7b. SeaORM 查询数据库
        D-->>A: 8b. 返回数据
        A->>R: 9b. 写入缓存
    end
    A-->>N: 10. 返回 JSON 响应
    N-->>U: 11. 返回响应

    U->>N: 12. AI 生成请求
    N->>A: 13. API 请求
    A->>A: 14. 发布 Redis 任务 (moling-worker)
    A-->>N: 15. 返回任务 ID
    N-->>U: 16. 返回任务 ID

    Note over A,L: Worker 异步处理
    A->>L: 17. 调用 DeepSeek API
    L-->>A: 18. 返回生成结果
    A->>D: 19. SeaORM 保存结果到数据库
```

### 异步任务流程

```mermaid
sequenceDiagram
    participant A as Rust Axum 后端
    participant Q as Redis (任务队列)
    participant W as moling-worker
    participant D as SQLite / PostgreSQL
    participant L as DeepSeek API

    A->>Q: 1. BRPOPLPUSH 发布任务 (task_id)
    Q->>W: 2. Worker 拉取任务
    W->>L: 3. 调用 DeepSeek API
    L-->>W: 4. 返回生成结果
    W->>D: 5. SeaORM 保存结果
    W->>Q: 6. 更新任务状态 (SUCCESS)
    Note over A,W: 前端轮询任务状态
    A->>Q: 7. 查询任务状态
    Q-->>A: 8. 返回任务结果
```

---

## 技术栈说明

### 后端技术栈（Rust — 主线）

| 技术 | 版本 | 用途 | 说明 |
|------|------|------|------|
| **Rust** | 1.85+ (edition 2024) | 编程语言 | 全后端 Rust 重写，零 GIL、编译时类型安全 |
| **Axum** | 0.8 | Web 框架 | 异步 HTTP 框架，Tokio 生态 |
| **Tokio** | 1 | 异步运行时 | 全异步 I/O，原生并发 |
| **SeaORM** | 1.1 | ORM | 异步数据库操作，支持 SQLite + PostgreSQL 双后端 |
| **SQLite** | 3 (via `libsqlite3-sys`) | 默认数据库 | 嵌入式、零配置，桌面端 / 单机部署首选 |
| **PostgreSQL** | 16 + pgvector | 生产数据库 | 高并发、向量搜索支持，生产环境可选 |
| **Redis** | 7 | 缓存 / 任务队列 | bb8-redis 连接池管理 |
| **Tower-HTTP** | 0.6 | 中间件 | CORS、限流、追踪、请求 ID |
| **Reqwest** | 0.12 | HTTP 客户端 | 调用 DeepSeek LLM API，内置重试 |
| **bb8-redis** | 0.17 | Redis 连接池 | 异步连接池管理，多 Worker 共享 |
| **Figment** | 0.10 | 配置管理 | 环境变量 + .env 多层加载 |
| **jsonwebtoken** | 9 | JWT | 用户认证与 Token 轮换 |
| **bcrypt** | 0.16 | 密码哈希 | 用户密码安全存储 |
| **Tracing** | 0.3 | 结构化日志 | JSON 格式输出，集成 OpenTelemetry |
| **Utoipa** | 5 | OpenAPI | API 文档自动生成 |

### 后端技术栈（Python — 遗留支持）

> **状态**: 维护模式，仅修复 Critical Bug。新功能全部在 Rust 主线开发。

| 技术 | 版本 | 用途 | 说明 |
|------|------|------|------|
| **Python** | >= 3.10 | 编程语言 | 原后端开发语言，处于淘汰过渡期 |
| **FastAPI** | >= 0.115.0 | Web 框架 | 原 Web 框架，已被 Axum 替代 |
| **SQLAlchemy** | >= 2.0.36 | ORM | 已被 SeaORM 替代 |
| **Celery** | >= 5.5.0 | 异步任务 | 已被 moling-worker (Rust) 替代 |

> **迁移状态**: Python → Rust 迁移已完成，详见 [ADR-001](./adr/adr-001-python-to-rust.md)。Python 代码仅作为历史参考保留。

#### Rust Crate 架构（8 crates）

```
moling-server-rs/
├── crates/
│   ├── moling-core/        # 配置、错误类型、Redis 客户端、日志
│   ├── moling-db/          # SeaORM 实体（22+ 表）、DAO 层、迁移脚本
│   ├── moling-auth/        # JWT 令牌、密码哈希、黑名单、锁仓、鉴权中间件
│   ├── moling-api/         # Axum 路由（20 模块）、中间件栈、AppState
│   ├── moling-services/    # 业务逻辑（31 服务模块）
│   ├── moling-llm/         # DeepSeek 客户端、Key 轮换器、RateLimitTracker、Prompt 构建
│   ├── moling-worker/      # Redis 任务队列、Cron 调度器、7 个 Worker
│   └── moling-server/      # 二进制入口（main.rs）—— 串联所有 crate
├── Cargo.toml              # Workspace 定义
├── Cargo.lock
└── Makefile
```

#### Worker 架构（10 Workers）

| Worker | 触发方式 | 说明 |
|--------|---------|------|
| **Generation** | 任务队列 (BRPOPLPUSH) | AI 续写生成——P0 核心路径 |
| **Phase4** | 任务队列 (post-confirm) | Phase 4 四库自动收纳 |
| **Coherence** | Cron / 手动 (批量扫描) | 全局连贯性检查 |
| **Vault Reanalyze** | Cron / 手动触发 | 伏笔库重新分析 |
| **Card Retire** | Cron (每日) | 过期卡牌自动退役 |
| **Health Notify** | Cron (每 10min) | 子情节健康度告警 |
| **Import** | 任务队列 (分阶段) | 外部文本导入 |
| **Analysis** | 任务队列 (按需) | 文本结构分析 |
| **Notification** | 任务队列 (异步投递) | 用户通知推送 |

**队列语义**: BRPOPLPUSH — 弹出任务 → 处理中列表 → 完成确认/死信队列
**优先级**: 高/中/低 三级 Redis 列表
**重试**: 最大 3 次，24h TTL

#### Docker 构建与部署

```bash
# 构建镜像
cd moling-server-rs
docker build -t moling-rs:latest -f docker/Dockerfile .

# 运行（SQLite 模式）
docker run -d --name moling-rs -p 8000:8000 \
  -v moling-data:/data \
  -e MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc \
  moling-rs:latest

# 运行（PostgreSQL 模式）
docker run -d --name moling-rs -p 8000:8000 \
  -e MOLING_DATABASE_URL=postgres://user:pass@host:5432/moling \
  -e MOLING_REDIS_URL=redis://host:6379 \
  moling-rs:latest

# 集成测试
docker compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit
```

### 前端技术栈

| 技术 | 版本 | 用途 | 说明 |
|------|------|------|------|
| **Node.js** | >= 18.0.0 | JavaScript 运行时 | 前端开发环境 |
| **React** | ^19.0.0 | UI 库 | 用户界面构建 |
| **Vite** | ^6.x | 构建工具 | 快速 HMR，替代 Next.js 构建 |
| **TypeScript** | ^5.7.0 | 类型系统 | 类型安全开发 |
| **Tailwind CSS** | 4 | CSS 框架 | utility-first，零 CSS Module |
| **zustand** | latest | 状态管理 | 客户端状态，按域拆分 store |
| **TanStack Query** | v5 | 服务端状态 | 缓存 + 自动刷新 |
| **Zod** | ^4.4.3 | 数据验证 | 前端数据验证 |
| **Sentry** | ^10.58.0 | 错误追踪 | 前端错误监控 |
| **Playwright** | ^1.60.0 | E2E 测试 | 端到端测试 |
| **Vitest** | ^4.1.8 | 单元测试 | 单元测试框架 |

> **注意**: 项目已从 Next.js App Router 迁移至 React 19 + Vite。Tauri 桌面端通过 static export + WebView 加载，Web 端通过 Vite dev server / Nginx 部署。

### 基础设施技术栈

| 技术 | 版本 | 用途 | 说明 |
|------|------|------|------|
| **Docker** | 20.10.0+ | 容器运行时 | 应用容器化 |
| **Docker Compose** | 2.0.0+ | 容器编排 | 多容器应用管理 |
| **Nginx** | 1.20+ | 反向代理 | 请求路由和负载均衡 |
| **Prometheus** | latest | 监控 | 指标收集和存储 |
| **Grafana** | latest | 可视化 | 监控仪表板 |
| **Sentry** | SaaS | 错误追踪 | 实时错误监控（云端服务） |

---

## 部署架构

### Docker Compose 两套编排

项目提供两套 Docker Compose 编排，适用于不同场景：

| 文件 | 用途 | 服务数 | 特点 |
|------|------|:------:|------|
| `./docker-compose.yml` | 开发 / 快速部署 | **3** | 仅核心服务（redis, server, web），端口全暴露，便于本地调试 |
| `./docker/docker-compose.yml` | 生产级完整编排 | **7** | 含 Nginx 反向代理、PostgreSQL、Prometheus、Grafana；仅 Nginx 对外暴露端口 |

#### 1. 根目录 docker-compose.yml — 开发 / 快速部署

```yaml
# 启动: docker compose up -d --build
# 访问: http://localhost:3000（前端）| http://localhost:8000/docs（API 文档）

services:
  redis:
    image: redis:7-alpine
    container_name: moling-redis
    ports: ["6379:6379"]
    command: redis-server --appendonly yes

  server:
    build:
      context: ./moling-server-rs
      dockerfile: docker/Dockerfile
    container_name: moling-server
    ports: ["8000:8000"]
    volumes:
      - moling-data:/data
    environment:
      - MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc
      - MOLING_REDIS_URL=redis://redis:6379
    depends_on:
      redis:
        condition: service_healthy

  web:
    build: ./moling-web
    container_name: moling-web
    ports: ["3000:3000"]
    depends_on: [server]
```

#### 2. docker/docker-compose.yml — 生产级完整编排

```yaml
# 启动: docker compose -f docker/docker-compose.yml up -d --build
# 访问: http://localhost（前端 Nginx :80）| http://localhost/api/v1/docs（API 文档）

services:
  frontend:       # Nginx（前端 + API 反向代理）
    build: { context: ../moling-web, dockerfile: Dockerfile }
    container_name: moling-frontend
    ports: ["80:80", "443:443"]

  server:         # Rust Axum 后端（仅 expose，不暴露宿主机端口）
    build:
      context: ../moling-server-rs
      dockerfile: docker/Dockerfile
    container_name: moling-server
    expose: ["8000"]
    environment:
      - MOLING_DATABASE_URL=postgres://user:pass@db:5432/moling
      - MOLING_REDIS_URL=redis://redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}

  worker:         # Rust 原生 Worker（替代 Celery）
    build:
      context: ../moling-server-rs
      dockerfile: docker/Dockerfile
    container_name: moling-worker
    command: /app/moling-worker
    environment:
      - MOLING_DATABASE_URL=postgres://user:pass@db:5432/moling
      - MOLING_REDIS_URL=redis://redis:6379

  db:             # PostgreSQL 16 + pgvector（生产模式）
    image: pgvector/pgvector:pg16
    container_name: moling-db
    # 生产环境不对外暴露端口（ports 注释掉）

  redis:          # Redis 7（带密码持久化）
    image: redis:7-alpine
    container_name: moling-redis
    # 生产环境不对外暴露端口（ports 注释掉）
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}

  prometheus:     # 监控指标收集
    image: prom/prometheus:latest
    container_name: moling-prometheus
    ports: ["9090:9090"]

  grafana:        # 可视化仪表板
    image: grafana/grafana:latest
    container_name: moling-grafana
    ports: ["3001:3000"]    # 宿主机 3001 → 容器内 3000
```

> **提示**：两套编排使用相同的 Docker 网络名 `moling-network`，可在同一主机共存（注意端口冲突）。

### 部署架构图

```mermaid
graph TB
    subgraph "云服务器 (Ubuntu 22.04)"
        subgraph "Docker Engine"
            subgraph "moling-network (bridge)"
                NGINX[Nginx<br/>:80/:443]
                WEB[moling-web<br/>:3000]
                SERVER[moling-server<br/>Rust Axum :8000]
                WORKER[moling-worker<br/>Rust 原生]
                DB[(moling-db<br/>PostgreSQL :5432)]
                REDIS[(moling-redis<br/>:6379)]
                PROM[moling-prometheus<br/>:9090]
                GRAF[moling-grafana<br/>:3001]
            end
        end

        subgraph "宿主机"
            VOLUME1[(pgdata<br/>PostgreSQL 数据)]
            VOLUME2[(redisdata<br/>Redis 数据)]
            VOLUME3[(prometheusdata<br/>Prometheus 数据)]
            VOLUME4[(grafanadata<br/>Grafana 数据)]
        end
    end

    NGINX -->|/| WEB
    NGINX -->|/api/| SERVER
    WEB --> SERVER
    SERVER --> DB
    SERVER --> REDIS
    WORKER --> DB
    WORKER --> REDIS
    SERVER -->|/metrics| PROM
    PROM -->|数据源| GRAF
```

> **桌面端部署 (Tauri)**: 无需 Docker。Rust 后端作为本地进程运行（`moling-server --db sqlite:///moling.db`），Tauri WebView 直连 `http://127.0.0.1:8000`。见 [ADR-002](./adr/adr-002-tauri-vs-electron.md)。

### 端口映射

> **Docker 端口格式**：`"宿主机:容器"`（如 `"3001:3000"` 表示宿主机 3001 → 容器内 3000）

| 服务 | 容器内端口 | 宿主机端口 | Docker 映射 | 说明 |
|------|:----------:|:----------:|-------------|------|
| Nginx (frontend) | 80, 443 | 80, 443 | `80:80`, `443:443` | 反向代理入口（仅生产编排） |
| moling-web | 3000 | 3000 | `3000:3000` | 前端 React + Vite |
| moling-server | 8000 | 8000 | `8000:8000` | 后端 Rust Axum（开发编排暴露；生产编排仅 `expose`） |
| moling-worker | — | — | 无端口 | Rust 原生 Worker（仅生产编排） |
| moling-db | 5432 | 5432 | `5432:5432` | PostgreSQL（开发编排暴露；生产编排注释掉 ports） |
| moling-redis | 6379 | 6379 | `6379:6379` | Redis（开发编排暴露；生产编排注释掉 ports） |
| Prometheus | 9090 | 9090 | `9090:9090` | 监控指标收集（仅生产编排） |
| Grafana | 3000 | 3001 | `3001:3000` | 可视化仪表板（仅生产编排） |

> **安全建议**：生产环境中仅暴露 Nginx 端口（80/443），其他服务只在 Docker 网络内访问。根目录 `docker-compose.yml` 为开发便利暴露了所有端口，**切勿直接用于生产**。

---

## 第三方服务

### LLM API

| 服务 | 用途 | 配置项 | 说明 |
|------|------|--------|------|
| **DeepSeek API** | 主 AI 内容生成 | `LLM_API_KEY` | deepseek-chat、deepseek-reasoner 等模型 |
| **其他 LLM** | 备用/成本优化 | `LLM_API_KEY`<br/>`LLM_BASE_URL` | 支持 OpenAI 兼容接口的其他 LLM |

**配置示例**：

```bash
# moling-server-rs/.env
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 双池模式（Pro + Flash）
# LLM_PRO_KEYS=sk-k1,sk-k2   # Pro Pool
# LLM_FLASH_KEYS=sk-f1,sk-f2 # Flash Pool
```

### Token 预算管理 (RF2.10)

> **状态**: ✅ 已实现 — 2026-06-21  
> **Rust 实现**: `moling-llm/crates/client.rs` (TokenBudgetManager)

**功能**: 基于 Redis 持久化的 Token 用量追踪与预算控制，多 Worker 进程间共享预算状态。

| 特性 | 说明 |
|------|------|
| **持久化** | Redis Sorted Set (`moling:token_budget:*`) 按日分区 |
| **预算上限** | `TOKEN_BUDGET_LIMIT` 环境变量配置（默认 1,000,000 tokens/天） |
| **多用户** | 按 `user_id` 维度独立追踪 |
| **超限处理** | `_check_budget()` 前置检查，超限立即拒绝并返回 429 |
| **异步接口** | `track_usage()` / `check_budget()` / `get_budget_status()` 均为 async |
| **进程重启** | Redis 持久化确保数据不丢失 |

**Redis Key 格式**:
```
moling:token_budget:{user_id} → Sorted Set
  score: Unix timestamp
  member: {timestamp_ms}:{tokens}
```

**配置**:
```bash
# .env
TOKEN_BUDGET_LIMIT=1000000    # 默认 100 万 tokens/天
```

### Sentry (错误追踪)

| 项目 | 说明 |
|------|------|
| **Sentry Org** | moling |
| **Sentry Project (后端)** | moling-server |
| **Sentry Project (前端)** | moling-web |
| **配置项** | `SENTRY_DSN` |

**配置示例**：

```bash
# moling-server/.env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# moling-web/.env.local
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

**访问地址**：
- 后端项目：https://sentry.io/organizations/moling/issues/
- 前端项目：https://sentry.io/organizations/moling/issues/

### pgBackRest (数据库备份)

> **注意**：当前项目尚未配置 pgBackRest，以下是推荐配置。

| 功能 | 说明 |
|------|------|
| **全量备份** | 每周一次 |
| **增量备份** | 每天一次 |
| **归档备份** | WAL 日志归档 |
| **远程存储** | 支持 S3、Azure、GCS 等 |

**推荐配置**：

```bash
# 安装 pgBackRest
sudo apt-get install pgbackrest

# 配置 /etc/pgbackrest.conf
[moling]
pg1-path=/var/lib/postgresql/data
backup-path=/var/backups/pgbackrest
backup-user=postgres
log-path=/var/log/pgbackrest

# 创建备份定时任务
0 2 * * * pgbackrest --stanza=moling backup
```

---

## 目录结构

### 项目根目录

```
MolingProject/
├── moling-server-rs/           # 后端项目 (Rust/Axum) — 主线 ★
│   ├── crates/                # Rust 8 crate workspace
│   │   ├── moling-core/       # 核心：配置、错误类型、Redis 客户端、日志
│   │   ├── moling-db/         # 数据库：SeaORM 实体(22+表)、DAO 层、迁移脚本
│   │   ├── moling-auth/       # 认证：JWT、密码哈希、黑名单、锁仓、鉴权中间件
│   │   ├── moling-api/        # API：Axum 路由(16 模块)、中间件栈、AppState
│   │   ├── moling-services/   # 服务：31 个业务逻辑模块
│   │   ├── moling-llm/        # LLM：DeepSeek 客户端、Key 轮换器、RateLimitTracker
│   │   ├── moling-worker/     # Worker：Redis 任务队列、Cron 调度器(10 Workers)
│   │   └── moling-server/     # 入口：main.rs 全启动流程 + 优雅关闭
│   ├── docker/                # Docker 配置（多阶段构建 + 测试编排）
│   ├── Cargo.toml             # Workspace 依赖管理
│   ├── Cargo.lock
│   ├── .env.example           # 环境变量模板
│   └── Makefile               # 构建/测试/运行命令
├── moling-server/              # 后端项目 (Python/FastAPI) — 遗留 ★
│   ├── app/                   # 应用代码（维护模式，仅修 Critical Bug）
│   ├── alembic/               # 数据库迁移脚本（遗留）
│   ├── tests/                 # 单元测试
│   └── pyproject.toml        # Python 项目配置
├── moling-web/                # 前端项目 (React 19 + Vite)
│   ├── src/                   # 源代码
│   │   ├── app/               # 路由页面
│   │   ├── components/        # React 组件 (ui/ + business/ + page/)
│   │   ├── stores/            # zustand 状态管理
│   │   ├── lib/               # 工具函数 + HTTP 客户端
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── mock/              # Mock 数据（开发阶段）
│   ├── src-tauri/             # Tauri 2 桌面端配置
│   │   ├── tauri.conf.json    # 窗口配置、CSP、打包参数
│   │   ├── Cargo.toml         # Tauri Rust 依赖
│   │   ├── src/               # Rust 入口 + 自定义命令
│   │   └── capabilities/      # 权限声明
│   ├── public/                # 静态资源
│   ├── index.html             # Vite 入口
│   ├── vite.config.ts         # Vite 配置
│   ├── package.json           # npm 依赖
│   └── tsconfig.json          # TypeScript 配置
├── docker/                    # Docker 配置
│   ├── docker-compose.yml     # 生产级完整编排
│   ├── nginx/                 # Nginx 配置
│   ├── prometheus.yml         # Prometheus 配置
│   └── grafana/              # Grafana 配置
├── docs/                      # 项目文档
│   ├── ARCHITECTURE.md        # 系统架构（本文档）
│   ├── DESIGN.md             # 前端设计规范
│   ├── SPECIFICATIONS.md     # 功能规格
│   ├── DEPLOYMENT.md         # 部署指南
│   └── adr/                  # 架构决策记录
│       ├── adr-001-python-to-rust.md
│       ├── adr-002-tauri-vs-electron.md
│       └── adr-003-sqlite-vs-postgresql.md
└── .github/                   # GitHub 配置
    └── workflows/             # CI/CD 流水线
```

---

## Phase 4 核心架构

### 状态机

Phase 4 是墨灵的核心流水线：从 LLM 提取章节变更 → 逐库合并 → 事务提交。完整状态定义如下：

```
IDLE → QUEUED → LOCKING → EXTRACTING → VERIFYING → MERGING → COMMITTING → DONE
                 ↓           ↓            ↓          ↓         ↓
               RETRY       RETRY        RETRY      RETRY     FAILED
                 ↓
               ⏎ (回补到 QUEUED，最多 5 次)
                 5 次后 → FAILED
```

| 状态 | 说明 |
|------|------|
| `IDLE` | 初始状态，等待任务 |
| `QUEUED` | 已入队列 |
| `LOCKING` | 获取分布式锁 |
| `EXTRACTING` | 调用 LLM 提取变更 |
| `VERIFYING` | SourceText Grounding 验证（防幻觉） |
| `MERGING` | 四库合并（人物/时间线/承诺/世界观） |
| `COMMITTING` | 事务提交 |
| `DONE` | 完成 |
| `FAILED` | 失败（不可恢复） |
| `RETRY` | 可重试失败（指数退避） |

### 分布式锁

使用 Redis SET NX EX 实现项目级写锁，防止同一项目并发写入：

- **Key**: `phase4:lock:{project_id}`
- **TTL**: 30s（自动过期防死锁）
- **轮询策略**: 每 200ms 重试，最多 15 次（总超时 3s）
- **释放**: 仅锁持有者（通过 `scheduler_id` 验证）可释放

### 幂等性（三层防护）

| 层 | 范围 | 机制 |
|:--:|------|------|
| L1 | 内存 | in-memory nonce LRU 缓存（最多 1000 条） |
| L2 | 数据库 | `Phase4Task.nonce` UNIQUE 约束 |
| L3 | 业务 | 幂等键 `chapter_id + chapter_text_hash` |

### 失败回补

指数退避重试，防止瞬时故障导致任务失败：

| 重试次数 | 等待间隔 |
|:--------:|----------|
| 第 1 次 | 10s |
| 第 2 次 | 30s |
| 第 3 次 | 60s |
| 第 4 次 | 120s |
| 第 5 次 | 300s |
| 超过 5 次 | 标记 FAILED，通知用户 |

### Phase4 调度器与存储（2026-06-22 新增）

#### Phase4Scheduler（Actor 模式）

独立 tokio task，通过 mpsc channel 接收 Phase4Task：

```text
Phase4Scheduler (独立 tokio task)
  ├── mpsc::Receiver<Phase4Task>  — 输入通道
  ├── Phase4Store                — nonce 去重 + 分布式锁
  ├── tokio::sync::Semaphore     — 并发限制（默认 3）
  ├── 指数退避重试               — [10, 30, 60, 120, 300]s，最多 5 次
  └── SourceText Grounding       — 编辑距离验证（阈值 85%）
```

#### Phase4Store（双模后端）

Redis 优先（跨 Worker 耐久协调），内存回退（单 Worker 开发）：

| 操作 | Redis 后端 | 内存后端 |
|------|-----------|---------|
| Nonce 去重 | SADD / SISMEMBER | Vec<String> + LRU 缓存 |
| 分布式锁 | SET NX EX + owner 验证 | RwLock<HashMap> |
| 任务状态 | SETEX（TTL 1h） | HashMap |

#### Genre 服务（拆书引擎）

从 Python `app/genre/` 移植的 A1→A5 分析管线：

- **A1** Opening: 黄金三章模式识别（冲突/日常/倒叙/设定），4 种评分
- **A2** Characters: 滑动窗口 n-gram 中文姓名提取 + 频率聚类
- **A3** Hooks: 钩子密度量化（hook 标记 + cliffhanger 检测）
- **A4** Rhythm: 节奏曲线拟合（fast_paced / balanced / slow_burn）
- **A5** Profile: 套路归纳 → GenreProfile（含卡牌充实 + 动态层种子）
- **ColdStartLoader**: 6 种预置体裁原型（fantasy/wuxia/xianxia/urban/scifi/romance）

### 事务边界

```
LLM 调用（事务外，可重试，不浪费 token）
    ↓
savepoint ─ 四库合并写入
          ├─ 卡牌充实
          ├─ 卡牌淘汰
          └─ 变更日志
    ↓
savepoint 失败 → 回滚到 savepoint（保留 LLM 结果）
    ↓
db.commit() → 全部成功
```

详细规格见 `docs/SPECIFICATIONS.md`。

### Phase 4 已知技术债（扫描 v4，2026-06-21）

> **扫描范围**: 15 文件 ~9000 行 | **加权总分**: 71.5/100 (B 级)  
> **报告完整版**: `docs/reports/scan-v4-phase4.md`

#### Critical (P0 — 必须修复)

| ID | 问题 | 影响 | 位置 | 状态 |
|----|------|------|------|:--:|
| P2-2 | Redis 释放锁无 owner 验证 | 可能误删其他 Worker 持有的锁 | `phase4_store.py:107-108` | ✅ |
| P9-2 | R2 健康规则 `event_type` → `event` 字段名错误 | R2 告警永不被触发 | `health_monitor.py` | ✅ |
| P5-3 | `consecutive_failures` 全局共享受影响跨项目告警 | 项目 A 失败导致项目 B 收到错误告警 | `phase4_scheduler.py` | ✅ |
| P6-4 | stale 检查只看 `planted_chapter` 忽略 `advancement_log` | 已推进承诺被误标 stale | `merge_service.py:758,864` | ✅ |

#### High (P1 — 强烈建议)

| ID | 问题 | 影响 | 位置 |
|----|------|------|------|
| P1-3 | `state`(Phase4State enum) 与 `status`(str) 双状态系统：多处同时更新但可能不一致 | 状态查询不可靠 | `phase4_task.py` 模型 + `phase4_service.py` |
| P7-2 | 两套 LLM 提取体系：`execute_storage` 走 `_analyze_chapter_content`（旧版），`run_phase4` 走 `_call_extraction_llm`（新版） | 提取结果结构不一致，维护成本翻倍 | `phase4_service.py` |
| P11-1 | 导入引擎无 BulkInserter：章节创建逐条 `db.add()`，1000+ 章导入性能差 | 大型导入极慢 | `import_service.py:327-339` |
| P11-2 | 导入引擎无 savepoint 事务回滚保护：第 50/100 章失败时前 49 章状态不确定 | 数据安全风险 | `import_service.py` |

#### 修复优先级

```
P2-2 (锁安全) → P9-2 (R2 失效) → P5-3 (全局计数器)
    ↓
P11-1 → P11-2 (导入引擎) → P1-3 (双状态) → P7-2 (两套提取)
```

所有修复完成后目标分数：**85+/100 (A 级)**

---

## 安全架构

### Core/Middleware 已知技术债（扫描 v4，2026-06-21）

> **扫描范围**: core/ + middleware/ + 上下文文件 | **发现**: 4 CRITICAL, 6 HIGH, 7 MEDIUM, 12 LOW  
> **报告完整版**: `docs/reports/scan-v4-core.md`

#### Critical (P0)

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| C1 | greenlet 补丁块中引用未定义的 `logger` — Windows 启动时 NameError | `dependencies.py:41,65` | Windows 应用完全不可用 | ✅ |
| C2 | 审计日志无条件 `await request.body()` — 全量缓冲至内存 | `audit_log.py:67-70` | OOM 攻击向量 |
| C3 | ResponseFormat 全量缓冲响应体 — 流式 SSE/文件下载不可用 | `response_format.py:46-61` | 文件下载 OOM，SSE 完全不可用 |
| C4 | 纯内存限流 — 多 Worker 独立计数 | `rate_limit.py:38-39` | 限流形同虚设（实际=配置×worker数） |

#### High (P1)

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| H1 | 审计日志敏感数据过滤仅检查 query string | `audit_log.py:161` | Token/API Key 明文泄露到日志 |
| H2 | 日志路径/轮转/保留全部硬编码 | `audit_log.py:15-55` | 运维不可控 |
| H3 | 审计日志仅按时间轮转无大小保护 | `audit_log.py:31` | 磁盘写满风险 |
| H4 | Content-Length limit 与 config 脱节 | `content_length_limit.py:16` vs `main.py:166` | 修改配置不生效 |
| H5 | SECRET_KEY validator 依赖 Pydantic 字段声明顺序 | `config.py:174-177` | 生产可能用弱密钥 | ✅ |
| H6 | PostgreSQL 连接池缺 pool_recycle/pool_pre_ping | `dependencies.py:127-132` | 空闲连接过期异常 | ✅ |

#### 修复优先级

```
C1 (Windows 崩溃) → C2/C3 (OOM) → C4 (限流)
    ↓
H1 (敏感数据) → H5 (弱密钥) → H6 (连接池) → H2-H4 (运维化)
```

### 认证安全已知技术债（扫描 v4，2026-06-21）

> **扫描范围**: config.py/auth_service.py/blacklist.py/dependencies.py | **发现**: 3 P0, 3 P1  
> **报告完整版**: `docs/reports/scan-v4-security.md`

#### P0 (立即修复)

| ID | 问题 | 位置 | 影响 | 状态 |
|----|------|------|------|:--:|
| S1 | Access Token 硬编码 `timedelta(minutes=15)` 忽视 `ACCESS_TOKEN_EXPIRE_MINUTES` 配置 | `auth_service.py:52` | 配置修改不生效，Token 过期时间不可控 | ✅ |
| S2 | Refresh Token 硬编码 `timedelta(days=30)` 忽视 `REFRESH_TOKEN_EXPIRE_DAYS=7` 配置 | `auth_service.py:67` | 实际有效期是配置的 4 倍，扩大泄露窗口 | ✅ |
| S3 | 密码策略不足：无账户锁定、无复杂度要求（允许 `12345678`）、无密码历史、无强度检查 | `auth_service.py` | 暴力破解风险 + 弱密码风险 |

#### P1 (尽快修复)

| ID | 问题 | 位置 | 影响 |
|----|------|------|------|
| S4 | 黑名单降级策略：Redis 不可用时 `is_blacklisted()` 返回 False | `auth/blacklist.py` | 所有已登出 Token 仍然有效 | ✅ |
| S5 | RBAC 不成熟：`status` 字段既是账户状态又是角色 | `models/user.py` | 权限模型脆弱，无法扩展 |
| S6 | python-jose 维护停滞（最后更新 2021） | `dependencies.py` | 建议迁移 PyJWT |

#### 修复优先级

```
S1/S2 (Token 过期) → S3 (密码策略) → S4 (黑名单降级) → S5 (RBAC) → S6 (jose→PyJWT)
```

### LLM 集成深度修复（扫描 v4，2026-06-21）

> **扫描范围**: `app/llm/` 6 文件（client.py/key_manager.py/context_budget.py/prompts.py） | **发现**: 2 CRITICAL, 2 HIGH, 4 MEDIUM  
> **报告完整版**: `docs/reports/scan-v4-llm.md`  
> **全部修复时间**: 2026-06-21 03:30

| ID | 严重度 | 问题 | 位置 | 影响 | 状态 |
|----|:--:|------|------|------|:--:|
| L1 | CRITICAL | Token 预算绕过：`_chat_stream` 流式请求不调用 `budget_manager.record_usage()` | `client.py:579` | 流式请求 Token 完全不记入预算 | ✅ |
| L2 | CRITICAL | `ContextBudget` 完整实现但 LLMClient 从未调用 | `context_budget.py` | Prompt 可能超过模型上下文窗口 | ✅ |
| L3 | HIGH | KeyManager `_recover_key` 后 backoff_level 不重置 | `key_manager.py` | 已恢复 Key 下次瞬时错误直接进 300s 冷却 | ✅ |
| L4 | HIGH | `get_effective_llm_config()` 硬编码 default，永远不读 `LLM_MODEL` | `config.py:263` | 配置修改不生效 | ✅ |
| M1 | MEDIUM | `prompts.py` 中 Prompt 模板无版本号管理 | `prompts.py` | 迭代时难以追溯变更 | ⬜ |
| M2 | MEDIUM | 缺少 LLM 响应 schema validation | `client.py` | 格式错误静默传播 | ⬜ |
| M3 | MEDIUM | 流式响应无 timeout 超时处理 | `client.py` | 长连接无保护 | ⬜ |
| M4 | MEDIUM | KeyManager 缺少 key 级别的并发锁 | `key_manager.py` | 高并发下可能重复选 key | ⬜ |

**修复详情**:
- **L1** (`client.py:584`): 流式路径新增 `budget_manager.record_usage()` + `report_success()`
- **L2** (`client.py`): `__init__` 中初始化 `ContextBudget` 实例，`chat()` 中调用 `check()` 做上下文窗口监测
- **L3** (`key_manager.py:257`): `_recover_key()` 中 `health.backoff_level = 0`
- **L4** (`config.py:263`): `get_effective_llm_config()` 正确读取 `_OVERRIDES.get("llm_model") or s.LLM_MODEL`

---

## 安全架构 (继续)

### 配置管理

> **Rust 实现**: `moling-core/src/config.rs` (Figment)

所有运行时配置通过 Figment 统一管理，支持环境变量 + `.env` 文件 + 默认值三层优先级。

| 配置项 | 环境变量 | 默认值 | 用途 |
|--------|---------|--------|------|
| `MOLING_DATABASE_URL` | `MOLING_DATABASE_URL` | `sqlite:///moling.db?mode=rwc` | 数据库连接串 |
| `MOLING_REDIS_URL` | `MOLING_REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `REDIS_PASSWORD` | `REDIS_PASSWORD` | `None` | Redis 密码 |
| `SECRET_KEY` | `SECRET_KEY` | (dev default, 生产强制覆盖) | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access Token 过期时间（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 过期时间（天） |
| `LLM_API_BASE` | `LLM_API_BASE` | `https://api.deepseek.com` | LLM API 地址 |
| `LLM_API_KEY` | `LLM_API_KEY` | (placeholder) | LLM API 密钥 |
| `LLM_MODEL` | `LLM_MODEL` | `deepseek-chat` | 默认 LLM 模型 |
| `CORS_ORIGINS` | `CORS_ORIGINS` | `localhost:3000,5173` | 允许的跨域来源 |
| `MAX_BODY_SIZE` | `MAX_BODY_SIZE` | `10MB` | 最大请求体大小 |
| `RATE_LIMIT_CALLS` | `RATE_LIMIT_CALLS` | `1000` | 限流周期内最大请求数 |
| `RATE_LIMIT_PERIOD` | `RATE_LIMIT_PERIOD` | `60` | 限流周期（秒） |
| `LLM_PRO_KEYS` | `LLM_PRO_KEYS` | `[]` | Pro API Key 池（逗号分隔） |
| `LLM_FLASH_KEYS` | `LLM_FLASH_KEYS` | `[]` | Flash API Key 池（逗号分隔） |
| `KEY_SELECT_STRATEGY` | `KEY_SELECT_STRATEGY` | `LEAST_USAGE` | Key 选择策略 |
| `SENTRY_DSN` | `SENTRY_DSN` | `None` | Sentry 错误追踪 DSN |
| `ENVIRONMENT` | `ENVIRONMENT` | `development` | 运行环境 |
| `TOKEN_BUDGET_LIMIT` | `TOKEN_BUDGET_LIMIT` | `1000000` | 每日 Token 预算上限 |

**安全验证器**:
- 生产环境 `SECRET_KEY` 不能使用默认值 → 启动时拒绝
- 生产环境 `CORS_ORIGINS` 包含 `*` → 警告
- `LLM_API_KEY` 为 placeholder → 警告
- `REDIS_PASSWORD` 未设置（非 dev）→ 警告
- `DATABASE_URL` 包含弱密码 → 警告

### Worker 定时调度（Rust Cron）

> 替代 Celery Beat，在 Rust 中实现，免外部 cron 触发。

4 个周期性任务通过 `moling-worker` Cron 调度器自动执行：

| 任务 | 调度周期 | 用途 |
|------|---------|------|
| `phase4-auto-advance` | 每小时 | 扫描自动审核项目，触发 Phase 4 分析 |
| `vault-periodic-reanalyze` | 每 6 小时 | 对近期活跃项目触发 Vault 重分析 |
| `card-retire-check` | 每天 | 检查卡片池新鲜度，标记过期卡片 |
| `health-auto-notify` | 每 30 分钟 | 活跃项目健康检查，生成 HealthAlert |

**启动命令**:
```bash
# 开发模式（包含 Cron 调度器）
cd moling-server-rs
cargo run --bin moling-server

# 生产模式（独立 Worker 进程 + Cron）
./moling-server --with-worker --with-cron
```

### 健康检查

> **Rust 实现**: `moling-api/health.rs`

`GET /api/v1/health` 端点验证三方依赖连通性：

| 检查项 | 方法 | 超时 |
|--------|------|------|
| **Database** | `SELECT 1` (SeaORM) | 继承 pool 超时 |
| **Redis** | `PING` | 3s 连接超时 |
| **Worker** | 内部健康报告 | 3s 超时 |

返回状态：`ok`（全部通过）或 `degraded`（任一失败）。`degraded` 时 `message` 字段列出失败的依赖。

### 子情节健康监控服务

> **新增于 2026-06-21 R1+R2 架构加固**

`app/service/health_monitor.py` 对活跃项目的剧情承诺（plot promises）执行三级预警检测，**纯算法/SQL 实现，零 LLM 成本**：

| 级别 | 触发条件 | 严重程度 | 行为 |
|:----:|----------|:--------:|------|
| **R1 (黄)** | 连续 8 章无对应 promise 推进 | 🟡 低 | 生成 HealthAlert，通知用户关注 |
| **R2 (橙)** | 连续 4+ 次同类型 promise 重复推进 | 🟠 中 | 生成 HealthAlert + 建议 plot 结构调整 |
| **R3 (红)** | 连续 10 章静默（promise 完全无提及） | 🔴 高 | 先检查最新章节关键词提及 → 若提及则**降级为 R1**；若无提及则生成严重告警 |

**防疲劳过滤**: 同一 `(promise_id, rule)` 组合在 3 章内最多触发 1 次，防止重复扰民。

**章级增量算法**: 每次检测只对比当前章节与历史推进记录，不重新分析全部历史章节——时间复杂度 O(1) 而非 O(n)。

### AppError 错误处理体系

> **新增于 2026-06-21 R1+R2 架构加固**

统一错误处理取代散落的 `HTTPException` 直接抛出：

| 层 | 组件 | 说明 |
|:--:|------|------|
| **枚举** | `ErrorCode` (IntEnum) | 数字编码 = `HTTP状态码 × 100 + 序号`（如 `40101`, `50001`），机器可读 |
| **消息** | `_ERROR_MESSAGES` 字典 | 每个 ErrorCode 对应中文可读消息 |
| **映射** | `_ERROR_TO_STATUS` 字典 | ErrorCode → HTTP 状态码自动映射 |
| **基类** | `AppError(HTTPException)` | 统一基类，接收 `ErrorCode` + 可选 `detail` 覆盖消息 |
| **子类** | `NotFoundError`, `AuthError`, `PermissionError`, `ValidationError`, `RateLimitError`, `ConflictError`, `VaultNotFoundError` | 语义化子类，方便 try/except 精确捕获 |

**调用契约**:
```python
# 旧: raise HTTPException(status_code=404, detail="项目不存在")
# 新: raise NotFoundError(ErrorCode.PROJECT_NOT_FOUND)
# 需要附加信息时:
raise NotFoundError(ErrorCode.PROJECT_NOT_FOUND, detail=f"项目 {project_id} 已被删除")
```

**全局异常处理器** (`app/main.py`): 捕获所有 `AppError` 子类，统一格式化为 `{"code": 40101, "message": "...", "data": null}` 响应，并自动调用 `_write_error_log()` 记录结构化日志。

### Content-Length 请求体限制

> **新增于 2026-06-21 R1+R2 架构加固**

`app/middleware/content_length_limit.py` 在 ASGI 层前置拦截超大请求体，**在读取 body 之前**就根据 `Content-Length` 头拒绝，防止内存攻击：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEFAULT_MAX_SIZE` | 10MB (`10 * 1024 * 1024`) | 默认最大请求体大小 |
| `excluded_paths` | `("/api/v1/import/upload",)` | 排除路径（如文件上传需要更大尺寸） |

413 响应格式: `{"code": 41301, "message": "请求体过大", "data": null, "meta": {"max_size": 10485760, "request_id": "..."}}`

### Worker 可靠性链路

> **Rust 实现**: `moling-worker/` crate

Rust 原生 Worker 配置经过生产级加固：

| 加固项 | 实现 | 作用 |
|--------|------|------|
| **超时控制** | Tokio `timeout()` 600s (硬), 540s (软) | 防止任务永久挂起 |
| **延迟确认** | BRPOPLPUSH 模式 — 完成确认后才出队 | Worker 崩溃不丢任务 |
| **预取控制** | 每次 BRPOPLPUSH 取 1 个任务 | 防止长任务堆积 |
| **队列分离** | 高/中/低 三级 Redis 列表 | LLM 任务不阻塞常规任务 |
| **故障恢复** | 死信队列 + 24h TTL | 未确认任务重新入队 |
| **内存泄漏防护** | 进程级隔离（独立二进制） | 任务间无共享内存泄漏 |
| **序列化安全** | JSON 序列化 | 防止反序列化攻击 |

**队列语义**: BRPOPLPUSH — 弹出任务 → 处理中列表 → 完成确认/死信队列
**重试策略**: 最大 3 次，指数退避 [10, 30, 60, 120, 300]s

**三层异常处理**:
```
Tokio timeout (软超时) → 重新投递
    ↓
可重试异常 (ConnectionError, TimeoutError, DBError) → 自动重试
    ↓
通用 Exception → 记录 Tracing 日志，标记任务 FAILED
```

### 跨平台支持

> **Rust 原生跨平台**: Rust 编译为原生二进制，Windows / macOS / Linux 均可直接运行，无需 Python 运行时或 greenlet 补丁。

| 平台 | 部署方式 | 说明 |
|------|---------|------|
| **Windows** | Tauri .msi 安装包 | 桌面端首选，内嵌 Rust 后端进程 |
| **macOS** | Tauri .dmg | macOS 桌面端，代码签名 + 公证 |
| **Linux** | Tauri .AppImage / Docker | 桌面端 + 服务器端均可 |
| **Docker** | Linux x86_64 容器 | 生产环境标准部署方式 |

> **注意**: 原有 Python 后端的 Windows 适配（greenlet 猴子补丁 / `_SyncAsyncSessionWrapper` 等）已随 Python → Rust 迁移废弃。参见 [ADR-001](./adr/adr-001-python-to-rust.md)。

### 认证和授权

```mermaid
sequenceDiagram
    participant U as 用户
    participant A as Rust Axum 后端
    participant D as SQLite / PostgreSQL

    U->>A: 1. 登录请求 (email + password)
    A->>D: 2. SeaORM 查询用户
    D-->>A: 3. 返回用户信息
    A->>A: 4. 验证密码 (bcrypt)
    A->>A: 5. 生成 JWT Token (jsonwebtoken)
    A-->>U: 6. 返回 JWT Token

    U->>A: 7. API 请求 (Authorization: Bearer <token>)
    A->>A: 8. 验证 JWT Token (moling-auth 中间件)
    alt Token 有效
        A->>A: 9a. 解析用户 ID
        A->>D: 10a. SeaORM 查询数据
        D-->>A: 11a. 返回数据
        A-->>U: 12a. 返回响应
    else Token 无效/过期
        A-->>U: 9b. 返回 401 Unauthorized
    end
```

### 安全措施

| 措施 | 说明 | 配置位置 |
|------|------|----------|
| **HTTPS** | 使用 SSL 证书加密传输 | Nginx 配置 |
| **JWT 认证** | 无状态认证 + Token 轮换 | `moling-auth` crate |
| **密码哈希** | 使用 bcrypt 加密密码 | `bcrypt` crate |
| **CORS 配置** | 限制跨域请求来源 | Tower-HTTP CORS 中间件 |
| **Rate Limiting** | API 速率限制（防止滥用） | Tower-HTTP 限流中间件 |
| **输入验证** | 使用 Serde 反序列化 + 自定义 validator | `moling-api` schemas |
| **SQL 注入防护** | SeaORM 参数化查询（编译时安全） | SeaORM |
| **XSS 防护** | React 自动转义 + CSP 头 | React + Nginx |
| **Sentry 监控** | 实时错误监控和告警 | Sentry SDK (前端 + tracing 集成) |
| **请求体限制** | Tower-HTTP ContentLengthLimit 中间件（10MB） | `moling-api` 中间件栈 |

### Refresh Token 轮换

> **Rust 实现**: `moling-auth/token_service.rs`

登录接口返回 `access_token` + `refresh_token`，`POST /api/v1/auth/refresh` 端点实现轮换逻辑：
- 验证 refresh token → 签发新 access token + 新 refresh token
- 旧 refresh token 加入 Redis 黑名单（TTL = 原过期时间）
- 防止 refresh token 泄露后的长期滥用

---

## DAO 层设计规范

> **Rust 实现**: `moling-db/src/dao/`

所有 DAO 子类统一行为规范：

| 规范 | 实现 | 目的 |
|------|------|------|
| **泛型类型** | Rust trait + 泛型参数 | 编译时类型安全 |
| **limit 钳制** | `DEFAULT_MAX_LIMIT = 500` / `_CURSOR_MAX_LIMIT = 200` | 防止 `?limit=999999` 拖垮数据库 |
| **软删除约定** | `include_deleted: bool = false` 默认过滤 | 数据可恢复 |
| **游标分页** | `list_cursor(cursor, cursor_field, limit) -> (Vec<Model>, Option<Cursor>)` | 替代 offset/limit |
| **统一错误处理** | `Result<T, AppError>` | 异常类型统一 |
| **事务契约** | DAO 接收 `&DatabaseConnection`，**禁止内部 commit** | 事务边界由 Service 层控制 |

**方法契约清单** (13 个 DAO 统一实现):

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `create(data)` | `ModelT` | 创建并 flush+refresh |
| `get_by_id(id)` | `ModelT \| None` | 主键查询，默认排除软删除 |
| `get_multi(filters, limit, offset)` | `list[ModelT]` | 批量查询，limit 钳制 ≤500 |
| `update(id, data)` | `ModelT` | 部分更新，flush+refresh |
| `delete(id, soft=True)` | `ModelT` | 软删除（设置 is_deleted=True）或物理删除 |
| `restore(id)` | `ModelT` | 恢复软删除记录 |
| `count(filters)` | `int` | 计数，默认排除软删除 |
| `list_cursor(cursor, cursor_field, limit)` | `tuple[list, cursor]` | 游标分页查询 |

### Model 层时间戳统一 (TimestampMixin)

> **更新于 2026-06-21 — SystemConfig 迁移**

`app/models/mixins.py` 定义了 `TimestampMixin`，为所有模型提供统一的 `created_at` / `updated_at` 字段管理：

- `created_at`: `DateTime(UTC, default=func.now(), nullable=False)` — 记录创建时自动填充
- `updated_at`: `DateTime(UTC, default=func.now(), onupdate=func.now(), nullable=False)` — 每次更新自动刷新

**SystemConfig 迁移**：`app/models/system_config.py` 的原 `SystemConfig` 模型手动管理 `updated_at` 字段。现已重构为继承 `TimestampMixin`，移除手动 `updated_at` 逻辑，新增 `created_at`。

**Alembic 迁移**：`alembic/versions/0005_add_system_config_created_at.py` 为 `system_config` 表新增 `created_at` 列。

此变更是统一模型基础设施的第一步，后续所有模型应逐步迁移到 `TimestampMixin`。

### Schema 层 UUID 类型修正

> **更新于 2026-06-21 — vault Response Schema 修复**

`app/schemas/vault.py` 的 `CharacterResp.id` 和 `PlotPromiseResp.id` 字段原定义为 `int`，但底层 BaseModel 主键为 `String(36)` UUID。修正为 `str` 以匹配 ORM 类型。

`app/router/vault.py` 的路由参数 `character_id` 同步从 `int` 改为 `str`，保持路径参数与 Schema 类型一致。

此修复属于 ID 类型统一计划（见 `docs/id-type-unification-plan.md`）的战术执行，消除了 Schema 层与 ORM 层的类型不一致。

---

## 性能优化

### 后端性能优化

| 优化项 | 说明 | 配置位置 |
|--------|------|----------|
| **异步框架** | Axum + Tokio (async/await) | `moling-server/src/main.rs` |
| **数据库连接池** | SeaORM 连接池复用（SQLx pool） | `moling-db/src/pool.rs` |
| **Redis 缓存** | bb8-redis 连接池，缓存热点数据 | `moling-core/src/redis.rs` |
| **Prometheus 指标** | 监控 API 响应时间、请求数等 | Tracing + metrics exporter |
| **Gzip 压缩** | 压缩响应体 | Nginx 配置 |

### 前端性能优化

| 优化项 | 说明 | 配置位置 |
|--------|------|----------|
| **Vite Code Splitting** | 按需加载 JS/CSS | Vite 自动处理 |
| **Tree Shaking** | 消除未使用代码 | Vite + Rollup |
| **HTTP Keep-Alive** | 复用 TCP 连接 | Vite dev server / Nginx |
| **Tauri 本地加载** | 桌面端零网络延迟，本地文件加载 | Tauri WebView |

---

## 监控和告警

### 监控指标

| 指标 | 来源 | 说明 |
|------|------|------|
| **API 请求数** | Prometheus | 统计每个 API 端点的请求数 |
| **API 响应时间** | Prometheus | P95、P99 响应时间 |
| **错误率** | Sentry | API 500 错误、前端 JS 错误 |
| **数据库连接数** | PostgreSQL | 当前活跃连接数 |
| **Redis 内存使用** | Redis | Redis 内存占用 |
| **容器资源使用** | Docker | CPU、内存、网络、磁盘 |

### 告警规则

| 告警项 | 阈值 | 严重级别 | 通知方式 |
|--------|------|----------|----------|
| **API 500 错误** | > 5 个/分钟 | 🔴 高 | Sentry + 邮件 |
| **API 响应时间** | P99 > 5 秒 | 🟡 中 | Sentry + Slack |
| **数据库连接数** | > 80% 最大连接数 | 🟡 中 | 邮件 |
| **Redis 内存使用** | > 80% 最大内存 | 🟡 中 | 邮件 |
| **磁盘空间** | > 80% 使用率 | 🟡 中 | 邮件 |
| **Worker 任务失败** | > 10 个/小时 | 🟡 中 | Sentry |

---

## 附录

### A. 参考文档

- [Axum 官方文档](https://docs.rs/axum/latest/axum/)
- [SeaORM 官方文档](https://www.sea-ql.org/SeaORM/)
- [Tokio 官方文档](https://tokio.rs/)
- [Tauri 2 官方文档](https://v2.tauri.app/)
- [React 官方文档](https://react.dev/)
- [Vite 官方文档](https://vitejs.dev/)
- [SQLite 官方文档](https://www.sqlite.org/docs.html)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Redis 官方文档](https://redis.io/docs/)
- [Docker 官方文档](https://docs.docker.com/)
- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [Sentry 官方文档](https://docs.sentry.io/)

### C. 常用操作命令

#### 本地开发快速启动

```bash
# 1. 后端 (Rust)
cd moling-server-rs
cp .env.example .env  # 编辑 .env，参照下节
cargo run --bin moling-server

# 2. 前端
cd moling-web
npm install && npm run dev

# 3. Worker（另一个终端，生产模式）
cd moling-server-rs
cargo run --bin moling-worker
```

#### .env 完整示例

```bash
# 数据库（SQLite 模式 — 桌面端 / 开发环境默认）
MOLING_DATABASE_URL=sqlite:///moling.db?mode=rwc
# 数据库（PostgreSQL 模式 — 生产环境）
# MOLING_DATABASE_URL=postgres://user:pass@localhost:5432/moling

SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=development
APP_VERSION=0.1.0
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

REDIS_URL=redis://localhost:6379/0
# REDIS_PASSWORD=          # 生产必须设置

LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_PRO_KEYS=sk-k1,sk-k2  # Pro Pool
# LLM_FLASH_KEYS=sk-f1,sk-f2 # Flash Pool

MAX_BODY_SIZE=10485760
TOKEN_BUDGET_LIMIT=1000000
# SENTRY_DSN=              # 可选
```

#### 健康检查

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","database":"ok","redis":"ok","celery":"ok"}
# 降级: {"status":"degraded","message":"redis,celery unreachable",...}
```

#### Redis 诊断

```bash
# Redis（无密码）
redis-cli ping
# Redis（有密码）
redis-cli -a "$REDIS_PASSWORD" ping

# Worker 状态（通过 API 端点查询）
curl http://localhost:8000/api/v1/admin/workers
```

#### Docker 部署（生产）

```bash
# Rust 后端
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f server worker

# SQLite 模式（桌面/单机）
docker run -d --name moling-rs -p 8000:8000 \
  -v moling-data:/data \
  -e MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc \
  moling-rs:latest
```

#### 数据库备份

```bash
docker exec moling-db pg_dump -U moling moling > backup_$(date +%Y%m%d).sql
```

### D. 文档版本历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 2.0.0 | 2026-06-24 | **重大更新** — 架构文档重构：Python FastAPI → Rust Axum 为主线技术栈；架构图重绘为 8 crate workspace Mermaid 图；PostgreSQL/SQLAlchemy/Celery → SQLite+PostgreSQL/SeaORM/Tokio；Docker Compose 编排更新为 Rust 服务；目录结构调整为 moling-server-rs 为主线；新增部署架构图与 8 crate 依赖图；技术栈表格标记 Python 为遗留模式；Cron 调度器从 Celery Beat 迁移至 Rust 原生；健康检查 / Worker 可靠性 / 认证 / DAO 层均更新为 Rust 对应实现 | Moling Team |
| 1.13.0 | 2026-06-22 | 🛠 全体 7 模块深度修复闭环 — CRITICAL: phase4_service/chapter_service 静默吞异常→logger.error, client.py 完整重试+Key轮换+Token计数统一, genre/__init__.py 删print调试; Service: 新建 service_helpers.py 抽取共享工具, template/card_pool/setting/vault 全量事务保护, card_service PermissionError→AppError; Router+DAO+Model: genre.py HTTPException→AppError, phase4_dao/template_dao 添加 is_deleted 过滤, 24端点 response_model Schema化, router/__init__.py 移除重复generation路由; Worker: card_retire/book_analysis/import/phase4 四模块10+任务全量幂等保护; Ingest+Genre+Schema: ingest 10端点 response_model Schema化, Genre LLM超时+重试, scraper依赖合并到项目根, secret Schema Field描述补齐; Frontend: 8个error.tsx错误边界, Mock数据文件创建, settings去"use client"; Infra: docker-compose.prod.yml 端口/env_file修复, CI合并+版本对齐, Nginx安全头统一 | Moling Team |
| 1.7.0 | 2026-06-21 | 🛠 架构加固 Batch 5-7 — 扫描 v4: Phase4(P2-2/P9-2/P5-3/P6-4) + Core(C1/H5/H6) + Auth(S1/S2/S4) + LLM(L1/L3/L4); RF3.4: IngestJob FK + 6 Schema类型修正。共 15 项修复，14 文件变更 | Moling Team |
| 1.6.2 | 2026-06-21 | 文档债：新增认证安全扫描 v4 发现 — 3 P0 + 3 P1 安全技术债入档（S1-S6 Token过期/密码/RBAC/黑名单降级/jose迁移） | Moling Team |
| 1.6.1 | 2026-06-21 | 文档债：新增 Core/Middleware 深度扫描 v4 发现 — 4 Critical + 6 High 已知技术债入档（C1-C4 Windows/限流/审计/OOM） | Moling Team |
| 1.6.0 | 2026-06-21 | 文档债：回填 Phase 4 深度扫描 v4 发现（71.5/100 B级）—— 4 Critical + 4 High 已知技术债入档，含修复优先级路线图 | Moling Team |
| 1.5.1 | 2026-06-21 | 文档债消灭：新增 Model 层时间戳统一 (TimestampMixin + SystemConfig 迁移 0005)、Schema 层 UUID 类型修正 (vault Response Schema int→str) | Moling Team |
| 1.5.0 | 2026-06-21 | Agent 优化：文档激进合并 — 附录新增常用操作命令（本地启动、.env 完整示例、健康检查、Redis/Celery 诊断、Docker 部署、数据库备份），吸收 DEPLOYMENT/RUNBOOK/ONBOARDING/SECURITY 中的操作级内容 | Moling Team |
| 1.4.0 | 2026-06-21 | 文档闭环回填：新增 AppError 错误处理体系、子情节健康监控服务、Worker 可靠性链路（7 项 Celery 加固 + DB 会话管理 + 三层异常处理）、Windows 平台适配层（greenlet 补丁 + 双轨会话）、DAO 层设计规范（limit 钳制 / 软删除 / 游标分页 / 事务契约）、Content-Length 中间件、Refresh Token 轮换 | Moling Team |
| 1.3.0 | 2026-06-21 | R3 架构加固：新增配置管理章节（26 项环境变量）、Celery Beat 定时调度（4 个周期性任务）、健康检查增强（DB+Redis+Celery 三方验证）、DAO 层命名规范 + 游标分页 | Moling Team |
| 1.2.0 | 2026-06-18 | 修正 Docker Compose 两套编排说明、端口映射表（Nginx 80/443、Grafana 3001:3000）、新增 Phase 4 核心架构章节 | Moling Team |
| 1.0.0 | 2026-06-16 | 初始版本 | Moling Team |

---

## Phase 2 专项优化 — 后端变更 (v1.11.0)

> **日期**: 2026-06-21 | **范围**: M8 Ingest / M9 Model / M10 Router+DAO / M11 Service

### M8: Ingest 类型安全

| 变更 | 文件 | 原因 |
|------|------|------|
| 新建 18 个 Pydantic 模型 | `app/schemas/ingest_data.py` | 消除 `dict` 裸类型传递，提供请求/响应全链路类型校验 |
| Phase 间传递改为 `model_dump()` | `phase4_service.py` 等调用方 | 替代手动 dict 构造，避免字段遗漏/拼写错误 |
| 新建 `IngestJobDAO` | `app/dao/ingest_dao.py` | 遵循 DAO 层统一规范（limit 钳制/软删除/事务契约），替代裸 session 查询 |
| `conflict.py` 3 处 `select()` 迁移至 DAO | `app/service/conflict.py` | 消除 Service 层直接操作 ORM，确保异常处理统一 |
| Phase 失败添加 `db.rollback()` | Phase 相关 Service | 防止失败时未提交的事务残留，避免后续请求读到脏数据 |
| Committer 去重外层 rollback | Phase 相关 Service | 重复提交时外层正确回滚，避免幂等键未命中时的事务泄漏 |

### M9: Model 规范化

| 变更 | 文件 | 原因 |
|------|------|------|
| 5 张表名单数→复数 | `app/models/` (vault_world→vault_worlds 等) | 遵循 SQLAlchemy 命名约定 `__tablename__` 复数形式，与数据库实际表名一致 |
| Alembic 迁移 | `c8e0a2417478` (rename_table) | 数据库侧同步重命名，保证 ORM 模型与物理表名一致 |
| 模型继承设计确认 | `app/models/` | 审查 `Base→TimestampMixin→业务Model` 三层继承链，确认无菱形继承/方法冲突 |

### M10: Router + DAO 一致性

| 变更 | 文件 | 原因 |
|------|------|------|
| auth 路由 register/login `sync`→`async` | `app/router/auth.py` | 统一使用 `Depends(get_db)` 异步会话，消除 sync/async 混用导致的 greenlet 问题 |
| `user_dao` 3 个 sync 方法加 `try/except` | `app/dao/user_dao.py` | 补齐异常处理，防止 DB 错误直接抛到 Router 层导致 500 |
| `card_dao` 5 个 sync 方法加 `try/except` | `app/dao/card_dao.py` | 同上，确保 DAO 层异常统一转为 AppError |

### M11: Service 深度清理

| 变更 | 文件 | 原因 |
|------|------|------|
| `phase4_scheduler` 异常→`AppError` | `app/service/phase4_scheduler.py` | 替代裸 `raise Exception()`，统一错误码和中文消息，便于前端解析 |
| `card_service` 常量文档化 | `app/service/card_service.py` | `MAX_ACTIVE_CARDS=80` / `FRESHNESS_DAYS` 等魔术数字添加注释说明来源和含义 |
| vault/auth Service 类型注解补充 | `app/service/vault.py`, `app/service/auth.py` | 补齐返回值类型注解，消除 `mypy` 严格模式警告 |
| LLM tenacity 添加 `ReadError`/`WriteError` | `app/llm/client.py` | 区分网络读/写超时，分别对应不同的重试策略（读可重试，写需幂等检查后重试） |

### D. 文档版本历史（续）

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| 1.11.0 | 2026-06-21 | Phase 2 专项优化 — 后端文档回填：M8 Ingest 类型安全(18 Pydantic模型+IngestJobDAO+conflict DAO迁移+Phase rollback)、M9 Model 规范化(5表复数重命名+Alembic迁移+继承确认)、M10 Router+DAO 一致性(auth async化+user_dao/card_dao try/except)、M11 Service 深度清理(phase4_scheduler AppError+card常量文档+vault/auth类型注解+LLM tenacity读写分离) | Moling Team |

---
**END**
