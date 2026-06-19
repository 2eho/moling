"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useWritingStore } from "@/stores/useWritingStore";
import { useTheme, THEMES } from "@/stores/useTheme";
import type { ThemeId } from "@/stores/useTheme";
import { Sidebar } from "@/components/vibe/Sidebar";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";
import {
  PanelRight,
  X,
} from "lucide-react";

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
      { id: 1, title: "废材少年", summary: "...", content: "", status: "completed" as const },
      { id: 2, title: "剑骨觉醒", summary: "...", content: "", status: "completed" as const },
      { id: 3, title: "剑指苍穹", summary: "...", content: "", status: "draft" as const },
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
];

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const router = useRouter();

  const project = useWritingStore((s) => s.project);
  const projects = useWritingStore((s) => s.projects);
  const loadProjects = useWritingStore((s) => s.loadProjects);
  const setActiveProject = useWritingStore((s) => s.setActiveProject);
  const { theme, setTheme } = useTheme();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  /** 加载多书 Mock */
  useEffect(() => {
    if (projects.length === 0) {
      loadProjects(MOCK_PROJECTS);
    }
    // 切换到 URL 中的 projectId
    if (projectId && project?.id !== projectId) {
      setActiveProject(projectId);
    }
  }, [loadProjects, setActiveProject, projectId, project?.id, projects.length]);

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
      />

      {/* ================================================================
          Main Stage
          ================================================================ */}
      <main className="flex-1 flex flex-col min-w-0 relative overflow-hidden">
        {/* Top bar — minimal */}
        <div className="shrink-0 flex items-center justify-end gap-2 px-4 py-3">
          <div className="flex-1" />
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

        {/* Center stage — reserved area (no white empty state) */}
        <div className="flex-1" />

        {/* Bottom status bar */}
        <div
          className="shrink-0 flex items-center justify-between px-4 py-1.5 text-[10px] border-t"
          style={{
            borderColor: "var(--th-border-subtle)",
            color: "var(--th-text-4)",
          }}
        >
          <span>
            {project.title} · 第 {project.currentChapter} 章 / {project.totalChapters} 章
          </span>
          <span>{project.genre}</span>
        </div>
      </main>

      {/* ================================================================
          Right Panel — collapsible
          ================================================================ */}
      {rightPanelOpen && (
        <aside
          className="shrink-0 h-full border-l flex flex-col transition-all duration-300"
          style={{
            width: 260,
            borderColor: "var(--th-border-subtle)",
            background: "var(--th-card)",
          }}
        >
          <div
            className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: "var(--th-border-subtle)" }}
          >
            <span className="text-xs font-semibold" style={{ color: "var(--th-text-2)" }}>
              项目信息
            </span>
            <button
              onClick={() => setRightPanelOpen(false)}
              className="p-1 rounded transition-colors hover:opacity-80"
              style={{ color: "var(--th-text-3)" }}
              aria-label="关闭右栏"
            >
              <X size={14} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <dl className="space-y-3 text-xs">
              <div>
                <dt style={{ color: "var(--th-text-4)" }} className="mb-1">
                  类型
                </dt>
                <dd style={{ color: "var(--th-text-2)" }}>{project.genre}</dd>
              </div>
              <div>
                <dt style={{ color: "var(--th-text-4)" }} className="mb-1">
                  进度
                </dt>
                <dd style={{ color: "var(--th-text-2)" }}>
                  第 {project.currentChapter} / {project.totalChapters} 章
                </dd>
              </div>
              <div>
                <dt style={{ color: "var(--th-text-4)" }} className="mb-1">
                  简介
                </dt>
                <dd style={{ color: "var(--th-text-2)" }}>{project.summary}</dd>
              </div>
            </dl>
          </div>
        </aside>
      )}
    </div>
  );
}
