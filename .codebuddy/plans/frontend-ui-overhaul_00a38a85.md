---
name: frontend-ui-overhaul
overview: 用 Tailwind CSS + Radix UI + Lucide React 全面重制前端 UI 和布局，实现深色/亮色双主题，替换 Emoji 图标，消除 85 个 CSS 文件为 Tailwind 工具类，统一布局系统。
design:
  architecture:
    framework: react
    component: shadcn
  styleKeywords:
    - 现代极简主义
    - 玻璃态 Glassmorphism
    - 深色科技感
    - 靛蓝品牌色
    - 微动画
    - 沉浸式创作
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 28px
      weight: 700
    subheading:
      size: 18px
      weight: 600
    body:
      size: 14px
      weight: 400
  colorSystem:
    primary:
      - "#6366f1"
      - "#4f46e5"
      - "#4338ca"
      - "#d4a843"
    background:
      - "#0d0f1a"
      - "#151829"
      - "#111327"
      - "#f8f9fc"
      - "#ffffff"
      - "#f1f3f8"
    text:
      - "#e8e9f0"
      - "#9ca3c4"
      - "#6b7199"
      - "#1a1d2e"
      - "#4a4d6e"
      - "#7a7d9e"
    functional:
      - "#34d399"
      - "#fbbf24"
      - "#ef4444"
      - "#6366f1"
todos:
  - id: install-deps
    content: 安装 Tailwind CSS 4、Radix UI 原语包、Lucide React 依赖
    status: completed
  - id: setup-tailwind-theme
    content: 配置 Tailwind CSS 4 入口文件，映射现有设计令牌为 Tailwind theme tokens，实现深色/亮色双主题 CSS 变量
    status: completed
    dependencies:
      - install-deps
  - id: theme-provider
    content: 创建 ThemeProvider 组件，注入主题切换脚本到 layout.tsx，支持 localStorage 持久化和系统偏好检测
    status: completed
    dependencies:
      - setup-tailwind-theme
  - id: rewrite-ui-components
    content: Use [subagent:codex-executor] 用 Radix UI + Tailwind 重写核心 UI 组件（Button/Input/Modal/Toast/DropdownMenu/Dialog/Popover/Tabs），保持现有 API 接口
    status: completed
    dependencies:
      - setup-tailwind-theme
  - id: rewrite-layout
    content: 重构 AppShell/Sidebar/Navbar/BottomNav，替换 Emoji 为 Lucide 图标，引入 Radix 交互原语
    status: completed
    dependencies:
      - rewrite-ui-components
  - id: migrate-workspace
    content: 迁移工作台页面（workspace）到 Tailwind，消除 workspace.module.css，保持三栏可拖拽布局
    status: completed
    dependencies:
      - rewrite-layout
      - rewrite-ui-components
  - id: migrate-all-pages
    content: Use [subagent:codex-executor] 批量迁移剩余页面（projects/vaults/settings/admin/landing/auth/notifications/import 等）到 Tailwind
    status: completed
    dependencies:
      - rewrite-layout
      - rewrite-ui-components
  - id: cleanup-verify
    content: Use [subagent:codex-reviewer] 删除所有旧 .module.css 文件，清理内联样式，验证构建通过和双主题切换正常
    status: completed
    dependencies:
      - migrate-workspace
      - migrate-all-pages
---

## 用户需求

用户对当前前端 UI 和布局非常不满意，要求全面改进。核心诉求：引入现代化 UI 框架、实现深色/亮色双主题、替换 Emoji 图标为专业 SVG 图标库、消除大量 CSS Module 文件带来的维护负担。

## 产品概述

墨灵 AI 创作工作台前端 UI 全面翻新，从纯手写 CSS Modules 方案迁移到 Tailwind CSS 4 + Radix UI 原语 + Lucide React 图标的技术栈，在保持现有设计令牌体系的基础上，实现专业级视觉体验和深色/亮色双主题支持。

## 核心功能

- **双主题系统**：深色/亮色模式无缝切换，基于 Tailwind dark mode class strategy，映射现有设计令牌
- **Radix UI 组件替换**：Button、Input、Modal、Toast、Dropdown Menu、Dialog、Popover、Tabs 等全部用 Radix 原语重写
- **Lucide 图标替换**：所有导航、按钮、工具栏中的 Emoji 替换为 Lucide React 图标
- **布局统一**：AppShell 重构，侧边栏/顶栏/底栏使用 Radix 组件增强交互，支持折叠动画和键盘导航
- **样式消除**：逐步删除 85 个 .module.css 文件，用 Tailwind 工具类替代，保留全局动画和玻璃态效果

## 技术栈选择

| 类别 | 原方案 | 新方案 |
| --- | --- | --- |
| 样式方案 | CSS Modules (85 文件) | Tailwind CSS 4.x |
| UI 组件 | 自建 Button/Input/Modal 等 | Radix UI 原语 (无样式 + 完整 a11y) |
| 图标 | Emoji 字符 | Lucide React (SVG 图标) |
| 主题 | 仅深色 (CSS 变量) | Tailwind dark mode class + CSS 变量双轨 |
| 动画 | CSS @keyframes | 保留现有动画系统 + Tailwind animate |


### 关键决策

