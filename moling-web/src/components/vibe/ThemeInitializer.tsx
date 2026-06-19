"use client";

import { useEffect } from "react";
import { useTheme } from "@/stores/useTheme";

/** 挂载时从 localStorage 恢复主题，应用到 <html data-theme> */
export function ThemeInitializer() {
  const theme = useTheme((s) => s.theme);
  const setTheme = useTheme((s) => s.setTheme);

  useEffect(() => {
    const stored = localStorage.getItem("vibe-writing-theme");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.state?.theme) {
          document.documentElement.setAttribute("data-theme", parsed.state.theme);
        }
      } catch {
        // ignore
      }
    }
  }, []);

  // Sync theme on change
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  return null;
}
