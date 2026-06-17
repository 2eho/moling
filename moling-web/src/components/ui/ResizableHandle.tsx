"use client";

import { memo, type ComponentProps } from "react";
import styles from "./ResizableHandle.module.css";

interface ResizableHandleProps extends ComponentProps<"div"> {
  /** 拖拽方向 — 影响鼠标图标和视觉指示 */
  direction?: "vertical" | "horizontal";
  /** 是否正在拖拽中 */
  active?: boolean;
}

/**
 * ResizableHandle — 可拖拽面板之间的分隔条。
 *
 * 用法:
 * ```tsx
 * <ResizableHandle onMouseDown={onResizeStart} active={isResizing} />
 * ```
 *
 * 视觉行为:
 * - 默认: 4px 宽的半透明条，hover 时品牌色高亮
 * - 拖拽中: 品牌色高亮 + 持续态
 * - 内部有一个 2px 宽的视觉指示线（居中）
 */
export const ResizableHandle = memo<ResizableHandleProps>(
  function ResizableHandle({
    direction = "vertical",
    active = false,
    className = "",
    ...props
  }) {
    const cls = [
      styles.handle,
      direction === "vertical" ? styles.vertical : styles.horizontal,
      active ? styles.active : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div
        className={cls}
        role="separator"
        aria-orientation={direction === "vertical" ? "vertical" : "horizontal"}
        aria-label="拖拽调整面板宽度"
        tabIndex={0}
        {...props}
      >
        <div className={styles.indicator} />
      </div>
    );
  },
);
