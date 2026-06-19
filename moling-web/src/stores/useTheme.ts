"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeId =
  | "moling"
  | "nord"
  | "onedark"
  | "dracula"
  | "solarized-dark"
  | "solarized-light"
  | "paper"
  | "github-light";

export interface Theme {
  id: ThemeId;
  name: string;
  icon: string;
  description: string;
}

export const THEMES: Theme[] = [
  { id: "moling", name: "墨灵·深空", icon: "🌌", description: "靛蓝深空 · 琥珀金 · 默认主题" },
  { id: "nord", name: "Nord", icon: "❄️", description: "极地冷蓝 · 低饱和 · 长写不刺眼" },
  { id: "onedark", name: "One Dark", icon: "🔵", description: "Atom 传承 · 钢蓝灰 · 柔和层次" },
  { id: "dracula", name: "Dracula", icon: "🧛", description: "暗紫霓虹 · 高对比 · 神秘深邃" },
  { id: "solarized-dark", name: "Solarized Dark", icon: "🌙", description: "色彩科学 · 青绿底 · 学术基准" },
  { id: "solarized-light", name: "Solarized Light", icon: "☀️", description: "暖纸白 · 蓝灰字 · 全天候通用" },
  { id: "paper", name: "Paper", icon: "📄", description: "纸张质感 · 暖米色 · 沉浸式写作" },
  { id: "github-light", name: "GitHub Light", icon: "⬜", description: "纯白底 · 蓝强调 · 结构化编辑" },
];

const DARK_THEMES: ThemeId[] = ["moling", "nord", "onedark", "dracula", "solarized-dark"];

export function isDarkTheme(id: ThemeId): boolean {
  return DARK_THEMES.includes(id);
}

interface ThemeStore {
  theme: ThemeId;
  setTheme: (id: ThemeId) => void;
  cycleNext: () => void;
}

export const useTheme = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: "moling",

      setTheme: (id: ThemeId) => {
        if (typeof window !== "undefined") {
          document.documentElement.setAttribute("data-theme", id);
        }
        set({ theme: id });
      },

      cycleNext: () => {
        const { theme } = get();
        const idx = THEMES.findIndex((t) => t.id === theme);
        const next = THEMES[(idx + 1) % THEMES.length];
        get().setTheme(next.id);
      },
    }),
    {
      name: "vibe-writing-theme",
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        if (state && typeof window !== "undefined") {
          document.documentElement.setAttribute("data-theme", state.theme);
        }
      },
    }
  )
);
