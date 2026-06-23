"use client";

import { ChevronDown, Pin, Ellipsis } from "lucide-react";
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
 * 尺寸铁律：gutter 20px = border(3) + padding(10) + chevron半宽(7)
 *   border-l 必须是 3px，严禁改动，否则竖线对不准箭头中心。
 *
 * 选中态：3px 左边线 accent 色（未选中透明）+ accent 背景
 * 已完结：字重 400 + 文字色淡化，无额外色条
 *
 * 右侧操作按钮：绝对定位覆盖，不影响行内布局
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

  return (
    <div>
      {/* ── Project row ── */}
      <div className="group/project relative">
        <button
          onClick={onProjectClick}
          className="w-full flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg text-left transition-colors border-l-[3px] border-transparent relative"
          style={{
            color: isCompleted ? "var(--th-text-3)" : "var(--th-text-2)",
            background: "transparent",
            borderRadius: 8,
          }}
        >
        
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

          {/* Pin */}
          <button
            className="p-1 rounded transition-all hover:bg-th-hover shrink-0"
            style={{ color: "var(--th-text-3)" }}
            title="置顶"
            onClick={(e) => e.stopPropagation()}
          >
            <Pin size={12} />
          </button>
          {/* More */}
          <button
            className="p-1 rounded transition-all hover:bg-th-hover shrink-0"
            style={{ color: "var(--th-text-3)" }}
            title="更多"
            onClick={(e) => e.stopPropagation()}
          >
            <Ellipsis size={13} />
          </button>
        </button>
      </div>

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
