"use client";

import styles from "./GenerationProgress.module.css";
import { GENERATION_STAGES } from "@/lib/constants";

interface GenerationProgressProps {
  percent: number;
  stage?: string;
}

export function GenerationProgress({
  percent,
  stage,
}: GenerationProgressProps) {
  const displayStage =
    stage ??
    (percent < 100
      ? GENERATION_STAGES[Math.min(Math.floor(percent / 35), 2)]
      : "完成");

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.stage}>{displayStage}</span>
        <span className={styles.percent}>{Math.round(percent)}%</span>
      </div>
      <div className={styles.track}>
        <div
          className={`${styles.fill} ${percent >= 100 ? styles.complete : ""}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className={styles.stages}>
        {GENERATION_STAGES.map((s, i) => (
          <span
            key={s}
            className={`${styles.stageDot} ${
              percent >= (i + 1) * 35 ? styles.done : ""
            } ${s === displayStage ? styles.current : ""}`}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
