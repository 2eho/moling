"use client";

import { useState } from "react";
import { useRouter } from "@/lib/navigation";
import { PanelLeft, Menu, X, Plus, Settings, Library, Package } from "lucide-react";
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
  const [tabletHovered, setTabletHovered] = useState(false);

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

  // Extracted content reused across mobile overlay, tablet hover, desktop full
  const renderSidebarContent = (isMobileOrTablet: boolean) => (
    <div className="flex flex-col h-full">
      {/* Top: collapse / close + new project */}
      <div className="shrink-0 flex items-center gap-2 px-3 py-3">
        {isMobileOrTablet ? (
          <button
            onClick={() => {
              setMobileOpen(false);
              setTabletHovered(false);
            }}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3"
            aria-label="关闭侧栏"
          >
            <X size={18} />
          </button>
        ) : (
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3"
            aria-label="折叠侧栏"
          >
            <PanelLeft size={18} />
          </button>
        )}

        <div className="flex-1" />

        <button
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors bg-th-accent-dim text-th-accent-text"
          onClick={() => {
            router.push("/projects/new");
            setMobileOpen(false);
            setTabletHovered(false);
          }}
        >
          <Plus size={13} />
          <span>新建</span>
        </button>
      </div>

      {/* Middle: project list */}
      {projects.length === 0 ? (
        <div className="flex-1 flex items-center justify-center px-4">
          <p className="text-xs text-center text-th-text-4">
            暂无项目，点击上方 &ldquo;新建&rdquo; 开始
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

      {/* Bottom: 知识中心 | 插件市场 | 用户设置 */}
      <div className="shrink-0 border-t border-th-border-subtle">
        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs transition-colors hover:opacity-80 text-th-text-2"
          title="功能开发中"
        >
          <Library size={14} className="text-th-text-3" />
          <span>知识中心</span>
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium bg-th-hover text-th-text-4">
            即将推出
          </span>
        </button>

        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs transition-colors hover:opacity-80 text-th-text-2"
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
            onClick={() => {
              router.push("/settings");
              setMobileOpen(false);
              setTabletHovered(false);
            }}
            className="p-1 rounded transition-colors hover:opacity-80 text-th-text-3"
            aria-label="设置"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </div>
  );

  // Desktop collapsed: narrow icon bar
  if (collapsed) {
    return (
      <>
        {/* Mobile hamburger */}
        <button
          className="fixed top-2.5 left-3 z-30 md:hidden p-1.5 rounded-lg bg-th-card border border-th-border-subtle text-th-text-3"
          onClick={() => setMobileOpen(true)}
          aria-label="打开菜单"
        >
          <Menu size={20} />
        </button>

        {/* Mobile overlay */}
        {mobileOpen && (
          <>
            <div
              className="fixed inset-0 z-40 md:hidden bg-th-overlay"
              onClick={() => setMobileOpen(false)}
            />
            <div
              className="fixed inset-y-0 left-0 z-50 md:hidden animate-slide-in-left bg-th-card"
              style={{ width: "80vw", boxShadow: "var(--th-shadow-panel)" }}
            >
              {renderSidebarContent(true)}
            </div>
          </>
        )}

        {/* Tablet narrow icon bar + hover expand */}
        <aside
          className="hidden md:flex lg:hidden shrink-0 flex-col items-center gap-3 pt-3 border-r transition-all duration-300 border-th-border-subtle bg-th-card relative"
          style={{ width: 44 }}
          onMouseEnter={() => setTabletHovered(true)}
        >
          <button className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3" aria-label="菜单">
            <Menu size={18} />
          </button>
          {tabletHovered && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setTabletHovered(false)}
              />
              <div
                className="absolute left-full top-0 z-40 animate-slide-in-left bg-th-card border border-th-border-subtle rounded-r-xl shadow-xl"
                style={{ width: 240, maxHeight: "calc(100vh - 1rem)" }}
                onMouseLeave={() => setTabletHovered(false)}
              >
                <div className="overflow-y-auto" style={{ maxHeight: "calc(100vh - 1rem)" }}>
                  {renderSidebarContent(true)}
                </div>
              </div>
            </>
          )}
        </aside>

        {/* Desktop narrow icon bar */}
        <aside
          className="hidden lg:flex shrink-0 flex-col items-center gap-3 pt-3 border-r transition-all duration-300 border-th-border-subtle bg-th-card"
          style={{ width: 44 }}
        >
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3"
            aria-label="展开侧栏"
          >
            <PanelLeft size={18} />
          </button>
        </aside>
      </>
    );
  }

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="fixed top-2.5 left-3 z-30 md:hidden p-1.5 rounded-lg bg-th-card border border-th-border-subtle text-th-text-3"
        onClick={() => setMobileOpen(true)}
        aria-label="打开菜单"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden bg-th-overlay"
            onClick={() => setMobileOpen(false)}
          />
          <div
            className="fixed inset-y-0 left-0 z-50 md:hidden animate-slide-in-left bg-th-card"
            style={{ width: "80vw", boxShadow: "4px 0 24px rgba(0,0,0,0.3)" }}
          >
            {renderSidebarContent(true)}
          </div>
        </>
      )}

      {/* Tablet narrow icon bar + hover expand */}
      <aside
        className="hidden md:flex lg:hidden shrink-0 flex-col items-center gap-3 pt-3 border-r transition-all duration-300 border-th-border-subtle bg-th-card relative"
        style={{ width: 44 }}
        onMouseEnter={() => setTabletHovered(true)}
      >
        <button className="p-1.5 rounded-lg transition-colors hover:opacity-80 text-th-text-3" aria-label="菜单">
          <Menu size={18} />
        </button>
        {tabletHovered && (
          <>
            <div
              className="fixed inset-0 z-30"
              onClick={() => setTabletHovered(false)}
            />
            <div
              className="absolute left-full top-0 z-40 animate-slide-in-left bg-th-card border border-th-border-subtle rounded-r-xl shadow-xl"
              style={{ width: 240, maxHeight: "calc(100vh - 1rem)" }}
              onMouseLeave={() => setTabletHovered(false)}
            >
              <div className="overflow-y-auto" style={{ maxHeight: "calc(100vh - 1rem)" }}>
                {renderSidebarContent(true)}
              </div>
            </div>
          </>
        )}
      </aside>

      {/* Desktop full sidebar */}
      <aside
        className="hidden lg:flex shrink-0 flex-col h-full transition-all duration-300 border-r overflow-hidden border-th-border-subtle bg-th-card"
        style={{ width }}
      >
        {renderSidebarContent(false)}
      </aside>
    </>
  );
}
