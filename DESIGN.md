# Design System — 墨灵 (Moling) v3.1

> **参考品牌**: Linear (极简暗色) × Raycast (玻璃态光影) × Notion (内容排版)
> **评分**: 93/100 — 生产级暗色主题设计系统（含完整色阶 + 玻璃态 + 编辑器排版）
> **解析度**: AI 可直读，CSS 变量一键映射

---

## 1. Visual Theme & Atmosphere（视觉主题与氛围）

**品牌设计哲学**: 沉静、专注、智慧。墨灵是 AI 驱动的网文创作平台，视觉语言需要传达"深度思考"与"灵感涌现"的双重气质——暗色基底让人沉入创作心流，靛蓝色光晕暗示 AI 智能的跃动，琥珀金点缀如书页边缘的烫金，唤起文学质感。

**视觉基调**: 
- 深空暗色（#0d0f1a）— 如深夜书房，消除视觉噪音
- 毛玻璃叠加 — 浮层面板使用 backdrop-filter blur，制造景深感
- 微阴影层次 — 不用重阴影，靠微妙亮暗差异区分层级

**核心关键词**: `沉静` `锐利` `文学质感` `玻璃态` `微光`

**光影倾向**:
- 表面层：纯色半透明叠加 (rgba 8%-12%)
- 浮层：backdrop-filter blur(12px) + 微边框
- 发光：品牌色 glow (indigo #6366f1 / amber #d4a843)，仅用于聚焦态和稀有元素
- 按钮：渐变微光，hover 时亮度提升 10-15%

---

## 2. Color Palette & Roles（调色板与角色）

### 2.1 背景层次

| 角色 | HEX | CSS 变量 | 用途 |
|------|-----|----------|------|
| 主背景 | `#0d0f1a` | `--color-bg` | 页面底色、布局背景 |
| 表面 | `#151829` | `--color-surface` | 卡片、面板、输入框背景 |
| 浮层 | `#111327` | `--color-elevated` | 弹窗、下拉菜单、Tooltip |

### 2.2 品牌色

| 角色 | HEX | CSS 变量 | 用途 |
|------|-----|----------|------|
| 品牌靛蓝 | `#6366f1` | `--color-brand-indigo` | 主按钮、链接、聚焦环、选中态 |
| 品牌琥珀 | `#d4a843` | `--color-brand-amber` | 强调元素、稀有标识、CTA 高亮 |
| 靛蓝深色 | `#4f46e5` | — | hover/active 状态 |
| 琥珀深色 | `#b8962f` | — | hover/active 状态 |

### 2.2b 品牌靛蓝完整色阶

> 新增于 v3.1。基于 Tailwind Indigo 色系，为渐变、状态变化、深度层次提供完整 50→900 色阶。

| Token | HEX | 色阶 | 在暗色主题中的用途 |
|-------|-----|------|-------------------|
| `--color-brand-indigo-50` | `#eef2ff` | 50 | 极浅指示、微背景高亮 |
| `--color-brand-indigo-100` | `#e0e7ff` | 100 | 强调背景、选中态背景 |
| `--color-brand-indigo-200` | `#c7d2fe` | 200 | 边框高亮、次要图标色 |
| `--color-brand-indigo-300` | `#a5b4fc` | 300 | 次要文字强调、禁用态图标 |
| `--color-brand-indigo-400` | `#818cf8` | 400 | 次要按钮文字、链接 hover |
| `--color-brand-indigo-500` | `#6366f1` | 500 | **主色** — 按钮、链接、聚焦环 |
| `--color-brand-indigo-600` | `#4f46e5` | 600 | 主按钮 hover 加深 |
| `--color-brand-indigo-700` | `#4338ca` | 700 | 主按钮 active 按下态 |
| `--color-brand-indigo-800` | `#3730a3` | 800 | 深色品牌面、暗色渐变终点 |
| `--color-brand-indigo-900` | `#312e81` | 900 | 最深品牌背景、渐变最深色 |

**使用规则**:
- 50–200: 暗色主题中作为 **文字/图标色** 或超浅背景
- 300–500: 标准交互色区域
- 600–900: **深色渐变终点** 或品牌背景面
- **禁止独立使用 800/900 作为文字色**（对比度不足，会被深色背景吞没）

### 2.3 交互色

| 角色 | HEX | CSS 变量 | 用途 |
|------|-----|----------|------|
| Hover 高亮 | `rgba(99,102,241,0.12)` | — | 列表项、菜单项 hover |
| 选中态 | `rgba(99,102,241,0.18)` | — | 选中列表项、活跃标签 |
| Focus 环 | `#6366f1` | — | `:focus-visible` 2px 轮廓 |

### 2.4 中性灰阶

| 角色 | HEX | CSS 变量 | 用途 |
|------|-----|----------|------|
| 主文字 | `#e8e9f0` | `--color-text-primary` | 标题、正文 |
| 次要文字 | `#9ca3c4` | `--color-text-secondary` | 描述、标签、元信息 |
| 三级文字 | `#6b7199` | `--color-text-tertiary` | 辅助信息、占位符 |
| 禁用文字 | `#3d4166` | `--color-text-disabled` | 禁用态文字 |
| 边框 | `#2a2d45` | `--color-border` | 卡片边框、分隔线 |
| 细微边框 | `#1e2138` | `--color-border-subtle` | 内部分隔、嵌套边框 |

### 2.5 语义色

| 角色 | HEX | CSS 变量 | 用途 |
|------|-----|----------|------|
| 成功 | `#34d399` | `--color-success` | 完成状态、确认消息 |
| 警告 | `#fbbf24` | `--color-warning` | 警告、待处理 |
| 危险 | `#ef4444` | `--color-danger` | 删除、错误、不可逆操作 |
| 信息 | `#38bdf8` | — | 提示、通知 |

### 2.6 稀有度色

| 稀有度 | HEX | 场景 |
|--------|-----|------|
| 普通 N | `#9ca3af` | 常规卡牌 |
| 稀有 R | `#67e8f9` | 稀有卡牌 |
| 史诗 SR | `#a855f7` | 史诗卡牌 |
| 传说 SSR | `#d4a843` | 传说卡牌（与品牌琥珀同色） |

### 2.7 阴影色

| 级别 | 值 | 用途 |
|------|-----|------|
| sm | `0 1px 2px rgba(0,0,0,0.3)` | 微妙浮起 |
| md | `0 2px 8px rgba(0,0,0,0.4)` | 卡片 |
| lg | `0 4px 16px rgba(0,0,0,0.5)` | 下拉菜单 |
| xl | `0 8px 32px rgba(0,0,0,0.6)` | 弹窗 |
| glow-indigo | `0 0 20px rgba(99,102,241,0.3)` | 品牌聚焦发光 |
| glow-amber | `0 0 20px rgba(212,168,67,0.3)` | 琥珀强调发光 |

---

## 3. Typography Rules（排版规则）

### 3.1 字体族

| 角色 | 字体栈 | CSS 变量 |
|------|--------|----------|
| 标题 | `'Noto Serif SC', '思源宋体', Georgia, serif` | `--font-heading` |
| 正文/UI | `-apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif` | `--font-body` |
| 代码/数据 | `'JetBrains Mono', 'Fira Code', Consolas, monospace` | `--font-mono` |

### 3.2 字号层级

| 层级 | Font Size | Weight | Line Height | Letter Spacing | 用途 |
|------|-----------|--------|-------------|----------------|------|
| Hero | `clamp(36px, 6vw, 64px)` | 700 | 1.1 | `-0.02em` | Landing 主标题 |
| 4xl | `36px / 2.25rem` | 700 | 1.2 | `-0.015em` | 页面大标题 |
| 3xl | `28px / 1.75rem` | 600 | 1.3 | `-0.01em` | 区块标题 |
| 2xl | `22px / 1.375rem` | 600 | 1.4 | `-0.005em` | 卡片标题 |
| xl | `18px / 1.125rem` | 600 | 1.5 | `0` | 子标题 |
| lg | `16px / 1rem` | 500 | 1.5 | `0` | 正文大字 |
| base | `14px / 0.875rem` | 400 | 1.6 | `0` | 正文 |
| sm | `13px / 0.8125rem` | 400 | 1.5 | `0` | 辅助文字 |
| xs | `11px / 0.6875rem` | 500 | 1.4 | `0.02em` | 标签、Badge |

### 3.3 排版哲学

- **标题用衬线**: Noto Serif SC 带来文学仪式感，与网文创作的属性相呼应
- **正文用无衬线**: PingFang SC 保证屏幕可读性，字号 14px 为基准
- **数字用等宽**: JetBrains Mono 用于字数统计、版本号、代码片段
- **行高宽松**: 正文 1.6 行高减少长文阅读疲劳
- **字重克制**: 正文只用 400/500，标题用 600/700，不过度强调

---

## 4. Component Stylings（组件样式）

### 4.1 Buttons

```css
/* Primary — 主操作按钮 */
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(99,102,241,0.25);
  transition: all 200ms ease;
}
.btn-primary:hover {
  background: linear-gradient(135deg, #7577f5, #6366f1);
  box-shadow: 0 4px 16px rgba(99,102,241,0.4);
  transform: translateY(-1px);
}
.btn-primary:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(99,102,241,0.2);
}

/* Secondary — 次要操作 */
.btn-secondary {
  background: rgba(99,102,241,0.1);
  color: #a5b4fc;
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  transition: all 200ms ease;
}
.btn-secondary:hover {
  background: rgba(99,102,241,0.18);
  border-color: rgba(99,102,241,0.35);
  color: #c7d2fe;
}

/* Ghost — 无背景按钮 */
.btn-ghost {
  background: transparent;
  color: #9ca3c4;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  transition: all 200ms ease;
}
.btn-ghost:hover {
  background: rgba(255,255,255,0.06);
  color: #e8e9f0;
}

/* Danger — 危险操作 */
.btn-danger {
  background: rgba(239,68,68,0.12);
  color: #f87171;
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
}
.btn-danger:hover {
  background: rgba(239,68,68,0.22);
  border-color: rgba(239,68,68,0.4);
  color: #fca5a5;
}

/* Size variants */
.btn-sm { padding: 4px 12px; font-size: 12px; border-radius: 6px; }
.btn-lg { padding: 12px 28px; font-size: 16px; border-radius: 10px; }
```

### 4.2 Cards

```css
.card {
  background: #151829;
  border: 1px solid #2a2d45;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
.card:hover {
  border-color: rgba(99,102,241,0.3);
  box-shadow: 0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.1);
}
```

### 4.3 Inputs

```css
.input {
  background: #111327;
  border: 1px solid #2a2d45;
  border-radius: 8px;
  padding: 10px 14px;
  color: #e8e9f0;
  font-size: 14px;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
.input::placeholder { color: #6b7199; }
.input:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}
.input.error {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239,68,68,0.12);
}
```

### 4.4 Navigation

```css
/* Sidebar — Web 端 */
.sidebar {
  background: #0d0f1a;
  border-right: 1px solid #1e2138;
  width: var(--sidebar-width);  /* 280px */
  transition: width 200ms ease;
}
.sidebar.collapsed { width: var(--sidebar-collapsed); }  /* 56px */

.nav-item {
  color: #9ca3c4;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  transition: all 150ms ease;
}
.nav-item:hover { background: rgba(255,255,255,0.04); color: #e8e9f0; }
.nav-item.active {
  background: rgba(99,102,241,0.12);
  color: #a5b4fc;
}

/* BottomNav — 移动端 */
.bottom-nav {
  background: rgba(13,15,26,0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid #1e2138;
  height: 56px;
}
```

### 4.5 Badges / Tags

```css
.badge {
  background: rgba(99,102,241,0.12);
  color: #a5b4fc;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
}
.badge-success { background: rgba(52,211,153,0.12); color: #6ee7b7; }
.badge-warning { background: rgba(251,191,36,0.12); color: #fcd34d; }
.badge-danger  { background: rgba(239,68,68,0.12); color: #f87171; }
/* 稀有度 Badge */
.badge-r { background: rgba(103,232,249,0.12); color: #67e8f9; }
.badge-sr { background: rgba(168,85,247,0.12); color: #a855f7; }
.badge-ssr { background: rgba(212,168,67,0.12); color: #d4a843; }
```

### 4.6 Modals / Dialogs

```css
.modal-overlay {
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(6px);
  animation: fadeIn 200ms ease;
}
.modal-content {
  background: #111327;
  border: 1px solid #2a2d45;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  max-width: 520px;
  width: 90vw;
  animation: scaleIn 250ms cubic-bezier(0.16,1,0.3,1);
}
```

### 4.7 Glass Panels（玻璃态面板）— 新增 v3.1

```css
/* 大面板 — 导航栏、侧边栏背景 */
.glass-panel {
  background: rgba(21, 24, 41, 0.7);          /* --color-surface @ 70% */
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-lg);            /* 14px */
}

/* 小卡片 — 浮动卡牌、Hover 弹出板 */
.glass-card {
  background: rgba(21, 24, 41, 0.6);          /* --color-surface @ 60% */
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);            /* 10px */
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  transition: all var(--transition-normal);
}
.glass-card:hover {
  background: rgba(21, 24, 41, 0.8);
  border-color: rgba(99, 102, 241, 0.15);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}
```

**使用约束**:
- `.glass-panel`: 仅用于导航容器、底部栏、大区块面板
- `.glass-card`: 用于悬浮卡片、Hover 预览、浮动工具栏
- 不在内容密集区使用（滚动时 backdrop-filter 有性能开销）

### 4.8 Prose / Editor（编辑器排版）— 新增 v3.1

```css
/* 编辑器写作区 — 类 Notion 排版 */
.prose-editor {
  font-family: var(--font-body);
  font-size: var(--font-size-lg);            /* 16px */
  line-height: 1.8;
  color: var(--color-text-primary);
  max-width: 720px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);    /* 32px 24px */
  caret-color: var(--color-brand-indigo);
}
.prose-editor h1 { font-family: var(--font-heading); font-size: 28px; font-weight: 700; margin: 24px 0 12px; }
.prose-editor h2 { font-family: var(--font-heading); font-size: 22px; font-weight: 600; margin: 20px 0 10px; }
.prose-editor h3 { font-size: 18px; font-weight: 600; margin: 16px 0 8px; }
.prose-editor p  { margin: 0 0 12px; }
.prose-editor blockquote {
  border-left: 3px solid var(--color-brand-indigo);
  padding-left: 16px;
  margin: 16px 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

/* 预览区 — 衬线字体渲染 */
.prose-preview {
  font-family: var(--font-heading);
  font-size: var(--font-size-lg);            /* 16px */
  line-height: 1.7;
  color: var(--color-text-primary);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-8);
  border: 1px solid var(--color-border-subtle);
  max-width: 720px;
  margin: 0 auto;
}
```

### 4.9 Utility Classes（工具类）— 新增 v3.1

```css
/* 渐变文字 — 用于 Hero 标题、品牌强调 */
.text-gradient {
  background: linear-gradient(135deg, var(--color-brand-indigo), var(--color-brand-indigo-300));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 微妙渐变背景 — 用于卡片内、区块背景 */
.bg-gradient-subtle {
  background: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.08),
    rgba(99, 102, 241, 0.02)
  );
}

/* Hover 上浮 — 用于卡牌、列表项 */
.hover-lift {
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
}
.hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* Active 按压 — 用于按钮、可点击面板 */
.active-press {
  transition: transform var(--transition-fast);
}
.active-press:active {
  transform: scale(0.97);
}
```

---

## 5. Layout Principles（布局原则）

### 5.1 Spacing System（8px 基数）

| Token | 值 | 用途 |
|-------|-----|------|
| `--space-1` | 4px | 图标与文字间距、紧凑内边距 |
| `--space-2` | 8px | 组件内间距、小元素间隙 |
| `--space-3` | 12px | 列表项内间距 |
| `--space-4` | 16px | 卡片 padding、标准间距 |
| `--space-5` | 20px | 区块内间距 |
| `--space-6` | 24px | 区块间距、Modal padding |
| `--space-8` | 32px | Section 间距 |
| `--space-10` | 40px | 大区块间距 |
| `--space-12` | 48px | 页面级间距 |
| `--space-16` | 64px | Hero 区域上下间距 |
| `--space-20` | 80px | Landing 页面 Section 间距 |
| `--space-24` | 96px | Landing 超大间距 |

### 5.2 Grid System

- **列数**: 12 列
- **列间距**: 16px (mobile) / 24px (desktop)
- **最大宽度**: 1200px（内容区）
- **Landing 最大宽度**: 1280px

### 5.3 Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}
.container-wide { max-width: 1280px; }  /* Landing */
.container-narrow { max-width: 720px; }  /* 阅读/表单 */
```

### 5.4 Section Spacing

- 页面内区块间距: 32px (`--space-8`)
- 主要 Section 间距: 48px (`--space-12`)
- Landing Section: 80px (`--space-20`) 起

### 5.5 留白哲学

**"呼吸感优先"** — 宁可多留白，不要挤压：
- 卡片之间至少 16px 间距
- 标题与内容之间至少 8px
- 按钮组之间 8px
- 表单字段之间 16px
- 页面内容区上下至少 24px padding

---

## 6. Depth & Elevation（深度与层级）

### 6.1 Shadow System

```css
--shadow-xs:    0 1px 2px rgba(0,0,0,0.3);
--shadow-sm:    0 1px 3px rgba(0,0,0,0.35);
--shadow-md:    0 2px 8px rgba(0,0,0,0.4);
--shadow-lg:    0 4px 16px rgba(0,0,0,0.5);
--shadow-xl:    0 8px 32px rgba(0,0,0,0.6);
--shadow-card:  0 2px 8px rgba(0,0,0,0.4);
--shadow-modal: 0 8px 32px rgba(0,0,0,0.6);
--shadow-glow-indigo: 0 0 20px rgba(99,102,241,0.3);
--shadow-glow-amber:  0 0 20px rgba(212,168,67,0.3);
```

### 6.2 Surface Layers

| 层级 | 背景色 | 用途 |
|------|--------|------|
| 0 — Background | `#0d0f1a` | 页面底色 |
| 1 — Surface | `#151829` | 卡片、面板 |
| 2 — Elevated | `#111327` | 弹窗、下拉菜单 |
| 3 — Overlay | `rgba(0,0,0,0.6)` + blur | 遮罩层 |

### 6.3 Z-index Scale

| 层级 | z-index | 元素 |
|------|---------|------|
| Base | 0 | 内容 |
| Dropdown | 100 | 下拉菜单 |
| Sticky | 200 | 固定导航 |
| Modal Backdrop | 300 | 遮罩 |
| Modal | 400 | 弹窗 |
| Toast | 500 | 通知 |
| Tooltip | 600 | 提示 |

### 6.4 Backdrop Effects

```css
.glass-surface {
  background: rgba(13,15,26,0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06);
}
.glass-elevated {
  background: rgba(17,19,39,0.9);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08);
}
```

---

## 7. Do's and Don'ts（设计规范与禁忌）

### ✅ Do's

1. **色彩克制**: 90% 中性色 + 8% 品牌靛蓝 + 2% 琥珀点缀，不引入第四种彩色
2. **间距一致**: 所有间距必须是 4px 的整数倍，优先用 8px 倍数
3. **过渡必加**: 所有交互元素（按钮/链接/输入框/卡片）必须有 transition
4. **聚焦可见**: 所有可交互元素必须支持 `:focus-visible`，用 indigo 2px 环
5. **状态完备**: 每个组件至少覆盖 default / hover / active / disabled / focus 五个状态
6. **移动优先**: 先设计 mobile 布局，再增强 desktop，触摸目标 ≥ 44px
7. **暗色原生**: 所有组件默认暗色，不做浅色变体，减少维护成本
8. **毛玻璃谨慎用**: 仅导航和弹窗遮罩使用 backdrop-filter，卡片不用

### ❌ Don'ts

1. **禁止纯黑文字**: 即使用在浅色区也不要用 `#000`，至少 `#e8e9f0`
2. **禁止彩色边框**: 边框只用灰阶 (#2a2d45 / #1e2138)，不要用品牌色做边框
3. **禁止突兀阴影**: 不用大偏移量阴影（如 0 10px 50px），保持微妙
4. **禁止纯白背景**: 白色在暗色主题中刺眼，最多用 `#e8e9f0` 文字
5. **禁止自定义滚动条**: 统一用 globals.css 中的 5px 暗色滚动条
6. **禁止大圆角卡片**: 卡片最多 12px，按钮最多 10px，不要用 20px+
7. **禁止无过渡突变**: 颜色/背景/阴影的切换必须有过渡
8. **禁止硬编码色值**: 始终使用 CSS 变量，不用写死 HEX

---

## 8. Responsive Behavior（响应式行为）

### 8.1 Breakpoints

| 断点 | 宽度 | 设备 |
|------|------|------|
| Mobile | < 640px | 手机竖屏 |
| Tablet | 640px - 1024px | 平板/手机横屏 |
| Desktop | 1024px - 1440px | 笔记本/台式 |
| Wide | > 1440px | 大屏/外接显示器 |

### 8.2 Touch Targets

- 最小触摸目标: **44×44px**
- 按钮最小高度: **36px**（desktop）/ **44px**（mobile）
- 列表项最小高度: **44px**（mobile）

### 8.3 折叠策略

| 断点 | Sidebar | BottomNav | 面板布局 |
|------|---------|-----------|----------|
| Mobile | 隐藏 | 显示 (2 主项 + 更多菜单) | 单栏 |
| Tablet | 折叠态 56px | 隐藏 | 可展开侧栏 |
| Desktop | 展开 280px | 隐藏 | 三栏 (workspace) / 双栏 |
| Wide | 展开 280px | 隐藏 | 三栏 + 宽间距 |

### 8.4 Font Scaling

- 基准: 14px / 16px（正文）
- Mobile: 不缩放，Hero 用 `clamp(36px, 8vw, 64px)`
- Desktop Wide: Hero 可达 64px
- 其他字号固定，不随视口变化

---

## 9. Agent Prompt Guide（AI 代理提示指南）

### 9.1 Quick Reference（供 AI 编程代理使用）

```
DESIGN SYSTEM: Moling v3.1
THEME: Dark only (#0d0f1a bg)
PRIMARY: #6366f1 (indigo-500) — buttons, links, focus
ACCENT: #d4a843 (amber) — highlights, rarity
INDIGO-SCALE: 50 #eef2ff → 900 #312e81 (10 阶)
FONT-HEADING: 'Noto Serif SC', serif
FONT-BODY: 'PingFang SC', sans-serif
FONT-MONO: 'JetBrains Mono', monospace
RADIUS: 6px sm, 10px md, 14px lg, 18px xl
SPACING: 8px base, 4px minimum
STYLE: CSS Modules only, NO Tailwind
SHADOW: subtle dark, max 48px blur
GLASS: backdrop-filter blur(12-20px), .glass-panel / .glass-card
PROSE: .prose-editor / .prose-preview, max-width 720px
UTILITY: .text-gradient, .bg-gradient-subtle, .hover-lift, .active-press
```

### 9.2 Component Prompts（可直接复制使用）

#### Prompt 1: 创建新页面
```
创建一个新的墨灵页面。使用 CSS Modules。
背景色: var(--color-bg) = #0d0f1a
文字色: var(--color-text-primary) = #e8e9f0
卡片用: var(--color-surface) = #151829, 边框 var(--color-border) = #2a2d45
圆角: 12px for cards, 8px for inputs/buttons
按钮主色用 var(--color-brand-indigo), 渐变背景
标题用 font-heading (Noto Serif SC), 正文用 font-body
所有交互元素必须有 transition: all 200ms ease
确保响应式：mobile 单栏，desktop 双栏/三栏
```

#### Prompt 2: 创建卡片组件
```
创建一个墨灵暗色卡片组件。
background: #151829
border: 1px solid #2a2d45
border-radius: 12px
padding: 20px
box-shadow: 0 2px 8px rgba(0,0,0,0.4)
hover: border-color → rgba(99,102,241,0.3), 加微光
使用 CSS Modules
需要 default / hover / active 状态
支持 title / subtitle / content / footer 插槽
```

#### Prompt 3: 创建数据表格
```
创建一个暗色主题数据表格。
表头: background #111327, color #9ca3c4, font-size 11px, uppercase
行: background #151829, border-bottom 1px solid #1e2138
hover行: background rgba(99,102,241,0.04)
选中行: background rgba(99,102,241,0.08)
数字列: font-mono, 右对齐
文本列: font-body, 左对齐
分页器在底部，居中
响应式: mobile 端表格横向滚动
```

#### Prompt 4: 创建表单
```
创建一个暗色表单。
输入框: background #111327, border #2a2d45, radius 8px
focus: border #6366f1, box-shadow 0 0 0 3px rgba(99,102,241,0.15)
label: color #9ca3c4, font-size 13px, margin-bottom 6px
必填标记: color #ef4444, 红色 *
错误提示: color #f87171, font-size 12px, margin-top 4px
提交按钮: gradient indigo, 全宽(mobile) / auto(desktop)
字段间距: 16px
使用 FormError 组件显示后端错误
```

#### Prompt 5: 创建导航Tab
```
创建暗色Tab切换组件。
活跃Tab: color #a5b4fc, border-bottom 2px solid #6366f1
非活跃Tab: color #6b7199, border-bottom 2px solid transparent
hover: color #e8e9f0
Tab padding: 12px 20px, font-size 14px
Tab间距: 0 (紧贴排列)
下方内容区 padding: 24px 0
底部指示线动画: transition transform 200ms ease
```

#### Prompt 6: 创建玻璃态面板（v3.1 新增）
```
创建墨灵玻璃态面板组件。使用 CSS Modules。
面板背景: rgba(21,24,41,0.7) + backdrop-filter blur(20px)
边框: 1px solid rgba(255,255,255,0.06)
圆角: var(--radius-lg) = 14px
内容区 padding: 24px
适用场景: 顶部导航栏、底部工具栏、侧边栏
注意: -webkit-backdrop-filter 兼容 Safari
移动端 blur 值降到 12px 以减少性能开销
```

#### Prompt 7: 创建编辑器/阅读排版区（v3.1 新增）
```
创建墨灵写作编辑器排版区。使用 CSS Modules。
编辑区: font-body, 16px, line-height 1.8, max-width 720px 居中
预览区: font-heading (Noto Serif SC), 16px, line-height 1.7
背景: var(--color-surface) = #151829
边框: var(--color-border-subtle) = #1e2138
圆角: var(--radius-md) = 10px
标题层级: h1 28px / h2 22px / h3 18px
引用块: 左侧 3px indigo 边线, italic, color-secondary
光标色: var(--color-brand-indigo) = #6366f1
添加 .text-gradient 类为章节标题加靛蓝渐变
添加 .bg-gradient-subtle 为选中段落加微妙渐变背景
使用 CSS Modules，不用 Tailwind
```

### 9.3 Iteration Guide（AI 生成 UI 的 10 条迭代建议）

1. **先用变量再用硬编码**: 生成组件时第一遍用 CSS 变量名，第二遍确认色值准确
2. **状态覆盖**: 每个组件至少检查 default / hover / active / disabled / focus
3. **间距审查**: 打开浏览器 DevTools，逐一检查 margin/padding 是否为 4px 倍数
4. **暗色验证**: 在暗色背景下检查文字对比度，三级文字必须有 4.5:1 以上
5. **过渡检查**: 鼠标快速划过组件，确认无闪烁、无突变
6. **响应式断点**: 拖动浏览器窗口检查 640px / 1024px / 1440px 三个断点
7. **触摸目标**: mobile 端所有可点击元素不小于 44×44px
8. **无 Tailwind 残留**: 确保 class 中没有 tailwind 类名，全用 CSS Modules
9. **动画性能**: 只用 transform 和 opacity 做动画，避免 width/height 动画
10. **accessibility**: 检查 `:focus-visible` 样式、skip-link、aria-label 完整性
