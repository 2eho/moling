"use client";

import { useState } from "react";
import Link from "next/link";
import { Sparkles, Plus, BookOpen, Clock, ChevronRight } from "lucide-react";

/** Mock 项目列表 */
const MOCK_PROJECTS = [
  {
    id: "novel-001",
    title: "剑道巅峰",
    genre: "玄幻修仙",
    phase: "drafting",
    chapter: 3,
    totalChapters: 12,
    updatedAt: "2 小时前",
  },
  {
    id: "novel-002",
    title: "末世重生",
    genre: "科幻末世",
    phase: "outline",
    chapter: 0,
    totalChapters: 20,
    updatedAt: "昨天",
  },
];

const PHASE_CN: Record<string, string> = {
  ideation: "构思中",
  outline: "大纲阶段",
  character: "人设阶段",
  worldbuilding: "世界观",
  drafting: "写作中",
  revision: "修订中",
};

export default function ProjectsPage() {
  const [projects] = useState(MOCK_PROJECTS);

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
              boxShadow: "0 2px 12px var(--th-accent-glow)",
            }}
          >
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="text-base font-bold">墨灵</span>
        </div>
        <Link
          href="/settings"
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          U
        </Link>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        {/* Title */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold mb-1">我的项目</h1>
            <p className="text-sm" style={{ color: "var(--th-text-3)" }}>
              {projects.length} 个项目
            </p>
          </div>
          <Link
            href="/projects/new"
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 hover:scale-105 active:scale-95"
            style={{
              background: "var(--th-accent-dim)",
              color: "var(--th-accent-text)",
            }}
          >
            <Plus size={16} />
            新建项目
          </Link>
        </div>

        {/* Project cards */}
        {projects.length === 0 ? (
          <div className="text-center py-20">
            <BookOpen size={48} className="mx-auto mb-4 opacity-10" />
            <p className="text-sm mb-3" style={{ color: "var(--th-text-3)" }}>
              还没有项目
            </p>
            <Link
              href="/projects/new"
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-medium"
              style={{
                background: "var(--th-accent-dim)",
                color: "var(--th-accent-text)",
              }}
            >
              <Plus size={16} />
              创建第一个项目
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {projects.map((p) => (
              <Link
                key={p.id}
                href={`/workspace/${p.id}`}
                className="glass-card p-5 flex items-center gap-4 transition-all duration-200 hover:translate-y-[-2px] group"
              >
                {/* Icon */}
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                  style={{
                    background: "linear-gradient(135deg, var(--th-logo-from), var(--th-logo-to))",
                  }}
                >
                  <BookOpen size={20} className="text-white" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold mb-0.5">{p.title}</h3>
                  <div className="flex items-center gap-2 text-xs" style={{ color: "var(--th-text-3)" }}>
                    <span>{p.genre}</span>
                    <span>·</span>
                    <span>{PHASE_CN[p.phase] ?? p.phase}</span>
                    <span>·</span>
                    <span>{p.chapter}/{p.totalChapters} 章</span>
                  </div>
                </div>

                {/* Meta */}
                <div className="text-right shrink-0">
                  <p className="text-xs mb-1 flex items-center gap-1" style={{ color: "var(--th-text-4)" }}>
                    <Clock size={11} />
                    {p.updatedAt}
                  </p>
                  <ChevronRight
                    size={16}
                    className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "var(--th-text-3)" }}
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
