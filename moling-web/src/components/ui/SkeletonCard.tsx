"use client";

import { memo } from "react";
import styles from "./SkeletonCard.module.css";

interface SkeletonCardProps {
  lines?: number;
  width?: string;
}

export const SkeletonCard = memo(function SkeletonCard({
  lines = 3,
  width,
}: SkeletonCardProps) {
  return (
    <div className={styles.skeleton} style={width ? { width } : undefined}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className={styles.skeletonLine} />
      ))}
    </div>
  );
});
