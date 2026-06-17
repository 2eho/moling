"use client";

import { memo } from "react";
import styles from "./ProjectCard.module.css";
import type { Project } from "@/lib/types";
import { PROJECT_STATUS_LABELS } from "@/lib/constants";

interface ProjectCardProps {
  project: Project;
  onClick: () => void;
}

function formatWordCount(count: number): string {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return `${count}`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const day = 86400000;
  if (diff < day) return "今天";
  if (diff < 2 * day) return "昨天";
  if (diff < 7 * day) return `${Math.floor(diff / day)}天前`;
  return date.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

const statusColors: Record<string, string> = {
  draft: "var(--color-text-disabled)",
  active: "var(--color-success)",
  completed: "var(--color-brand-primary)",
  archived: "var(--color-warning)",
};

function getCoverType(genre: string): number {
  const g = genre;
  if (g.includes("玄幻")) return 1;
  if (g.includes("都市")) return 2;
  if (g.includes("古代")) return 3;
  if (g.includes("科幻")) return 4;
  if (g.includes("历史")) return 5;
  return 6; // 灵异作为默认/兜底
}

export const ProjectCard = memo(function ProjectCard({ project, onClick }: ProjectCardProps) {
  const coverType = getCoverType(project.genre);
  return (
    <div className={styles.card} onClick={onClick}>
      {/* 封面视觉 */}
      <div className={`${styles.cover} ${styles[`coverType${coverType}`]}`}>
        <span className={styles.coverGenre}>{project.genre}</span>
        <span className={styles.coverPattern} aria-hidden="true" />
      </div>

      <div className={styles.cardContent}>
        <div className={styles.header}>
          <h3 className={styles.title}>{project.title}</h3>
          <span
            className={styles.status}
            style={{ backgroundColor: statusColors[project.status] ?? "var(--color-text-disabled)" }}
          >
            {PROJECT_STATUS_LABELS[project.status] ?? project.status}
          </span>
        </div>

        <div className={styles.meta}>
          <span className={styles.author}>{project.author}</span>
          <span className={styles.separator}>·</span>
          <span className={styles.genre}>{project.genre}</span>
        </div>

        <p className={styles.synopsis}>{project.synopsis}</p>

        <div className={styles.stats}>
          <span className={styles.statItem}>
            <span className={styles.statIcon}>📝</span>
            {formatWordCount(project.word_count)}字
          </span>
          <span className={styles.statItem}>
            <span className={styles.statIcon}>🕐</span>
            {formatDate(project.updated_at)}
          </span>
        </div>
      </div>
    </div>
  );
});
