"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { setTauriTitlebarTheme, setWindowBackgroundColor } from "../lib/tauri-theme";

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
  {
    id: "solarized-dark",
    name: "Solarized Dark",
    icon: "🌙",
    description: "色彩科学 · 青绿底 · 学术基准",
  },
  {
    id: "solarized-light",
    name: "Solarized Light",
    icon: "☀️",
    description: "暖纸白 · 蓝灰字 · 全天候通用",
  },
  { id: "paper", name: "Paper", icon: "📄", description: "纸张质感 · 暖米色 · 沉浸式写作" },
  {
    id: "github-light",
    name: "GitHub Light",
    icon: "⬜",
    description: "纯白底 · 蓝强调 · 结构化编辑",
  },
];

const DARK_THEMES: ThemeId[] = ["moling", "nord", "onedark", "dracula", "solarized-dark"];

export function isDarkTheme(id: ThemeId): boolean {
  return DARK_THEMES.includes(id);
}

/**
 * 检测系统 prefers-color-scheme 并返回对应主题 ID
 * - 暗色 → "moling"（默认暗色主题）
 * - 亮色 → "solarized-light"（默认亮色主题）
 */
export function detectSystemTheme(): ThemeId {
  if (typeof window === "undefined") return "moling";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "moling" : "solarized-light";
}

interface ThemeStore {
  theme: ThemeId;
  /** 是否自动跟随系统主题，初始默认 false */
  autoFollow: boolean;
  setTheme: (id: ThemeId) => void;
  cycleNext: () => void;
  /** 清除锁定，恢复系统主题跟随 */
  resetToAuto: () => void;
}

export const useTheme = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: "moling",
      autoFollow: false,

      setTheme: (id: ThemeId) => {
        if (typeof window !== "undefined") {
          document.documentElement.setAttribute("data-theme", id);
        }
        // Sync native title bar color in Tauri
        setTauriTitlebarTheme(id);
        // Sync window background colour in Tauri
        setWindowBackgroundColor(id);
        // 用户手动切换 → 锁定选择，不再跟随系统
        set({ theme: id, autoFollow: false });
      },

      cycleNext: () => {
        const { theme } = get();
        const idx = THEMES.findIndex((t) => t.id === theme);
        const next = THEMES[(idx + 1) % THEMES.length];
        // setTheme 内部已设置 autoFollow: false
        get().setTheme(next.id);
      },

      resetToAuto: () => {
        const systemTheme = detectSystemTheme();
        if (typeof window !== "undefined") {
          document.documentElement.setAttribute("data-theme", systemTheme);
        }
        setTauriTitlebarTheme(systemTheme);
        setWindowBackgroundColor(systemTheme);
        set({ theme: systemTheme, autoFollow: true });
      },
    }),
    {
      name: "vibe-writing-theme",
      partialize: (state) => ({ theme: state.theme, autoFollow: state.autoFollow }),
      onRehydrateStorage: () => (state) => {
        if (!state || typeof window === "undefined") return;

        const raw = localStorage.getItem("vibe-writing-theme");
        let storedAutoFollow: boolean | undefined;

        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            storedAutoFollow = parsed.state?.autoFollow;
          } catch {
            // ignore corrupted data
          }
        }

        if (storedAutoFollow === true) {
          // 用户之前开启了自动跟随 → 重新检测系统主题
          state.theme = detectSystemTheme();
        } else if (storedAutoFollow === false) {
          // 用户锁定了主题 → 保持存储的主题不变
          // state.theme 已从 localStorage 恢复
        } else if (!raw) {
          // 首次访问（localStorage 为空）→ 检测系统主题并开启自动跟随
          state.theme = detectSystemTheme();
          state.autoFollow = true;
        } else {
          // 旧格式数据迁移（只有 theme 字段，无 autoFollow）
          // 保留用户已选择的主题，关闭自动跟随
          state.autoFollow = false;
        }

        document.documentElement.setAttribute("data-theme", state.theme);
        setTauriTitlebarTheme(state.theme);
        setWindowBackgroundColor(state.theme);
      },
    },
  ),
);
