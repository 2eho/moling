"use client";

import styles from "./PlotPromiseList.module.css";
import type { VaultPlotPromise } from "@/lib/types";

interface PlotPromiseListProps {
  promises: VaultPlotPromise[];
}

const promiseStatusColors: Record<string, string> = {
  pending: "var(--color-warning)",
  fulfilled: "var(--color-success)",
  broken: "var(--color-error)",
};

const promiseStatusLabels: Record<string, string> = {
  pending: "待兑现",
  fulfilled: "已兑现",
  broken: "已破裂",
};

export function PlotPromiseList({ promises }: PlotPromiseListProps) {
  if (promises.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyText}>暂无剧情承诺数据</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {promises.map((pp) => (
        <div key={pp.id} className={styles.item}>
          <div className={styles.header}>
            <span
              className={styles.status}
              style={{
                backgroundColor:
                  promiseStatusColors[pp.status] ?? "var(--color-text-disabled)",
              }}
            >
              {promiseStatusLabels[pp.status] ?? pp.status}
            </span>
            <span className={styles.chapter}>
              第{pp.introduced_at}章引入
            </span>
          </div>
          <p className={styles.description}>{pp.description}</p>
          {pp.resolved_at && (
            <span className={styles.resolved}>
              已解决于第{pp.resolved_at}章
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
