"use client";

import styles from "./WorldList.module.css";
import type { VaultWorld } from "@/lib/types";

interface WorldListProps {
  worlds: VaultWorld[];
}

export function WorldList({ worlds }: WorldListProps) {
  if (worlds.length === 0) {
    return (
      <div className={styles.empty}>
        <p className={styles.emptyText}>暂无世界观数据</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {worlds.map((w) => (
        <div key={w.id} className={styles.item}>
          <div className={styles.header}>
            <h5 className={styles.name}>{w.name}</h5>
            <span className={styles.category}>{w.category}</span>
          </div>
          <p className={styles.desc}>{w.description}</p>

          {w.rules.length > 0 && (
            <div className={styles.section}>
              <span className={styles.sectionLabel}>规则</span>
              <ul className={styles.ruleList}>
                {w.rules.map((rule, idx) => (
                  <li key={`${rule}-${idx}`} className={styles.rule}>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {w.factions.length > 0 && (
            <div className={styles.section}>
              <span className={styles.sectionLabel}>势力</span>
              {w.factions.map((f, idx) => (
                <div key={f.name || `faction-${idx}`} className={styles.faction}>
                  <div className={styles.factionHeader}>
                    <span className={styles.factionName}>{f.name}</span>
                    <span className={styles.factionInfluence}>
                      影响力: {f.influence}
                    </span>
                  </div>
                  <p className={styles.factionDesc}>{f.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
