"use client";

import { useParams } from "next/navigation";
import { useState, useCallback } from "react";
import { VaultTabs } from "@/components/workspace/VaultTabs";
import { CharacterLibrary } from "@/components/phase4/CharacterLibrary";
import { TimelineLibrary } from "@/components/phase4/TimelineLibrary";
import { ForeshadowingLibrary } from "@/components/phase4/ForeshadowingLibrary";
import { WorldviewLibrary } from "@/components/phase4/WorldviewLibrary";
import { CardManager } from "@/components/phase4/CardManager";
import { useWorkspace } from "@/hooks/useWorkspace";
import { VAULT_TABS } from "@/lib/constants";
import type { VaultTab } from "@/components/workspace/LeftPanel";
import styles from "./page.module.css";

type Phase4Tab = VaultTab | "cards";

const PHASE4_TABS: Array<{ id: Phase4Tab; label: string; icon: string }> = [
  ...VAULT_TABS,
  { id: "cards", label: "卡牌管理", icon: "🃏" },
];

export default function Phase4Page() {
  const params = useParams();
  const projectId = params.projectId as string;
  const [activeTab, setActiveTab] = useState<Phase4Tab>("characters");
  const { currentChapter } = useWorkspace();

  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab as Phase4Tab);
  }, []);

  return (
    <div className={styles.page}>
      {/* 页面标题 */}
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>四库管理</h1>
        <p className={styles.pageDescription}>
          管理小说中的角色、时间线、伏笔、世界观和卡牌
        </p>
      </div>

      {/* 标签页导航 */}
      <div className={styles.tabsWrapper}>
        <div className={styles.tabs}>
          {PHASE4_TABS.map((tab) => (
            <button
              key={tab.id}
              className={`${styles.tab} ${activeTab === tab.id ? styles.active : ""}`}
              onClick={() => handleTabChange(tab.id)}
            >
              <span className={styles.tabIcon}>{tab.icon}</span>
              <span className={styles.tabLabel}>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 内容区域 */}
      <div className={styles.content}>
        {activeTab === "characters" && (
          <CharacterLibrary projectId={projectId} />
        )}
        {activeTab === "timeline" && (
          <TimelineLibrary projectId={projectId} />
        )}
        {activeTab === "plot-promises" && (
          <ForeshadowingLibrary projectId={projectId} />
        )}
        {activeTab === "world" && (
          <WorldviewLibrary projectId={projectId} />
        )}
        {activeTab === "cards" && (
          <CardManager
            projectId={projectId}
            chapterId={currentChapter?.id}
          />
        )}
      </div>
    </div>
  );
}
