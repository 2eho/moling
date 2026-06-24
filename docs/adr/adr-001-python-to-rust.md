# ADR-001: Python (FastAPI) → Rust (Axum) 后端迁移

> **状态**: 已接受 ✅  
> **日期**: 2026-06-24  
> **决策者**: Moling Team  
> **关联**: [ADR-002 Tauri 2 选型](./adr-002-tauri-vs-electron.md) | [ADR-003 SQLite 选型](./adr-003-sqlite-vs-postgresql.md)

---

## 背景

墨灵项目最初使用 Python + FastAPI 作为后端技术栈，技术债务于 v1.10-v1.13 期间累积了 30+ Critical/High 项（内存泄漏、限流失效、Windows 兼容性问题等）。同时，Tauri 桌面端的引入要求后端能与 Rust 前端壳紧密集成。

## 决策

**将后端从 Python (FastAPI + SQLAlchemy + Celery) 迁移至 Rust (Axum + SeaORM + Tokio)**。

## 原因

1. **性能**: Rust 零成本抽象 + 无 GC，编译为原生二进制。API 吞吐量预期提升 3-5×，内存占用降低 60-80%。
2. **类型安全**: 编译时类型检查消除整个类别的运行时错误（None 引用、类型不匹配、未处理错误分支）。
3. **编译时检查**: `Result<T, E>` 强制错误处理，`clippy` 零警告门禁保证代码质量。
4. **Tauri 集成**: Tauri 2 基于 Rust，统一前后端技术栈。后端可以作为 Tauri sidecar 进程运行，或编译为同一二进制。
5. **运维简化**: 单二进制部署（`moling-server`），无需 Python 运行时、virtualenv、pip 依赖管理。
6. **消除 Python 技术债**: greenlet 补丁、Windows 兼容层、纯内存限流等全部从根因解决。
7. **并发模型**: Tokio 原生 async/await，无 GIL 限制，多核充分利用。

## 后果

### 正向

- 编译为单二进制，部署和分发极大简化
- SeaORM 编译时 SQL 检查，零 SQL 注入风险
- Rust 生态工具链成熟（cargo fmt/clippy/test/audit）
- Docker 镜像从 ~400MB (python:3.12-slim) 降至 ~10MB (scratch)

### 负向

- 团队需要学习 Rust（所有权、生命周期、trait 系统学习曲线）
- 开发迭代速度初期可能略慢于 Python（编译时间 vs 热重载）
- 部分 Python 生态库无直接替代（需自行实现或寻找替代）

### 风险缓解

- Python 代码保留为 `moling-server/`，进入维护模式（仅修 Critical Bug）
- Rust 与 Python 共享同一 API 契约（uthipa OpenAPI 生成文档）
- 迁移采用增量策略：先核心路径（Auth/DB/LLM），再外围服务

## 替代方案

### 方案 A: 保持 Python + 性能优化（Cyton/uvloop）
- **拒绝理由**: 治标不治本，greenlet/Windows 问题无法根解，Tauri 集成需要额外 IPC 层

### 方案 B: Go (Gin/Fiber)
- **拒绝理由**: GC 暂停延迟不可预测，无 Tauri 生态整合优势，ORM 成熟度不如 SeaORM

### 方案 C: Node.js (Express/Fastify)
- **拒绝理由**: 运行时体积大，并发模型不如 Rust 高效，与 Tauri Rust 侧进程通信效率低

## 迁移范围

| 模块 | Python 文件 | Rust crate | 状态 |
|------|------------|------------|:----:|
| 配置管理 | `app/config.py` | `moling-core/config.rs` | ✅ |
| 错误处理 | `app/errors.py` | `moling-core/error.rs` | ✅ |
| 数据库/ORM | `app/models/` + `app/dao/` | `moling-db/` (SeaORM) | ✅ |
| 认证 | `app/auth_service.py` | `moling-auth/` | ✅ |
| API 路由 | `app/api/` | `moling-api/` (16 模块) | ✅ |
| 业务逻辑 | `app/services/` | `moling-services/` (31 模块) | ✅ |
| LLM 客户端 | `app/llm/` | `moling-llm/` | ✅ |
| Worker | `app/worker/` (Celery) | `moling-worker/` (Tokio) | ✅ |
| 入口 | `main.py` | `moling-server/main.rs` | ✅ |

**测试结果**: `cargo test --workspace` → 274 passed / 0 failed / 11 ignored

---

**END**
