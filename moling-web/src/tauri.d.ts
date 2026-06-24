/**
 * Type declarations for Tauri v2 APIs used by the desktop shell.
 *
 * These are intentionally minimal — full type coverage comes from the
 * `@tauri-apps/api` package which is available in the Tauri webview
 * via `withGlobalTauri: true` (set in tauri.conf.json).
 *
 * When running in browser mode, `window.__TAURI__` is undefined and
 * the tauri-bridge module provides graceful fallbacks.
 */

declare module "@tauri-apps/api/core" {
  export function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}

declare module "@tauri-apps/api/event" {
  export function listen<T>(
    event: string,
    handler: (event: { payload: T }) => void,
  ): Promise<() => void>;
}

/** Global injected by Tauri v2 when `withGlobalTauri: true` is set. */
interface Window {
  readonly __TAURI__?: {
    core: {
      invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T>;
    };
  };
}
