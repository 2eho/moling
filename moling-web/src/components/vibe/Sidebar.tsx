"use client";

import { useRouter } from "next/navigation";
import {
  PanelLeft,
  Plus,
  Settings,
  ChevronDown,
  Library,
  Package,
  Pen,
  Eye,
} from "lucide-react";
import { useWritingStore } from "@/stores/useWritingStore";

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

  /** 渲染单个项目卡片 */
  const renderProject = (proj: typeof projects[number]) => {
    const isActive = proj.id === activeProjectId;
    const isExpanded = expandedProjectId === proj.id;
    const isCompleted = proj.chapters.length > 0 && proj.chapters.every((ch) => ch.status === "completed");
    return (
      <div key={proj.id}>
        {/* Project row — click name to toggle expand */}
        <button
          onClick={() => {
            setActiveProject(proj.id);
            toggleProjectExpand(proj.id);
            router.push(`/workspace/${proj.id}`);
          }}
          className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs transition-colors group"
          style={{
            color: isActive ? "var(--th-accent-text)" : "var(--th-text-2)",
            background: isActive ? "var(--th-accent-dim)" : "transparent",
          }}
        >
          <span
            className="flex-shrink-0 transition-transform duration-200"
            style={{
              color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)",
              transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)",
            }}
          >
            <ChevronDown size={13} />
          </span>
          {isCompleted ? (
            <Eye
              size={13}
              className="shrink-0"
              style={{ color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)" }}
            />
          ) : (
            <Pen
              size={13}
              className="shrink-0"
              style={{ color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)" }}
            />
          )}
          <span className="flex-1 text-left truncate">{proj.title}</span>
          {isCompleted && (
            <span
              className="text-[9px] px-1 py-0.5 rounded font-medium shrink-0"
              style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}
            >
              完结
            </span>
          )}
          {isActive && (
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: "var(--th-accent-text)" }}
            />
          )}
        </button>

        {/* Expanded chapters — 倒序：最新一章紧贴项目名 */}
        {isExpanded && proj.chapters.length > 0 && (
          <div className="ml-7 border-l" style={{ borderColor: "var(--th-border-subtle)" }}>
            {[...proj.chapters].reverse().map((ch) => {
              const isCurrent = ch.id === activeChapterId && isActive;
              const isEditable = ch.id === proj.chapters.length;
              const isDisabled = !isActive;
              return (
                <button
                  key={ch.id}
                  disabled={isDisabled}
                  onClick={() => {
                    if (isDisabled) return;
                    setActiveChapter(ch.id);
                    router.push(`/workspace/${proj.id}`);
                  }}
                  className="w-full flex items-center gap-2 pl-3 pr-2.5 py-1.5 text-[11px] transition-colors text-left rounded-r-lg disabled:cursor-not-allowed"
                  style={{
                    color: isCurrent ? "var(--th-accent-text)" : "var(--th-text-3)",
                    background: isCurrent ? "var(--th-accent-dim)" : "transparent",
                    opacity: isDisabled ? 0.35 : 1,
                  }}
                >
                  <span
                    className="w-4 h-4 rounded-full text-[9px] flex items-center justify-center shrink-0 font-medium"
                    style={{
                      background: ch.status === "completed"
                        ? "var(--th-accent-dim)"
                        : isEditable ? "var(--th-accent-text)" : "var(--th-hover)",
                      color: ch.status === "completed"
                        ? "var(--th-accent-text)"
                        : isEditable ? "#fff" : "var(--th-text-3)",
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
        width: collapsed ? 44 : width,
        borderColor: "var(--th-border-subtle)",
        background: "var(--th-card)",
      }}
    >
      {/* ================================================================
          Top: 新建项目 + 搜索
          ================================================================ */}
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

      {/* ================================================================
          Middle: 小说项目列表 — 分为连载中 / 已完结
          ================================================================ */}
      <nav className="flex-1 overflow-y-auto" aria-label="项目列表">
        {/* Section label — 连载中 */}
        <div className="flex items-center justify-between px-3.5 py-2">
          <span
            className="text-[10px] font-semibold tracking-wider uppercase select-none"
            style={{ color: "var(--th-text-4)" }}
          >
            连载中
          </span>
          <span
            className="text-[10px] font-medium tabular-nums"
            style={{ color: "var(--th-text-4)" }}
          >
            {projects.filter((p) => p.chapters.some((ch) => ch.status !== "completed")).length}
          </span>
        </div>

        {/* Project cards */}
        <div className="px-2 pb-2 space-y-0.5">
          {projects.length === 0 ? (
            <p
              className="px-2.5 py-3 text-xs text-center rounded-lg"
              style={{ color: "var(--th-text-4)" }}
            >
              暂无项目，点击上方 &ldquo;新建&rdquo; 开始
            </p>
          ) : (
            /* 连载中 */
            projects.filter((p) => p.chapters.some((ch) => ch.status !== "completed")).map((proj) => renderProject(proj))
          )}
        </div>

        {/* 已完结 — 仅在有已完结项目时显示，与连载中间级 */}
        {(() => {
          const completed = projects.filter((p) => p.chapters.length > 0 && p.chapters.every((ch) => ch.status === "completed"));
          if (completed.length === 0) return null;
          return (
            <>
              <div className="flex items-center justify-between px-3.5 py-2">
                <span
                  className="text-[10px] font-semibold tracking-wider uppercase select-none"
                  style={{ color: "var(--th-text-4)" }}
                >
                  已完结
                </span>
                <span
                  className="text-[10px] font-medium tabular-nums"
                  style={{ color: "var(--th-text-4)" }}
                >
                  {completed.length}
                </span>
              </div>
              <div className="px-2 pb-2 space-y-0.5">
                {completed.map((proj) => renderProject(proj))}
              </div>
            </>
          );
        })()}
      </nav>

      {/* ================================================================
          Bottom: 知识中心 | 插件市场 | 用户设置
          ================================================================ */}
      <div className="shrink-0 border-t" style={{ borderColor: "var(--th-border-subtle)" }}>
        {/* 知识中心 placeholder */}
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

        {/* 插件市场 placeholder */}
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

        {/* 用户设置 */}
        <div
          className="flex items-center justify-between px-3.5 py-2.5 border-t"
          style={{ borderColor: "var(--th-border-subtle)" }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold"
              style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
            >
              U
            </div>
            <span className="text-xs truncate" style={{ color: "var(--th-text-2)" }}>
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
