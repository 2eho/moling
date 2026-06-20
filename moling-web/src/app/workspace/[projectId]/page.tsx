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
import { PanelRight, Send, RefreshCw, BookOpen, Edit3, Eye, CheckCircle2, Activity, GitBranch, Library } from "lucide-react";

/** 多书 Mock 数据 */
const MOCK_PROJECTS = [
  {
    id: "novel-001",
    title: "剑道巅峰",
    genre: "玄幻修仙",
    phase: "drafting" as const,
    currentChapter: 3,
    totalChapters: 12,
    summary: "少年林风身怀绝世剑骨，却被视为废材。一朝觉醒，踏上逆天改命之路。",
    chapters: [
      { id: 1, title: "废材少年", summary: "...", content: `林风站在宗门演武场上，周围的嘲笑声如潮水般涌来。\n\n\u201c废材\u201d——这是他十六年来听得最多的两个字。\n\n身怀绝世剑骨，却因经脉堵塞无法凝聚灵力。在九州大陆，不能修炼就等于废物。\n\n但他从未放弃。\n\n每个深夜，当师兄弟们沉睡时，他独自在后山挥剑三千次。汗水浸透布衣，剑柄磨破掌心，结痂再裂，裂了再结。\n\n\u201c我不信命。\u201d\n\n月光下，少年眼中燃着一团不灭的火。`, status: "completed" as const },
      { id: 2, title: "剑骨觉醒", summary: "...", content: `剧痛自脊柱蔓延全身，林风咬紧牙关，鲜血从嘴角渗出。\n\n剑骨正在觉醒，那股沉寂了十六年的力量如洪荒猛兽般苏醒。\n\n骨骼寸寸爆响，经脉中仿佛有千万柄利剑在奔涌。痛，但畅快。\n\n\u201c原来……这就是剑骨的力量。\u201d\n\n一道通天剑意自他体内迸发，直冲云霄。整个宗门为之震动。`, status: "completed" as const },
      { id: 3, title: "剑指苍穹", summary: "...", content: `宗门议事大殿中，掌门与诸位长老目光灼灼。\n\n\u201c林风，你可知剑骨觉醒意味着什么？\u201d掌门的声音带着一丝颤抖。\n\n九州千年以来，剑骨觉醒者不过三人。每一人，都曾改写了大陆的格局。\n\n林风抬头，目光平静却坚定：\u201c我只知道，我再也不做废材了。\u201d`, status: "draft" as const },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
  },
  {
    id: "novel-002",
    title: "都市修仙传",
    genre: "都市异能",
    phase: "outline" as const,
    currentChapter: 1,
    totalChapters: 24,
    summary: "现代都市中隐藏的修仙世界，平凡大学生意外觉醒灵根。",
    chapters: [
      { id: 1, title: "灵根初醒", summary: "...", content: "", status: "draft" as const },
      { id: 2, title: "都市暗流", summary: "...", content: "", status: "draft" as const },
      { id: 3, title: "初入宗门", summary: "...", content: "", status: "draft" as const },
      { id: 4, title: "破境之战", summary: "...", content: "", status: "draft" as const },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
  },
  {
    id: "novel-003",
    title: "末世重生",
    genre: "末世科幻",
    phase: "character" as const,
    currentChapter: 2,
    totalChapters: 18,
    summary: "重生回到末世降临前三小时，这一世他不再做任何人的棋子。",
    chapters: [
      { id: 1, title: "血月降临", summary: "...", content: "", status: "completed" as const },
      { id: 2, title: "前世记忆", summary: "...", content: "", status: "draft" as const },
      { id: 3, title: "末日倒计时", summary: "...", content: "", status: "draft" as const },
      { id: 4, title: "第一滴血", summary: "...", content: "", status: "draft" as const },
      { id: 5, title: "安全区", summary: "...", content: "", status: "draft" as const },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
  },
  {
    id: "novel-004",
    title: "星际流浪者",
    genre: "科幻",
    phase: "revision" as const,
    currentChapter: 3,
    totalChapters: 3,
    summary: "人类最后的方舟在星际间漂流，找寻新家园的故事。",
    chapters: [
      { id: 1, title: "启航", summary: "...", content: "", status: "completed" as const },
      { id: 2, title: "深空", summary: "...", content: "", status: "completed" as const },
      { id: 3, title: "新世界", summary: "...", content: "", status: "completed" as const },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
  },
];

const MOCK_OPTIONS: Option[] = [
  {
    id: "a",
    label: "A",
    title: "展开宗门试炼",
    description: "林风在剑骨觉醒后迎来第一次宗门试炼，面对昔日嘲笑他的同门，用实力证明自己。",
    preview: `\u201c林风，你敢与我一战？\u201d 曾经最看不起他的人站在擂台中央……`,
    agent: "plot",
    confidence: 0.87,
  },
  {
    id: "b",
    label: "B",
    title: "神秘老者来访",
    description: "剑骨觉醒震动了一位隐居多年的剑道宗师，他夜访林风，带来了一个关于剑骨的惊天秘密。",
    preview: `\u201c你的剑骨，并非天生的。\u201d 月光下，老者的话让林风愣住了……`,
    agent: "character",
    confidence: 0.82,
  },
  {
    id: "c",
    label: "C",
    title: "外门试剑大会",
    description: "宗门举办外门试剑大会，林风代表外门出战内门天才，一场越级之战即将打响。",
    preview: `\u201c外门废材也想挑战内门？\u201d 全场哗然，只有林风神色如常……`,
    agent: "plot",
    confidence: 0.75,
  },
];

function OptionsPanel({ project }: { project: Project }) {
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

  /** 基于业务状态计算状态描述 */
  const statusInfo = useMemo(() => {
    if (!project) return { icon: <BookOpen size={13} />, label: "加载中", color: "var(--th-text-4)" };

    if (isProjectCompleted) {
      return { icon: <CheckCircle2 size={13} />, label: "已完结", color: "var(--th-accent-text)" };
    }

    if (isEditable) {
      return { icon: <Edit3 size={13} />, label: `写作中 · ${PHASE_LABELS[project.phase]}`, color: "var(--th-accent-text)" };
    }

    return { icon: <Eye size={13} />, label: "回顾中", color: "var(--th-text-3)" };
  }, [project, isProjectCompleted, isEditable, currentChapter]);

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
          Left Sidebar — collapsible
          ================================================================ */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        width={sidebarWidth}
      />

      {/* Left resize handle — only when expanded */}
      {!sidebarCollapsed && (
        <div
          onMouseDown={onResizeMouseDown("left")}
          className="shrink-0 w-1.5 cursor-col-resize hover:opacity-100 opacity-0 transition-opacity relative group"
          style={{ background: "var(--th-accent-dim)" }}
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
        </div>
      )}

      {/* ================================================================
          Main Stage
          ================================================================ */}
      <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
        {/* Top bar — status left + theme + right panel toggle */}
        <div className="shrink-0 flex items-center gap-2 px-4 py-3">
          {/* 状态条 — 左对齐 */}
          <div className="flex items-center gap-2.5">
            <span style={{ color: statusInfo.color }}>{statusInfo.icon}</span>
            <span className="text-[11px] font-semibold" style={{ color: statusInfo.color }}>
              {statusInfo.label}
            </span>
          </div>
          <div className="flex-1" />
          {/* Feature navigation */}
          <div className="flex items-center gap-1 mr-2">
            <Link
              href={`/workspace/${projectId}/health`}
              className="p-1.5 rounded-lg transition-colors hover:opacity-80"
              style={{ color: "var(--th-text-3)" }}
              title="健康监控"
            >
              <Activity size={16} />
            </Link>
            <Link
              href={`/workspace/${projectId}/phase4/tasks`}
              className="p-1.5 rounded-lg transition-colors hover:opacity-80"
              style={{ color: "var(--th-text-3)" }}
              title="Phase 4 任务"
            >
              <GitBranch size={16} />
            </Link>
            <Link
              href={`/vaults/${projectId}`}
              className="p-1.5 rounded-lg transition-colors hover:opacity-80"
              style={{ color: "var(--th-text-3)" }}
              title="四库系统"
            >
              <Library size={16} />
            </Link>
          </div>
          <ThemeSwitcher />
          <button
            onClick={() => setRightPanelOpen((v) => !v)}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ color: rightPanelOpen ? "var(--th-accent-text)" : "var(--th-text-3)" }}
            aria-label="切换右栏"
          >
            <PanelRight size={18} />
          </button>
        </div>

        {/* Center stage — chapter content */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Content area */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            <div className="max-w-4xl mx-auto">
              {/* Chapter title */}
              <h2
                className="text-base font-semibold mb-4"
                style={{ color: "var(--th-text)" }}
              >
                {currentChapter ? `第 ${currentChapter.id} 章 — ${currentChapter.title}` : "选择章节"}
                {(!isEditable || isProjectCompleted) && currentChapter && (
                  <span
                    className="ml-2 text-[10px] px-1.5 py-0.5 rounded align-middle"
                    style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}
                  >
                    只读
                  </span>
                )}
                {isProjectCompleted && (
                  <span
                    className="ml-2 text-[10px] px-1.5 py-0.5 rounded align-middle"
                    style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
                  >
                    已完结
                  </span>
                )}
              </h2>

              {/* Chapter content */}
              <div
                className="text-sm leading-relaxed whitespace-pre-wrap"
                style={{ color: "var(--th-text-2)" }}
              >
                {currentChapter?.content || "暂无内容"}
              </div>

              {/* 完成本章 button — 仅对活跃连载项目的可编辑章节 */}
              {isEditable && !isProjectCompleted && currentChapter && (
                <button
                  onClick={() => {
                    if (!project) return;
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
          {isEditable && !isProjectCompleted && <OptionsPanel project={project} />}
        </div>

        {/* Bottom status bar */}
        <div
          className="shrink-0 flex items-center justify-between px-4 py-1.5 text-[10px] border-t"
          style={{
            borderColor: "var(--th-border-subtle)",
            color: "var(--th-text-4)",
          }}
        >
          <span>
            {project.title} · {currentChapter ? `第 ${currentChapter.id} 章 / ${project.totalChapters} 章` : `共 ${project.totalChapters} 章`}
            {currentChapter && (
              <span className="ml-2" style={{ color: currentChapter.status === "completed" ? "var(--th-accent-text)" : "var(--th-text-4)" }}>
                · {currentChapter.status === "completed" ? "已完成" : "草稿"}
              </span>
            )}
          </span>
          <span>{project.genre}</span>
        </div>
      </main>

      {/* ================================================================
          Right Panel — Agent of Agents 调度中心
          ================================================================ */}
      {rightPanelOpen && (
        <>
          {/* Right resize handle */}
          <div
            onMouseDown={onResizeMouseDown("right")}
            className="shrink-0 w-1.5 cursor-col-resize hover:opacity-100 opacity-0 transition-opacity relative"
            style={{ background: "var(--th-accent-dim)" }}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>
          <AgentPanel onClose={() => setRightPanelOpen(false)} width={rightPanelWidth} />
        </>
      )}
    </div>
  );
}
