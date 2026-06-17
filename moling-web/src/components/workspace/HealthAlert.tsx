"use client";

import { useState, useMemo } from "react";
import { useRouter, useParams } from "next/navigation";
import styles from "./HealthAlert.module.css";
import type { HealthAlert as HealthAlertType } from "@/lib/types";

interface HealthAlertProps {
  alert: HealthAlertType;
}

const severityColors: Record<string, { bg: string; border: string; dot: string }> = {
  info: {
    bg: "rgba(96, 165, 250, 0.1)",
    border: "rgba(96, 165, 250, 0.3)",
    dot: "var(--color-rarity-rare)",
  },
  warning: {
    bg: "rgba(245, 158, 11, 0.1)",
    border: "rgba(245, 158, 11, 0.3)",
    dot: "var(--color-warning)",
  },
  critical: {
    bg: "rgba(239, 68, 68, 0.1)",
    border: "rgba(239, 68, 68, 0.3)",
    dot: "var(--color-danger)",
  },
};

/**
 * Individual health alert item.
 */
export function HealthAlert({ alert }: HealthAlertProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const colors = severityColors[alert.severity] ?? severityColors.info;

  return (
    <div
      className={styles.alert}
      style={{ backgroundColor: colors.bg, borderColor: colors.border }}
    >
      <div className={styles.dot} style={{ backgroundColor: colors.dot }} />
      <div className={styles.content}>
        <div className={styles.header}>
          <span className={styles.title}>{alert.title}</span>
          <button
            className={styles.close}
            onClick={() => setDismissed(true)}
            aria-label="关闭告警"
          >
            ✕
          </button>
        </div>
        <p className={styles.detail}>{alert.detail}</p>
      </div>
    </div>
  );
}

interface HealthAlertBannerProps {
  alerts: HealthAlertType[];
  /** Maximum alerts visible before carousel wraps. Default 3. */
  maxVisible?: number;
}

/**
 * Enhanced health alert banner with:
 * - Alert count badge
 * - Clickable link to health dashboard
 * - Multi-alert carousel (max 3 visible)
 */
export function HealthAlertBanner({ alerts, maxVisible = 3 }: HealthAlertBannerProps) {
  const router = useRouter();
  const params = useParams();
  const projectId = params?.projectId as string | undefined;

  const [currentIndex, setCurrentIndex] = useState(0);

  // Show all if under threshold, otherwise carousel
  const hasCarousel = alerts.length > maxVisible;
  const visibleAlerts = useMemo(() => {
    if (!hasCarousel) return alerts;
    return alerts.slice(currentIndex, currentIndex + maxVisible);
  }, [alerts, currentIndex, maxVisible, hasCarousel]);

  // Count by severity
  const severityCounts = useMemo(() => {
    const c = { critical: 0, warning: 0, info: 0 };
    for (const a of alerts) {
      if (a.severity === "critical") c.critical++;
      else if (a.severity === "warning") c.warning++;
      else c.info++;
    }
    return c;
  }, [alerts]);

  if (alerts.length === 0) return null;

  const handleNav = () => {
    if (projectId) {
      router.push(`/workspace/${projectId}/health`);
    }
  };

  const cycleForward = () => {
    setCurrentIndex((prev) => (prev + 1) % alerts.length);
  };

  const cycleBackward = () => {
    setCurrentIndex((prev) => (prev - 1 + alerts.length) % alerts.length);
  };

  return (
    <div className={styles.banner}>
      {/* Header with badge and navigation */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "var(--space-2)",
        padding: "4px 0",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <span style={{ fontSize: "var(--font-size-xs)", color: "var(--color-text-secondary)", fontWeight: 600 }}>
            健康告警
          </span>
          {severityCounts.critical > 0 && (
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "0 6px",
              height: 18,
              borderRadius: 9,
              fontSize: 10,
              fontWeight: 700,
              background: severityColors.critical.bg,
              color: "var(--color-danger)",
              border: `1px solid ${severityColors.critical.border}`,
            }}>
              R1 {severityCounts.critical}
            </span>
          )}
          {severityCounts.warning > 0 && (
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "0 6px",
              height: 18,
              borderRadius: 9,
              fontSize: 10,
              fontWeight: 700,
              background: severityColors.warning.bg,
              color: "var(--color-warning)",
              border: `1px solid ${severityColors.warning.border}`,
            }}>
              R2 {severityCounts.warning}
            </span>
          )}
          {severityCounts.info > 0 && (
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "0 6px",
              height: 18,
              borderRadius: 9,
              fontSize: 10,
              fontWeight: 700,
              background: severityColors.info.bg,
              color: "var(--color-rarity-rare)",
              border: `1px solid ${severityColors.info.border}`,
            }}>
              R3 {severityCounts.info}
            </span>
          )}
        </div>
        {projectId && (
          <button
            onClick={handleNav}
            style={{
              fontSize: "var(--font-size-xs)",
              color: "var(--color-brand-indigo)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "2px 4px",
              fontWeight: 500,
              whiteSpace: "nowrap",
            }}
            title="查看完整仪表盘"
          >
            查看详情 →
          </button>
        )}
      </div>

      {/* Alert list / carousel */}
      {visibleAlerts.map((alert) => (
        <HealthAlert key={alert.id} alert={alert} />
      ))}

      {/* Carousel controls */}
      {hasCarousel && (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "var(--space-3)",
          paddingTop: "var(--space-1)",
        }}>
          <button
            onClick={cycleBackward}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-text-tertiary)",
              cursor: "pointer",
              fontSize: 11,
              padding: "2px 8px",
            }}
            aria-label="上一个"
          >
            ← 上一个
          </button>
          <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>
            {currentIndex + 1} / {alerts.length}
          </span>
          <button
            onClick={cycleForward}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-text-tertiary)",
              cursor: "pointer",
              fontSize: 11,
              padding: "2px 8px",
            }}
            aria-label="下一个"
          >
            下一个 →
          </button>
        </div>
      )}
    </div>
  );
}
