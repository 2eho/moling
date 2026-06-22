"use client";

import { useState } from "react";
import { useRouter } from "@/lib/navigation";
import { PanelLeft, PanelLeftClose, Menu, X, Plus, Settings, Library, Package, Home } from "lucide-react";
import { useWritingStore } from "@/stores/useWritingStore";
import { ProjectList } from "./ProjectList";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  width?: number;
}

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

  // ── Full sidebar content ──
  const fullSidebar = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-2 px-3 py-3">
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg transition-colors text-th-text-3 hover:text-th-text hover:bg-th-hover"
          aria-label="折叠侧栏"
          title="折叠侧栏"
        >
          <PanelLeftClose size={18} />
        </button>
        <div className="flex-1" />
        <button
          onClick={() => {
            router.push("/projects/new");
            setMobileOpen(false);
          }}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-th-accent-dim text-th-accent-text hover:brightness-110 transition-all"
        >
          <Plus size={13} />
          <span>新建</span>
        </button>
      </div>

      {/* Project list */}
      {projects.length === 0 ? (
        <div className="flex-1 flex items-center justify-center px-4">
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

      {/* Footer */}
      <div className="shrink-0 border-t border-th-border-subtle">
        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-th-text-2 hover:bg-th-hover transition-colors"
          title="功能开发中"
        >
          <Library size={14} className="text-th-text-3" />
          <span>知识中心</span>
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium bg-th-hover text-th-text-4">
            即将推出
          </span>
        </button>

        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-th-text-2 hover:bg-th-hover transition-colors"
          title="功能开发中"
        >
          <Package size={14} className="text-th-text-3" />
          <span>插件市场</span>
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium bg-th-hover text-th-text-4">
            即将推出
          </span>
        </button>

        <div className="flex items-center justify-between px-3.5 py-2.5 border-t border-th-border-subtle">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold bg-th-accent-dim text-th-accent-text">
              U
            </div>
            <span className="text-xs truncate text-th-text-2">用户</span>
          </div>
          <button
            onClick={() => router.push("/settings")}
            className="p-1 rounded transition-colors text-th-text-3 hover:text-th-text hover:bg-th-hover"
            aria-label="设置"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </div>
  );

  // ── Collapsed narrow bar ──
  const narrowBar = (
    <aside
      className="shrink-0 flex flex-col items-center gap-2 py-3 border-r bg-th-card border-th-border-subtle"
      style={{ width: 44 }}
    >
      <button
        onClick={onToggle}
        className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover transition-colors"
        aria-label="展开侧栏"
        title="展开侧栏"
      >
        <PanelLeft size={18} />
      </button>

      {/* Project quick-nav icons */}
      <div className="flex-1 flex flex-col items-center gap-1.5 overflow-y-auto px-1 w-full">
        {projects.map((proj) => {
          const isActive = proj.id === activeProjectId;
          return (
            <button
              key={proj.id}
              onClick={() => handleProjectClick(proj.id)}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold transition-all shrink-0 hover:scale-105"
              style={{
                color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)",
                background: isActive ? "var(--th-accent-dim)" : "transparent",
              }}
              title={proj.title}
            >
              {proj.title.charAt(0)}
            </button>
          );
        })}
      </div>

      <button
        onClick={() => router.push("/projects")}
        className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover transition-colors"
        aria-label="项目列表"
        title="项目列表"
      >
        <Home size={16} />
      </button>
    </aside>
  );

  return (
    <>
      {/* ── Mobile hamburger (always visible on small screens) ── */}
      <button
        className="fixed top-2.5 left-3 z-30 p-1.5 rounded-lg bg-th-card border border-th-border-subtle text-th-text-3 md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="打开菜单"
      >
        <Menu size={20} />
      </button>

      {/* ── Mobile fullscreen overlay ── */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div
            className="fixed inset-y-0 left-0 z-50 md:hidden animate-slide-in-left bg-th-card"
            style={{ width: "80vw", boxShadow: "4px 0 24px rgba(0,0,0,0.25)" }}
          >
            {/* Mobile header: close + new */}
            <div className="flex items-center gap-2 px-3 py-3 border-b border-th-border-subtle">
              <button
                onClick={() => setMobileOpen(false)}
                className="p-1.5 rounded-lg text-th-text-3"
              >
                <X size={18} />
              </button>
              <div className="flex-1" />
              <button
                onClick={() => {
                  router.push("/projects/new");
                  setMobileOpen(false);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-th-accent-dim text-th-accent-text"
              >
                <Plus size={13} />
                <span>新建</span>
              </button>
            </div>
            {fullSidebar}
          </div>
        </>
      )}

      {/* ── Desktop: collapsed or expanded (md+) ── */}
      {collapsed ? (
        narrowBar
      ) : (
        <aside
          className="shrink-0 hidden md:flex flex-col h-full border-r overflow-hidden bg-th-card border-th-border-subtle transition-all duration-300"
          style={{ width }}
        >
          {fullSidebar}
        </aside>
      )}
    </>
  );
}
