"use client";

import { useState } from "react";
import { useRouter } from "@/lib/navigation";
import { Menu, X, Plus } from "lucide-react";
import { useWritingStore } from "@/stores/useWritingStore";
import { SidebarHeader } from "./SidebarHeader";
import { SidebarFooter } from "./SidebarFooter";
import { SidebarCollapsed } from "./SidebarCollapsed";
import { ProjectList } from "./ProjectList";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  width?: number;
}

/** 纯容器组件 — 只处理展开/折叠和响应式 */
export function Sidebar({ collapsed, onToggle, width = 240 }: SidebarProps) {
  const router = useRouter();
  const projects = useWritingStore((s) => s.projects);
  const activeProjectId = useWritingStore((s) => s.activeProjectId);
  const expandedProjectId = useWritingStore((s) => s.expandedProjectId);
  const activeChapterId = useWritingStore((s) => s.activeChapterId);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const setActiveChapter = useWritingStore((s) => s.setActiveChapter);
  const toggleProjectExpand = useWritingStore((s) => s.toggleProjectExpand);

  const [mobileOpen, setMobileOpen] = useState(false);

  // ── Handlers ──
  const handleProjectClick = (projId: string) => {
    setActiveProject(projId);
    toggleProjectExpand(projId);
    router.push(`/workspace/${projId}`);
    setMobileOpen(false);
  };

  const handleChapterClick = (projId: string, chId: number) => {
    setActiveChapter(chId);
    router.push(`/workspace/${projId}`);
    setMobileOpen(false);
  };

  const handleNewProject = () => {
    router.push("/projects/new");
    setMobileOpen(false);
  };

  const handleSettings = () => {
    router.push("/settings");
    setMobileOpen(false);
  };

  // ── Render ──
  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="fixed top-2.5 left-3 z-30 p-1.5 rounded-lg bg-th-card border border-th-border-subtle text-th-text-3 md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="打开菜单"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div
            className="fixed inset-y-0 left-0 z-50 md:hidden flex flex-col animate-slide-in-left bg-th-card"
            style={{ width: "80vw", boxShadow: "4px 0 24px rgba(0,0,0,0.25)" }}
          >
            {/* Override: close button instead of collapse */}
            <div className="shrink-0 flex items-center gap-2 px-3 py-3">
              <button
                onClick={() => setMobileOpen(false)}
                className="p-1.5 rounded-lg text-th-text-3"
                aria-label="关闭侧栏"
              >
                <X size={18} />
              </button>
              <div className="flex-1" />
              <button
                onClick={handleNewProject}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-th-accent-dim text-th-accent-text"
              >
                <Plus size={13} />
                <span>新建</span>
              </button>
            </div>

            {projects.length === 0 ? (
              <div className="flex-1 min-h-0 flex items-center justify-center px-4">
                <p className="text-xs text-center text-th-text-4">
                  暂无项目，点击上方「新建」开始
                </p>
              </div>
            ) : (
              <ProjectList
                projects={projects}
                activeProjectId={activeProjectId}
                expandedProjectId={expandedProjectId}
                activeChapterId={activeChapterId}
                onProjectClick={handleProjectClick}
                onChapterClick={handleChapterClick}
              />
            )}

            <SidebarFooter onSettings={handleSettings} />
          </div>
        </>
      )}

      {/* Desktop — use `max-md:hidden` for JSDOM test visibility */}
      {collapsed ? (
        <div className="max-md:hidden">
          <SidebarCollapsed
            projects={projects}
            activeProjectId={activeProjectId}
            onExpand={onToggle}
            onProjectClick={handleProjectClick}
            onProjectList={() => router.push("/projects")}
          />
        </div>
      ) : (
        <aside
          className="shrink-0 flex max-md:hidden flex-col h-full border-r overflow-hidden bg-th-card border-th-border-subtle transition-all duration-300 relative"
          style={{ width }}
        >
            {/* 5% 灰度遮罩 */}
            <div className="absolute inset-0 bg-black/5 pointer-events-none" />
            <SidebarHeader onCollapse={onToggle} onNewProject={handleNewProject} />
            {projects.length === 0 ? (
              <div className="flex-1 min-h-0 flex items-center justify-center px-4">
                <p className="text-xs text-center text-th-text-4">
                  暂无项目，点击上方「新建」开始
                </p>
              </div>
            ) : (
              <ProjectList
                projects={projects}
                activeProjectId={activeProjectId}
                expandedProjectId={expandedProjectId}
                activeChapterId={activeChapterId}
                onProjectClick={handleProjectClick}
                onChapterClick={handleChapterClick}
              />
            )}
            <SidebarFooter onSettings={handleSettings} />
          </aside>
        )}
    </>
  );
}
