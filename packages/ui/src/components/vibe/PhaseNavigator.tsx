"use client";

import { cn } from "@/lib/cn";
import { PHASE_LABELS, PHASE_ORDER, useWritingStore } from "@/stores/useWritingStore";

export function PhaseNavigator() {
  const project = useWritingStore((s) => s.project);
  const setPhase = useWritingStore((s) => s.setPhase);

  if (!project) return null;

  const currentIdx = PHASE_ORDER.indexOf(project.phase);

  return (
    <nav className="flex items-center gap-1 px-4 py-3 overflow-x-auto" aria-label="写作阶段导航">
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
            className={cn(
              "group relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ease-out",
              isCurrent &&
                "bg-th-accent text-white shadow-[0_2px_12px_var(--th-accent-glow)] scale-105",
              isCompleted && "bg-th-card text-th-text-2",
              isFuture && "bg-transparent text-th-text-3",
            )}
            title={PHASE_LABELS[phase]}
          >
            {isCompleted && (
              <svg
                className="w-4 h-4 shrink-0 text-th-success"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}

            {isCurrent && (
              <span className="w-2 h-2 rounded-full animate-pulse-dot shrink-0 bg-current" />
            )}

            {isFuture && <span className="w-2 h-2 rounded-full border shrink-0 border-th-text-3" />}

            <span className="whitespace-nowrap">{PHASE_LABELS[phase]}</span>
          </button>
        );
      })}
    </nav>
  );
}
