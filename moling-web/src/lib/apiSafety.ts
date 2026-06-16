/**
 * API 响应安全处理工具
 * 
 * 确保所有 API 响应都有安全的默认值，
 * 防止 `Cannot read properties of undefined` 错误。
 */

import type { ApiResponse } from "@/lib/types";

/**
 * 安全地从一个可能 undefined 的值获取数组
 * @param value - 可能的值
 * @param defaultValue - 默认空数组
 * @returns 确保是数组
 * 
 * @example
 * // ✅ 安全：即使 res.data 是 undefined，也返回 []
 * const projects = safeArray(res.data);
 * 
 * // ✅ 可以指定默认值
 * const projects = safeArray(res.data, []);
 */
export function safeArray<T>(value: T[] | undefined | null, defaultValue: T[] = []): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  
  if (process.env.NODE_ENV === "development") {
    console.warn("[safeArray] Expected array but got:", value);
  }
  
  return defaultValue;
}

/**
 * 安全地从一个可能 undefined 的值获取对象
 * @param value - 可能的值
 * @param defaultValue - 默认 null
 * @returns 确保是对象或 null
 * 
 * @example
 * const project = safeObject<Project>(res.data);
 */
export function safeObject<T>(
  value: T | undefined | null,
  defaultValue: T | null = null,
): T | null {
  if (value === undefined || value === null) {
    return defaultValue;
  }
  
  return value;
}

/**
 * 安全地从一个 API 响应中提取数据
 * @param response - API 响应（格式：{ code, data, message }）
 * @param defaultValue - 默认值
 * @returns 安全的数据
 * 
 * @example
 * // ✅ 安全获取数组
 * const projects = safeResponseData(res, []);
 * 
 * // ✅ 安全获取对象
 * const project = safeResponseData(res, null);
 */
export function safeResponseData<T>(
  response: ApiResponse<T> | undefined,
  defaultValue: T,
): T {
  if (!response) {
    if (process.env.NODE_ENV === "development") {
      console.warn("[safeResponseData] Response is undefined, using default value");
    }
    return defaultValue;
  }

  // 后端返回格式：{ code: 0, data: T, message: "success" }
  // apiClient 返回完整响应，所以 response.data 是实际数据
  const data = (response as any).data;
  
  if (data === undefined || data === null) {
    if (process.env.NODE_ENV === "development") {
      console.warn("[safeResponseData] Response data is undefined, using default value");
    }
    return defaultValue;
  }

  return data;
}

/**
 * 安全地从一个 API 响应中提取分页数据
 * @param response - API 响应（格式：{ code, data: { items: [], total: number } }）
 * @returns { items: [], total: 0 }
 * 
 * @example
 * const { items, total } = safePaginatedData(res);
 * // items 永远是数组，total 永远是数字
 */
export function safePaginatedData<T>(
  response: ApiResponse<{ items: T[]; total: number }> | undefined,
): { items: T[]; total: number } {
  if (!response) {
    return { items: [], total: 0 };
  }

  const data = (response as any).data;
  
  if (!data) {
    return { items: [], total: 0 };
  }

  return {
    items: safeArray(data.items),
    total: typeof data.total === "number" ? data.total : 0,
  };
}

/**
 * 安全地处理 Promise rejection
 * @param promise - Promise
 * @param defaultValue - 默认值和错误信息
 * @returns [data, error]
 * 
 * @example
 * const [projects, error] = await safeAsync(projectApi.list(), []);
 * if (error) { console.error(error); }
 * // projects 永远是数组
 */
export async function safeAsync<T>(
  promise: Promise<T>,
  defaultValue: T,
): Promise<[T, null] | [null, Error]> {
  try {
    const data = await promise;
    return [data, null];
  } catch (error) {
    if (process.env.NODE_ENV === "development") {
      console.error("[safeAsync] Promise rejected:", error);
    }
    return [defaultValue, error instanceof Error ? error : new Error(String(error))] as [T, null] | [null, Error];
  }
}

/**
 * React Hook：安全地获取 API 数据
 * @param fetchFn - 获取数据的函数
 * @param defaultValue - 默认值
 * @returns { data, loading, error, refetch }
 * 
 * @example
 * const { data: projects, loading, error } = useSafeFetch(
 *   () => projectApi.list(),
 *   [],
 * );
 * // projects 永远是数组，不会是 undefined
 */
export function useSafeFetch<T>(
  fetchFn: () => Promise<T>,
  defaultValue: T,
  deps: any[] = [],
) {
  const [data, setData] = useState<T>(defaultValue);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const result = await fetchFn();
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setData(defaultValue);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    
    fetchFn()
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err : new Error(String(err)));
        setData(defaultValue);
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchFn, defaultValue]);

  return { data, loading, error, refetch };
}

// ──────────────────────────────────────────────────
// 导入 useState, useEffect, useCallback 用于 useSafeFetch
// ──────────────────────────────────────────────────
import { useState, useEffect, useCallback } from "react";
