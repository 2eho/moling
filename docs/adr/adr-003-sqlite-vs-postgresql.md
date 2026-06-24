# ADR-003: SQLite 数据库选型

> **状态**: 已接受 ✅  
> **日期**: 2026-06-24  
> **决策者**: Moling Team  
> **关联**: [ADR-001 Python → Rust 迁移](./adr-001-python-to-rust.md) | [ADR-002 Tauri 2 选型](./adr-002-tauri-vs-electron.md)

---

## 背景

墨灵后端需要数据库存储用户数据、小说项目、章节内容、Phase 4 四库（人物/时间线/伏笔/世界观）。原 Python 实现使用 PostgreSQL 16 作为默认数据库。迁移至 Rust + Tauri 后，需要重新评估数据库选型。

核心使用场景：
- 桌面端：单用户、本地使用、零网络依赖
- Web 端：多用户 SaaS，需要并发支持
- 数据规模：单个项目最多 ~500 章节，数据库总量 < 500MB

## 决策

**默认使用 SQLite 作为数据库，同时通过 SeaORM 抽象层支持 PostgreSQL 作为生产可选后端**。

具体策略：
- 桌面端 / 开发环境：**SQLite（默认）**
- 生产 SaaS 部署：**PostgreSQL（可选）**
- 数据库访问层统一通过 SeaORM，应用代码无需关心底层数据库（编译时切换）

## 原因

1. **嵌入式 / 零配置**: SQLite 无需独立数据库服务进程、无需网络配置、无需用户管理。桌面端用户无需安装或配置任何数据库。
2. **桌面端友好**: 数据存储在单个文件 `moling.db` 中，备份 = 复制文件，迁移 = 移动文件。写作者不关心数据库运维。
3. **性能足够**: SQLite 在单写入者场景下性能优异。墨灵是写作工具，写操作集中在单用户章节编辑，WAL 模式可支持一定并发读。
4. **SeaORM 抽象**: 通过 SeaORM 的 `DatabaseConnection` 抽象，应用代码与底层数据库解耦。开发时用 SQLite，需要时切换 PostgreSQL 仅需改一行连接串。
5. **Rust 集成**: `libsqlite3-sys` 是 Rust 生态中最成熟的嵌入式数据库绑定，与 Tokio 异步兼容。
6. **发布简化**: 桌面端安装包无需捆绑数据库服务，启动 `moling-server` 即可使用。

## 后果

### 正向

- 桌面端零安装、零配置、零运维
- 数据库文件可随项目导出/导入
- 开发环境极简（`sqlite:///moling.db?mode=rwc`）
- WAL 模式支持并发读 + 单写入者（对写作工具完全足够）
- 备份简单（`cp moling.db moling_backup.db`）

### 负向

- 高并发 Web SaaS 场景不如 PostgreSQL（连接池负载高时写入串行化）
- 缺少 pgvector 向量搜索支持（如未来需要语义搜索章节内容）
- 无原生 JSONB / 全文搜索 / 地理空间等高级特性
- 单机部署，无原生主从复制

### 风险缓解

- **高并发场景**: 切换到 PostgreSQL 仅需改 `MOLING_DATABASE_URL` 环境变量
- **向量搜索**: 如需语义搜索，可通过 SeaORM 扩展 + 外部向量数据库（如 Qdrant）实现
- **Web SaaS**: `docker/docker-compose.yml` 生产编排默认使用 PostgreSQL
- **数据迁移**: 提供 SQLite → PostgreSQL 数据导出导入脚本（`moling-db/migrations/`）

## 替代方案

### 方案 A: 仅 PostgreSQL
- **拒绝理由**: 桌面端用户需安装/配置 PostgreSQL 服务，违反"零配置"原则。Tauri 桌面端捆绑 PostgreSQL 体积过大。

### 方案 B: 仅 SQLite
- **拒绝理由**: Web SaaS 多用户并发写入性能瓶颈。缺少向量搜索扩展能力。

### 方案 C: 双数据库方案（SQLite + PostgreSQL 同时运行）
- **拒绝理由**: 维护成本翻倍，数据同步复杂。应用代码需条件分支处理数据库差异，违反 DRY 原则。

### 方案 D: DuckDB
- **拒绝理由**: OLAP 优化，OLTP 场景不如 SQLite。Rust 绑定不如 `libsqlite3-sys` 成熟。

## 连接参数

### SQLite（桌面端 / 开发）

```
MOLING_DATABASE_URL=sqlite:///data/moling.db?mode=rwc
```

- `mode=rwc`: 读写 + 自动创建
- WAL 模式启用（`PRAGMA journal_mode=WAL`）
- 外键约束启用（`PRAGMA foreign_keys=ON`）
- 超时 5000ms（`PRAGMA busy_timeout=5000`）

### PostgreSQL（生产部署）

```
MOLING_DATABASE_URL=postgres://user:pass@db:5432/moling
```

- 连接池: min=2, max=10
- `pool_pre_ping`: 启用
- pgvector 扩展（未来可选）

---

**END**
