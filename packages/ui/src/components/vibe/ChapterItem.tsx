"use client";

import type { Chapter } from "@/stores/useWritingStore";

interface ChapterItemProps {
  chapter: Chapter;
  isActive: boolean;
  isDisabled: boolean;
  onClick: () => void;
}

/**
 * 章节入口 — 圆点编号 + 标题。
 * 树形引导线由父级 Grid 的 gutter 列统一管理，不再内部绘制。
 */
export function ChapterItem({
  chapter,
  isActive,
  isDisabled,
  onClick,
}: ChapterItemProps) {
  const isCompleted = chapter.status === "completed";

  const dotBg = isCompleted
    ? "var(--th-accent-dim)"
    : isActive
      ? "var(--th-accent-text)"
      : "var(--th-hover)";
  const dotColor = isCompleted
    ? "var(--th-accent-text)"
    : isActive
      ? "#fff"
      : "var(--th-text-3)";

  return (
    <button
      disabled={isDisabled}
      onClick={onClick}
      className="w-full flex items-center text-left rounded-r-lg transition-colors disabled:cursor-not-allowed"
      style={{
        color: isActive
          ? "var(--th-accent-text)"
          : isCompleted
            ? "var(--th-text-2)"
            : "var(--th-text-2)",
        background: isActive ? "var(--th-accent-dim)" : "transparent",
        opacity: isDisabled ? 0.7 : 1,
      }}
    >
      {/* 标题 — 左对齐，主信息 */}
      <span className="truncate text-[13px] py-2.5 md:py-2 leading-snug">
        {chapter.title}
      </span>

      {/* 圆点 — 右对齐，编号为辅助信息 */}
      <span
        className="chapter-badge w-[18px] h-[18px] rounded-full text-[10px] flex items-center justify-center shrink-0 font-semibold leading-none ml-auto"
        style={{ background: dotBg, color: dotColor }}
      >
        {chapter.id}
      </span>
    </button>
  );
}
