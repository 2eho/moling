"use client";

import { useState, useEffect } from "react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { chapterAgentApi } from "@/lib/api";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { ChapterSuggestion } from "@/lib/api";
import styles from "./RightPanel.module.css";

export type RightPanelTab = "ai-suggestions" | "card-draw" | "generation-history";

export function RightPanel() {
  const { currentChapter, cards, generationTask } = useWorkspace();
  const [activeTab, setActiveTab] = useState<RightPanelTab>("ai-suggestions");
  const [suggestions, setSuggestions] = useState<ChapterSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!currentChapter?.id || activeTab !== "ai-suggestions") {
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
  }, [currentChapter?.id, currentChapter?.project_id, activeTab]);

  const renderContent = () => {
    switch (activeTab) {
      case "ai-suggestions":
        return (
          <div className={styles.tabContent}>
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
        );
      case "card-draw":
        return (
          <div className={styles.tabContent}>
            {cards && cards.length > 0 ? (
              <div className={styles.cardList}>
                <h5 className={styles.tabSectionTitle}>当前卡牌</h5>
                <ul className={styles.cardItems}>
                  {cards.map((card) => (
                    <li key={card.id} className={styles.cardItem}>
                      <span className={styles.cardName}>{card.name}</span>
                      <span className={styles.cardRarity}>{card.rarity}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <EmptyState
                icon="🎴"
                title="暂无卡牌"
                description="点击底部工具栏的「抽卡」按钮来抽取灵感卡牌"
              />
            )}
          </div>
        );
      case "generation-history":
        return (
          <div className={styles.tabContent}>
            {generationTask ? (
              <div className={styles.historyList}>
                <h5 className={styles.tabSectionTitle}>当前生成任务</h5>
                <div className={styles.historyItem}>
                  <div className={styles.historyStage}>{generationTask.progress_stage}</div>
                  <div className={styles.historyProgress}>
                    {generationTask.progress_percent}%
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                icon="📜"
                title="暂无生成历史"
                description="生成历史将在此处显示"
              />
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className={styles.panel}>
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "ai-suggestions" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("ai-suggestions")}
          title="AI 建议"
        >
          <span className={styles.tabIcon}>💡</span>
          <span className={styles.tabLabel}>AI 建议</span>
        </button>
        <button
          className={`${styles.tab} ${activeTab === "card-draw" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("card-draw")}
          title="抽卡"
        >
          <span className={styles.tabIcon}>🎴</span>
          <span className={styles.tabLabel}>抽卡</span>
        </button>
        <button
          className={`${styles.tab} ${activeTab === "generation-history" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("generation-history")}
          title="生成历史"
        >
          <span className={styles.tabIcon}>📜</span>
          <span className={styles.tabLabel}>历史</span>
        </button>
      </div>
      {renderContent()}
    </div>
  );
}
