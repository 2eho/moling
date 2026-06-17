# 墨灵前端布局改造 — 阶段一+二完成报告

## 阶段一：可拖拽面板 ✅

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/hooks/useResizablePanel.ts` | 新建 | 拖拽 hook：rAF 节流、min/max 约束、localStorage 持久化 |
| `src/components/ui/ResizableHandle.tsx` | 新建 | 4px 分隔条、hover 高亮、键盘焦点 |
| `src/components/ui/ResizableHandle.module.css` | 新建 | 垂直/水平方向样式 |
| `src/app/workspace/[projectId]/page.tsx` | 修改 | 集成可拖拽 + ResizableHandle |
| `src/app/workspace/[projectId]/workspace.module.css` | 修改 | 移除固定宽度，inline style 驱动 |

## 阶段二：Sidebar 拆分 ✅

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/components/layout/AppShell.tsx` | 修改 | 工作台页面隐藏 Sidebar（全宽布局） |
| `src/app/workspace/[projectId]/page.tsx` | 修改 | TopBar 加左下/右上功能 |
| `src/app/workspace/[projectId]/workspace.module.css` | 修改 | 新增 TopBar 元素样式 |

### TopBar 最终布局

```
左下角:
  [☰ 面板切换] [← 返回] [▼ 剑来]  [第一章: 开局 ▼]

右上角:
  [🛡] [⚙ 设置] [👤 U ▼] [✦ 面板切换]
```

### 左侧面板宽度
- 默认 280px，可拖拽 200~400px，localStorage 持久化
- 右侧面板宽度
- 默认 300px，可拖拽 220~450px，localStorage 持久化

### 工作台布局
- 全宽三栏，无 Sidebar，编辑区更宽敞
