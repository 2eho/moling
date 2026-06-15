import { Skeleton } from "@/components/ui/Skeleton";
import styles from "./workspace.module.css";

export default function WorkspaceLoading() {
  return (
    <div className={styles.page}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "var(--space-3) var(--space-4)",
          gap: "var(--space-4)",
          background: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border-subtle)",
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
        <div
          style={{
            width: 280,
            flexShrink: 0,
            background: "var(--color-surface)",
            borderRight: "1px solid var(--color-border)",
            padding: "var(--space-3)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
          }}
        >
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} height={36} borderRadius={8} />
          ))}
        </div>

        <div
          style={{
            flex: 1,
            padding: "var(--space-8)",
            contain: "layout style",
          }}
        >
          <Skeleton height="100%" borderRadius={8} />
        </div>

        <div
          style={{
            width: 280,
            flexShrink: 0,
            background: "var(--color-surface)",
            borderLeft: "1px solid var(--color-border)",
            padding: "var(--space-4)",
            contain: "layout style",
          }}
        >
          <Skeleton height={24} width={80} borderRadius={4} />
          <div style={{ marginTop: "var(--space-8)" }}>
            <Skeleton height={120} borderRadius={8} />
          </div>
        </div>
      </div>
    </div>
  );
}
