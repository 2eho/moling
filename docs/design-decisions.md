# 设计决策记录 — 墨灵 (Moling)

> 只记「为什么」，不记「怎么做」。实际设计系统 → `moling-web/src/app/globals.css`

---

## 1. 品牌哲学

墨灵是 AI 驱动的网文创作平台。视觉语言传达 **沉静 × 专注 × 智慧**：
- 暗色基底让人沉入创作心流
- 靛蓝色光晕暗示 AI 智能的跃动
- 琥珀金点缀如书页烫金，唤起文学质感

关键词：`沉静` `锐利` `文学质感` `玻璃态` `微光`

## 2. 色彩系统（2026-06-20 更新 — 8 主题驱动）

**不再使用单一品牌色板。** 墨灵 Vibe Writing 采用 8 套经典主题，每套独立定义完整的 `--th-*` CSS 变量族，用户可自由切换。

| 分类 | 主题 | ID | 基调 |
|------|------|----|------|
| 暗色 | 墨灵·深空 | `moling` | 深靛蓝 + 琥珀金，默认主题 |
| 暗色 | Nord | `nord` | 极地冷蓝，低饱和，长写不刺眼 |
| 暗色 | One Dark | `onedark` | Atom 传承，钢蓝灰，柔和层次 |
| 暗色 | Dracula | `dracula` | 暗紫霓虹，高对比，神秘深邃 |
| 暗色 | Solarized Dark | `solarized-dark` | 色彩科学，青绿底，学术基准 |
| 亮色 | Solarized Light | `solarized-light` | 暖纸白，蓝灰字，全天候 |
| 亮色 | Paper | `paper` | 纸张质感，暖米色，沉浸式写作 |
| 亮色 | GitHub Light | `github-light` | 纯白底，蓝强调，结构化 |

**驱动机制**：`<html data-theme="moling">` → `[data-theme]` CSS 选择器注入全部 `--th-*` 变量。

**设计约束**：
- 零硬编码色值 — 所有颜色通过 `--th-*` 引用
- 主题切换 `Ctrl+Shift+T`，localStorage 持久化
- 每套主题必须提供 30+ `--th-*` token，覆盖背景/文字/边框/强调/Option/A/B/C/滚动条
- 新增组件不得引入新的硬编码颜色

**旧品牌色约束已废止**：90%灰+8%靛蓝+2%琥珀的公式已不适用，因为每套主题有自己的色彩语言。

## 3. 字体选择

| 角色 | 字体 | 为什么 |
|------|------|--------|
| 标题 | Noto Serif SC（衬线） | 文学仪式感，与网文创作属性呼应 |
| 正文 | PingFang SC（无衬线） | 屏幕可读性最佳，14px 基准 |
| 代码/数据 | JetBrains Mono（等宽） | 字数统计、版本号、代码片段 |

正文行高：1.6（长文阅读不疲劳）

## 4. 布局原则

- **8px 基数间距** — 所有间距 4px 或 8px 的整数倍
- **12 列网格** — max 1200px 内容区，1280px Landing
- **呼吸感优先** — 卡片间距 ≥16px，标题与内容 ≥8px，按钮组 8px
- **移动优先** — 触摸目标 ≥44px，mobile 单栏 → desktop 多栏

## 5. 交互约束

- 所有交互元素必须有 `transition: all 200ms ease`
- Focus 状态必须可见（`:focus-visible` 靛蓝 2px 环）
- 每个组件覆盖 5 状态：default / hover / active / disabled / focus
- 动画只用 `transform` + `opacity`，不用 `width/height`（性能）

## 6. 已废弃的旧决策

| 旧决策 | 原因 | 当前做法 |
|--------|------|----------|
| 「CSS Modules only，禁 Tailwind」 | 开发效率低，Tailwind v4 更好用 | 纯 Tailwind v4 utility classes |
| 「暗色 only」 | 用户需要亮色阅读 | 8 主题（5 暗色 + 3 亮色），任意切换 |
| 「--color-brand-indigo 命名」 | 名字太长，且单主题无法覆盖 | `--th-*` 通用语义变量（th-text / th-accent / th-border…） |
| 「DESIGN.md v3.1 固定色板」 | 8 主题各有独立色板，单一色板无法覆盖 | 每套主题独立定义 30+ `--th-*` token |
| 「Tailwind @theme 令牌」 | `--th-*` CSS 变量 + [data-theme] 选择器更灵活 | CSS 变量驱动，Tailwind 类通过 `var(--th-*)` 引用 |

---

> **设计在代码中，不在这里。** 完整 token 定义见 `moling-web/src/app/globals.css`
