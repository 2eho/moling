import {
  useWritingStore,
  PHASE_LABELS,
  PHASE_ORDER,
} from '../store/useWritingStore';

/**
 * 阶段导航器组件
 * 水平展示 6 个写作阶段，当前阶段高亮，已完成阶段显示勾选标记
 */
export function PhaseNavigator() {
  const novel = useWritingStore((s) => s.novel);
  const setPhase = useWritingStore((s) => s.setPhase);

  const currentIdx = PHASE_ORDER.indexOf(novel.phase);

  return (
    <nav
      className="flex items-center gap-1 px-4 py-3 overflow-x-auto"
      role="navigation"
      aria-label="写作阶段导航"
    >
      {PHASE_ORDER.map((phase, idx) => {
        const isCompleted = idx < currentIdx;
        const isCurrent = idx === currentIdx;
        const isFuture = idx > currentIdx;

        return (
          <button
            key={phase}
            type="button"
            onClick={() => setPhase(phase)}
            disabled={isCurrent}
            className={[
              'group relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium',
              'transition-all duration-300 ease-out',
              'focus-visible:outline-2 focus-visible:outline-offset-2',
              isCurrent
                ? 'bg-[var(--th-accent)] text-white shadow-lg scale-105'
                : isCompleted
                  ? 'bg-[var(--th-card)] text-[var(--th-text-2)] hover:bg-[var(--th-card-hover)] hover:text-[var(--th-text)]'
                  : 'text-[var(--th-text-3)] hover:bg-[var(--th-card)] hover:text-[var(--th-text-2)]',
            ].join(' ')}
            title={PHASE_LABELS[phase]}
          >
            {/* 完成勾选 */}
            {isCompleted && (
              <svg
                className="w-4 h-4 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
                aria-hidden="true"
                style={{ color: 'var(--th-success)' }}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M5 13l4 4L19 7"
                />
              </svg>
            )}

            {/* 当前指示点 */}
            {isCurrent && (
              <span className="w-2 h-2 rounded-full animate-pulse-dot shrink-0" style={{ background: 'currentColor' }} />
            )}

            {/* 未来虚线点 */}
            {isFuture && (
              <span className="w-2 h-2 rounded-full border shrink-0" style={{ borderColor: 'var(--th-text-3)' }} />
            )}

            <span className="whitespace-nowrap">{PHASE_LABELS[phase]}</span>
          </button>
        );
      })}

      {/* 连接线 */}
      <div
        className="hidden sm:block h-px flex-1 min-w-4 mx-2"
        style={{
          background: `linear-gradient(to right, var(--th-accent) ${((currentIdx + 1) / PHASE_ORDER.length) * 100}%, var(--th-text-3) 0%)`,
        }}
      />
    </nav>
  );
}
