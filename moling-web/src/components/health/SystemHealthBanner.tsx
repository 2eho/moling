"use client";

import { memo, useState, useEffect, useRef, useMemo } from "react";import { useSystemHealth } from "@/contexts/SystemHealthContext";
import styles from "./SystemHealthBanner.module.css";

/**
 * 系统健康监控横幅组件
 *
 * 显示系统健康状态的三级横幅提示：
 * - R1（严重/红色）：系统故障，不可消除，需手动关闭
 * - R2（警告/黄色）：功能受限，可点击关闭
 * - R3（信息/蓝色）：系统正常，3秒后自动消失
 */
export const SystemHealthBanner = memo(function SystemHealthBanner() {
  const { health, isLoading, error, dismissWarning, warningDismissed } =
    useSystemHealth();

  const [exiting, setExiting] = useState(false);
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const autoDismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const r3AutoHideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Handle visibility and auto-dismiss based on health level
  useEffect(() => {
    if (!health || isLoading) return;

    // R3 auto-dismiss after 3 seconds
    if (health.level === "R3") {
      setVisible(true);
      setExiting(false);

      if (r3AutoHideTimer.current) clearTimeout(r3AutoHideTimer.current);
      r3AutoHideTimer.current = setTimeout(() => {
        setExiting(true);
        // Remove from DOM after animation completes
        setTimeout(() => setVisible(false), 500);
      }, 3000);

      return () => {
        if (r3AutoHideTimer.current) clearTimeout(r3AutoHideTimer.current);
      };
    }

    // R2: respect manual dismissal
    if (health.level === "R2" && warningDismissed) {
      setExiting(true);
      const timer = setTimeout(() => setVisible(false), 500);
      return () => clearTimeout(timer);
    }

    // R1: always visible
    if (health.level === "R1") {
      setVisible(true);
      setExiting(false);
    }

    // R2 not dismissed
    if (health.level === "R2" && !warningDismissed) {
      setVisible(true);
      setExiting(false);
    }
  }, [health, isLoading, warningDismissed]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (r3AutoHideTimer.current) clearTimeout(r3AutoHideTimer.current);
      if (autoDismissTimer.current) clearTimeout(autoDismissTimer.current);
    };
  }, []);

  // Don't render if no health data or not visible
  if (!health || !visible) return null;

  const isR1 = health.level === "R1";
  const isR2 = health.level === "R2";
  const isR3 = health.level === "R3";

  const bannerClass = useMemo(() => [
    styles.banner,
    isR1 && styles.bannerR1,
    isR2 && styles.bannerR2,
    isR3 && styles.bannerR3,
    exiting && styles.bannerExiting,
  ].filter(Boolean).join(" "), [isR1, isR2, isR3, exiting, styles]);

  const iconClass = useMemo(() => [
    styles.icon,
    isR1 && styles.iconR1,
    isR2 && styles.iconR2,
    isR3 && styles.iconR3,
  ].filter(Boolean).join(" "), [isR1, isR2, isR3, styles]);

  const titleClass = useMemo(() => [
    styles.title,
    isR1 && styles.titleR1,
    isR2 && styles.titleR2,
    isR3 && styles.titleR3,
  ].filter(Boolean).join(" "), [isR1, isR2, isR3, styles]);

  // Icon symbols
  const iconSymbol = isR1 ? "✕" : isR2 ? "⚠" : "✓";

  // Close handler
  const handleClose = () => {
    if (isR2) {
      // R2: dismissable
      setExiting(true);
      autoDismissTimer.current = setTimeout(() => {
        dismissWarning();
      }, 500);
    }
    // R1: clicking close button still hides it (but reappears on next poll)
    if (isR1) {
      setExiting(true);
      autoDismissTimer.current = setTimeout(() => setVisible(false), 500);
    }
  };

  return (
    <div className={styles.container} role="alert" aria-live="polite">
      <div className={bannerClass}>
        {/* Icon */}
        <div className={iconClass} aria-hidden="true">
          {iconSymbol}
        </div>

        {/* Content */}
        <div className={styles.content}>
          <div className={titleClass}>
            {health.title}
            {isR3 && (
              <span
                style={{
                  fontSize: 11,
                  color: "var(--color-text-tertiary)",
                  marginLeft: 8,
                  fontWeight: 400,
                }}
              >
                即将自动关闭...
              </span>
            )}
          </div>
          <div className={styles.message}>
            {health.message}
            {error && (
              <span style={{ color: "var(--color-danger)", marginLeft: 8 }}>
                {error}
              </span>
            )}
          </div>

          {/* Details toggle for R1/R2 */}
          {health.details && health.details.length > 0 && (
            <>
              <button
                className={styles.detailsToggle}
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? "收起详情" : "查看详情"}
              </button>
              {showDetails && (
                <ul className={styles.detailsList}>
                  {health.details.map((detail, i) => (
                    <li key={i} className={styles.detailItem}>
                      {detail}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>

        {/* Close button (R1: persistent close, R2: dismiss, R3: no close needed) */}
        {!isR3 && (
          <button
            className={styles.closeBtn}
            onClick={handleClose}
            aria-label="关闭提示"
            title={isR1 ? "暂时隐藏（下次检查时重新显示）" : "关闭提示"}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
});
