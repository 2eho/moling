import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { useWritingStore } from "@/stores/useWritingStore";
import { useTheme, THEMES } from "@/stores/useTheme";
import type { ThemeId } from "@/stores/useTheme";
import { useToast } from "@/stores/useToast";
import { Sidebar } from "@/components/vibe/Sidebar";
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
  X,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  ArrowRight,
  Clock,
} from "lucide-react";
import { MOCK_PROJECTS } from "@/mock/data/workspace";

export function WorkspacePage() {
  const projectId = useParams<{ projectId: string }>().projectId;

  const activeProjectId = useWritingStore((s) => s.activeProjectId);
  const activeChapterId = useWritingStore((s) => s.activeChapterId);
  const projects = useWritingStore((s) => s.projects);
  const loadProjects = useWritingStore((s) => s.loadProjects);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const setActiveChapter = useWritingStore((s) => s.setActiveChapter);
  const completeChapter = useWritingStore((s) => s.completeChapter);
  const toggleProjectExpand = useWritingStore((s) => s.toggleProjectExpand);
  const [hasHydrated, setHasHydrated] = useState(false);

  // Derive `project` solely from `projects` + `activeProjectId`.
  // Never rely on the store's `project` field — it can be stale
  // after zustand persist rehydration.
  const project = activeProjectId
    ? projects.find((p) => p.id === activeProjectId) ?? null
    : projects[0] ?? null;

  // Wait for zustand persist rehydration before showing content.
  useEffect(() => {
    if (projects.length === 0) {
      loadProjects(MOCK_PROJECTS);
    }
    setHasHydrated(true);
  }, []);
  const { theme, setTheme } = useTheme();
  const { addToast } = useToast();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [draftStepCount, setDraftStepCount] = useState(0);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDraftStepCount(0);
  }, [activeChapterId]);

  const resizeRef = useRef<{
    side: "left" | "right";
    startX: number;
    startW: number;
  } | null>(null);
  const { leftWidth: sidebarWidth, rightWidth: rightPanelWidth, onResizeMouseDown } =
    usePanelResize({
      resizeRef,
      leftBounds: [180, 420],
      rightBounds: [220, 520],
    });

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

  useEffect(() => {
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    };
  }, []);

  const handleCopy = useCallback(() => {
    const text = currentChapter?.content || "";
    navigator.clipboard.writeText(text).then(
      () => {
        addToast({ type: "success", message: "已复制到剪贴板" });
        setCopied(true);
        if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
        copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
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
        if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
        copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
      },
    );
  }, [currentChapter?.content, addToast]);

  const chapterInfo = useMemo(() => {
    if (!project || !currentChapter) return null;
    const chIdx = project.chapters.findIndex((c) => c.id === currentChapter.id);
    return {
      index: chIdx,
      total: project.chapters.length,
      title: currentChapter.title,
      number: currentChapter.id,
      canPrev: chIdx > 0,
      canNext: chIdx < project.chapters.length - 1,
      prevId: chIdx > 0 ? project.chapters[chIdx - 1].id : null,
      nextId: chIdx < project.chapters.length - 1 ? project.chapters[chIdx + 1].id : null,
    };
  }, [project, currentChapter]);

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

  // Sync active project/chapter from URL params
  useEffect(() => {
    if (projectId && project?.id !== projectId) {
      setActiveProject(projectId);
      toggleProjectExpand(projectId);
    }
    if (activeChapterId === null && project && project.chapters.length > 0) {
      setActiveChapter(project.chapters.length);
    }
  }, [setActiveProject, setActiveChapter, toggleProjectExpand, projectId, project?.id, activeChapterId, project]);

  // Ctrl+Shift+T → cycle theme
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "T") {
        e.preventDefault();
        const idx = THEMES.findIndex((t) => t.id === theme);
        const next = THEMES[(idx + 1) % THEMES.length];
        setTheme(next.id as ThemeId);
        addToast({ type: "info", message: `主题: ${next.name}`, duration: 1500 });
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [theme, setTheme, addToast]);

  // --- Loading (wait for hydration + project derivation) ---
  if (!hasHydrated || !project) {
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-4 bg-th-bg">
        <div className="w-8 h-8 rounded-full border-2 border-th-accent border-t-transparent animate-spin" />
        <p className="text-sm text-th-text-3">加载项目中...</p>
      </div>
    );
  }

  // --- No chapter active ---
  if (!currentChapter) {
    return (
      <div className="h-screen flex overflow-hidden bg-th-bg text-th-text">
        <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((v) => !v)} width={sidebarWidth} />
        <main className="flex-1 flex flex-col items-center justify-center gap-4 min-w-0">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-th-accent-dim">
            <BookOpen size={28} className="text-th-accent-text/50" />
          </div>
          <p className="text-sm text-th-text-3">从左侧选择章节开始阅读或创作</p>
          <p className="text-xs text-th-text-4">{project.title} · {project.chapters.length} 章</p>
        </main>
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden bg-th-bg text-th-text">
      {/* ── Left: Sidebar ── */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        width={sidebarWidth}
      />

      {!sidebarCollapsed && (
        <div
          className="hidden lg:block shrink-0 w-[6px] cursor-col-resize bg-th-accent-dim hover:bg-th-accent/30 transition-colors"
          onMouseDown={onResizeMouseDown("left")}
        />
      )}

      {/* ── Center: Content ── */}
      <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
        {/* Toolbar */}
        <div className="shrink-0 flex items-center gap-2 md:gap-3 px-3 md:px-6 py-2.5 md:py-3 border-b border-th-border-subtle bg-th-bg/60 backdrop-blur">
          {/* Chapter info */}
          <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0">
            <div className="flex items-center gap-1.5 md:gap-2">
              {currentChapter.status === "completed" ? (
                <CheckCircle2 size={14} className="text-[var(--th-success)] shrink-0" />
              ) : isEditable ? (
                <Edit3 size={14} className="text-th-accent-text shrink-0" />
              ) : (
                <Eye size={14} className="text-th-text-3 shrink-0" />
              )}
              <span className="text-[13px] md:text-sm font-semibold text-th-text truncate">
                {currentChapter.title}
              </span>
            </div>

            {/* Progress badge */}
            {chapterInfo && (
              <span className="hidden sm:inline-flex items-center gap-1 text-xs text-th-text-4 bg-th-hover px-2 py-0.5 rounded-md">
                {chapterInfo.index + 1}/{chapterInfo.total}
              </span>
            )}
          </div>

          {/* Right toolbar */}
          <div className="flex items-center gap-1 md:gap-2">
            <ThemeSwitcher />

            {/* Desktop chapter nav */}
            {chapterInfo && (
              <div className="hidden md:flex items-center gap-1">
                <button
                  onClick={() => chapterInfo.prevId !== null && navigateChapter(chapterInfo.prevId!)}
                  disabled={!chapterInfo.canPrev}
                  className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  aria-label="上一章"
                >
                  <ChevronLeft size={18} />
                </button>
                <button
                  onClick={() => chapterInfo.nextId !== null && navigateChapter(chapterInfo.nextId!)}
                  disabled={!chapterInfo.canNext}
                  className="p-1.5 rounded-lg text-th-text-3 hover:text-th-text hover:bg-th-hover disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  aria-label="下一章"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            )}

            <button
              className={`p-1.5 rounded-lg transition-colors hover:opacity-80 ${
                rightPanelOpen ? "text-th-accent-text bg-th-accent-dim" : "text-th-text-3"
              }`}
              onClick={() => setRightPanelOpen((v) => !v)}
              aria-label="切换 Agent 面板"
            >
              <PanelRight size={18} />
            </button>
          </div>
        </div>

        {/* Chapter content */}
        <div className="flex-1 overflow-y-auto">
          <div className="reading-container max-w-3xl mx-auto px-5 md:px-12 py-6 md:py-12">
            {currentChapter.content ? (
              <>
                {/* Chapter header */}
                <div className="mb-8 pb-6 border-b border-th-border-subtle">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="chapter-badge text-xs font-medium text-th-accent-text bg-th-accent-dim px-2.5 py-1 rounded-md">
                      第 {currentChapter.id} 章
                    </span>
                    <span className="text-xs text-th-text-4 flex items-center gap-1">
                      <Clock size={11} />
                      {currentChapter.status === "completed" ? "已完成" : "草稿"}
                    </span>
                  </div>
                  <h1 className="prose-title text-th-text">{currentChapter.title}</h1>
                </div>

                {/* Content reading view */}
                <article className="prose-reading whitespace-pre-wrap">
                  {currentChapter.content}
                </article>

                {/* Chapter footer — copy + nav */}
                <div className="mt-12 pt-6 border-t border-th-border-subtle flex items-center justify-between">
                  <button
                    onClick={handleCopy}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                      copied
                        ? "bg-[var(--th-success)]/10 text-[var(--th-success)]"
                        : "bg-th-hover text-th-text-3 hover:text-th-text hover:bg-th-hover-strong"
                    }`}
                  >
                    {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    {copied ? "已复制" : "复制全文"}
                  </button>

                  {chapterInfo && (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => chapterInfo.prevId !== null && navigateChapter(chapterInfo.prevId!)}
                        disabled={!chapterInfo.canPrev}
                        className="flex items-center gap-1.5 text-xs font-medium text-th-text-3 hover:text-th-text disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        <ArrowLeft size={14} />
                        上一章
                      </button>
                      <span className="text-xs text-th-text-4">·</span>
                      <button
                        onClick={() => chapterInfo.nextId !== null && navigateChapter(chapterInfo.nextId!)}
                        disabled={!chapterInfo.canNext}
                        className="flex items-center gap-1.5 text-xs font-medium text-th-text-3 hover:text-th-text disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        下一章
                        <ArrowRight size={14} />
                      </button>
                    </div>
                  )}
                </div>

                {/* Complete chapter button */}
                {isEditable && !isProjectCompleted && draftStepCount >= 1 && (
                  <div className="mt-6">
                    <button
                      onClick={() => {
                        if (!project || !currentChapter) return;
                        completeChapter(project.id, currentChapter.id);
                        addToast({ type: "success", message: "本章已标记为只读" });
                      }}
                      className="w-full py-2.5 rounded-lg text-xs font-medium bg-th-accent-dim text-th-accent-text hover:bg-th-accent-dim/70 transition-colors"
                    >
                      <CheckCircle2 size={14} className="inline mr-1.5" />
                      完成本章，标为只读
                    </button>
                  </div>
                )}
              </>
            ) : (
              /* Empty chapter — needs to be written */
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-th-hover">
                  <Edit3 size={24} className="text-th-text-4" />
                </div>
                <h3 className="text-base font-semibold text-th-text">开始创作</h3>
                <p className="text-sm text-th-text-3 text-center max-w-sm">
                  这是你的最新章节，选择下方的写作选项或自由输入来推进剧情。
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Options Panel (editable chapter) */}
        {isEditable && !isProjectCompleted && (
          <OptionsPanel
            project={project}
            onDraftStep={() => setDraftStepCount((c) => c + 1)}
          />
        )}

        {/* Mobile bottom nav (completed chapters) */}
        {currentChapter?.status === "completed" && (
          <div className="shrink-0 md:hidden grid grid-cols-3 items-center px-3 py-3 border-t border-th-border-subtle bg-th-card safe-bottom">
            <button
              onClick={() => chapterNav.prev !== null && navigateChapter(chapterNav.prev!)}
              disabled={chapterNav.prev === null}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-30 justify-self-start text-th-text-2 bg-th-hover"
            >
              <ChevronLeft size={14} />
              上一章
            </button>
            <button
              onClick={handleCopy}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all justify-self-center ${
                copied
                  ? "text-[var(--th-success)] bg-[var(--th-success)]/10 border-[1.5px] border-[var(--th-success)]/30"
                  : "text-th-accent-text bg-th-card border-[1.5px] border-th-border"
              }`}
            >
              {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
              {copied ? "已复制" : "一键复制"}
            </button>
            <button
              onClick={() => chapterNav.next !== null && navigateChapter(chapterNav.next!)}
              disabled={chapterNav.next === null}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-30 justify-self-end text-th-text-2 bg-th-hover"
            >
              下一章
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </main>

      {/* ── Right: Agent Panel (desktop) ── */}
      {rightPanelOpen && (
        <div className="hidden md:flex">
          <div
            onMouseDown={onResizeMouseDown("right")}
            className="shrink-0 w-1.5 cursor-col-resize hover:opacity-100 opacity-0 transition-opacity relative bg-th-accent-dim"
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
          <AgentPanel onClose={() => setRightPanelOpen(false)} width={rightPanelWidth} />
        </div>
      )}

      {/* ── Right: Agent Panel (mobile overlay) ── */}
      {rightPanelOpen && (
        <>
          <div
            className="fixed inset-0 z-40 md:hidden transition-opacity duration-250 bg-th-overlay"
            onClick={() => setRightPanelOpen(false)}
          />
          <div className="fixed inset-y-0 right-0 z-50 overflow-y-auto md:hidden animate-slide-in-right bg-th-card shadow-[var(--th-shadow-panel-right)] w-4/5 max-w-sm">
            <div className="flex items-center justify-between px-4 py-3.5 border-b border-th-border-subtle bg-th-bg/60 backdrop-blur">
              <span className="text-sm font-semibold text-th-text">Agent 调度</span>
              <button
                onClick={() => setRightPanelOpen(false)}
                className="p-1.5 rounded-lg transition-colors text-th-text-3 hover:bg-th-hover"
              >
                <X size={18} />
              </button>
            </div>
            <AgentPanel onClose={() => setRightPanelOpen(false)} width={0} />
          </div>
        </>
      )}
    </div>
  );
}
