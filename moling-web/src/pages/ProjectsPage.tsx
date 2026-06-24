import { BookOpen, ChevronRight, Clock, Plus, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useWritingStore } from "@/stores/useWritingStore";

const PHASE_CN: Record<string, string> = {
  ideation: "构思中",
  outline: "大纲阶段",
  character: "人设阶段",
  worldbuilding: "世界观",
  drafting: "写作中",
  revision: "修订中",
};

export function ProjectsPage() {
  const projects = useWritingStore((s) => s.projects);

  return (
    <div className="min-h-screen flex flex-col bg-th-bg text-th-text">
      {/* Header */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-6 py-4 backdrop-blur-xl bg-th-bg/80 border-b border-th-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)] shadow-[0_2px_12px_var(--th-accent-glow)]">
            <Sparkles size={17} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight">墨灵</span>
        </div>
        <Link
          to="/settings"
          className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-th-accent-dim text-th-accent-text hover:scale-105 transition-transform"
          aria-label="设置"
        >
          U
        </Link>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold mb-1">我的项目</h1>
            <p className="text-sm text-th-text-3">{projects.length} 个项目</p>
          </div>
          <Link
            to="/projects/new"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold bg-th-accent-dim text-th-accent-text hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
          >
            <Plus size={16} />
            新建项目
          </Link>
        </div>

        {/* 📭 Empty state */}
        {projects.length === 0 ? (
          <div className="text-center py-20">
            <BookOpen size={48} className="mx-auto mb-4 text-th-text-4/20" />
            <p className="text-sm mb-1 text-th-text-2">还没有项目</p>
            <p className="text-xs mb-4 text-th-text-3">创建你的第一本网文，开始用 AI 辅助创作</p>
            <Link
              to="/projects/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-th-accent-dim text-th-accent-text hover:scale-[1.02] transition-all"
            >
              <Plus size={16} />
              创建第一个项目
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <Link
                key={p.id}
                to={`/workspace/${p.id}`}
                className="glass-card p-5 flex items-center gap-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_24px_rgba(0,0,0,0.1)] group"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 bg-gradient-to-br from-[var(--th-logo-from)] to-[var(--th-logo-to)]">
                  <BookOpen size={20} className="text-white" />
                </div>

                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold mb-1 text-th-text truncate">{p.title}</h3>
                  <div className="flex items-center gap-2 text-xs text-th-text-3">
                    <span>{p.genre}</span>
                    <span className="text-th-text-4">·</span>
                    <span>{PHASE_CN[p.phase] ?? p.phase}</span>
                    <span className="text-th-text-4">·</span>
                    <span>
                      {p.currentChapter}/{p.totalChapters} 章
                    </span>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <p className="text-xs mb-1.5 flex items-center gap-1 text-th-text-4">
                    <Clock size={11} />
                    {p.updatedAt}
                  </p>
                  <ChevronRight
                    size={16}
                    className="ml-auto opacity-0 group-hover:opacity-100 text-th-text-3 transition-opacity duration-200"
                  />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
