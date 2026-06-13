"use client";

import styles from "./VaultTabs.module.css";
import { VAULT_TABS } from "@/lib/constants";
import type { VaultTab } from "./LeftPanel";

interface VaultTabsProps {
  activeTab: VaultTab;
  onChange: (tab: VaultTab) => void;
}

export function VaultTabs({ activeTab, onChange }: VaultTabsProps) {
  return (
    <div className={styles.tabs}>
      {VAULT_TABS.map((tab) => (
        <button
          key={tab.id}
          className={`${styles.tab} ${activeTab === tab.id ? styles.active : ""}`}
          onClick={() => onChange(tab.id as VaultTab)}
        >
          <span className={styles.icon}>{tab.icon}</span>
          <span className={styles.label}>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}
