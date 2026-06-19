import { useState, useEffect, useCallback } from 'react'

export type ThemeId = 'moling' | 'nord' | 'onedark' | 'dracula' | 'solarized-dark' | 'solarized-light' | 'paper' | 'github-light'

export interface Theme {
  id: ThemeId
  name: string
  icon: string
  description: string
}

export const THEMES: Theme[] = [
  // ── 暗色经典 ──
  { id: 'moling', name: '墨灵·深空', icon: '\u{1F30C}', description: '靛蓝深空 · 琥珀金 · 默认主题' },
  { id: 'nord', name: 'Nord', icon: '\u{2744}\u{FE0F}', description: '极地冷蓝 · 低饱和 · 长写不刺眼' },
  { id: 'onedark', name: 'One Dark', icon: '\u{1F535}', description: 'Atom 传承 · 钢蓝灰 · 柔和层次' },
  { id: 'dracula', name: 'Dracula', icon: '\u{1F9DB}', description: '暗紫霓虹 · 高对比 · 神秘深邃' },
  { id: 'solarized-dark', name: 'Solarized Dark', icon: '\u{1F319}', description: '色彩科学 · 青绿底 · 学术基准' },

  // ── 亮色经典 ──
  { id: 'solarized-light', name: 'Solarized Light', icon: '\u{2600}\u{FE0F}', description: '暖纸白 · 蓝灰字 · 全天候通用' },
  { id: 'paper', name: 'Paper', icon: '\u{1F4C4}', description: '纸张质感 · 暖米色 · 沉浸式写作' },
  { id: 'github-light', name: 'GitHub Light', icon: '\u{2B1C}', description: '纯白底 · 蓝强调 · 结构化编辑' },
]

const STORAGE_KEY = 'vibe-writing-theme'

function getStoredTheme(): ThemeId {
  if (typeof window === 'undefined') return 'moling'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && THEMES.some(t => t.id === stored)) return stored as ThemeId
  return 'moling'
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeId>(getStoredTheme)

  useEffect(() => {
    const stored = getStoredTheme()
    if (stored !== theme) setThemeState(stored)
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const setTheme = useCallback((id: ThemeId) => {
    setThemeState(id)
  }, [])

  const currentTheme = THEMES.find(t => t.id === theme) ?? THEMES[0]

  return { theme, setTheme, currentTheme, themes: THEMES }
}
