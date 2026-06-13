"use client";

import { useState } from "react";
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
    dot: "var(--color-error)",
  },
};

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
          >
            ✕
          </button>
        </div>
        <p className={styles.detail}>{alert.detail}</p>
      </div>
    </div>
  );
}

export function HealthAlertBanner({ alerts }: { alerts: HealthAlertType[] }) {
  if (alerts.length === 0) return null;

  return (
    <div className={styles.banner}>
      {alerts.map((alert) => (
        <HealthAlert key={alert.id} alert={alert} />
      ))}
    </div>
  );
}
