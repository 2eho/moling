import { Skeleton } from "@/components/ui/Skeleton";
import styles from "./workspace.module.css";

export default function WorkspaceLoading() {
  return (
    <div className={styles.page}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "var(--spacing-3) var(--spacing-4)",
          gap: "var(--spacing-4)",
          backgroundColor: "var(--color-bg-card)",
          borderBottom: "1px solid var(--color-border-default)",
          flexShrink: 0,
        }}
      >
        <Skeleton width={120} height={24} />
        <Skeleton width={180} height={32} borderRadius={8} />
      </div>

      <div
        style={{
          flex: 1,
          display: "flex",
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {/* Left Panel Skeleton */}
        <div
          style={{
            width: 240,
            flexShrink: 0,
            backgroundColor: "var(--color-bg-card)",
            borderRight: "1px solid var(--color-border-default)",
            padding: "var(--spacing-3)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--spacing-2)",
          }}
        >
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} height={36} borderRadius={8} />
          ))}
        </div>

        {/* Center Skeleton */}
        <div
          style={{
            flex: 1,
            padding: "var(--spacing-8)",
          }}
        >
          <Skeleton height="100%" borderRadius={8} />
        </div>

        {/* Right Panel Skeleton */}
        <div
          style={{
            width: 280,
            flexShrink: 0,
            backgroundColor: "var(--color-bg-card)",
            borderLeft: "1px solid var(--color-border-default)",
            padding: "var(--spacing-4)",
          }}
        >
          <Skeleton height={24} width={80} borderRadius={4} />
          <div style={{ marginTop: "var(--spacing-8)" }}>
            <Skeleton height={120} borderRadius={8} />
          </div>
        </div>
      </div>
    </div>
  );
}
