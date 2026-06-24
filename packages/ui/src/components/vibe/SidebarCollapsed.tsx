"use client";

import { Home, PanelLeft } from "lucide-react";
import type { WritingProject } from "@/stores/useWritingStore";

interface SidebarCollapsedProps {
  projects: WritingProject[];
  activeProjectId: string | null;
  onExpand: () => void;
  onProjectClick: (projectId: string) => void;
  onProjectList: () => void;
}

function ProjectDot({
  project,
  isActive,
  onClick,
}: {
  project: WritingProject;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all shrink-0 hover:scale-105 ${
        isActive ? "text-th-accent-text bg-th-accent-dim" : "text-th-text-3 bg-transparent"
      }`}
      title={project.title}
    >
      {project.title.charAt(0)}
    </button>
  );
}

export function SidebarCollapsed({
  projects,
  activeProjectId,
  onExpand,
  onProjectClick,
  onProjectList,
}: SidebarCollapsedProps) {
  return (
    <aside className="shrink-0 flex flex-col items-center gap-2 py-3 border-r bg-th-card border-th-border-subtle w-[44px]">
      {/* Expand button */}
      <button
        type="button"
        onClick={onExpand}
        className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover transition-colors"
        aria-label="展开侧栏"
        title="展开侧栏"
      >
        <PanelLeft size={18} />
      </button>

      {/* Project quick-nav dots */}
      <div className="flex-1 flex flex-col items-center gap-1.5 overflow-hidden px-1 w-full">
        {projects.map((proj) => (
          <ProjectDot
            key={proj.id}
            project={proj}
            isActive={proj.id === activeProjectId}
            onClick={() => onProjectClick(proj.id)}
          />
        ))}
      </div>

      {/* Project list button */}
      <button
        type="button"
        onClick={onProjectList}
        className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover transition-colors"
        aria-label="项目列表"
        title="项目列表"
      >
        <Home size={16} />
      </button>
    </aside>
  );
}
