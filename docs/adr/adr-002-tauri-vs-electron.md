# ADR-002: Tauri 2 桌面端框架选型

> **状态**: 已接受 ✅  
> **日期**: 2026-06-24  
> **决策者**: Moling Team  
> **关联**: [ADR-001 Python → Rust 迁移](./adr-001-python-to-rust.md) | [ADR-003 SQLite 选型](./adr-003-sqlite-vs-postgresql.md)  
> **相关文档**: [DESIGN.md §11 Tauri 桌面端设计规范](../DESIGN.md#11-tauri-桌面端设计规范)

---

## 背景

墨灵需要为小说创作者提供桌面端应用，要求：
- 与 Web 端共享同一套前端代码（React + TypeScript）
- 支持 Windows、macOS、Linux 三大平台
- 安装包体积小（目标 < 30MB 压缩后）
- 与 Rust 后端（moling-server）无缝集成

## 决策

**使用 Tauri 2 作为桌面端框架**，WebView 加载 React 前端，Rust 层管理后端进程和系统功能。

## 原因

1. **安装包体积**: Tauri 2 平均包体积 < 10MB（压缩后），Electron 起步 ~120MB。墨灵作为写作工具，小体积对用户下载体验至关重要。
2. **性能**: Tauri 使用系统原生 WebView（Windows: WebView2, macOS: WKWebView, Linux: WebKitGTK），内存占用 < 100MB。Electron 捆绑完整 Chromium 实例，内存 ~300MB+。
3. **Rust 生态统一**: 后端（moling-server-rs）和桌面壳（Tauri）均为 Rust，零语言边界。后端可作为 Tauri sidecar 子进程直接管理，或通过 `Command::new_sidecar` 启动。
4. **原生体验**: Tauri 2 支持原生窗口标题栏（Overlay 模式）、系统托盘、全局快捷键、原生对话框、自动更新。
5. **安全性**: Tauri CSP 策略、capabilities 权限声明、编译时 IPC 校验。Electron `nodeIntegration` 默认开启，攻击面更大。
6. **TAO 窗口系统**: Tauri 底层使用 TAO（纯 Rust 跨平台窗口库），无 GTK/Qt 等重依赖。

## 后果

### 正向

- 安装包 ~15MB（压缩），下载和安装快速
- 桌面端可直接启动/管理 Rust 后端进程
- 前端 100% 复用（React + Vite），零额外 UI 开发
- 系统 API（文件系统、通知、快捷键）通过 Tauri Plugin 安全调用

### 负向

- macOS 需要 Developer ID 签名 + 公证（App Store 发布需额外工作）
- Linux 平台 WebKitGTK 版本碎片化（需 Flatpak/AppImage 打包）
- Tauri 2 仍较新（2024 GA），部分 Plugin 生态不如 Electron 成熟

### 风险缓解

- Web 端保持独立部署（Nginx + Docker），桌面端为增量发布
- 自动更新通过 Tauri Updater Plugin（GitHub Releases 源）
- 文件导入导出通过 Tauri dialog/fs plugin，降级为 HTML5 File API

## 替代方案

### 方案 A: Electron
- **拒绝理由**: 安装包 ~150MB（含 Chromium），内存 ~400MB+，与 Rust 后端技术栈不一致。Node.js IPC 额外序列化开销。

### 方案 B: Flutter Desktop
- **拒绝理由**: 需用 Dart 重写全部 UI（当前 React 代码 100% 无法复用），Dart 与 Rust 后端 FFI 复杂度高。

### 方案 C: PWA / Web Only
- **拒绝理由**: 无法使用系统功能（托盘、全局快捷键、原生文件对话框），离线体验差。写作者偏好桌面端工具。

### 方案 D: React Native (Windows + macOS)
- **拒绝理由**: 桌面端支持不成熟（Microsoft 维护的 Windows 端口），UI 组件与 Web React 不兼容。

## 双模式构建策略

```
同一套 React + Vite 代码
    ├── npm run dev        → Vite dev server (Web 开发)
    ├── npm run build      → dist/ → Docker/Nginx (Web 部署)
    └── npm run build:tauri → dist/ → Tauri WebView (桌面端)
```

Tauri 模式下：
- `VITE_TAURI_BUILD=true` 环境变量触发适配代码
- CSP: `connect-src 'self' http://127.0.0.1:*` 允许直连后端
- AuthGuard 客户端组件替代 SSR middleware
- 后端进程通过 `Command::new_sidecar("moling-server")` 自动启动

详见 [DESIGN.md §11 Tauri 桌面端设计规范](../DESIGN.md#11-tauri-桌面端设计规范)。

---

**END**
