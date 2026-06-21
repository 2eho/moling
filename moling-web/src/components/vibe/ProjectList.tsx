"use client";

import { ChevronDown, Pen, Eye } from "lucide-react";
import type { WritingProject } from "@/stores/useWritingStore";

interface ProjectListProps {
  projects: WritingProject[];
  activeProjectId: string | null;
  expandedProjectId: string | null;
  activeChapterId: number | null;
  onProjectClick: (projectId: string) => void;
  onChapterClick: (projectId: string, chapterId: number) => void;
  /** 移动端：点击后关闭菜单 */
  onClose?: () => void;
}

export function ProjectList({
  projects,
  activeProjectId,
  expandedProjectId,
  activeChapterId,
  onProjectClick,
  onChapterClick,
  onClose,
}: ProjectListProps) {
  // Split into ongoing and completed
  const ongoing = projects.filter((p) =>
    p.chapters.some((ch) => ch.status !== "completed"),
  );
  const completed = projects.filter(
    (p) =>
      p.chapters.length > 0 && p.chapters.every((ch) => ch.status === "completed"),
  );

  // Handlers that also call onClose
  const handleProject = (projId: string) => {
    onProjectClick(projId);
    onClose?.();
  };
  const handleChapter = (projId: string, chId: number) => {
    onChapterClick(projId, chId);
    onClose?.();
  };

  const renderGroup = (items: typeof ongoing) => (
    <div className="space-y-0.5">
      {items.map((proj) => {
        const isActive = proj.id === activeProjectId;
        const isExpanded = expandedProjectId === proj.id;
        const isCompleted =
          proj.chapters.length > 0 &&
          proj.chapters.every((ch) => ch.status === "completed");

        return (
          <div key={proj.id}>
            {/* Project row */}
            <button
              onClick={() => handleProject(proj.id)}
              className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm transition-colors"
              style={{
                color: isActive ? "var(--th-accent-text)" : "var(--th-text-2)",
                background: isActive ? "var(--th-accent-dim)" : "transparent",
              }}
            >
              <span
                className="transition-transform duration-200"
                style={{
                  transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)",
                }}
              >
                <ChevronDown size={14} />
              </span>
              {isCompleted ? (
                <Eye size={14} className="shrink-0" style={{ color: "var(--th-text-3)" }} />
              ) : (
                <Pen size={14} className="shrink-0" style={{ color: "var(--th-text-3)" }} />
              )}
              <span className="flex-1 text-left truncate font-medium">{proj.title}</span>
              {isCompleted && (
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded shrink-0"
                  style={{
                    background: "var(--th-hover)",
                    color: "var(--th-text-4)",
                  }}
                >
                  完结
                </span>
              )}
            </button>

            {/* Expanded chapters */}
            {isExpanded && proj.chapters.length > 0 && (
              <div
                className="ml-7 border-l"
                style={{ borderColor: "var(--th-border-subtle)" }}
              >
                {[...proj.chapters].reverse().map((ch) => {
                  const isCurrent = ch.id === activeChapterId && isActive;
                  const isLast = ch.id === proj.chapters.length;
                  const isDisabled = !isActive;
                  return (
                    <button
                      key={ch.id}
                      disabled={isDisabled}
                      onClick={() => handleChapter(proj.id, ch.id)}
                      className="w-full flex items-center gap-2.5 pl-3 pr-2.5 py-2 text-xs transition-colors text-left rounded-r-lg disabled:cursor-not-allowed"
                      style={{
                        color: isCurrent
                          ? "var(--th-accent-text)"
                          : "var(--th-text-3)",
                        background: isCurrent
                          ? "var(--th-accent-dim)"
                          : "transparent",
                        opacity: isDisabled ? 0.6 : 1,
                      }}
                    >
                      <span
                        className="w-5 h-5 rounded-full text-[10px] flex items-center justify-center shrink-0 font-medium"
                        style={{
                          background:
                            ch.status === "completed"
                              ? "var(--th-accent-dim)"
                              : isLast
                                ? "var(--th-accent-text)"
                                : "var(--th-hover)",
                          color:
                            ch.status === "completed"
                              ? "var(--th-accent-text)"
                              : isLast
                                ? "#fff"
                                : "var(--th-text-3)",
                        }}
                      >
                        {ch.id}
                      </span>
                      <span className="truncate">{ch.title}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );

  return (
    <nav className="flex-1 overflow-y-auto px-2">
      {/* 连载中 */}
      <div className="flex items-center justify-between px-2.5 py-2">
        <span
          className="text-[10px] font-semibold tracking-wider uppercase"
          style={{ color: "var(--th-text-4)" }}
        >
          连载中
        </span>
        <span className="text-[10px]" style={{ color: "var(--th-text-4)" }}>
          {ongoing.length}
        </span>
      </div>
      {renderGroup(ongoing)}

      {/* 已完结 */}
      {completed.length > 0 && (
        <>
          <div className="flex items-center justify-between px-2.5 py-2 mt-3">
            <span
              className="text-[10px] font-semibold tracking-wider uppercase"
              style={{ color: "var(--th-text-4)" }}
            >
              已完结
            </span>
            <span className="text-[10px]" style={{ color: "var(--th-text-4)" }}>
              {completed.length}
            </span>
          </div>
          {renderGroup(completed)}
        </>
      )}
    </nav>
  );
}
