"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useWritingStore } from "@/stores/useWritingStore";
import type { WritingProject } from "@/stores/useWritingStore";
import { useTheme, THEMES } from "@/stores/useTheme";
import type { ThemeId } from "@/stores/useTheme";
import { useToast } from "@/stores/useToast";
import { Sidebar } from "@/components/vibe/Sidebar";
import { ProjectList } from "@/components/vibe/ProjectList";
import { OptionsPanel } from "@/components/vibe/OptionsPanel";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";
import { AgentPanel } from "@/components/vibe/AgentPanel";
import { usePanelResize } from "@/hooks/usePanelResize";
import {
  PanelRight,
  BookOpen,
  Edit3,
  Eye,
  CheckCircle2,
  Copy,
  Menu,
  X,
  Plus,
  ChevronLeft,
  ChevronRight,
  Library,
  Package,
  Settings,
} from "lucide-react";
import { MOCK_PROJECTS } from "@/mock/data/workspace";

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const router = useRouter();

  const project = useWritingStore((s) => s.project);
  const activeChapterId = useWritingStore((s) => s.activeChapterId);
  const projects = useWritingStore((s) => s.projects);
  const activeProjectIdFromStore = useWritingStore((s) => s.activeProjectId);
  const expandedProjectIdFromStore = useWritingStore((s) => s.expandedProjectId);
  const loadProjects = useWritingStore((s) => s.loadProjects);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const setActiveChapter = useWritingStore((s) => s.setActiveChapter);
  const toggleProjectExpand = useWritingStore((s) => s.toggleProjectExpand);
  const completeChapter = useWritingStore((s) => s.completeChapter);
  const { theme, setTheme } = useTheme();
  const { addToast } = useToast();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [draftStepCount, setDraftStepCount] = useState(0);

  // Reset draft step count on chapter change
  useEffect(() => {
    setDraftStepCount(0);
  }, [activeChapterId]);

  // Panel resize
  const resizeRef = useRef<{
    side: "left" | "right";
    startX: number;
    startW: number;
  } | null>(null);
  const { leftWidth: sidebarWidth, rightWidth: rightPanelWidth, onResizeMouseDown } =
    usePanelResize({
      resizeRef,
      leftBounds: [160, 400],
      rightBounds: [200, 500],
    });

  // Current chapter
  const currentChapter = activeChapterId
    ? project?.chapters.find((c) => c.id === activeChapterId) ?? null
    : null;
  const lastChapter = project?.chapters[project.chapters.length - 1];
  const lastChapterId = lastChapter?.id ?? null;

  const isEditable =
    activeChapterId !== null &&
    lastChapterId !== null &&
    activeChapterId === lastChapterId &&
    currentChapter?.status !== "completed";
  const isProjectCompleted =
    project &&
    project.chapters.length > 0 &&
    project.chapters.every((ch) => ch.status === "completed");

  // Copy handler with toast
  const handleCopy = useCallback(() => {
    const text = currentChapter?.content || "";
    navigator.clipboard.writeText(text).then(
      () => {
        addToast({ type: "success", message: "已复制到剪贴板" });
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        addToast({ type: "info", message: "已复制到剪贴板" });
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
    );
  }, [currentChapter?.content, addToast]);

  // Status info
  const statusInfo = useMemo(() => {
    const chapterLabel = currentChapter
      ? `第 ${currentChapter.id} 章 · ${currentChapter.title}`
      : "第 ? 章";

    if (!project) return { icon: <BookOpen size={13} />, label: "加载中", color: "var(--th-text-4)" };

    if (isProjectCompleted) {
      return { icon: <CheckCircle2 size={13} />, label: chapterLabel, color: "var(--th-accent-text)" };
    }

    if (isEditable) {
      return { icon: <Edit3 size={13} />, label: chapterLabel, color: "var(--th-accent-text)" };
    }

    return { icon: <Eye size={13} />, label: chapterLabel, color: "var(--th-text-3)" };
  }, [project, isProjectCompleted, isEditable, currentChapter]);

  // Chapter navigation
  const chapterNav = useMemo(() => {
    if (!project || activeChapterId === null) return { prev: null, next: null };
    const chapters = project.chapters;
    const idx = chapters.findIndex((c) => c.id === activeChapterId);
    return {
      prev: idx > 0 ? chapters[idx - 1].id : null,
      next: idx < chapters.length - 1 ? chapters[idx + 1].id : null,
    };
  }, [project, activeChapterId]);

  const navigateChapter = useCallback(
    (chId: number) => setActiveChapter(chId),
    [setActiveChapter],
  );

  // Load mock projects
  useEffect(() => {
    if (projects.length === 0) {
      loadProjects(MOCK_PROJECTS);
    }
    if (projectId && project?.id !== projectId) {
      setActiveProject(projectId);
    }
    if (activeChapterId === null && project && project.chapters.length > 0) {
      setActiveChapter(project.chapters.length);
    }
  }, [
    loadProjects,
    setActiveProject,
    setActiveChapter,
    projectId,
    project?.id,
    projects.length,
    activeChapterId,
    project,
  ]);

  // Theme cycle: Ctrl+Shift+T
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "T") {
        e.preventDefault();
        const idx = THEMES.findIndex((t) => t.id === theme);
        const next = THEMES[(idx + 1) % THEMES.length];
        setTheme(next.id as ThemeId);
        addToast({ type: "info", message: `主题切换为: ${next.name}`, duration: 1500 });
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [theme, setTheme, addToast]);

  // Mobile sidebar handlers
  const handleMobileProjectClick = (projId: string) => {
    setActiveProject(projId);
    toggleProjectExpand(projId);
    router.push(`/workspace/${projId}`);
    setMobileMenuOpen(false);
  };
  const handleMobileChapterClick = (_projId: string, chId: number) => {
    setActiveChapter(chId);
    setMobileMenuOpen(false);
  };

  if (!project) {
    return (
      <div
        className="h-screen flex items-center justify-center"
        style={{ background: "var(--th-bg)" }}
      >
        <p className="text-sm" style={{ color: "var(--th-text-3)" }}>
          加载中...
        </p>
      </div>
    );
  }

  return (
    <div
      className="h-screen flex overflow-hidden"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      {/* ── Desktop Sidebar ── */}
      <div className="hidden md:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((v) => !v)}
          width={sidebarWidth}
        />
      </div>

      {/* Left resize handle */}
      {!sidebarCollapsed && (
        <div
          className="hidden md:block"
          onMouseDown={onResizeMouseDown("left")}
          style={{
            width: 6,
            cursor: "col-resize",
            background: "var(--th-accent-dim)",
            flexShrink: 0,
          }}
        />
      )}

      {/* ── Mobile Sidebar Overlay ── */}
      {mobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden transition-opacity duration-250"
            style={{ background: "var(--th-overlay)" }}
            onClick={() => setMobileMenuOpen(false)}
          />
          <div
            className="fixed inset-y-0 left-0 z-50 overflow-y-auto md:hidden animate-slide-in-left"
            style={{
              width: "80vw",
              background: "var(--th-card)",
              boxShadow: "4px 0 24px rgba(0,0,0,0.3)",
            }}
          >
            <div
              className="flex items-center justify-between px-4 py-3.5 border-b"
              style={{ borderColor: "var(--th-border-subtle)" }}
            >
              <span className="text-sm font-semibold" style={{ color: "var(--th-text)" }}>
                墨灵
              </span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: "var(--th-text-3)" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Mobile: New project button */}
            <div className="px-3 py-3">
              <button
                onClick={() => {
                  router.push("/projects/new");
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors"
                style={{
                  background: "var(--th-accent-dim)",
                  color: "var(--th-accent-text)",
                }}
              >
                <Plus size={16} />
                <span>新建项目</span>
              </button>
            </div>

            <ProjectList
              projects={projects}
              activeProjectId={activeProjectIdFromStore}
              expandedProjectId={expandedProjectIdFromStore}
              activeChapterId={activeChapterId}
              onProjectClick={handleMobileProjectClick}
              onChapterClick={handleMobileChapterClick}
            />

            {/* Mobile bottom nav */}
            <div
              className="shrink-0 border-t"
              style={{ borderColor: "var(--th-border-subtle)" }}
            >
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-sm"
                style={{ color: "var(--th-text-2)" }}
              >
                <Library size={16} style={{ color: "var(--th-text-3)" }} />
                <span>知识中心</span>
                <span
                  className="ml-auto text-[9px] px-1.5 py-0.5 rounded"
                  style={{
                    background: "var(--th-hover)",
                    color: "var(--th-text-4)",
                  }}
                >
                  即将推出
                </span>
              </button>
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-sm"
                style={{ color: "var(--th-text-2)" }}
              >
                <Package size={16} style={{ color: "var(--th-text-3)" }} />
                <span>插件市场</span>
                <span
                  className="ml-auto text-[9px] px-1.5 py-0.5 rounded"
                  style={{
                    background: "var(--th-hover)",
                    color: "var(--th-text-4)",
                  }}
                >
                  即将推出
                </span>
              </button>
              <button
                onClick={() => {
                  router.push("/settings");
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm border-t"
                style={{
                  borderColor: "var(--th-border-subtle)",
                  color: "var(--th-text-2)",
                }}
              >
                <Settings size={16} style={{ color: "var(--th-text-3)" }} />
                <span>用户设置</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* ── Main Stage ── */}
      <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
        {/* Top bar */}
        <div className="shrink-0 flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3">
          <button
            className="md:hidden p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--th-text-3)" }}
            onClick={() => setMobileMenuOpen(true)}
            aria-label="菜单"
          >
            <Menu size={20} />
          </button>

          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="shrink-0" style={{ color: statusInfo.color }}>
              {statusInfo.icon}
            </span>
            <span
              className="text-[11px] font-semibold truncate"
              style={{ color: statusInfo.color }}
            >
              {statusInfo.label}
            </span>
          </div>
          <ThemeSwitcher />
          <button
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            onClick={() => setRightPanelOpen((v) => !v)}
            style={{
              color: rightPanelOpen ? "var(--th-accent-text)" : "var(--th-text-3)",
            }}
            aria-label="切换右栏"
          >
            <PanelRight size={18} />
          </button>
        </div>

        {/* Center stage */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto px-4 md:px-6 py-3 md:py-4">
            <div className="max-w-4xl mx-auto">
              <div
                className="text-sm leading-relaxed whitespace-pre-wrap"
                style={{ color: "var(--th-text-2)" }}
              >
                {currentChapter?.content || "暂无内容"}
              </div>

              {isEditable && !isProjectCompleted && draftStepCount >= 1 && (
                <button
                  onClick={() => {
                    if (!project || !currentChapter) return;
                    completeChapter(project.id, currentChapter.id);
                    addToast({ type: "success", message: "本章已标记为只读" });
                  }}
                  className="mt-4 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors hover:opacity-80"
                  style={{
                    background: "var(--th-accent-dim)",
                    color: "var(--th-accent-text)",
                  }}
                >
                  完成本章，标为只读
                </button>
              )}
            </div>
          </div>

          {/* OptionsPanel */}
          {isEditable && !isProjectCompleted && (
            <OptionsPanel
              project={project}
              onDraftStep={() => setDraftStepCount((c) => c + 1)}
            />
          )}

          {/* Mobile chapter nav */}
          {currentChapter?.status === "completed" && (
            <div
              className="shrink-0 md:hidden grid grid-cols-3 items-center px-3 py-3 border-t"
              style={{
                borderColor: "var(--th-border-subtle)",
                background: "var(--th-card)",
              }}
            >
              <button
                onClick={() => chapterNav.prev !== null && navigateChapter(chapterNav.prev)}
                disabled={chapterNav.prev === null}
                className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-30 justify-self-start"
                style={{ color: "var(--th-text-2)", background: "var(--th-hover)" }}
              >
                <ChevronLeft size={14} />
                <span>上一章</span>
              </button>
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all justify-self-center"
                style={{
                  color: copied ? "#34d399" : "var(--th-accent-text)",
                  background: copied ? "rgba(52,211,153,0.12)" : "var(--th-card)",
                  border: copied
                    ? "1.5px solid #34d399"
                    : "1.5px solid var(--th-border)",
                }}
              >
                {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                <span>{copied ? "已复制" : "一键复制"}</span>
              </button>
              <button
                onClick={() => chapterNav.next !== null && navigateChapter(chapterNav.next)}
                disabled={chapterNav.next === null}
                className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-30 justify-self-end"
                style={{ color: "var(--th-text-2)", background: "var(--th-hover)" }}
              >
                <span>下一章</span>
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </main>

      {/* ── Desktop Right Panel ── */}
      {rightPanelOpen && (
        <div className="hidden md:flex">
          <div
            onMouseDown={onResizeMouseDown("right")}
            className="shrink-0 w-1.5 cursor-col-resize hover:opacity-100 opacity-0 transition-opacity relative"
            style={{ background: "var(--th-accent-dim)" }}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
          <AgentPanel
            onClose={() => setRightPanelOpen(false)}
            width={rightPanelWidth}
          />
        </div>
      )}

      {/* ── Mobile Right Panel Overlay ── */}
      {rightPanelOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden transition-opacity duration-250"
            style={{ background: "var(--th-overlay)" }}
            onClick={() => setRightPanelOpen(false)}
          />
          <div
            className="fixed inset-y-0 right-0 z-50 overflow-y-auto md:hidden animate-slide-in-right"
            style={{
              width: "80vw",
              background: "var(--th-card)",
              boxShadow: "-4px 0 24px rgba(0,0,0,0.3)",
            }}
          >
            <div
              className="flex items-center justify-between px-4 py-3.5 border-b"
              style={{ borderColor: "var(--th-border-subtle)" }}
            >
              <span className="text-sm font-semibold" style={{ color: "var(--th-text)" }}>
                Agent 调度
              </span>
              <button
                onClick={() => setRightPanelOpen(false)}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: "var(--th-text-3)" }}
              >
                <X size={20} />
              </button>
            </div>
            <AgentPanel onClose={() => setRightPanelOpen(false)} width={0} />
          </div>
        </>
      )}
    </div>
  );
}
