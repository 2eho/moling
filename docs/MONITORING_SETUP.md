# 墨灵 (Moling) Sentry 监控配置文档

> **版本**: 1.0.0  
> **更新日期**: 2026-06-16  
> **维护者**: 墨灵团队

---

## 目录

1. [概述](#概述)
2. [Sentry 项目创建](#sentry-项目创建)
3. [后端接入（FastAPI）](#后端接入fastapi)
4. [前端接入（Next.js）](#前端接入nextjs)
5. [环境变量配置](#环境变量配置)
6. [验证接入](#验证接入)
7. [最佳实践](#最佳实践)
8. [故障排查](#故障排查)

---

## 概述

本文档描述如何在墨灵项目中接入 Sentry 错误监控和性能监控。

### 为什么需要 Sentry？

- **快速定位生产环境问题**：捕获未处理的异常和性能瓶颈
- **用户体验监控**：跟踪前端错误和用户行为
- **性能分析**：识别慢查询、慢接口
- **告警通知**：关键错误实时通知团队

### 架构概览

```
┌─────────────────┐         ┌─────────────────┐
│   前端 (Next.js) │ ─────── │   后端 (FastAPI) │
│   @sentry/nextjs │         │   sentry-sdk     │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └───────────┬───────────────┘
                     │
              ┌──────▼──────┐
              │   Sentry.io  │
              │   Dashboard  │
              └──────────────┘
```

---

## Sentry 项目创建

### 步骤 1：注册并登录 Sentry

1. 访问 [https://sentry.io](https://sentry.io)
2. 注册账号并创建组织（Organization）：`moling`
3. 创建两个项目（Project）：
   - **后端项目**：`moling-server`（Python FastAPI）
   - **前端项目**：`moling-web`（Next.js）

### 步骤 2：获取 DSN

在每个项目的 **Settings > Projects > [项目名] > Client Keys (DSN)** 页面中：

1. 复制 **DSN**（`https://<key>@<org>.ingest.sentry.io/<project_id>`）
2. 记录 **Project ID** 和 **Organization Slug**（用于 `withSentryConfig`）

### 步骤 3：配置告警规则

在 **Settings > Projects > [项目名] > Alerts** 中：

1. 创建 **Issue Alert**：
   - 触发条件：错误次数 > 10 次/小时
   - 通知方式：邮件 + Slack（可选）
2. 创建 **Metric Alert**：
   - 触发条件：API 响应时间 > 2 秒
   - 通知方式：邮件

---

## 后端接入（FastAPI）

### 安装依赖

```bash
cd moling-server
pip install sentry-sdk[fastapi]
```

### 配置说明

Sentry 已在 `app/main.py` 中自动初始化（第 266-297 行）。

**关键配置项**：

```python
sentry_sdk.init(
    dsn=sentry_dsn,  # 从环境变量 SENTRY_DSN 读取
    integrations=[
        FastApiIntegration(),      # 捕获 FastAPI 异常
        SqlalchemyIntegration(),   # 捕获 SQLAlchemy 查询性能
    ],
    environment=settings.ENVIRONMENT,  # development | staging | production
    release=f"moling@{__version__}",
    traces_sample_rate=0.2,      # 生产环境建议 0.2（20% 采样）
    profiles_sample_rate=0.2,     # 性能分析采样率
    send_default_pii=True,        # 捕获用户 IP
)
```

### 手动捕获异常

在服务代码中，可以手动捕获异常：

```python
import sentry_sdk

try:
    # 某些可能失败的操作
    result = risky_operation()
except Exception as e:
    # 捕获并上报到 Sentry
    sentry_sdk.capture_exception(e)
    # 继续执行或重新抛出
    raise
```

### 添加自定义标签

```python
import sentry_sdk

# 设置用户上下文
sentry_sdk.set_user({"id": user_id, "email": user_email})

# 设置标签
sentry_sdk.set_tag("tenant_id", tenant_id)
sentry_sdk.set_tag("feature", "novel_generation")

# 设置额外上下文
sentry_sdk.set_context("novel", {"id": novel_id, "title": novel_title})
```

---

## 前端接入（Next.js）

### 安装依赖

```bash
cd moling-web
npm install @sentry/nextjs
```

### 配置文件

#### 1. `next.config.ts`

已配置 `withSentryConfig` 包装器，用于：
- 自动上传 Source Maps
- 自动包装 App Router 路由
- 启用性能监控

#### 2. `sentry.client.config.ts`

浏览器端 Sentry 配置：
- 捕获全局错误
- 性能监控（页面加载、路由切换）
- 控制台错误捕获

#### 3. `sentry.server.config.ts`

Node.js 服务器端 Sentry 配置：
- 捕获 API 路由错误
- 捕获 SSR 错误
- 过滤敏感信息（如 Authorization 头）

#### 4. `src/app/layout.tsx`

已导入 `sentry.client.config.ts`，确保客户端监控生效。

### 手动捕获异常

在 React 组件中：

```typescript
import * as Sentry from "@sentry/nextjs";

try {
  await riskyOperation();
} catch (error) {
  Sentry.captureException(error);
  // 显示用户友好的错误提示
  toast.error("操作失败，请稍后重试");
}
```

### 添加用户反馈

```typescript
import * as Sentry from "@sentry/nextjs";

// 在捕获异常后，显示用户反馈对话框
Sentry.showReportDialog({
  title: "抱歉，出错了！",
  subtitle: "请告诉我们发生了什么，我们会尽快修复。",
  subtitle2: "您的反馈将帮助我们改进产品。",
  labelName: "姓名",
  labelEmail: "邮箱",
  labelComments: "描述问题",
  labelClose: "关闭",
  labelSubmit: "提交",
  successMessage: "感谢您的反馈！",
});
```

---

## 环境变量配置

### 后端（moling-server/.env）

```bash
# Sentry DSN（必填）
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project_id>

# 环境标识（可选，默认：development）
ENVIRONMENT=production
```

### 前端（moling-web/.env.local）

```bash
# Sentry DSN（必填）
NEXT_PUBLIC_SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project_id>

# Sentry 环境标识（可选，默认：NODE_ENV）
SENTRY_ENVIRONMENT=production
```

### 环境变量说明

| 变量名 | 位置 | 说明 | 示例 |
|--------|------|------|------|
| `SENTRY_DSN` | 后端 `.env` | Sentry 项目 DSN | `https://...@ingest.sentry.io/...` |
| `NEXT_PUBLIC_SENTRY_DSN` | 前端 `.env.local` | Sentry 项目 DSN（必须公开） | `https://...@ingest.sentry.io/...` |
| `ENVIRONMENT` | 后端 `.env` | 环境标识 | `development`, `staging`, `production` |
| `SENTRY_ENVIRONMENT` | 前端 `.env.local` | 环境标识 | `development`, `staging`, `production` |

### 安全注意事项

⚠️ **不要将真实 DSN 提交到代码仓库**：

- 后端：`.env` 已在 `.gitignore` 中
- 前端：`NEXT_PUBLIC_` 前缀的变量会暴露给浏览器，**但 DSN 本身设计为可公开**
- 建议使用环境变量注入（Docker、CI/CD）

---

## 验证接入

### 后端验证

1. **触发测试异常**：

   ```python
   # 在任意 API 路由中添加
   @router.get("/test-sentry")
   def test_sentry():
       division_by_zero = 1 / 0
   ```

2. **访问测试接口**：

   ```bash
   curl http://localhost:8000/api/v1/test-sentry
   ```

3. **检查 Sentry 后台**：
   - 登录 Sentry.io
   - 进入 `moling-server` 项目
   - 查看 **Issues** 页面，应看到新增错误

### 前端验证

1. **在浏览器触发错误**：

   ```typescript
   // 在任意页面组件中添加
   useEffect(() => {
     throw new Error("Sentry Test Error");
   }, []);
   ```

2. **访问页面**：
   - 打开浏览器开发者工具
   - 访问触发错误的页面
   - 查看 Console，应看到 Sentry 上报日志

3. **检查 Sentry 后台**：
   - 登录 Sentry.io
   - 进入 `moling-web` 项目
   - 查看 **Issues** 页面，应看到新增错误

### 性能监控验证

1. **后端**：
   - 访问 Sentry 后台 > `moling-server` > **Performance**
   - 应看到 API 请求的性能数据

2. **前端**：
   - 访问 Sentry 后台 > `moling-web` > **Performance**
   - 应看到页面加载、路由切换的性能数据

---

## 最佳实践

### 1. 采样率设置

| 环境 | `traces_sample_rate` | `profiles_sample_rate` | 说明 |
|------|----------------------|------------------------|------|
| 开发 | 1.0 | 1.0 | 全量采集，便于调试 |
| 测试 | 1.0 | 1.0 | 全量采集，便于调试 |
| 生产 | 0.2 | 0.2 | 20% 采样，平衡成本与覆盖率 |

### 2. 敏感信息过滤

**后端**（`app/main.py`）：

```python
def before_send(event, hint):
    # 过滤请求中的敏感信息
    if "request" in event:
        # 移除 Authorization 头
        if "headers" in event["request"]:
            event["request"]["headers"].pop("authorization", None)
        # 移除 Cookie
        event["request"].pop("cookies", None)
    return event

sentry_sdk.init(
    # ...
    before_send=before_send,
)
```

**前端**（`sentry.client.config.ts`）：

```typescript
beforeSend(event) {
  // 不发送包含身份验证令牌的错误
  if (event.request?.cookies) {
    delete event.request.cookies;
  }
  return event;
}
```

### 3. 自定义错误类型

定义业务错误类，便于在 Sentry 中分类：

```python
class BusinessError(Exception):
    """业务错误基类"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

# 抛出业务错误
raise BusinessError(40001, "用户不存在")
```

### 4. 性能监控关键点

**后端**：

```python
import sentry_sdk

# 手动测量代码块性能
with sentry_sdk.start_transaction(op="task", name="novel_generation"):
    # 执行耗时操作
    result = generate_novel()
```

**前端**：

```typescript
import * as Sentry from "@sentry/nextjs";

// 手动测量组件性能
const span = Sentry.startInactiveSpan({
  op: "ui",
  name: "NovelEditorRender",
});

// 执行操作
await renderNovel();

// 结束测量
span?.end();
```

---

## 故障排查

### 问题 1：Sentry 未收到错误

**可能原因**：

1. DSN 配置错误
2. 网络问题（无法访问 Sentry 服务器）
3. `traces_sample_rate` 设置过低

**排查步骤**：

```bash
# 1. 检查 DSN 是否正确
echo $SENTRY_DSN

# 2. 检查网络连接
curl https://<org>.ingest.sentry.io

# 3. 检查 Sentry 初始化日志
# 后端启动时应看到：[OK] Sentry initialized (env: ...)
```

### 问题 2：前端 Source Maps 未上传

**可能原因**：

1. `withSentryConfig` 未正确配置
2. `widenClientFileUpload` 未启用
3. CI/CD 环境中未设置 `SENTRY_AUTH_TOKEN`

**排查步骤**：

```bash
# 1. 检查 next.config.ts 是否正确导出 withSentryConfig 包装的配置
cat moling-web/next.config.ts | grep withSentryConfig

# 2. 本地构建并检查是否生成 Source Maps
npm run build
ls -la .next/static/chunks/*.js.map

# 3. 检查 Sentry 后台是否收到 Source Maps
# Settings > Projects > moling-web > Source Maps
```

### 问题 3：性能数据不完整

**可能原因**：

1. `traces_sample_rate` 设置过低
2. 集成（Integration）未正确配置

**排查步骤**：

```python
# 检查 Sentry 初始化代码
import sentry_sdk
print(sentry_sdk.get_current_scope()._level)
print(sentry_sdk.get_current_scope()._tags)
```

---

## 参考资料

- [Sentry 官方文档](https://docs.sentry.io/)
- [Sentry FastAPI 集成](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Sentry Next.js 集成](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [Sentry 性能监控](https://docs.sentry.io/product/performance/)
- [Sentry 告警配置](https://docs.sentry.io/product/alerts/)

---

## 更新日志

| 日期 | 版本 | 更新内容 | 作者 |
|------|------|----------|------|
| 2026-06-16 | 1.0.0 | 初始版本 | 墨灵团队 |

---

**文档结束**
