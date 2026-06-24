"use client";

import { useEffect } from "react";
import { setWindowBackgroundColor } from "@/lib/tauri-theme";
import { detectSystemTheme, useTheme } from "@/stores/useTheme";

/**
 * Returns true when running inside the Tauri desktop shell.
 */
function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Listen for the Tauri "toggle-theme" event (emitted by Ctrl+Shift+T global shortcut)
 * and cycle to the next theme.
 */
function useGlobalShortcutTheme() {
  useEffect(() => {
    if (!isTauri()) return;

    let unlisten: (() => void) | undefined;

    async function setup() {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        const unlistenFn = await listen<unknown>("toggle-theme", () => {
          useTheme.getState().cycleNext();
        });
        unlisten = unlistenFn;
      } catch {
        // Tauri API not available — silently ignore (browser mode)
      }
    }

    setup();

    return () => {
      unlisten?.();
    };
  }, []);
}

/**
 * 挂载时从 Zustand persist 恢复主题，并监听系统 prefers-color-scheme 变化。
 * 当 autoFollow 为 true 时，系统主题变化 → 自动同步。
 *
 * Also listens for the Tauri desktop global shortcut (Ctrl+Shift+T / Cmd+Shift+T)
 * to cycle through themes via the native shell.
 */
export function ThemeInitializer() {
  const theme = useTheme((s) => s.theme);

  // Listen for Tauri global shortcut event
  useGlobalShortcutTheme();

  // Set window background colour on mount (defence-in-depth: the store's
  // onRehydrateStorage also does this, but CSS may not have loaded yet
  // at rehydration time — this catches any missed cases).
  useEffect(() => {
    setWindowBackgroundColor(theme);
    // Run once on mount — subsequent changes are handled by setTheme / resetToAuto
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  // 同步 theme 变更到 <html data-theme>
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // 监听系统主题变化：当 autoFollow 为 true 时自动切换
  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");

    const handleChange = () => {
      const currentState = useTheme.getState();
      if (currentState.autoFollow) {
        const systemTheme = detectSystemTheme();
        document.documentElement.setAttribute("data-theme", systemTheme);
        useTheme.setState({ theme: systemTheme });
        setWindowBackgroundColor(systemTheme);
      }
    };

    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, []);

  return null;
}
