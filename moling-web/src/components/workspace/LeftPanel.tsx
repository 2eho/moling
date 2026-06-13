"use client";

import { useState } from "react";
import { VaultTabs } from "./VaultTabs";
import { CharacterList } from "./CharacterList";
import { TimelineList } from "./TimelineList";
import { PlotPromiseList } from "./PlotPromiseList";
import { WorldList } from "./WorldList";
import { useWorkspace } from "@/hooks/useWorkspace";
import styles from "./LeftPanel.module.css";

export type VaultTab = "characters" | "timeline" | "plot-promises" | "world";

export function LeftPanel() {
  const [activeTab, setActiveTab] = useState<VaultTab>("characters");
  const { vaultData } = useWorkspace();

  const renderContent = () => {
    if (!vaultData) {
      return <div className={styles.loading}>加载中…</div>;
    }

    switch (activeTab) {
      case "characters":
        return <CharacterList characters={vaultData.characters} />;
      case "timeline":
        return <TimelineList timelines={vaultData.timelines} />;
      case "plot-promises":
        return <PlotPromiseList promises={vaultData.plotPromises} />;
      case "world":
        return <WorldList worlds={vaultData.worlds} />;
      default:
        return null;
    }
  };

  return (
    <div className={styles.panel}>
      <VaultTabs activeTab={activeTab} onChange={setActiveTab} />
      <div className={styles.content}>{renderContent()}</div>
    </div>
  );
}
