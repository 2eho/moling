/* ============================================
   墨灵 (Moling) — Token & Auth Utilities
   ============================================ */

const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  REFRESH_TOKEN: "refresh_token",
  USER: "user",
} as const;

/**
 * Retrieve the access token from localStorage.
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Retrieve the refresh token from localStorage.
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Retrieve the serialized user object from localStorage.
 */
export function getUser<T = unknown>(): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.USER);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/**
 * Store access and refresh tokens in localStorage.
 */
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, access);
  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh);
}

/**
 * Store the user object in localStorage (serialized as JSON).
 */
export function setUser<T>(user: T): void {
  localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
}

/**
 * Remove all authentication data from localStorage.
 */
export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.USER);
}

/**
 * Check whether the user has a valid (non-expired) access token.
 *
 * Decodes the JWT payload and compares the `exp` claim with the current time.
 * Returns `false` if no token exists, the token is malformed, or it is expired.
 */
export function isAuthenticated(): boolean {
  const token = getAccessToken();
  if (!token) return false;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const exp = payload.exp as number;
    if (Date.now() >= exp * 1000) {
      // Token expired — clean up
      clearAuth();
      return false;
    }
    return true;
  } catch {
    // Malformed token — clean up
    clearAuth();
    return false;
  }
}
