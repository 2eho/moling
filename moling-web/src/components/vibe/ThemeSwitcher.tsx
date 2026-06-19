"use client";

import { useState } from "react";
import { useTheme, THEMES, isDarkTheme } from "@/stores/useTheme";
import type { ThemeId } from "@/stores/useTheme";
import { Check, Palette } from "lucide-react";

const darkThemes = THEMES.filter((t) => isDarkTheme(t.id));
const lightThemes = THEMES.filter((t) => !isDarkTheme(t.id));

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);

  const current = THEMES.find((t) => t.id === theme);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all duration-200 text-[11px]"
        style={{ background: "var(--th-hover)", color: "var(--th-text-2)" }}
      >
        <Palette size={13} />
        <span className="font-medium">{current?.icon}</span>
        <span className="hidden sm:inline">主题</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 top-full mt-2 z-50 w-72 rounded-xl overflow-hidden shadow-2xl"
            style={{ background: "var(--th-card)", border: "1px solid var(--th-border)" }}
          >
            <div className="px-3 pt-2.5 pb-1.5 text-[10px] font-semibold tracking-wider uppercase" style={{ color: "var(--th-text-3)" }}>
              暗色
            </div>
            {darkThemes.map((t) => (
              <ThemeRow key={t.id} t={t} active={theme === t.id} onClick={() => { setTheme(t.id as ThemeId); setOpen(false); }} />
            ))}

            <div className="mx-3 my-1 h-px" style={{ background: "var(--th-border-subtle)" }} />

            <div className="px-3 pt-2.5 pb-1.5 text-[10px] font-semibold tracking-wider uppercase" style={{ color: "var(--th-text-3)" }}>
              亮色
            </div>
            {lightThemes.map((t) => (
              <ThemeRow key={t.id} t={t} active={theme === t.id} onClick={() => { setTheme(t.id as ThemeId); setOpen(false); }} />
            ))}

            <div className="px-3 py-2 text-[10px] text-center" style={{ color: "var(--th-text-4)" }}>
              快捷键: Ctrl+Shift+T  |  选择记住
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ThemeRow({ t, active, onClick }: { t: (typeof THEMES)[number]; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-2 text-left transition-all duration-150 text-xs"
      style={{ background: active ? "var(--th-hover-strong)" : "transparent", color: active ? "var(--th-text)" : "var(--th-text-2)" }}
    >
      <div
        className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-sm"
        style={{
          background: "linear-gradient(135deg, var(--th-bg), var(--th-accent-dim))",
          border: `1px solid ${active ? "var(--th-accent)" : "var(--th-border-subtle)"}`,
        }}
      >
        {t.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium truncate text-xs" style={{ color: active ? "var(--th-accent-text)" : "var(--th-text)" }}>
          {t.name}
        </div>
        <div className="text-[10px] truncate" style={{ color: "var(--th-text-3)" }}>{t.description}</div>
      </div>
      {active && <Check size={14} style={{ color: "var(--th-accent)" }} />}
    </button>
  );
}
