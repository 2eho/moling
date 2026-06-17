"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { chapterAgentApi } from "@/lib/api";
import { useWorkspace } from "@/hooks/useWorkspace";
import type { ChapterSuggestion } from "@/lib/api";
import styles from "./RightPanel.module.css";

export type RightPanelTab = "chapters" | "ai-suggestions" | "card-draw" | "generation-history";

export function RightPanel() {
  const { currentChapter, chapters, cards, generationTask, createChapter, setCurrentChapter, loadChapters } = useWorkspace();
  const [activeTab, setActiveTab] = useState<RightPanelTab>("chapters");
  const [suggestions, setSuggestions] = useState<ChapterSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!currentChapter?.project_id) return;
    loadChapters(currentChapter.project_id);
  }, [currentChapter?.project_id, loadChapters]);

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

  const handleAddChapter = async () => {
    try {
      await createChapter();
      if (currentChapter?.project_id) {
        loadChapters(currentChapter.project_id);
      }
    } catch (error) {
      console.error("创建章节失败:", error);
    }
  };

  const handleSelectChapter = (chapter: any) => {
    setCurrentChapter(chapter);
  };

  const renderContent = () => {
    switch (activeTab) {
      case "chapters":
        return (
          <div className={styles.tabContent}>
            <div className={styles.chapterHeader}>
              <h5 className={styles.tabSectionTitle}>章节列表</h5>
              <button className={styles.addChapterBtn} onClick={handleAddChapter} title="新增章节">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
                <span>新增</span>
              </button>
            </div>
            {chapters && chapters.length > 0 ? (
              <ul className={styles.chapterList}>
                {chapters.map((ch) => (
                  <li
                    key={ch.id}
                    className={`${styles.chapterItem} ${currentChapter?.id === ch.id ? styles.chapterItemActive : ""}`}
                    onClick={() => handleSelectChapter(ch)}
                  >
                    <span className={styles.chapterNum}>#{ch.chapter_number}</span>
                    <span className={styles.chapterTitle}>{ch.title}</span>
                    {ch.word_count > 0 && (
                      <span className={styles.chapterWords}>{ch.word_count}字</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <div className={styles.emptyChapter}>
                <p>暂无章节</p>
                <p className={styles.emptyHint}>点击"新增"创建第一个章节</p>
              </div>
            )}
          </div>
        );
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
          className={`${styles.tab} ${activeTab === "chapters" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("chapters")}
          title="章节"
        >
          <span className={styles.tabIcon}>📄</span>
          <span className={styles.tabLabel}>章节</span>
        </button>
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
