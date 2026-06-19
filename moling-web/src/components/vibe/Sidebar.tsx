"use client";

import { useRouter } from "next/navigation";
import {
  PanelLeft,
  Search,
  Plus,
  BookOpen,
  Settings,
  ChevronDown,
  ChevronRight,
  Library,
  Package,
  Edit3,
} from "lucide-react";
import { useWritingStore } from "@/stores/useWritingStore";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const router = useRouter();
  const projects = useWritingStore((s) => s.projects);
  const activeProjectId = useWritingStore((s) => s.activeProjectId);
  const expandedProjects = useWritingStore((s) => s.expandedProjects);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const toggleProjectExpand = useWritingStore((s) => s.toggleProjectExpand);

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
        width: 240,
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
          Middle: 小说项目列表
          ================================================================ */}
      <nav className="flex-1 overflow-y-auto" aria-label="项目列表">
        {/* Section label */}
        <div className="flex items-center justify-between px-3.5 py-2">
          <span
            className="text-[10px] font-semibold tracking-wider uppercase select-none"
            style={{ color: "var(--th-text-4)" }}
          >
            小说
          </span>
          <span
            className="text-[10px] font-medium tabular-nums"
            style={{ color: "var(--th-text-4)" }}
          >
            {projects.length}
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
            projects.map((proj) => {
              const isActive = proj.id === activeProjectId;
              const isExpanded = expandedProjects.has(proj.id);

              return (
                <div key={proj.id}>
                  {/* Project row */}
                  <button
                    onClick={() => {
                      setActiveProject(proj.id);
                      router.push(`/workspace/${proj.id}`);
                    }}
                    className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs transition-colors group"
                    style={{
                      color: isActive ? "var(--th-accent-text)" : "var(--th-text-2)",
                      background: isActive
                        ? "var(--th-accent-dim)"
                        : "transparent",
                    }}
                  >
                    {/* Expand toggle */}
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleProjectExpand(proj.id);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.stopPropagation();
                          toggleProjectExpand(proj.id);
                        }
                      }}
                      className="p-0.5 rounded transition-colors hover:opacity-70 flex-shrink-0"
                      style={{ color: "var(--th-text-3)" }}
                      aria-label={isExpanded ? "折叠" : "展开"}
                    >
                      {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </span>

                    {/* Icon */}
                    <Edit3
                      size={13}
                      className="shrink-0"
                      style={{ color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)" }}
                    />

                    {/* Title + genre */}
                    <span className="flex-1 text-left truncate">{proj.title}</span>

                    {/* Active indicator */}
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
                        const isCurrent = ch.id === proj.currentChapter;
                        return (
                          <button
                            key={ch.id}
                            className="w-full flex items-center gap-2 pl-3 pr-2.5 py-1.5 text-[11px] transition-colors text-left rounded-r-lg"
                            style={{
                              color: isCurrent ? "var(--th-accent-text)" : "var(--th-text-3)",
                              background: isCurrent ? "var(--th-accent-dim)" : "transparent",
                            }}
                          >
                            <span
                              className="w-4 h-4 rounded-full text-[9px] flex items-center justify-center shrink-0 font-medium"
                              style={{
                                background: ch.status === "completed"
                                  ? "var(--th-accent-dim)"
                                  : "var(--th-hover)",
                                color: ch.status === "completed"
                                  ? "var(--th-accent-text)"
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
            })
          )}
        </div>
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
