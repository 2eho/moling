"use client";

import { useState, useRef, useCallback, useEffect } from "react";

/**
 * 可拖拽面板的配置选项。
 */
export interface UseResizablePanelOptions {
  /** localStorage 存储键名 */
  storageKey: string;
  /** 默认宽度（px） */
  defaultWidth: number;
  /** 最小宽度（px） */
  minWidth: number;
  /** 最大宽度（px） */
  maxWidth: number;
  /** 方向: 'left' 表示左侧面板（从右边拖拽）, 'right' 表示右侧面板（从左边拖拽） */
  side: "left" | "right";
}

/**
 * useResizablePanel 的返回值。
 */
export interface UseResizablePanelReturn {
  /** 当前面板宽度 */
  width: number;
  /** 是否正在拖拽 */
  isResizing: boolean;
  /** 拖拽开始的处理器（绑定到 ResizableHandle 的 onMouseDown） */
  onResizeStart: (e: React.MouseEvent) => void;
  /** 重置为默认宽度 */
  resetWidth: () => void;
}

// ---------------------------------------------------------------------------
// 内部常量
// ---------------------------------------------------------------------------

/** localStorage key 前缀 */
const STORAGE_PREFIX = "moling:workspace:";

// ---------------------------------------------------------------------------
// 内部工具函数
// ---------------------------------------------------------------------------

/**
 * 从 localStorage 读取宽度值，解析失败或不存在时返回 fallback。
 */
function loadWidth(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const value = Number(raw);
    return Number.isFinite(value) ? value : fallback;
  } catch {
    return fallback;
  }
}

/**
 * 将宽度值写入 localStorage。
 */
function saveWidth(key: string, width: number): void {
  try {
    localStorage.setItem(key, String(Math.round(width)));
  } catch {
    // 存储空间满或不可用 — 静默失败
  }
}

/**
 * 将数值限制在 [min, max] 闭区间内。
 */
function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/**
 * 根据 side 方向计算鼠标拖拽后的新面板宽度。
 *
 * - `side="left"` ：手柄在面板右侧，拖拽向右↗ 增加宽度
 * - `side="right"`：手柄在面板左侧，拖拽向右↗ 减少宽度
 */
