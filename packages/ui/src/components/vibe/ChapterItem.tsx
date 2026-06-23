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

  return (
    <button
      disabled={isDisabled}
      onClick={onClick}
      className="w-full flex items-center text-left rounded-lg transition-colors disabled:cursor-not-allowed border-l-[3px] border-transparent relative"
      style={{
        color: isActive
          ? "var(--th-accent-text)"
          : isCompleted
            ? "var(--th-text-2)"
            : "var(--th-text-2)",
        background: isActive ? "var(--th-accent-dim)" : "transparent",
        opacity: isDisabled ? 0.7 : 1,
        borderRadius: 8,
      }}
    >
      {/* Active pill */}
      {isActive && (
        <div
          className="absolute left-0.5 top-1.5 bottom-1.5 w-[5px] z-10"
          style={{ background: "var(--th-accent-text)", borderRadius: 9999 }}
        />
      )}
      {/* 5px spacer */}
      <span className="inline-block w-[5px] shrink-0 overflow-hidden">&nbsp;</span>
      {/* 标题 — 左对齐，主信息 */}
      <span className="truncate text-[13px] py-2.5 md:py-2 leading-snug">
        {chapter.title}
      </span>

      {/* 编号 — 右对齐，样式与标题同步 */}
      <span
        className="text-[13px] py-2.5 md:py-2 leading-snug shrink-0 font-semibold ml-auto"
      >
        {chapter.id}
      </span>
      {/* 右侧间距 */}
      <span className="inline-block w-[5px] shrink-0 overflow-hidden">&nbsp;</span>
    </button>
  );
}
