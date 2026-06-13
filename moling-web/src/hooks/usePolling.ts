"use client";

import { useEffect, useRef } from "react";

/**
 * 轮询工具 hook — 以固定间隔轮询指定函数。
 *
 * @param fn - 轮询执行函数
 * @param interval - 轮询间隔（毫秒），默认 3000
 * @param enabled - 是否启用轮询，默认 true
 *
 * @example
 * ```tsx
 * usePolling(() => fetchStatus(), 5000, isTaskRunning);
 * ```
 */
export function usePolling(
  fn: () => void | Promise<void>,
  interval = 3000,
  enabled = true,
): void {
  const savedFn = useRef(fn);
  savedFn.current = fn;

  useEffect(() => {
    if (!enabled) return;

    const tick = async () => {
      try {
        await savedFn.current();
      } catch {
        // 轮询失败时静默处理，避免频繁报错
      }
    };

    // 立即执行一次
    tick();

    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [interval, enabled]);
}
