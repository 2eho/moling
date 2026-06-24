/**
 * Tauri theme bridge — sync React theme to native title bar and window chrome.
 * Safely no-ops in browser (non-Tauri) environment.
 */

type ThemeId = string;

/** Hardcoded fallback when CSS variables are not yet available (e.g. SSR / first frame). */
const THEME_BG_FALLBACK: Record<string, string> = {
  moling: "#0f1117",
  nord: "#2e3440",
  onedark: "#282c34",
  dracula: "#282a36",
  "solarized-dark": "#002b36",
  "solarized-light": "#fdf6e3",
  paper: "#f5f0e8",
  "github-light": "#ffffff",
};

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Call a Tauri command, silently no-op in browser dev mode.
 */
async function invokeCmd<T>(cmd: string, args?: Record<string, unknown>): Promise<T | undefined> {
  if (!isTauri()) return undefined;
  try {
    const { invoke } = await import("@tauri-apps/api/core");
    return invoke<T>(cmd, args);
  } catch {
    // @tauri-apps/api not installed or failed to load — silently ignore
    return undefined;
  }
}

/**
 * Read the current background colour from the DOM's --th-bg CSS variable.
 *
 * Returns null when the variable is not available (SSR, CSS not loaded, or
 * the theme hasn't been applied yet). Callers should fall back to
 * THEME_BG_FALLBACK in that case.
 */
function readCssBackground(): string | null {
  if (typeof window === "undefined") return null;
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--th-bg").trim();
  // getPropertyValue may return empty string for unset variables
  if (!bg) return null;
  return bg;
}

/**
 * Notify Tauri to update the native title bar color based on the active theme.
 * Called from useTheme.setTheme() whenever the user switches themes.
 */
export async function setTauriTitlebarTheme(theme: ThemeId): Promise<void> {
  if (!isTauri()) return;
  try {
    await invokeCmd("set_titlebar_theme", { theme });
  } catch {
    // Silently ignore — browser dev mode or Tauri API not ready
  }
}

/**
 * Sync the Tauri webview window background colour to the active theme.
 *
 * Reads the computed --th-bg CSS variable from the DOM, falling back to a
 * hardcoded theme→hex map when the variable is not yet available (e.g.
 * initial page load before styles are applied).
 *
 * Called whenever the theme changes (setTheme / resetToAuto / rehydrate).
 */
export async function setWindowBackgroundColor(theme: ThemeId): Promise<void> {
  if (!isTauri()) return;

  const color = readCssBackground() ?? THEME_BG_FALLBACK[theme] ?? "#0f1117";

  try {
    await invokeCmd("set_window_color", { color });
  } catch {
    // Silently ignore — browser dev mode or Tauri API not ready
  }
}
