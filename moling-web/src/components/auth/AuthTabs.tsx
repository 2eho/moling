"use client";

import styles from "./AuthTabs.module.css";
import { AUTH_PAGE_TABS } from "@/lib/constants";

interface AuthTabsProps {
  activeTab: string;
  onChange: (tabId: string) => void;
}

export function AuthTabs({ activeTab, onChange }: AuthTabsProps) {
  return (
    <div className={styles.tabs}>
      {AUTH_PAGE_TABS.map((tab) => (
        <button
          key={tab.id}
          className={`${styles.tab} ${activeTab === tab.id ? styles.active : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {activeTab === tab.id && <span className={styles.indicator} />}
        </button>
      ))}
    </div>
  );
}
