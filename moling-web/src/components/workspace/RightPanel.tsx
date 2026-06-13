"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import styles from "./RightPanel.module.css";

export function RightPanel() {
  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h4 className={styles.title}>AI 建议</h4>
      </div>
      <div className={styles.content}>
        <EmptyState
          icon="💡"
          title="暂无 AI 建议"
          description="AI 建议将在您创作过程中自动生成，帮助您拓展思路"
        />
      </div>
    </div>
  );
}
