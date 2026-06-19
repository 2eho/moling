import { apiPost } from "./client";

let refreshPromise: Promise<string> | null = null;

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

export function setTokens(accessToken: string, refreshToken?: string): void {
  localStorage.setItem("access_token", accessToken);
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
}

export function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  refreshPromise = null;
}

export async function refreshAccessToken(): Promise<string> {
  // 去重：多个并发请求共享同一个刷新
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    try {
      const res = await apiPost<{
        access_token: string;
        refresh_token?: string;
      }>("/auth/refresh", { refresh_token: refreshToken });

      setTokens(res.access_token, res.refresh_token);
      return res.access_token;
    } catch (error) {
      clearTokens();
      throw error;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
