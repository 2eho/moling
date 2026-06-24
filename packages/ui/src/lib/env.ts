/**
 * Environment configuration — dual mode (Web + Tauri Desktop)
 *
 * Web mode (Vite): VITE_* env vars injected at build time via import.meta.env
 * Tauri mode (static export): same VITE_* from .env.tauri, plus runtime Tauri detection
 */

// Detect Tauri runtime environment (works in both modes)
const isTauriRuntime = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;

// Detect Tauri build mode (VITE_TAURI_BUILD=true set during Tauri build)
const isTauriBuild = import.meta.env.VITE_TAURI_BUILD === "true";

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  skipAuth: import.meta.env.VITE_SKIP_AUTH === "true",
  mockEnabled: import.meta.env.VITE_MOCK_ENABLED === "true",
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  isTauri: isTauriRuntime,
  isTauriBuild,
  sentryDsn: import.meta.env.VITE_SENTRY_DSN || "",
} as const;
