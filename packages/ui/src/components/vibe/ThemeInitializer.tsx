"use client";

import { useEffect } from "react";
import { useTheme, detectSystemTheme } from "@/stores/useTheme";

/**
 * 挂载时从 Zustand persist 恢复主题，并监听系统 prefers-color-scheme 变化。
 * 当 autoFollow 为 true 时，系统主题变化 → 自动同步。
 */
export function ThemeInitializer() {
  const theme = useTheme((s) => s.theme);

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
      }
    };

    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, []);

  return null;
}
