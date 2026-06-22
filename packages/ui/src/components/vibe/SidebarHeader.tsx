"use client";

import { PanelLeftClose, Plus } from "lucide-react";

interface SidebarHeaderProps {
  onCollapse: () => void;
  onNewProject: () => void;
}

export function SidebarHeader({ onCollapse, onNewProject }: SidebarHeaderProps) {
  return (
    <div className="shrink-0 flex items-center gap-2 px-3 py-3">
      <button
        onClick={onCollapse}
        className="p-1.5 rounded-lg transition-colors text-th-text-3 hover:text-th-text hover:bg-th-hover"
        aria-label="折叠侧栏"
        title="折叠侧栏"
      >
        <PanelLeftClose size={18} />
      </button>

      <div className="flex-1" />

      <button
        onClick={onNewProject}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-th-accent-dim text-th-accent-text hover:brightness-110 transition-all"
      >
        <Plus size={13} />
        <span>新建</span>
      </button>
    </div>
  );
}
