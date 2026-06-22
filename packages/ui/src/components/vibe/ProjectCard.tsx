"use client";

import { ChevronDown } from "lucide-react";
import type { WritingProject } from "@/stores/useWritingStore";
import { ChapterItem } from "./ChapterItem";

interface ProjectCardProps {
  project: WritingProject;
  isActive: boolean;
  isExpanded: boolean;
  activeChapterId: number | null;
  onProjectClick: () => void;
  onChapterClick: (chapterId: number) => void;
}

/**
 * 项目卡片
 *
 * 连载中 vs 已完结：左边框色条 + 字重区分
 * 章节列表：CSS Grid [20px gutter + 1fr]
 *   gutter 列 center = 箭头中心，竖线天生对齐，无需像素计算
 *
 *   ▎▼ 剑道巅峰
 *    │
 *    ├── ③ 章节
 *    ├── ② 章节
 *    └── ① 章节
 */
export function ProjectCard({
  project,
  isActive,
  isExpanded,
  activeChapterId,
  onProjectClick,
  onChapterClick,
}: ProjectCardProps) {
  const isCompleted =
    project.chapters.length > 0 &&
    project.chapters.every((ch) => ch.status === "completed");

  const reversedChapters = [...project.chapters].reverse();

  const accentBorder = isCompleted
    ? "var(--th-border-subtle)"
    : "var(--th-accent-text)";

  return (
    <div>
      {/* ── Project row ── */}
      <button
        onClick={onProjectClick}
        className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-r-lg text-left transition-colors border-l-[3px]"
        style={{
          borderLeftColor: accentBorder,
          color: isActive
            ? "var(--th-accent-text)"
            : isCompleted
              ? "var(--th-text-3)"
              : "var(--th-text-2)",
          background: isActive ? "var(--th-accent-dim)" : "transparent",
        }}
      >
        {/* Chevron — left 7px to align with tree-line center */}
        <span
          className="shrink-0 transition-transform duration-200"
          style={{ transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)", marginLeft: -6 }}
        >
          <ChevronDown size={14} />
        </span>

        {/* Title */}
        <span
          className="flex-1 truncate text-[14px] leading-snug"
          style={{ fontWeight: isCompleted ? 400 : 600 }}
        >
          {project.title}
        </span>

      </button>

      {/* ── Chapters in Grid ──
          gutter 20px = border(3) + padding(10) + chevron半宽(7)
          竖线在 gutter 列 center → 天生对齐箭头中心 */}
      {isExpanded && project.chapters.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "20px 1fr",
          }}
        >
          {reversedChapters.map((ch, idx) => {
            const isCurrent = ch.id === activeChapterId && isActive;
            const isTreeEnd = idx === reversedChapters.length - 1;
            const isDisabled = !isActive;
            const lineColor = isCurrent
              ? "var(--th-accent-text)"
              : "var(--th-border)";

            return (
              <div key={ch.id} style={{ display: "contents" }}>
                {/* Col 1: gutter — tree guide line, center = arrow center */}
                <div style={{ position: "relative" }}>
                  {/* 竖线 */}
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      marginLeft: -0.75,
                      top: 0,
                      bottom: isTreeEnd ? "50%" : 0,
                      width: 1.5,
                      background: lineColor,
                    }}
                  />
                  {/* 横线 — from center to right edge, connects to dot in col 2 */}
                  <div
                    style={{
                      position: "absolute",
                      top: "50%",
                      left: "50%",
                      right: 0,
                      height: 1.5,
                      background: lineColor,
                    }}
                  />
                </div>

                {/* Col 2: chapter entry */}
                <ChapterItem
                  chapter={ch}
                  isActive={isCurrent}
                  isDisabled={isDisabled}
                  onClick={() => onChapterClick(ch.id)}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
