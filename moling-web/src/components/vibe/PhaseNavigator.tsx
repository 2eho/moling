"use client";

import { useWritingStore, PHASE_LABELS, PHASE_ORDER } from "@/stores/useWritingStore";

export function PhaseNavigator() {
  const project = useWritingStore((s) => s.project);
  const setPhase = useWritingStore((s) => s.setPhase);

  if (!project) return null;

  const currentIdx = PHASE_ORDER.indexOf(project.phase);

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
            className="group relative flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ease-out"
            style={{
              background: isCurrent
                ? "var(--th-accent)"
                : isCompleted
                  ? "var(--th-card)"
                  : "transparent",
              color: isCurrent
                ? "#fff"
                : isCompleted
                  ? "var(--th-text-2)"
                  : "var(--th-text-3)",
              boxShadow: isCurrent ? "0 2px 12px var(--th-accent-glow)" : "none",
              transform: isCurrent ? "scale(1.05)" : "scale(1)",
            }}
            title={PHASE_LABELS[phase]}
          >
            {isCompleted && (
              <svg
                className="w-4 h-4 shrink-0"
                fill="none" viewBox="0 0 24 24"
                stroke="currentColor" strokeWidth={2.5}
                aria-hidden="true"
                style={{ color: "var(--th-success)" }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}

            {isCurrent && (
              <span className="w-2 h-2 rounded-full animate-pulse-dot shrink-0" style={{ background: "currentColor" }} />
            )}

            {isFuture && (
              <span className="w-2 h-2 rounded-full border shrink-0" style={{ borderColor: "var(--th-text-3)" }} />
            )}

            <span className="whitespace-nowrap">{PHASE_LABELS[phase]}</span>
          </button>
        );
      })}
    </nav>
  );
}
