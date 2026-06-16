/* ============================================
   墨灵 (Moling) — Unified API Client
   ============================================
   Features:
   - Base URL from NEXT_PUBLIC_API_BASE_URL env
   - Auto-injected Authorization header
   - 401 auto-refresh (token rotation)
   - X-Request-ID on every request
   - Mock mode when NEXT_PUBLIC_MOCK_ENABLED=true
   - GET 请求去重（并发重复请求合并）
   - GET 请求结果缓存（TTL 可配置）
   - AbortController 支持
   ============================================ */

import { getAccessToken, getRefreshToken, setTokens, clearAuth } from "./auth";

// ---- Custom Error Class ----

/**
 * 结构化 API 错误，包含状态码、错误信息和字段级验证错误。
 */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly message: string,
    public readonly errors: Record<string, string> | null = null,
    public readonly data: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---- Types ----

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestParams = Record<string, string | number | boolean | undefined>;

interface MockHandler {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (...args: any[]): unknown;
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

// ---- Mock Registry ----

const mockHandlers = new Map<string, MockHandler>();

/**
 * Register a mock handler for development / testing.
 * The key format is `${METHOD}:${path}` (e.g. "GET:/projects").
 */
export function registerMock(pattern: string, handler: MockHandler): void {
  mockHandlers.set(pattern, handler);
}

// ---- 请求去重（Deduplication） ----
// 同一 URL 的并发 GET 请求只发一次，所有调用者共享同一个 Promise

const inflightRequests = new Map<string, Promise<unknown>>();

function deduplicateKey(method: HttpMethod, path: string, params?: RequestParams): string {
  const url = buildUrl(path, params);
  return `${method}:${url}`;
}

// ---- 响应缓存（Response Cache） ----
// 只缓存 GET 请求，默认 TTL = 5000ms

const responseCache = new Map<string, CacheEntry<unknown>>();
const DEFAULT_CACHE_TTL = 5_000; // 5 seconds

function getCacheKey(method: HttpMethod, path: string, params?: RequestParams): string {
  return deduplicateKey(method, path, params);
}

function getFromCache<T>(key: string): T | null {
  const entry = responseCache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;
  if (Date.now() - entry.timestamp > DEFAULT_CACHE_TTL) {
    responseCache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache<T>(key: string, data: T): void {
  responseCache.set(key, { data, timestamp: Date.now() });
  // 缓存数量控制：超过 50 条时清理最旧的
  if (responseCache.size > 50) {
    const oldest = responseCache.keys().next().value;
    if (oldest) responseCache.delete(oldest);
  }
}

/**
 * 清空缓存（在登出或需要强制刷新时调用）
 */
export function clearApiCache(): void {
  responseCache.clear();
  inflightRequests.clear();
}

// ---- Internal Helpers ----

function generateRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getBaseUrl(): string {
  // 使用相对路径，由 Nginx 反代到后端
  // 优先级: NEXT_PUBLIC_API_BASE_URL > 相对路径 fallback
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl) {
    // 如果设置了环境变量，确保是相对路径（以 / 开头）
    if (envUrl.startsWith("/")) {
      return envUrl;
    }
    // 如果是完整 URL，提取路径部分
    try {
      const url = new URL(envUrl);
      return url.pathname.replace(/\/+$/, "");
    } catch {
      // 忽略解析错误，继续使用默认值
    }
  }
  
  // 默认使用相对路径（由 Nginx 反代）
  return "/moling/api/v1";
}

function isMockEnabled(): boolean {
  return process.env.NEXT_PUBLIC_MOCK_ENABLED === "true";
}

function buildUrl(path: string, params?: RequestParams): string {
  const baseUrl = getBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  // Helper to append query params to a URL string
  function appendParams(url: string): string {
    if (!params) return url;
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) search.append(key, String(value));
    });
    const qs = search.toString();
    return qs ? `${url}?${qs}` : url;
  }

  // 情况 A: baseUrl 为空 → 相对路径（无前缀）
  if (!baseUrl) {
    return appendParams(normalizedPath);
  }

  const normalizedBase = baseUrl.replace(/\/+$/, "");

  // 情况 B: baseUrl 以 / 开头 → 带前缀的相对路径（如 /moling/api/v1）
  if (baseUrl.startsWith("/")) {
    // 注意：这里不能使用 new URL()，因为不包含 host
    // 直接用字符串拼接，浏览器会自动解析为相对于当前 origin 的 URL
    const url = `${normalizedBase}${normalizedPath}`;
    return appendParams(url);
  }

  // 情况 C: baseUrl 是完整 URL（http://...）→ 绝对路径
  // 适用于开发环境（前后端不同端口）或前后端不同域
  const fullUrl = `${normalizedBase}${normalizedPath}`;
  const url = new URL(fullUrl);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns `true` on success (tokens updated in localStorage), `false` otherwise.
 */
