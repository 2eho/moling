"use client";

import { memo } from "react";
import styles from "./Spinner.module.css";

interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  color?: string;
}

export const Spinner = memo(function Spinner({ size = "md", color }: SpinnerProps) {
  const sizeMap = { sm: 16, md: 24, lg: 36 };
  const px = sizeMap[size];

  return (
    <span
      className={`${styles.spinner} ${styles[size]}`}
      style={{
        width: px,
        height: px,
        borderColor: color ? `${color}33` : undefined,
        borderTopColor: color ?? undefined,
      }}
      aria-hidden="true"
    />
  );
});
