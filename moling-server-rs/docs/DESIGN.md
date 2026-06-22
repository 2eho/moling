# 墨灵 (Moling) — 设计文档

> **后端已 Rust 重写**：详见 `docs/ARCHITECTURE.md` Rust 重写章节。
> 前端 `moling-web` 不变：Next.js 15 + React 19 + TypeScript + Tailwind CSS 4

> **最后更新**: 2026-06-21

---

## 设计原则

### 1. 混合架构

Rust 负责高性能 HTTP/API/DB 核心链路，Python 保留 LLM 编排和 Prompt 工程。
两个运行时通过 HTTP API 或 Redis 队列互通，不共享内存。

### 2. 类型安全

- 数据库 → SeaORM 实体编译期校验
- API 请求/响应 → Serde 序列化 + 强类型 struct
- 错误 → 统一 `AppError` 枚举，每个变体携带 HTTP 状态码 + 中文消息

### 3. 优雅降级

- Redis 不可用时：黑名单/限流/锁/计数器返回 `Ok(None)`，不阻塞请求
- 数据库不可用时：返回 503（与 Nginx upstream 联动重试）
- Worker 失败时：任务进入死信队列（DLQ），支持手动重试

### 4. 零技术债

- 项目中无 `TODO` / `FIXME` / `HACK` 标记
- 所有 pub API 有 rustdoc 注释
- `cargo check` 零 warning（除 1 个 moling-db 预存 `async_fn_in_trait`）

---

## 数据流

```
Browser → Nginx (:80) → moling-app (:8000)
                              │
                    ┌─────────┼──────────┐
                    │         │          │
                 Axum       moling-auth  moling-db
                Router        (JWT)      (SeaORM)
                    │                      │
              ┌─────┼──────┐          ┌────▼────┐
              │     │      │          │PostgreSQL│
           routes  middleware  state  └─────────┘
              │
        moling-services
              │
        moling-db (DAO)
```

### 请求生命周期

1. Nginx 接收 HTTP 请求 → 反向代理到 moling-app:8000
2. Axum 中间件栈：request-id → cors → sentry → audit → response → content-length → rate-limit → trace
3. 路由匹配 → handler 函数
4. `CurrentUser` 提取器从 request extensions 获取 JWT 身份
5. Handler 调用 Service 层 → Service 调用 DAO → DAO 执行 SeaORM 查询
6. JSON 序列化响应 → 返回客户端

---

## API 版本化

所有 API 端点位于 `/api/v1/` 下。
Python 后端的 API 契约保持不变——Rust 后端完全兼容。

### 端点统计

| 模块 | 端点数 | HTTP 方法 |
|------|--------|-----------|
| auth | 8 | POST/GET/PUT |
| project | 7 | POST/GET/PUT/DELETE |
| chapter | 9 | POST/GET/PUT/DELETE |
| card | 5 | POST/GET |
| vault | 22 | POST/GET/PUT/DELETE |
| secret | 6 | POST/GET/PUT/DELETE |
| generation | 4 | POST/GET |
| health | 1 | GET |
| admin | 4 | GET/POST |
| notification | 5 | GET/POST/DELETE |
| settings | 4 | GET/PUT/POST |
| templates | 5 | POST/GET/PUT/DELETE |
| phase4 | 5 | GET/POST |
| weave | 4 | GET/POST |
| subscriptions | 4 | GET/POST |
| import | 5 | POST |
| genre | 2 | POST |
| **总计** | **99** | |

---

## 错误处理

错误响应格式（匹配 Python API）：

```json
{
  "code": "PROJECT_NOT_FOUND",
  "message": "项目不存在",
  "detail": null
}
```

### 错误码

| 错误码 | HTTP 状态 | 中文消息 |
|--------|----------|---------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 |
| `AUTH_TOKEN_EXPIRED` | 401 | 登录已过期，请重新登录 |
| `AUTH_INVALID_TOKEN` | 401 | 无效的认证令牌 |
| `AUTH_INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 |
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `USER_EMAIL_EXISTS` | 409 | 该邮箱已被注册 |
| `PROJECT_NOT_FOUND` | 404 | 项目不存在 |
| `PROJECT_ACCESS_DENIED` | 403 | 无权访问该项目 |
| `CHAPTER_NOT_FOUND` | 404 | 章节不存在 |
| `CARD_NOT_FOUND` | 404 | 卡片不存在 |
| `VAULT_ENTRY_NOT_FOUND` | 404 | 四库条目不存在 |
| `GENERATION_TASK_NOT_FOUND` | 404 | 生成任务不存在 |
| `VALIDATION_ERROR` | 422 | 请求参数验证失败 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 数据库

### 表统计

| 类别 | 表数 | 表名 |
|------|------|------|
| 核心 | 4 | users, projects, chapters, generation_tasks |
| 四库 | 5 | vault_characters, vault_timeline, vault_plot_promises, vault_worlds, vault_changelogs |
| 卡池 | 2 | card_pools, draw_histories |
| 秘密 | 1 | secrets |
| 健康 | 1 | health_alerts |
| 通知 | 1 | notifications |
| 模板 | 1 | templates |
| 订阅 | 2 | plans, user_subscriptions |
| Phase4 | 2 | phase4_tasks, dynamic_layers |
| 子线 | 2 | sub_plots, sub_plot_status_logs |
| 配置 | 1 | system_configs |
| 导入 | 1 | ingest_jobs |

### 迁移

8 个 SeaORM 迁移对应 Python Alembic 脚本：

| 迁移 | 表 | 状态 |
|------|----|------|
| m0001_initial | 22 表初始创建 | ✅ |
| m0002_ingest_jobs | ingest_jobs | ✅ |
| m0004_align_models | 模型对齐 | ✅ |
| m0005_system_config | system_configs.created_at | ✅ |
| m0006_drop_status | Phase4 status 列删除 | ✅ |
| m0007_user_role | users.role 列 | ✅ |
| m0008_sub_plots | sub_plots + sub_plot_status_logs | ✅ |

---

## 安全

- JWT HS256，leeway=0（无时钟偏移）
- bcrypt cost=12 密码哈希
- 登录锁定：5 次失败后 15 分钟冷却
- 令牌黑名单：登出时立即失效（Redis SETEX）
- Rate limiting：100 req/60s per IP（Redis 滑动窗口）
- 请求体限制：默认 10MB
- Nginx 安全头：X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- 非 root 用户运行容器
