import { memo } from "react";
import styles from "./Skeleton.module.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  variant?: "text" | "circular" | "rectangular";
}

export const Skeleton = memo(function Skeleton({
  width = "100%",
  height = 16,
  borderRadius,
  variant = "text",
}: SkeletonProps) {
  const resolvedBorderRadius =
    borderRadius ??
    (variant === "circular" ? "50%" : variant === "text" ? "4px" : "8px");

  return (
    <div
      className={`${styles.skeleton} ${styles[variant]}`}
      style={{
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
        borderRadius: typeof resolvedBorderRadius === "number"
          ? `${resolvedBorderRadius}px`
          : resolvedBorderRadius,
      }}
      aria-hidden="true"
    />
  );
});
