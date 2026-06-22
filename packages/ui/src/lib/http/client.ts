import { env } from "@/lib/env";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeout?: number;
}

/**
 * Resolve the full API URL.
 * - Web mode: uses Next.js rewrites (relative path → proxy to backend)
 * - Tauri mode: uses absolute URL to local backend
 */
function resolveApiUrl(path: string): string {
  const base = env.apiBaseUrl;

  // In Tauri (build-time or runtime) with relative base URL, default to local backend
  if ((env.isTauriBuild || env.isTauri) && base.startsWith("/")) {
    return `http://127.0.0.1:8000${base}${path}`;
  }

  return `${base}${path}`;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  const url = resolveApiUrl(path);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers,
  };
  // token 改为 httpOnly Cookie 自动携带，不再手动设置 Authorization header
  // 待后端 Set-Cookie 后生效

  const controller = new AbortController();
  const timeoutId = options?.timeout
    ? setTimeout(() => controller.abort(), options.timeout)
    : undefined;

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: options?.signal || controller.signal,
      credentials: "include",
    });

    if (timeoutId) clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData: unknown;
      try {
        errorData = await response.json();
      } catch {
        errorData = await response.text();
      }
      throw new ApiError(
        response.status,
        `HTTP ${response.status}: ${response.statusText}`,
        errorData
      );
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return response.json();
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "请求超时");
    }
    throw new ApiError(
      0,
      error instanceof Error ? error.message : "网络请求失败"
    );
  }
}

export async function apiGet<T>(
  path: string,
  options?: RequestOptions
): Promise<T> {
  return request<T>("GET", path, undefined, options);
}

export async function apiPost<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>("POST", path, body, options);
}

export async function apiPut<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>("PUT", path, body, options);
}

export async function apiPatch<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>("PATCH", path, body, options);
}

export async function apiDelete<T>(
  path: string,
  options?: RequestOptions
): Promise<T> {
  return request<T>("DELETE", path, undefined, options);
}
