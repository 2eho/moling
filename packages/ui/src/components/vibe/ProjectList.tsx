"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { WritingProject } from "@/stores/useWritingStore";
import { ProjectCard } from "./ProjectCard";

interface ProjectListProps {
  projects: WritingProject[];
  activeProjectId: string | null;
  expandedProjectId: string | null;
  activeChapterId: number | null;
  onProjectClick: (projectId: string) => void;
  onChapterClick: (projectId: string, chapterId: number) => void;
}

interface ProjectGroupProps {
  label: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
  projects: WritingProject[];
  activeProjectId: string | null;
  expandedProjectId: string | null;
  activeChapterId: number | null;
  onProjectClick: (projectId: string) => void;
  onChapterClick: (projectId: string, chapterId: number) => void;
  /** 分组左边框颜色 — 连载中用活跃色，已完结用归档色 */
  barColor: string;
  /** 标签文字颜色 */
  labelColor: string;
}

function ProjectGroup({
  label,
  count,
  collapsed,
  onToggle,
  projects,
  activeProjectId,
  expandedProjectId,
  activeChapterId,
  onProjectClick,
  onChapterClick,
  barColor,
  labelColor,
}: ProjectGroupProps) {
  return (
    <div>
      {/* ── Group header (clickable) ── */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 sticky top-0 z-10 transition-colors hover:brightness-95"
        style={{ background: "var(--th-card)" }}
      >
        {/* Chevron */}
        <span
          className="transition-transform duration-200 shrink-0"
          style={{
            transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
            color: labelColor,
          }}
        >
          <ChevronDown size={12} />
        </span>

        {/* Label */}
        <span
          className="text-[10px] font-semibold tracking-wider uppercase"
          style={{ color: labelColor }}
        >
          {label}
        </span>

        {/* Count badge */}
        <span
          className="text-[10px] ml-auto"
          style={{ color: labelColor }}
        >
          {count}
        </span>
      </button>

      {/* ── Group body (collapsible) ── */}
      {!collapsed && (
        <div className="space-y-0.5" style={{ marginLeft: 16, borderLeft: `2px solid ${barColor}`, paddingLeft: 8 }}>
          {projects.map((proj) => (
            <ProjectCard
              key={proj.id}
              project={proj}
              isActive={proj.id === activeProjectId}
              isExpanded={expandedProjectId === proj.id}
              activeChapterId={activeChapterId}
              onProjectClick={() => onProjectClick(proj.id)}
              onChapterClick={(chId) => onChapterClick(proj.id, chId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProjectList({
  projects,
  activeProjectId,
  expandedProjectId,
  activeChapterId,
  onProjectClick,
  onChapterClick,
}: ProjectListProps) {
  const ongoing = projects.filter((p) =>
    p.chapters.some((ch) => ch.status !== "completed"),
  );
  const completed = projects.filter(
    (p) =>
      p.chapters.length > 0 && p.chapters.every((ch) => ch.status === "completed"),
  );

  const [ongoingCollapsed, setOngoingCollapsed] = useState(false);
  const [completedCollapsed, setCompletedCollapsed] = useState(true);

  const groupProps = {
    activeProjectId,
    expandedProjectId,
    activeChapterId,
    onProjectClick,
    onChapterClick,
  };

  return (
    <nav className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-2">
      {/* 连载中 — 青色竖线，活跃标签 */}
      <ProjectGroup
        label="连载中"
        count={ongoing.length}
        collapsed={ongoingCollapsed}
        onToggle={() => setOngoingCollapsed((v) => !v)}
        projects={ongoing}
        barColor="var(--th-accent-text)"
        labelColor="var(--th-accent-text)"
        {...groupProps}
      />

      {/* 已完结 — 灰色竖线，归档标签，默认折叠 */}
      {completed.length > 0 && (
        <div className="mt-2 pt-2 border-t border-th-border-subtle">
          <ProjectGroup
            label="已完结"
            count={completed.length}
            collapsed={completedCollapsed}
            onToggle={() => setCompletedCollapsed((v) => !v)}
            projects={completed}
            barColor="var(--th-border)"
            labelColor="var(--th-text-4)"
            {...groupProps}
          />
        </div>
      )}
    </nav>
  );
}
