import { useWritingStore } from './store/useWritingStore'
import { useTheme } from './store/useTheme'
import { THEMES } from './store/useTheme'
import type { ThemeId } from './store/useTheme'
import { PhaseNavigator } from './components/PhaseNavigator'
import { ProgressBar } from './components/ProgressBar'
import { ContextPanel } from './components/ContextPanel'
import { OptionCard } from './components/OptionCard'
import { FreeInput } from './components/FreeInput'
import { AgentPanel } from './components/AgentPanel'
import { ActionBar } from './components/ActionBar'
import { ThemeSwitcher } from './components/ThemeSwitcher'
import { Sparkles } from 'lucide-react'
import { useEffect } from 'react'

export default function App() {
  const novel = useWritingStore((s) => s.novel)
  const options = useWritingStore((s) => s.options)
  const selectedOption = useWritingStore((s) => s.selectedOption)
  const setSelectedOption = useWritingStore((s) => s.setSelectedOption)
  const selectOption = useWritingStore((s) => s.selectOption)
  const isGenerating = useWritingStore((s) => s.isGenerating)
  const generateOptions = useWritingStore((s) => s.generateOptions)
  const { theme, setTheme } = useTheme()

  /** Ctrl+Shift+T: 循环切换主题 */
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'T') {
        e.preventDefault()
        const idx = THEMES.findIndex((t) => t.id === theme)
        const next = THEMES[(idx + 1) % THEMES.length]
        setTheme(next.id as ThemeId)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [theme, setTheme])

  /** 处理选项点击：一次选中，二次确认执行（Codex 式双重确认） */
  const handleOptionClick = (id: string) => {
    if (isGenerating) return
    if (selectedOption === id) {
      selectOption(id)
    } else {
      setSelectedOption(id)
    }
  }

  return (
    <div
      className="h-screen flex flex-col overflow-hidden"
      style={{
        background: 'var(--th-bg)',
        color: 'var(--th-text)',
      }}
    >
      {/* ---- Header: Logo + Theme + Version ---- */}
      <header className="shrink-0">
        <div className="flex items-center justify-between px-6 pt-4 pb-2">
          {/* Left: Logo */}
          <div className="flex items-center gap-2.5 select-none">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shadow-lg"
              style={{
                background: `linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))`,
                boxShadow: `0 2px 12px var(--th-accent-glow)`,
              }}
            >
              <Sparkles size={14} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight" style={{ color: 'var(--th-text)' }}>
                Vibe Writing
              </h1>
              <p className="text-[9px] -mt-0.5" style={{ color: 'var(--th-text-3)' }}>
                选择推进，灵感不中断
              </p>
            </div>
          </div>

          {/* Right: Theme + Version */}
          <div className="flex items-center gap-2">
            <ThemeSwitcher />
            <span className="text-[10px] tracking-wider" style={{ color: 'var(--th-text-4)' }}>
              v1.0
            </span>
          </div>
        </div>
        <ProgressBar />
      </header>

      {/* ---- Phase Navigation ---- */}
      <PhaseNavigator />

      {/* ---- Main: 三栏布局 ---- */}
      <main className="flex-1 flex overflow-hidden min-h-0">
        <ContextPanel />

        {/* Center: 主交互区 */}
        <div className="flex-1 flex flex-col p-5 gap-4 overflow-y-auto">
          {/* Chapter indicator */}
          <div className="flex items-center gap-3 mb-1">
            <div
              className="h-px flex-1"
              style={{
                background: `linear-gradient(to right, transparent, var(--th-accent-dim), transparent)`,
              }}
            />
            <span className="text-[10px] tracking-wider whitespace-nowrap" style={{ color: 'var(--th-text-3)' }}>
              第{novel.currentChapter}章 · {novel.chapters.find((c) => c.id === novel.currentChapter)?.title ?? '草稿'}
            </span>
            <div
              className="h-px flex-1"
              style={{
                background: `linear-gradient(to right, transparent, var(--th-accent-dim), transparent)`,
              }}
            />
          </div>

          {/* Options area */}
          <div className="flex-1 flex flex-col gap-3 justify-center min-h-0">
            {/* Empty state */}
            {options.length === 0 && !isGenerating && (
              <div className="text-center py-16">
                <Sparkles size={36} className="mx-auto mb-4 opacity-10" style={{ color: 'var(--th-text)' }} />
                <p className="text-sm mb-3" style={{ color: 'var(--th-text-3)' }}>
                  暂无可用选项
                </p>
                <button
                  onClick={generateOptions}
                  className="px-5 py-2 rounded-xl text-xs font-medium transition-all duration-200 hover:scale-105 active:scale-95"
                  style={{
                    background: 'var(--th-accent-dim)',
                    color: 'var(--th-accent-text)',
                  }}
                >
                  生成选项
                </button>
              </div>
            )}

            {/* Generating state */}
            {isGenerating && (
              <div className="text-center py-16">
                <div className="flex items-center justify-center gap-1.5 mb-4">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-2.5 h-2.5 rounded-full agent-pulse"
                      style={{
                        background: 'var(--th-accent-text)',
                        animationDelay: `${i * 0.2}s`,
                      }}
                    />
                  ))}
                </div>
                <p className="text-xs mb-1" style={{ color: 'var(--th-accent-text)' }}>
                  Agent 正在协作生成选项...
                </p>
                <p className="text-[10px]" style={{ color: 'var(--th-text-3)' }}>
                  分析上下文 · 调用代理 · 整合提案
                </p>
              </div>
            )}

            {/* Option cards */}
            {!isGenerating &&
              options.map((option) => (
                <OptionCard
                  key={option.id}
                  option={option}
                  isSelected={selectedOption === option.id}
                  onSelect={handleOptionClick}
                />
              ))}
          </div>

          {/* Free input */}
          <FreeInput />
        </div>

        <AgentPanel />
      </main>

      {/* ---- Bottom Action Bar ---- */}
      <ActionBar />

      {/* ---- Theme transition key (hidden) ---- */}
      <div aria-hidden="true" data-theme-key={theme} className="hidden" />
    </div>
  )
}
