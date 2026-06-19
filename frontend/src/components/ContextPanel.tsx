import { useWritingStore } from '../store/useWritingStore'
import { Users, BookOpen, Zap, AlertCircle } from 'lucide-react'

const ROLE_COLORS: Record<string, string> = {
  protagonist: 'var(--th-warning)',
  antagonist: 'var(--th-danger)',
  supporting: 'var(--th-opt-b-text)',
  minor: 'var(--th-text-3)',
}

const ROLE_LABELS: Record<string, string> = {
  protagonist: '主角',
  antagonist: '反派',
  supporting: '配角',
  minor: '龙套',
}

/** 左侧上下文面板 — Codex 式: 全览小说状态 */
export function ContextPanel() {
  const novel = useWritingStore((s) => s.novel)
  const currentChap = novel.chapters.find((c) => c.id === novel.currentChapter)
  const unresolvedForeshadowing = novel.foreshadowing.filter((f) => f.status === 'planted')

  return (
    <aside
      className="w-72 shrink-0 flex flex-col gap-3 p-4 h-full overflow-y-auto"
      style={{ borderRight: '1px solid var(--th-border-subtle)' }}
    >
      {/* 小说信息 */}
      <div className="glass-card p-3">
        <h2 className="text-sm font-semibold mb-0.5" style={{ color: 'var(--th-text)' }}>
          {novel.title}
        </h2>
        <p className="text-[11px]" style={{ color: 'var(--th-accent-text)' }}>{novel.genre}</p>
        <p className="text-[11px] mt-1 line-clamp-2" style={{ color: 'var(--th-text-3)' }}>
          {novel.summary}
        </p>
      </div>

      {/* 当前章节 */}
      {currentChap && (
        <div className="glass-card p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <BookOpen size={13} style={{ color: 'var(--th-accent-text)' }} />
            <span className="text-[11px] font-medium" style={{ color: 'var(--th-text-2)' }}>
              第{currentChap.id}章 · {currentChap.title}
            </span>
            <span
              className="ml-auto text-[10px] px-1.5 py-0.5 rounded"
              style={{ background: 'var(--th-accent-dim)', color: 'var(--th-accent-text)' }}
            >
              {currentChap.status === 'draft' ? '草稿中' : '已完成'}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed" style={{ color: 'var(--th-text-3)' }}>
            {currentChap.summary}
          </p>
        </div>
      )}

      {/* 关键人物 */}
      <div className="glass-card p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Users size={13} style={{ color: 'var(--th-opt-b-text)' }} />
          <span className="text-[11px] font-medium" style={{ color: 'var(--th-text-2)' }}>
            关键人物
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          {novel.characters.map((c) => (
            <div key={c.id} className="flex items-center gap-2">
              <div
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: ROLE_COLORS[c.role] ?? 'var(--th-text-3)' }}
              />
              <span className="text-[11px]" style={{ color: 'var(--th-text)' }}>
                {c.name}
              </span>
              <span className="text-[10px] ml-auto" style={{ color: 'var(--th-text-3)' }}>
                {ROLE_LABELS[c.role] ?? c.role}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 伏笔追踪 */}
      <div className="glass-card p-3">
        <div className="flex items-center gap-1.5 mb-2">
          <Zap size={13} style={{ color: 'var(--th-warning)' }} />
          <span className="text-[11px] font-medium" style={{ color: 'var(--th-text-2)' }}>
            伏笔追踪
          </span>
        </div>
        {unresolvedForeshadowing.length > 0 ? (
          <div className="flex flex-col gap-1">
            {unresolvedForeshadowing.map((f) => (
              <div key={f.id} className="flex items-start gap-1.5">
                <AlertCircle
                  size={10}
                  className="mt-0.5 shrink-0"
                  style={{ color: 'var(--th-warning)', opacity: 0.6 }}
                />
                <span className="text-[10px] leading-relaxed" style={{ color: 'var(--th-text-3)' }}>
                  {f.description}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[10px]" style={{ color: 'var(--th-text-4)' }}>
            暂无待回收伏笔
          </p>
        )}
      </div>

      {/* 世界观 */}
      <div className="glass-card p-3">
        <span className="text-[11px] font-medium" style={{ color: 'var(--th-text-2)' }}>
          世界观设定
        </span>
        <p className="text-[10px] mt-1 leading-relaxed line-clamp-3" style={{ color: 'var(--th-text-3)' }}>
          {novel.worldRules}
        </p>
      </div>
    </aside>
  )
}
