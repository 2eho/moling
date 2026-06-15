"use client";

import { useState, useEffect } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { chapterAgentApi } from "@/lib/api";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { ChapterSuggestion } from "@/lib/api";
import styles from "./RightPanel.module.css";

export function RightPanel() {
  const { currentChapter } = useWorkspace();
  const [suggestions, setSuggestions] = useState<ChapterSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!currentChapter?.id) {
      setSuggestions([]);
      return;
    }
    const loadSuggestions = async () => {
      setIsLoading(true);
      try {
        const res = await chapterAgentApi.getSuggestions(
          currentChapter.project_id,
          currentChapter.id,
        );
        setSuggestions(res.data.suggestions ?? []);
      } catch {
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    };
    loadSuggestions();
  }, [currentChapter?.id, currentChapter?.project_id]); // ✅ 使用原始值而非对象引用，避免内容编辑时重复请求

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h4 className={styles.title}>AI 建议</h4>
      </div>
      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <Spinner size="sm" />
            <span>加载中…</span>
          </div>
        ) : suggestions.length > 0 ? (
          <ul className={styles.suggestionList}>
            {suggestions.map((s) => (
              <li key={s.id} className={styles.suggestionCard}>
                <div className={styles.suggestionType}>{s.type}</div>
                <div className={styles.suggestionTitle}>{s.title}</div>
                <div className={styles.suggestionDesc}>{s.description}</div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon="💡"
            title="暂无 AI 建议"
            description="AI 建议将在您创作过程中自动生成，帮助您拓展思路"
          />
        )}
      </div>
    </div>
  );
}
