import { useWritingStore, getPhaseProgress } from '../store/useWritingStore';

/**
 * 全局进度条 — Codex 式: 微光渐变 + 生成中流光动画
 */
export function ProgressBar() {
  const novel = useWritingStore((s) => s.novel);
  const isGenerating = useWritingStore((s) => s.isGenerating);

  const progress = getPhaseProgress(novel.phase);

  return (
    <div
      className="sticky top-0 z-50 w-full h-[3px]"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`写作进度: ${progress}%`}
      style={{ background: 'var(--th-border-subtle)' }}
    >
      <div
        className={[
          'h-full transition-all duration-700 ease-out',
          isGenerating ? 'animate-shimmer' : '',
        ].join(' ')}
        style={{
          width: `${progress}%`,
          background: isGenerating
            ? `linear-gradient(90deg, var(--th-accent), var(--th-logo-to), var(--th-accent))`
            : `linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))`,
          backgroundSize: isGenerating ? '200% 100%' : undefined,
          boxShadow: `0 0 8px var(--th-accent-glow)`,
        }}
      />
    </div>
  );
}

