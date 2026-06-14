/* ============================================
   墨灵 (Moling) — Unified API Client
   ============================================
   Features:
   - Base URL from NEXT_PUBLIC_API_BASE_URL env
   - Auto-injected Authorization header
   - 401 auto-refresh (token rotation)
   - X-Request-ID on every request
   - Mock mode when NEXT_PUBLIC_MOCK_ENABLED=true
   ============================================ */

import { getAccessToken, getRefreshToken, setTokens, clearAuth } from "./auth";

// ---- Types ----

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestParams = Record<string, string | number | boolean | undefined>;

interface MockHandler {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (...args: any[]): unknown;
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
  // 优先级: NEXT_PUBLIC_API_BASE_URL > NEXT_PUBLIC_API_URL (旧) > fallback
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000/api/v1"
  );
}

function isMockEnabled(): boolean {
  return process.env.NEXT_PUBLIC_MOCK_ENABLED === "true";
}

function buildUrl(path: string, params?: RequestParams): string {
  // path already includes /api/v1 prefix from env, so we just append
  const baseUrl = getBaseUrl();
  // Remove trailing slash from base + ensure path starts with /
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${normalizedBase}${normalizedPath}`);

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
    const baseUrl = getBaseUrl();
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

  let response: Response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (fetchError) {
    // 网络不可达 / DNS 解析失败 / CORS 被拦截 等
    const reason =
      fetchError instanceof TypeError
        ? `无法连接到服务器 (${url}) — 请检查网络或 API 地址配置`
        : `请求失败: ${(fetchError as Error).message}`;
    throw new Error(reason);
  }

  // ---- 401 Auto-Refresh ----
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await tryRefreshToken();
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
      throw new Error("认证已过期，请重新登录");
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
    const message =
      (data as Record<string, unknown>)?.message ??
      `请求失败 (${response.status})`;
    throw new Error(message as string);
  }

  return data;
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
