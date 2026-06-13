"use client";

import styles from "./ProjectStats.module.css";
import type { ProjectStats as Stats } from "@/contexts/ProjectContext";

interface ProjectStatsProps {
  stats: Stats | null;
  isLoading: boolean;
}

export function ProjectStats({ stats, isLoading }: ProjectStatsProps) {
  const items = [
    { label: "总项目", value: stats?.total ?? 0, icon: "📚" },
    { label: "活跃中", value: stats?.active ?? 0, icon: "✍" },
    { label: "草稿箱", value: stats?.draft ?? 0, icon: "📄" },
    { label: "总字数", value: stats ? formatWords(stats.total_words) : "0", icon: "📝" },
  ];

  return (
    <div className={styles.grid}>
      {items.map((item) => (
        <div key={item.label} className={styles.card}>
          <span className={styles.icon}>{item.icon}</span>
          <div className={styles.info}>
            <span className={styles.value}>
              {isLoading ? "—" : item.value}
            </span>
            <span className={styles.label}>{item.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatWords(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return `${count}`;
}
