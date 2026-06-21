"use client";

import { useRouter } from "next/navigation";
import { PanelLeft, Plus, Settings, Library, Package } from "lucide-react";
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

  // Handlers for ProjectList
  const handleProjectClick = (projId: string) => {
    setActiveProject(projId);
    toggleProjectExpand(projId);
    router.push(`/workspace/${projId}`);
  };

  const handleChapterClick = (projId: string, chId: number) => {
    setActiveChapter(chId);
    router.push(`/workspace/${projId}`);
  };

  if (collapsed) {
    return (
      <aside
        className="shrink-0 flex flex-col items-center gap-3 pt-3 border-r transition-all duration-300"
        style={{
          width: 44,
          borderColor: "var(--th-border-subtle)",
          background: "var(--th-card)",
        }}
      >
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--th-text-3)" }}
          aria-label="展开侧栏"
        >
          <PanelLeft size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside
      className="shrink-0 flex flex-col h-full transition-all duration-300 border-r overflow-hidden"
      style={{
        width,
        borderColor: "var(--th-border-subtle)",
        background: "var(--th-card)",
      }}
    >
      {/* Top: 新建项目 */}
      <div className="shrink-0 flex items-center gap-2 px-3 py-3">
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--th-text-3)" }}
          aria-label="折叠侧栏"
        >
          <PanelLeft size={18} />
        </button>

        <div className="flex-1" />

        <button
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
          style={{
            background: "var(--th-accent-dim)",
            color: "var(--th-accent-text)",
          }}
          onClick={() => router.push("/projects/new")}
        >
          <Plus size={13} />
          <span>新建</span>
        </button>
      </div>

      {/* Middle: 项目列表 */}
      {projects.length === 0 ? (
        <div className="flex-1 flex items-center justify-center px-4">
          <p
            className="text-xs text-center"
            style={{ color: "var(--th-text-4)" }}
          >
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
      <div
        className="shrink-0 border-t"
        style={{ borderColor: "var(--th-border-subtle)" }}
      >
        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs transition-colors hover:opacity-80"
          style={{ color: "var(--th-text-2)" }}
          title="功能开发中"
        >
          <Library size={14} style={{ color: "var(--th-text-3)" }} />
          <span>知识中心</span>
          <span
            className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium"
            style={{
              background: "var(--th-hover)",
              color: "var(--th-text-4)",
            }}
          >
            即将推出
          </span>
        </button>

        <button
          className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs transition-colors hover:opacity-80"
          style={{ color: "var(--th-text-2)" }}
          title="功能开发中"
        >
          <Package size={14} style={{ color: "var(--th-text-3)" }} />
          <span>插件市场</span>
          <span
            className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-medium"
            style={{
              background: "var(--th-hover)",
              color: "var(--th-text-4)",
            }}
          >
            即将推出
          </span>
        </button>

        <div
          className="flex items-center justify-between px-3.5 py-2.5 border-t"
          style={{ borderColor: "var(--th-border-subtle)" }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold"
              style={{
                background: "var(--th-accent-dim)",
                color: "var(--th-accent-text)",
              }}
            >
              U
            </div>
            <span
              className="text-xs truncate"
              style={{ color: "var(--th-text-2)" }}
            >
              用户
            </span>
          </div>
          <button
            onClick={() => router.push("/settings")}
            className="p-1 rounded transition-colors hover:opacity-80"
            style={{ color: "var(--th-text-3)" }}
            aria-label="设置"
          >
            <Settings size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