async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    // 使用相对路径，由 Nginx 反代
    const baseUrl = getBaseUrl(); // 返回 /moling/api/v1
    const response = await fetch(`${baseUrl}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": generateRequestId(),
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    const { access_token, refresh_token } = data.data ?? data;

    if (access_token && refresh_token) {
      setTokens(access_token, refresh_token);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

// ---- Token Refresh 防并发 ----
let refreshPromise: Promise<boolean> | null = null;

async function tryRefreshTokenDeduped(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = tryRefreshToken().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

/**
 * Core request function.
 */
async function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  params?: RequestParams,
): Promise<T> {
  const requestId = generateRequestId();

  // ---- Mock Mode ----
  if (isMockEnabled()) {
    const mockKey = `${method}:${path}`;
    const handler = mockHandlers.get(mockKey);
    if (handler) {
      return handler(body, params) as T;
    }
  }

  // ---- GET 请求缓存命中 ----
  if (method === "GET") {
    const cacheKey = getCacheKey(method, path, params);
    const cached = getFromCache<T>(cacheKey);
    if (cached !== null) {
      return cached;
    }
  }

  // ---- GET 请求去重（并发重复请求合并） ----
  if (method === "GET") {
    const dedupKey = deduplicateKey(method, path, params);
    const inflight = inflightRequests.get(dedupKey);
    if (inflight) {
      return inflight as Promise<T>;
    }
  }

  // ---- Build Headers ----
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-ID": requestId,
  };

  const accessToken = getAccessToken();
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  // ---- Build URL & Fetch ----
  const url = buildUrl(path, params);

  const fetchOptions: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined && method !== "GET") {
    fetchOptions.body = JSON.stringify(body);
  }

  // 创建实际请求的 Promise
  const executeFetch = async (): Promise<T> => {
    let response: Response;
    try {
      response = await fetch(url, fetchOptions);
    } catch (fetchError) {
      // 网络不可达 / DNS 解析失败 / CORS 被拦截 等
      const reason =
        fetchError instanceof TypeError
          ? `无法连接到服务器 (${url}) — 请检查网络或 API 地址配置`
          : `请求失败: ${(fetchError as Error).message}`;

      if (process.env.NODE_ENV === "development") {
        console.error("[API Error] Network error:", reason, fetchError);
      }

      throw new ApiError(0, reason);
    }

    // ---- 401 Auto-Refresh（防并发） ----
    if (response.status === 401 && getRefreshToken()) {
      const refreshed = await tryRefreshTokenDeduped();
      if (refreshed) {
        // Retry original request with new token
        headers["Authorization"] = `Bearer ${getAccessToken()}`;
        response = await fetch(url, { ...fetchOptions, headers });
      } else {
        // Refresh failed — clear auth and redirect
        clearAuth();
        if (typeof window !== "undefined") {
          window.location.href = "/auth";
        }
        throw new ApiError(401, "认证已过期，请重新登录");
      }
    }

    // ---- Parse Response ----
    let data: T;
    try {
      data = (await response.json()) as T;
    } catch {
      data = {} as T;
    }

    if (!response.ok) {
      // 提取错误信息（支持多种后端响应格式）
      const dataObj = data as Record<string, unknown>;
      const errorMessage =
        (dataObj?.message as string) ||
        (dataObj?.detail as string) ||
        `请求失败 (${response.status})`;

      // 提取字段级验证错误（支持 errors 和 validation_errors 两种格式）
      const rawErrors =
        (dataObj?.errors as Record<string, string>) ||
        (dataObj?.validation_errors as Record<string, string>) ||
        null;

      if (process.env.NODE_ENV === "development") {
        console.error("[API Error]", {
          status: response.status,
          message: errorMessage,
          errors: rawErrors,
          data,
        });
      }

      throw new ApiError(response.status, errorMessage, rawErrors, data);
    }

    return data;
  };

  // ---- 执行请求（GET 去重） ----
  const dedupKey = deduplicateKey(method, path, params);
  const promise = executeFetch().finally(() => {
    // 请求完成后从去重 Map 中移除
    if (method === "GET") {
      inflightRequests.delete(dedupKey);
    }
  });

  if (method === "GET") {
    inflightRequests.set(dedupKey, promise);

    // 写入缓存
    promise.then((data) => {
      const cacheKey = getCacheKey(method, path, params);
      setCache(cacheKey, data);
    }).catch(() => {
      // 请求失败不缓存
    });
  }

  return promise;
}

// ---- Public API ----

export const apiClient = {
  get<T>(path: string, params?: RequestParams): Promise<T> {
    return request<T>("GET", path, undefined, params);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PUT", path, body);
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, body);
  },

  delete<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },
};
