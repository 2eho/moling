import { apiPost } from "./client";

let refreshPromise: Promise<string> | null = null;

/**
 * 获取 access_token。
 * 改为 httpOnly Cookie 后，JS 无法读取 token 值，始终返回 null。
 * 客户端不再直接使用 token 值 —— 所有请求通过 cookie 自动携带。
 * 待后端 Set-Cookie 后生效。
 */
export function getAccessToken(): null {
  // httpOnly cookie 中，JS 不可读
  return null;
}

/**
 * 获取 refresh_token。
 * 改为 httpOnly Cookie 后，JS 无法读取 token 值，始终返回 null。
 * 待后端 Set-Cookie 后生效。
 */
export function getRefreshToken(): null {
  // httpOnly cookie 中，JS 不可读
  return null;
}

/**
 * 设置 token。改为 httpOnly Cookie 方案后，token 由后端通过 Set-Cookie 设置，
 * 前端无需手动存储，此函数为空操作。
 */
export function setTokens(_accessToken?: string, _refreshToken?: string): void {
  // token 由后端 Set-Cookie 管理，前端无需操作
}

/**
 * 清除 token。调用后端 /auth/logout 接口，由后端清除 httpOnly Cookie。
 */
export async function clearTokens(): Promise<void> {
  refreshPromise = null;
  try {
    await apiPost("/auth/logout");
  } catch {
    // 即使 logout 失败也要清除本地状态
  }
}

/**
 * 刷新 access_token。通过 cookie 自动携带 refresh_token，无需手动传参。
 * 待后端 Set-Cookie 后生效。
 */
export async function refreshAccessToken(): Promise<string> {
  // 去重：多个并发请求共享同一个刷新
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    // refresh_token 由 httpOnly cookie 自动携带，无需手动获取
    try {
      const res = await apiPost<{
        access_token: string;
        refresh_token?: string;
      }>("/auth/refresh");

      // 后端通过 Set-Cookie 设置新的 token，前端无需手动管理
      return res.access_token;
    } catch (error) {
      // 刷新失败，尝试清除 cookie（调用 logout）
      try {
        await apiPost("/auth/logout");
      } catch {
        // ignore
      }
      throw error;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * 判断 JWT token 是否已过期（仅客户端检查 exp claim）。
 * 用于中间件无法覆盖的场景下，前端自行判断是否需要跳转登录页。
 */
export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    if (!payload.exp) return false;
    // exp 单位是秒，加 30 秒缓冲
    return Date.now() / 1000 > payload.exp - 30;
  } catch {
    return true;
  }
}
