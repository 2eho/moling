"use client";

import { useState, useEffect } from "react";

/**
 * 防抖 hook — 延迟更新值，直到指定间隔内无变化。
 *
 * @param value - 需要防抖的值
 * @param delay - 延迟毫秒数，默认 300
 * @returns 防抖后的值
 *
 * @example
 * ```tsx
 * const debouncedSearch = useDebounce(searchTerm, 500);
 * ```
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
