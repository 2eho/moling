/**
 * Tauri desktop bridge — typed wrappers around all Rust IPC commands.
 *
 * All heavy business logic lives in the Axum backend (port 8000).
 * This bridge is intentionally thin: it only wraps IPC calls and
 * provides graceful fallbacks when running in browser mode.
 *
 * ## Architecture
 *
 * - `isTauri()` → check whether the app is running inside the Tauri webview.
 * - `invoke()`   → type-safe wrapper around `window.__TAURI__.core.invoke`.
 * - The rest are typed command functions that the React UI can call directly.
 *
 * ## No-Tauri fallback
 *
 * When `isTauri()` returns false, `invoke()` throws. Callers should guard
 * with `isTauri()` before calling any command, or catch the error.
 */

// ---------------------------------------------------------------------------
// Low-level Tauri detection and invoke
// ---------------------------------------------------------------------------

/** Minimal type for the Tauri v2 global injected by `withGlobalTauri: true`. */
interface TauriCore {
  invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T>;
}

interface TauriGlobal {
  core: TauriCore;
}

function getTauri(): TauriGlobal | null {
  if (
    typeof window !== "undefined" &&
    "__TAURI__" in (window as unknown as Record<string, unknown>)
  ) {
    const w = window as unknown as Record<string, unknown>;
    const tauri = w.__TAURI__ as TauriGlobal | undefined;
    if (tauri?.core && typeof tauri.core.invoke === "function") {
      return tauri;
    }
  }
  return null;
}

/** Returns true when the app is running inside the Tauri desktop shell. */
export function isTauri(): boolean {
  return getTauri() !== null;
}

/**
 * Low-level typed invoke.
 *
 * Throws if Tauri is not available. Callers must either guard with
 * `isTauri()` or handle the rejection.
 */
async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const tauri = getTauri();
  if (!tauri) {
    throw new Error(
      "[tauri-bridge] invoke() called but Tauri is not available. " +
        "Guard with isTauri() before calling IPC commands.",
    );
  }
  return tauri.core.invoke<T>(cmd, args);
}

// ---------------------------------------------------------------------------
// Typed command response types
// ---------------------------------------------------------------------------

export interface AppInfo {
  name: string;
  version: string;
  backend_url: string;
  platform: "windows" | "macos" | "linux" | string;
  arch: string;
}

export interface BackendHealth {
  reachable: boolean;
  status: Record<string, unknown> | null;
  error: string | null;
}

export interface UpdateCheckResult {
  available: boolean;
  version: string | null;
  body: string | null;
  date: string | null;
}

// ---------------------------------------------------------------------------
// Typed IPC command wrappers
// ---------------------------------------------------------------------------

/** Returns application metadata (name, version, platform, backend URL). */
export async function getAppInfo(): Promise<AppInfo> {
  return invoke<AppInfo>("get_app_info");
}

/** Proxies a health-check to the Axum backend. */
export async function checkBackendHealth(): Promise<BackendHealth> {
  return invoke<BackendHealth>("check_backend_health");
}

/**
 * Sets the native title bar theme.
 *
 * The frontend theme name is mapped to light/dark by the Rust side.
 * Only "solarized-light", "paper", and "github-light" produce a light
 * title bar; everything else is dark.
 */
export async function setTitlebarTheme(theme: string): Promise<void> {
  await invoke("set_titlebar_theme", { theme });
}

/**
 * Checks for available application updates.
 *
 * Returns metadata about the update (version, release notes, date).
 * The frontend should present this to the user and, if accepted,
 * use the updater plugin's JS API to download and install.
 */
export async function checkUpdate(): Promise<UpdateCheckResult> {
  return invoke<UpdateCheckResult>("check_update");
}

/**
 * Opens a native file dialog to select a `.moling` project file,
 * reads it, and returns the parsed JSON.
 *
 * The returned JSON should be sent to the backend for validation
 * and full import processing.
 */
export async function importProject(): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>("import_project");
}

/**
 * Opens a native save dialog and writes the serialized project data
 * to the chosen `.moling` file.
 *
 * `data` must be a JSON-serializable object representing the project.
 */
export async function exportProject(data: Record<string, unknown>): Promise<void> {
  await invoke("export_project", { data: JSON.stringify(data) });
}
