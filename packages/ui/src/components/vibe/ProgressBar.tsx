"use client";

import { getPhaseProgress, useWritingStore } from "@/stores/useWritingStore";

export function ProgressBar() {
  const project = useWritingStore((s) => s.project);
  const isGenerating = useWritingStore((s) => s.isGenerating);

  if (!project) return null;

  const progress = getPhaseProgress(project.phase);

  return (
    <div
      className="sticky top-0 z-50 w-full h-[3px] bg-th-border-subtle"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`写作进度: ${progress}%`}
    >
      <div
        className={`h-full transition-all duration-700 ease-out shadow-[0_0_8px_var(--th-accent-glow)] ${
          isGenerating ? "animate-shimmer" : ""
        }`}
        style={{
          width: `${progress}%`,
          background: isGenerating
            ? "linear-gradient(90deg, var(--th-accent), var(--th-logo-to), var(--th-accent))"
            : "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
          backgroundSize: isGenerating ? "200% 100%" : undefined,
        }}
      />
    </div>
  );
}
