"use client";

import styles from "./ChapterSelector.module.css";
import type { Chapter } from "@/lib/types";
import { Button } from "@/components/ui/Button";

interface ChapterSelectorProps {
  chapters: Chapter[];
  currentChapterId: string | undefined;
  onChange: (chapter: Chapter) => void;
  onAddChapter: () => void;
}

export function ChapterSelector({
  chapters,
  currentChapterId,
  onChange,
  onAddChapter,
}: ChapterSelectorProps) {
  return (
    <div className={styles.container}>
      <select
        className={styles.select}
        value={currentChapterId ?? ""}
        onChange={(e) => {
          const ch = chapters.find((c) => c.id === e.target.value);
          if (ch) onChange(ch);
        }}
      >
        {chapters.map((ch, idx) => (
          <option key={ch.id} value={ch.id}>
            第{idx + 1}章 {ch.title}
          </option>
        ))}
      </select>
      <Button variant="ghost" size="sm" onClick={onAddChapter}>
        + 新增章节
      </Button>
    </div>
  );
}