- **Tailwind CSS 4** 而非 v3：Next.js 15 原生支持，CSS-first 配置，零 JS 配置文件
- **Radix UI 原语**而非 Ant Design：不引入设计语言冲突，保留现有视觉风格，同时获得完整无障碍支持
- **渐进迁移**：先建立基础设施（Tailwind 入口 + 主题 + 核心组件），再逐页面迁移，确保随时可运行

## 实现方案

### 总体策略

1. **基础设施层**：安装依赖 → 配置 Tailwind CSS 4 → 映射设计令牌 → 注入主题脚本
2. **组件层**：用 Radix UI 重写核心 UI 组件，保持现有 API 接口不变
3. **布局层**：重构 AppShell/Sidebar/Navbar/BottomNav，引入 Radix 交互原语
4. **页面层**：逐页面将 CSS Modules 迁移到 Tailwind 工具类
5. **清理层**：删除旧 CSS 文件，统一代码风格

### Tailwind CSS 4 设计令牌映射

基于现有 `globals.css` 中的 CSS 变量体系，在 `src/app/globals.css` 中配置 `@theme`：

- 色彩：`--color-bg` → `bg-bg`，`--color-surface` → `bg-surface`，`--color-brand-indigo` → `brand-indigo` 等
- 间距：`--space-*` 映射到 Tailwind spacing scale
- 圆角：`--radius-*` 映射到 Tailwind radius tokens
- 阴影：`--shadow-*` 保留为 CSS 变量，在 Tailwind 中引用
- 字体：`--font-heading` / `--font-body` 映射到 Tailwind fontFamily

### 双主题实现

```css
/* globals.css */
@import "tailwindcss";

@theme {
  --color-bg: #0d0f1a;
  --color-surface: #151829;
  /* ... 深色默认值 ... */
}

/* 亮色主题 */
.light, [data-theme="light"] {
  --color-bg: #f8f9fc;
  --color-surface: #ffffff;
  /* ... 亮色值 ... */
}
```

布局中通过 `<html class="dark">` 切换，Tailwind 的 `dark:` 变体自动生效。

### 组件重写策略

保持现有组件 API 接口不变（如 `Button` 的 `variant/size/loading/fullWidth` props），内部实现替换为 Radix + Tailwind：

- **Button** → 保留 `variant` (primary/secondary/ghost/danger) + `size` (sm/md/lg)，内部用 Tailwind 类
- **Input** → Radix 无障碍模式 + Tailwind 样式
- **Modal** → Radix Dialog 原语
- **Toast** → Radix Toast 原语
- **Dropdown** → Radix DropdownMenu 原语
- **Tabs** → Radix Tabs 原语（settings/admin 页使用）

### 性能考虑

- Tailwind CSS 4 使用 JIT 编译，生产构建仅包含使用到的类
- Radix UI 组件按需导入，不影响 bundle size
- Lucide React 支持 tree-shaking，仅打包使用的图标
- 消除 85 个 CSS 文件减少 HTTP 请求和构建时间

## 设计风格

基于现有墨灵设计令牌体系，延续**深色科技感 + 玻璃态**视觉基因，新增**亮色优雅专业**主题。整体采用**现代极简主义**融合**玻璃态 (Glassmorphism)** 风格，营造沉浸式创作氛围。

### 深色主题（默认）

- 深邃星空背景 (#0d0f1a)，多层表面色阶
- 靛蓝 (#6366f1) 为主品牌色，琥珀 (#d4a843) 为点缀
- 玻璃态面板 (backdrop-filter blur) 用于侧边栏、浮动卡片
- 微妙渐变和发光阴影增强层次感

### 亮色主题

- 柔和灰白背景 (#f8f9fc)，白色卡片
- 靛蓝保持为品牌色，降低饱和度适配亮色背景
- 玻璃态改为半透明白色背景
- 阴影更轻更柔和

### 布局架构

- **Web端**：固定侧边栏 (280px) + 主内容区，侧边栏可折叠至 56px
- **工作台**：全宽三栏布局（资料库 280px + 编辑器 flex-1 + AI 工具箱 320px），面板可拖拽调整宽度
- **移动端**：顶栏 + 内容 + 底部导航（3项）
- **简单页**（登录/注册/Landing）：独立布局无导航

### 交互规范

- 所有可点击元素有 hover/active 状态反馈
- 侧边栏折叠带 200ms 过渡动画
- 模态框从中心缩放弹出 (scale 0.95 → 1)
- 页面切换有淡入上浮动画
- Toast 通知从右上角滑入
- 下拉菜单有 150ms 展开动画

### 响应式策略

- ≥1024px：完整三栏工作台
- 768px-1023px：侧边栏默认折叠，工作台双栏
- <768px：移动端布局，底部导航

## Agent Extensions

### SubAgent

- **code-explorer**
- Purpose: 深度探索所有页面组件和 CSS 文件，生成完整迁移清单
- Expected outcome: 列出每个页面/组件的迁移优先级、CSS 类映射、内联样式清单

- **codex-executor**
- Purpose: 批量执行组件重写和页面迁移（多文件并行处理）
- Expected outcome: 高效完成大量文件的 Tailwind 迁移和 Radix 组件替换

- **codex-reviewer**
- Purpose: 每批次迁移后检查代码质量、无障碍性和视觉一致性
- Expected outcome: 确保所有组件符合 a11y 标准，Tailwind 类使用正确

### Skill

- **professional-premium**
- Purpose: 确保本次 UI 翻新达到专业级交付标准
- Expected outcome: 高质量的视觉体验、完整的主题支持、零 Bug 交付