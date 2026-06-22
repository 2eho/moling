"use client";

import { useWritingStore, getPhaseProgress } from "@/stores/useWritingStore";

export function ProgressBar() {
  const project = useWritingStore((s) => s.project);
  const isGenerating = useWritingStore((s) => s.isGenerating);

  if (!project) return null;

  const progress = getPhaseProgress(project.phase);

  return (
    <div
      className="sticky top-0 z-50 w-full h-[3px]"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`写作进度: ${progress}%`}
      style={{ background: "var(--th-border-subtle)" }}
    >
      <div
        className={`h-full transition-all duration-700 ease-out ${isGenerating ? "animate-shimmer" : ""}`}
        style={{
          width: `${progress}%`,
          background: isGenerating
            ? "linear-gradient(90deg, var(--th-accent), var(--th-logo-to), var(--th-accent))"
            : "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
          backgroundSize: isGenerating ? "200% 100%" : undefined,
          boxShadow: "0 0 8px var(--th-accent-glow)",
        }}
      />
    </div>
  );
}
