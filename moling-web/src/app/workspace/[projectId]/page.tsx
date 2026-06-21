"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useWritingStore, PHASE_LABELS } from "@/stores/useWritingStore";
import type { Project } from "@/stores/useWritingStore";
import { useTheme, THEMES } from "@/stores/useTheme";
import type { ThemeId } from "@/stores/useTheme";
import type { Option } from "@/stores/useWritingStore";
import { Sidebar } from "@/components/vibe/Sidebar";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";
import { AgentPanel } from "@/components/vibe/AgentPanel";
import { PanelRight, Send, RefreshCw, BookOpen, Edit3, Eye, CheckCircle2, Copy, Menu, X, Plus, ChevronDown, ChevronLeft, ChevronRight, Library, Package, Settings } from "lucide-react";
import { MOCK_PROJECTS, MOCK_OPTIONS } from "@/mock/data/workspace";

function OptionsPanel({ project, onDraftStep }: { project: Project; onDraftStep?: () => void }) {
  const [options] = useState<Option[]>(MOCK_OPTIONS);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [mode, setMode] = useState<"options" | "custom">("options");

  const handleSelect = (optionId: string) => {
    setSelectedOption(optionId);
  };

  const handleConfirm = () => {
    // TODO: 确认选择，推进剧情
    setIsGenerating(true);
    onDraftStep?.();
    setTimeout(() => {
      setIsGenerating(false);
      setSelectedOption(null);
    }, 1200);
  };

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => setIsGenerating(false), 1200);
  };

  return (
    <div
      className="shrink-0 border-t"
      style={{ borderColor: "var(--th-border-subtle)" }}
    >
      <div className="px-4 py-3">
        {/* Mode toggle */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setMode("options")}
              className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
              style={{
                background: mode === "options" ? "var(--th-accent-dim)" : "transparent",
                color: mode === "options" ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              选项
            </button>
            <button
              onClick={() => setMode("custom")}
              className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
              style={{
                background: mode === "custom" ? "var(--th-accent-dim)" : "transparent",
                color: mode === "custom" ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              自定义
            </button>
          </div>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors hover:opacity-80 disabled:opacity-50"
            style={{ color: "var(--th-text-4)" }}
          >
            <RefreshCw size={11} className={isGenerating ? "animate-spin" : ""} />
            <span>重新生成</span>
          </button>
        </div>

        {mode === "options" ? (
          /* A/B/C 选项卡片 */
          <div className="space-y-2">
            {options.map((opt) => {
              const isSelected = selectedOption === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => handleSelect(opt.id)}
                  className="w-full text-left px-3 py-2.5 rounded-lg border transition-all"
                  style={{
                    borderColor: isSelected ? "var(--th-accent-text)" : "var(--th-border-subtle)",
                    background: isSelected ? "var(--th-accent-dim)" : "var(--th-card)",
                  }}
                >
                  <div className="flex items-start gap-3">
                    {/* Label badge */}
                    <span
                      className="w-6 h-6 rounded text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5"
                      style={{
                        background: isSelected ? "var(--th-accent-text)" : "var(--th-hover)",
                        color: isSelected ? "#fff" : "var(--th-text-3)",
                      }}
                    >
                      {opt.label}
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-semibold" style={{ color: "var(--th-text)" }}>
                          {opt.title}
                        </span>
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{
                            background: `hsl(${opt.confidence * 120}, 40%, 90%)`,
                            color: `hsl(${opt.confidence * 120}, 50%, 30%)`,
                          }}
                        >
                          {Math.round(opt.confidence * 100)}%
                        </span>
                      </div>
                      <p className="text-[11px] leading-relaxed mb-1" style={{ color: "var(--th-text-3)" }}>
                        {opt.description}
                      </p>
                      <p className="text-[10px] italic" style={{ color: "var(--th-text-4)" }}>
                        {opt.preview}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}

            {/* Confirm button */}
            <button
              onClick={handleConfirm}
              disabled={!selectedOption || isGenerating}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-40"
              style={{
                background: selectedOption ? "var(--th-accent-text)" : "var(--th-hover)",
                color: selectedOption ? "#fff" : "var(--th-text-4)",
              }}
            >
              {isGenerating ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              <span>{isGenerating ? "生成中..." : selectedOption ? "确认选择" : "请先选择一个选项"}</span>
            </button>
          </div>
        ) : (
          /* D — 自由输入 */
          <div className="space-y-2">
            <textarea
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="写下你的想法，或选择上方「选项」让 AI 提供建议..."
              className="w-full h-20 rounded-lg px-3 py-2 text-xs resize-none transition-colors"
              style={{
                background: "var(--th-card)",
                borderColor: "var(--th-border-subtle)",
                color: "var(--th-text-2)",
                border: "1px solid var(--th-border-subtle)",
              }}
            />
            <button
              onClick={() => {
                if (!customInput.trim()) return;
                setIsGenerating(true);
                onDraftStep?.();
                setTimeout(() => {
                  setIsGenerating(false);
                  setCustomInput("");
                }, 1200);
              }}
              disabled={!customInput.trim() || isGenerating}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-40"
              style={{
                background: customInput.trim() ? "var(--th-accent-text)" : "var(--th-hover)",
                color: customInput.trim() ? "#fff" : "var(--th-text-4)",
              }}
            >
              {isGenerating ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              <span>{isGenerating ? "提交中..." : "提交"}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Mobile sidebar content — extracted for overlay use */
function MobileSidebarContent({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const projects = useWritingStore((s) => s.projects);
  const activeProjectId = useWritingStore((s) => s.activeProjectId);
  const expandedProjectId = useWritingStore((s) => s.expandedProjectId);
  const activeChapterId = useWritingStore((s) => s.activeChapterId);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const setActiveChapter = useWritingStore((s) => s.setActiveChapter);
  const toggleProjectExpand = useWritingStore((s) => s.toggleProjectExpand);

  const handleProjectClick = (projId: string) => {
    setActiveProject(projId);
    toggleProjectExpand(projId);
    router.push(`/workspace/${projId}`);
    onClose();
  };

  const handleChapterClick = (projId: string, chId: number) => {
    setActiveChapter(chId);
    router.push(`/workspace/${projId}`);
    onClose();
  };

  // Filter projects
  const ongoing = projects.filter((p) => p.chapters.some((ch) => ch.status !== "completed"));
  const completed = projects.filter((p) => p.chapters.length > 0 && p.chapters.every((ch) => ch.status === "completed"));

  return (
    <div className="flex flex-col h-full">
      {/* New project */}
      <div className="px-3 py-3">
        <button
          onClick={() => { router.push("/projects/new"); onClose(); }}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-colors"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          <Plus size={16} />
          <span>新建项目</span>
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2">
        {/* 连载中 */}
        <div className="flex items-center justify-between px-2.5 py-2">
          <span className="text-[10px] font-semibold tracking-wider uppercase" style={{ color: "var(--th-text-4)" }}>连载中</span>
          <span className="text-[10px]" style={{ color: "var(--th-text-4)" }}>{ongoing.length}</span>
        </div>

        {ongoing.map((proj) => {
          const isActive = proj.id === activeProjectId;
          const isExpanded = expandedProjectId === proj.id;
          return (
            <div key={proj.id} className="mb-0.5">
              <button
                onClick={() => handleProjectClick(proj.id)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm transition-colors"
                style={{
                  color: isActive ? "var(--th-accent-text)" : "var(--th-text-2)",
                  background: isActive ? "var(--th-accent-dim)" : "transparent",
                }}
              >
                <span style={{ transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}>
                  <ChevronDown size={14} />
                </span>
                <span className="flex-1 text-left truncate font-medium">{proj.title}</span>
              </button>

              {isExpanded && (
                <div className="ml-7 border-l" style={{ borderColor: "var(--th-border-subtle)" }}>
                  {[...proj.chapters].reverse().map((ch) => (
                    <button
                      key={ch.id}
                      onClick={() => handleChapterClick(proj.id, ch.id)}
                      className="w-full flex items-center gap-2.5 pl-3 pr-2.5 py-2 text-xs transition-colors text-left rounded-r-lg"
                      style={{
                        color: ch.id === activeChapterId ? "var(--th-accent-text)" : "var(--th-text-3)",
                        background: ch.id === activeChapterId ? "var(--th-accent-dim)" : "transparent",
                      }}
                    >
                      <span className="w-5 h-5 rounded-full text-[10px] flex items-center justify-center shrink-0 font-medium"
                        style={{
                          background: ch.status === "completed" ? "var(--th-accent-dim)" : "var(--th-accent-text)",
                          color: ch.status === "completed" ? "var(--th-accent-text)" : "#fff",
                        }}
                      >{ch.id}</span>
                      <span className="truncate">{ch.title}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* 已完结 */}
        {completed.length > 0 && (
          <>
            <div className="flex items-center justify-between px-2.5 py-2 mt-3">
              <span className="text-[10px] font-semibold tracking-wider uppercase" style={{ color: "var(--th-text-4)" }}>已完结</span>
              <span className="text-[10px]" style={{ color: "var(--th-text-4)" }}>{completed.length}</span>
            </div>
            {completed.map((proj) => {
              const isActive = proj.id === activeProjectId;
              const isExpanded = expandedProjectId === proj.id;
              return (
                <div key={proj.id} className="mb-0.5">
                  <button
                    onClick={() => handleProjectClick(proj.id)}
                    className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-sm transition-colors"
                    style={{
                      color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)",
                      background: isActive ? "var(--th-accent-dim)" : "transparent",
                    }}
                  >
                    <span style={{ transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)", transition: "transform 0.2s" }}>
                      <ChevronDown size={14} />
                    </span>
                    <span className="flex-1 text-left truncate">{proj.title}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded shrink-0" style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}>完结</span>
                  </button>
                  {isExpanded && (
                    <div className="ml-7 border-l" style={{ borderColor: "var(--th-border-subtle)" }}>
                      {[...proj.chapters].reverse().map((ch) => (
                        <button
                          key={ch.id}
                          onClick={() => handleChapterClick(proj.id, ch.id)}
                          className="w-full flex items-center gap-2.5 pl-3 pr-2.5 py-2 text-xs transition-colors text-left rounded-r-lg"
                          style={{
                            color: "var(--th-text-3)",
                            opacity: 0.6,
                          }}
                        >
                          <span className="w-5 h-5 rounded-full text-[10px] flex items-center justify-center shrink-0 font-medium"
                            style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
                          >{ch.id}</span>
                          <span className="truncate">{ch.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </nav>

      {/* Bottom: 知识中心 | 插件市场 | 用户设置 */}
      <div className="shrink-0 border-t" style={{ borderColor: "var(--th-border-subtle)" }}>
        <button className="w-full flex items-center gap-3 px-4 py-3 text-sm" style={{ color: "var(--th-text-2)" }}>
          <Library size={16} style={{ color: "var(--th-text-3)" }} />
          <span>知识中心</span>
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded" style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}>即将推出</span>
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-3 text-sm" style={{ color: "var(--th-text-2)" }}>
          <Package size={16} style={{ color: "var(--th-text-3)" }} />
          <span>插件市场</span>
          <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded" style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}>即将推出</span>
        </button>
        <button
          onClick={() => { router.push("/settings"); onClose(); }}
          className="w-full flex items-center gap-3 px-4 py-3 text-sm border-t"
          style={{ borderColor: "var(--th-border-subtle)", color: "var(--th-text-2)" }}
        >
          <Settings size={16} style={{ color: "var(--th-text-3)" }} />
          <span>用户设置</span>
        </button>
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const router = useRouter();

  const project = useWritingStore((s) => s.project);
  const activeChapterId = useWritingStore((s) => s.activeChapterId);
  const projects = useWritingStore((s) => s.projects);
  const loadProjects = useWritingStore((s) => s.loadProjects);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const setActiveChapter = useWritingStore((s) => s.setActiveChapter);
  const completeChapter = useWritingStore((s) => s.completeChapter);
  const { theme, setTheme } = useTheme();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(240);
  const [rightPanelWidth, setRightPanelWidth] = useState(260);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [draftStepCount, setDraftStepCount] = useState(0);

  // 切换章节时重置写作步数
  useEffect(() => {
    setDraftStepCount(0);
  }, [activeChapterId]);

  // ── 拖拽缩放逻辑 ──
  const resizeRef = useRef<{ side: "left" | "right"; startX: number; startW: number } | null>(null);

  const onResizeMouseDown = useCallback((side: "left" | "right") => (e: React.MouseEvent) => {
    e.preventDefault();
    const startW = side === "left" ? sidebarWidth : rightPanelWidth;
    resizeRef.current = { side, startX: e.clientX, startW };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [sidebarWidth, rightPanelWidth]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!resizeRef.current) return;
      const { side, startX, startW } = resizeRef.current;
      const delta = side === "left" ? e.clientX - startX : startX - e.clientX;
      const newW = Math.round(startW + delta);
      if (side === "left") {
        setSidebarWidth(Math.max(160, Math.min(400, newW)));
      } else {
        setRightPanelWidth(Math.max(200, Math.min(500, newW)));
      }
    };
    const onUp = () => {
      resizeRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  // 当前查看的章节
  const currentChapter = activeChapterId
    ? project?.chapters.find((c) => c.id === activeChapterId) ?? null
    : null;
  /** 最后一个章节 — 以实际数据为准，而非依赖 chapters.length */
  const lastChapter = project?.chapters[project.chapters.length - 1];
  const lastChapterId = lastChapter?.id ?? null;

  /** 当前章节是否可编辑 */
  const isEditable = (
    activeChapterId !== null &&
    lastChapterId !== null &&
    activeChapterId === lastChapterId &&
    currentChapter?.status !== "completed"
  );
  const isProjectCompleted = project && project.chapters.length > 0 && project.chapters.every((ch) => ch.status === "completed");

  const handleCopy = useCallback(() => {
    const text = currentChapter?.content || "";
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed"; ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [currentChapter?.content]);

  /** 基于业务状态计算状态描述 */
  const statusInfo = useMemo(() => {
    const chapterLabel = currentChapter ? `第 ${currentChapter.id} 章 · ${currentChapter.title}` : `第 ? 章`;

    if (!project) return { icon: <BookOpen size={13} />, label: "加载中", color: "var(--th-text-4)" };

    if (isProjectCompleted) {
      return { icon: <CheckCircle2 size={13} />, label: chapterLabel, color: "var(--th-accent-text)" };
    }

    if (isEditable) {
      return { icon: <Edit3 size={13} />, label: chapterLabel, color: "var(--th-accent-text)" };
    }

    return { icon: <Eye size={13} />, label: chapterLabel, color: "var(--th-text-3)" };
  }, [project, isProjectCompleted, isEditable, currentChapter]);

  /** 章节导航：上/下一章 ID */
  const chapterNav = useMemo(() => {
    if (!project || activeChapterId === null) return { prev: null, next: null };
    const chapters = project.chapters;
    const idx = chapters.findIndex((c) => c.id === activeChapterId);
    return {
      prev: idx > 0 ? chapters[idx - 1].id : null,
      next: idx < chapters.length - 1 ? chapters[idx + 1].id : null,
    };
  }, [project, activeChapterId]);

  const navigateChapter = useCallback((chId: number) => {
    setActiveChapter(chId);
  }, [setActiveChapter]);

  /** 加载多书 Mock */
  useEffect(() => {
    if (projects.length === 0) {
      loadProjects(MOCK_PROJECTS);
    }
    if (projectId && project?.id !== projectId) {
      setActiveProject(projectId);
    }
    // 默认选中最后一章（可编辑章节）
    if (activeChapterId === null && project && project.chapters.length > 0) {
      setActiveChapter(project.chapters.length);
    }
  }, [loadProjects, setActiveProject, setActiveChapter, projectId, project?.id, projects.length, activeChapterId, project]);

  /** Ctrl+Shift+T: 循环切换主题 */
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === "T") {
        e.preventDefault();
        const idx = THEMES.findIndex((t) => t.id === theme);
        const next = THEMES[(idx + 1) % THEMES.length];
        setTheme(next.id as ThemeId);
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [theme, setTheme]);

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
      {/* ================================================================
          Desktop Sidebar — hidden below md, replaced by overlay
          ================================================================ */}
      <div className="hidden md:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((v) => !v)}
          width={sidebarWidth}
        />
      </div>

      {/* Left resize handle — desktop only */}
      {!sidebarCollapsed && (
        <div className="hidden md:block"
          onMouseDown={onResizeMouseDown("left")}
          style={{
            width: 6,
            cursor: "col-resize",
            background: "var(--th-accent-dim)",
            flexShrink: 0,
          }}
        />
      )}

      {/* ================================================================
          Mobile Left Panel — 80vw overlay from left
          参考: Material Design (360dp/80%) · 微信 (80%) · ChatGPT (85%)
          ================================================================ */}
      {mobileMenuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 md:hidden transition-opacity duration-250"
            style={{ background: "var(--th-overlay)" }}
            onClick={() => setMobileMenuOpen(false)}
          />
          {/* 80vw slide-in from left */}
          <div
            className="fixed inset-y-0 left-0 z-50 overflow-y-auto md:hidden animate-slide-in-left"
            style={{
              width: "80vw",
              background: "var(--th-card)",
              boxShadow: "4px 0 24px rgba(0,0,0,0.3)",
            }}
          >
            <div className="flex items-center justify-between px-4 py-3.5 border-b" style={{ borderColor: "var(--th-border-subtle)" }}>
              <span className="text-sm font-semibold" style={{ color: "var(--th-text)" }}>墨灵</span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg transition-colors"
                style={{ color: "var(--th-text-3)" }}
              >
                <X size={20} />
              </button>
            </div>
            <MobileSidebarContent onClose={() => setMobileMenuOpen(false)} />
          </div>
        </>
      )}

      {/* ================================================================
          Main Stage
          ================================================================ */}
      <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
        {/* Top bar — hamburger (mobile) | status (desktop) | theme | right panel */}
        <div className="shrink-0 flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3">
          {/* Mobile hamburger */}
          <button
            className="md:hidden p-1.5 rounded-lg transition-colors"
            style={{ color: "var(--th-text-3)" }}
            onClick={() => setMobileMenuOpen(true)}
            aria-label="菜单"
          >
            <Menu size={20} />
          </button>

          {/* Status — 全端可见 */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="shrink-0" style={{ color: statusInfo.color }}>{statusInfo.icon}</span>
            <span className="text-[11px] font-semibold truncate" style={{ color: statusInfo.color }}>
              {statusInfo.label}
            </span>
          </div>
          <ThemeSwitcher />
          {/* Right panel toggle — mobile + desktop */}
          <button
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            onClick={() => setRightPanelOpen((v) => !v)}
            style={{ color: rightPanelOpen ? "var(--th-accent-text)" : "var(--th-text-3)" }}
            aria-label="切换右栏"
          >
            <PanelRight size={18} />
          </button>
        </div>

        {/* Center stage — chapter content */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Content area */}
          <div className="flex-1 overflow-y-auto px-4 md:px-6 py-3 md:py-4">
            <div className="max-w-4xl mx-auto">
              {/* Chapter content */}
              <div
                className="text-sm leading-relaxed whitespace-pre-wrap"
                style={{ color: "var(--th-text-2)" }}
              >
                {currentChapter?.content || "暂无内容"}
              </div>

              {/* 完成本章 button — 仅在完成 1 步以上写作后出现（最后一步写作） */}
              {isEditable && !isProjectCompleted && draftStepCount >= 1 && (
                <button
                  onClick={() => {
                    if (!project || !currentChapter) return;
                    completeChapter(project.id, currentChapter.id);
                  }}
                  className="mt-4 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors hover:opacity-80"
                  style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
                >
                  完成本章，标为只读
                </button>
              )}
            </div>
          </div>

          {/* Options Panel — only for non-completed projects with editable chapter */}
          {isEditable && !isProjectCompleted && <OptionsPanel project={project} onDraftStep={() => setDraftStepCount(c => c + 1)} />}

          {/* Mobile 章节导航条 — 仅已完结章节显示（参考番茄小说/起点读书） */}
          {currentChapter?.status === "completed" && (
            <div
              className="shrink-0 md:hidden grid grid-cols-3 items-center px-3 py-3 border-t"
              style={{ borderColor: "var(--th-border-subtle)", background: "var(--th-card)" }}
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
                  border: copied ? "1.5px solid #34d399" : "1.5px solid var(--th-border)",
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

      {/* ================================================================
          Right Panel — Agent of Agents 调度中心 (desktop only)
          ================================================================ */}
      {rightPanelOpen && (
        <div className="hidden md:flex">
          {/* Right resize handle */}
          <div
            onMouseDown={onResizeMouseDown("right")}
            className="shrink-0 w-1.5 cursor-col-resize hover:opacity-100 opacity-0 transition-opacity relative"
            style={{ background: "var(--th-accent-dim)" }}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
          <AgentPanel onClose={() => setRightPanelOpen(false)} width={rightPanelWidth} />
        </div>
      )}

      {/* ================================================================
          Mobile Right Panel — 80vw overlay from right
          参考: 微信读书书签 · iOS Sheets · Telegram 侧边
          ================================================================ */}
      {rightPanelOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 md:hidden transition-opacity duration-250"
            style={{ background: "var(--th-overlay)" }}
            onClick={() => setRightPanelOpen(false)}
          />
          {/* 80vw slide-in from right */}
          <div
            className="fixed inset-y-0 right-0 z-50 overflow-y-auto md:hidden animate-slide-in-right"
            style={{
              width: "80vw",
              background: "var(--th-card)",
              boxShadow: "-4px 0 24px rgba(0,0,0,0.3)",
            }}
          >
            <div className="flex items-center justify-between px-4 py-3.5 border-b" style={{ borderColor: "var(--th-border-subtle)" }}>
              <span className="text-sm font-semibold" style={{ color: "var(--th-text)" }}>Agent 调度</span>
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