function computePanelWidth(
  side: "left" | "right",
  startWidth: number,
  startX: number,
  currentX: number,
): number {
  const delta = currentX - startX;
  return side === "left" ? startWidth + delta : startWidth - delta;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * `useResizablePanel` — 实现类似 VS Code 的可拖拽面板宽度调整 hook。
 *
 ### 拖拽行为
 - `side="left"`：手柄在面板**右**边缘，向右拖拽↗ 增加宽度
 - `side="right"`：手柄在面板**左**边缘，向右拖拽↗ 减少宽度
 - 拖拽过程中通过 `requestAnimationFrame` 节流更新，保证性能
 - 自动在 `document.body` 上设置 `user-select: none` 和 `cursor: col-resize`，
   防止拖拽时文本被选中
 - 结束后自动恢复 body 样式并移除全局事件监听

 ### 持久化
 - 每次拖拽结束自动将宽度写入 `localStorage`
 - 组件 mount 时从 `localStorage` 读取恢复（fallback 到 `defaultWidth`）
 - storage key 格式：`moling:workspace:${storageKey}`

 ### 清理
 - `useEffect` 清理函数移除所有 `document` 上挂载的事件监听，防止内存泄露

 @param options - 配置项
 @param options.storageKey - localStorage 存储键名
 @param options.defaultWidth - 默认宽度（px）
 @param options.minWidth - 最小宽度（px）
 @param options.maxWidth - 最大宽度（px）
 @param options.side - 面板方向

 @returns 包含当前宽度、拖拽状态及操作方法的对象

 @example
 ```ts
 const leftPanel = useResizablePanel({
   storageKey: "leftPanelWidth",
   defaultWidth: 280,
   minWidth: 200,
   maxWidth: 400,
   side: "left",
 });

 // 在组件中使用:
 // <div style={{ width: leftPanel.width, position: "relative" }}>
 //   <ResizableHandle onMouseDown={leftPanel.onResizeStart} />
 // </div>
 ```
 */
export function useResizablePanel(
  options: UseResizablePanelOptions,
): UseResizablePanelReturn {
  const { storageKey, defaultWidth, minWidth, maxWidth, side } = options;

  // ---- 响应式状态 ----

  const [width, setWidth] = useState<number>(() => {
    const fullKey = `${STORAGE_PREFIX}${storageKey}`;
    return loadWidth(fullKey, defaultWidth);
  });
  const [isResizing, setIsResizing] = useState(false);

  // ---- Ref（避免闭包陷阱 + 减少不必要的 re-render） ----

  /** 鼠标按下时的 clientX */
  const startXRef = useRef(0);
  /** 鼠标按下时的面板宽度 */
  const startWidthRef = useRef(0);
  /** 在拖拽过程中保持最新宽度的 ref，用于 mouseup 持久化 */
  const currentDragWidthRef = useRef(0);
  /** requestAnimationFrame 的 ID，用于取消 */
  const rafIdRef = useRef<number | null>(null);

  // 用 ref 同步配置项，保证事件处理函数里拿到的是最新值
  const optionsRef = useRef({ minWidth, maxWidth, side, storageKey });
  useEffect(() => {
    optionsRef.current = { minWidth, maxWidth, side, storageKey };
  }, [minWidth, maxWidth, side, storageKey]);

  // ---- 持久化：mount 时检查数据一致性 ----

  useEffect(() => {
    const fullKey = `${STORAGE_PREFIX}${storageKey}`;
    const stored = loadWidth(fullKey, defaultWidth);
    if (stored !== width) {
      saveWidth(fullKey, width);
    }
    // 仅在 mount 时执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 全局事件：mousemove ----

  /**
   * 拖拽移动处理函数。
   * 使用 `requestAnimationFrame` 节流，保证每帧最多更新一次 UI。
   */
  const handleMouseMove = useCallback((e: MouseEvent) => {
    // 已有一个待执行的 rAF，跳过
    if (rafIdRef.current !== null) return;

    rafIdRef.current = requestAnimationFrame(() => {
      rafIdRef.current = null;

      const opts = optionsRef.current;
      const newWidth = clamp(
        computePanelWidth(
          opts.side,
          startWidthRef.current,
          startXRef.current,
          e.clientX,
        ),
        opts.minWidth,
        opts.maxWidth,
      );

      currentDragWidthRef.current = newWidth;
      setWidth(newWidth);
    });
  }, []);

  // ---- 全局事件：mouseup ----

  /**
   * 拖拽结束处理函数。
   * 清理事件监听、恢复 body 样式、持久化宽度。
   */
  const handleMouseUp = useCallback(() => {
    // 取消待执行的回调
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }

    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);

    document.body.style.userSelect = "";
    document.body.style.cursor = "";

    setIsResizing(false);

    // 持久化（保存拖拽中最后一次更新的值）
    saveWidth(
      `${STORAGE_PREFIX}${optionsRef.current.storageKey}`,
      currentDragWidthRef.current,
    );
  }, [handleMouseMove]);

  // ---- 暴露给组件的方法 ----

  /**
   * 拖拽开始处理函数 — 绑定到 ResizableHandle 的 `onMouseDown`。
   *
   * - 记录鼠标起始位置和面板起始宽度
   * - 在 `document` 上挂载 `mousemove` / `mouseup` 全局监听
   * - 设置 body 样式防止拖拽过程中意外选中文本
   */
  const onResizeStart = useCallback(
    (e: React.MouseEvent): void => {
      // 只响应鼠标左键
      if (e.button !== 0) return;

      e.preventDefault();

      const fullKey = `${STORAGE_PREFIX}${storageKey}`;
      const currentWidth = loadWidth(fullKey, defaultWidth);

      startXRef.current = e.clientX;
      startWidthRef.current = currentWidth;
      currentDragWidthRef.current = currentWidth;

      setWidth(currentWidth);
      setIsResizing(true);

      // 防止拖拽时文本被选中；不设置 pointer-events 以免影响 document 事件冒泡
      document.body.style.userSelect = "none";
      document.body.style.cursor = "col-resize";

      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    },
    [storageKey, defaultWidth, handleMouseMove, handleMouseUp],
  );

  /**
   * 重置面板宽度为 `defaultWidth`，并持久化。
   */
  const resetWidth = useCallback((): void => {
    const clamped = clamp(defaultWidth, minWidth, maxWidth);
    setWidth(clamped);
    saveWidth(`${STORAGE_PREFIX}${storageKey}`, clamped);
  }, [defaultWidth, minWidth, maxWidth, storageKey]);

  // ---- 清理 ----

  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
  }, [handleMouseMove, handleMouseUp]);

  return {
    width,
    isResizing,
    onResizeStart,
    resetWidth,
  };
}
