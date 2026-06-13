"use client";

import { useWorkspace } from "@/hooks/useWorkspace";
import styles from "./Editor.module.css";

export function Editor() {
  const { currentChapter, updateChapterContent } = useWorkspace();

  if (!currentChapter) {
    return (
      <div className={styles.empty}>
        <span className={styles.emptyIcon}>📝</span>
        <p className={styles.emptyText}>选择章节开始写作</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <textarea
        className={styles.textarea}
        value={currentChapter.content}
        onChange={(e) => updateChapterContent(e.target.value)}
        placeholder="在此开始创作..."
        spellCheck={false}
      />
      <div className={styles.wordCount}>
        {currentChapter.word_count} 字
      </div>
    </div>
  );
}
