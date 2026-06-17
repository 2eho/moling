"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { healthApi } from "@/lib/api";
import type { HealthAlert } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import styles from "./HealthDashboard.module.css";

// ── Extended Alert for Dashboard ──

interface DashboardAlert extends HealthAlert {
  subplot_name?: string;
  chapter_number?: number;
  suggestion?: string;
  is_suppressed?: boolean;
  suppress_reason?: string;
}

interface AlertCounts {
  critical: number;
  warning: number;
  info: number;
}

// ── Severity Display Configuration ──

const SEVERITY_CONFIG = {
  critical: { label: "R1", name: "严重", color: "var(--color-danger, #ef4444)", bg: "var(--color-danger-dim, rgba(239,68,68,0.08))" },
  warning:  { label: "R2", name: "警告", color: "var(--color-warning, #fbbf24)", bg: "var(--color-warning-dim, rgba(251,191,36,0.08))" },
  info:     { label: "R3", name: "信息", color: "var(--color-brand-indigo, #6366f1)", bg: "var(--color-brand-indigo-dim, rgba(99,102,241,0.08))" },
} as const;

const SEVERITY_ORDER: Array<keyof AlertCounts> = ["critical", "warning", "info"];

// ── Component ──

export function HealthDashboard({ projectId }: { projectId: string }) {
  const [alerts, setAlerts] = useState<DashboardAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // ── Data Fetching ──

  const fetchAlerts = useCallback(async (showRefreshIndicator = false) => {
    if (showRefreshIndicator) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    try {
      const res = await healthApi.getAlerts(projectId);
      setAlerts(Array.isArray(res.data) ? (res.data as DashboardAlert[]) : []);
      setLastChecked(new Date().toISOString());
    } catch (err) {
      const msg = err instanceof Error ? err.message : "获取健康告警失败";
      setError(msg);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  // ── Actions ──

  const handleRefreshCheck = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await healthApi.refreshCheck(projectId);
      await fetchAlerts(true);
    } catch {
      setIsRefreshing(false);
    }
  }, [projectId, fetchAlerts]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // ── Derived Data ──

  const counts = useMemo<AlertCounts>(() => ({
    critical: alerts.filter((a) => a.severity === "critical").length,
    warning:  alerts.filter((a) => a.severity === "warning").length,
    info:     alerts.filter((a) => a.severity === "info").length,
  }), [alerts]);

  const totalAlerts = useMemo(() => counts.critical + counts.warning + counts.info, [counts]);

  const sortedAlerts = useMemo(() => {
    const order: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    return [...alerts].sort((a, b) => (order[a.severity] ?? 99) - (order[b.severity] ?? 99));
  }, [alerts]);

  // ── Loading / Error / Empty ──

  if (isLoading) {
    return (
      <div className={styles.container} aria-busy="true">
        <div className={styles.header}>
          <Skeleton width={200} height={24} />
          <Skeleton width={100} height={32} borderRadius={8} />
        </div>
        <div className={styles.skeletonCards}>
          <div className={styles.skeletonCard}><Skeleton width="60%" height={40} /><Skeleton width="30%" height={16} /></div>
          <div className={styles.skeletonCard}><Skeleton width="60%" height={40} /><Skeleton width="30%" height={16} /></div>
          <div className={styles.skeletonCard}><Skeleton width="60%" height={40} /><Skeleton width="30%" height={16} /></div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className={styles.alertItemSkeleton}>
            <Skeleton width="100%" height={56} borderRadius={12} />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>健康监控仪表盘</h2>
        </div>
        <div className={styles.emptyContainer}>
          <EmptyState
            icon="⚠️"
            title="获取健康告警失败"
            description={error}
            action={{ label: "重试", onClick: () => fetchAlerts() }}
          />
        </div>
      </div>
    );
  }

  if (totalAlerts === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h2 className={styles.title}>健康监控仪表盘</h2>
            {lastChecked && <span className={styles.lastChecked}>上次检查: {new Date(lastChecked).toLocaleString("zh-CN")}</span>}
          </div>
          <div className={styles.headerActions}>
            <Button variant="secondary" size="sm" onClick={handleRefreshCheck} loading={isRefreshing}>
              刷新检查
            </Button>
          </div>
        </div>
        <div className={styles.emptyContainer}>
          <EmptyState
            icon="✅"
            title="所有子情节健康"
            description="未检测到任何健康告警，所有子情节运行正常"
          />
        </div>
      </div>
    );
  }

  // ── Normal Render ──

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2 className={styles.title}>健康监控仪表盘</h2>
          {lastChecked && (
            <span className={styles.lastChecked}>
              上次检查: {new Date(lastChecked).toLocaleString("zh-CN")}
            </span>
          )}
        </div>
        <div className={styles.headerActions}>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRefreshCheck}
            loading={isRefreshing}
          >
            刷新检查
          </Button>
        </div>
      </div>

      {/* Severity Count Cards */}
      <div className={styles.countCards}>
        {SEVERITY_ORDER.map((sev) => {
          const cfg = SEVERITY_CONFIG[sev];
          const count = counts[sev];
          return (
            <div
              key={sev}
              className={styles.countCard}
              style={{ borderLeftColor: cfg.color, background: cfg.bg }}
            >
              <span className={styles.countLabel} style={{ color: cfg.color }}>
                {cfg.label}
              </span>
              <span className={styles.countNumber} style={{ color: cfg.color }}>
                {count}
              </span>
              <span className={styles.countName}>{cfg.name}</span>
            </div>
          );
        })}
      </div>

      {/* Alert List */}
      <div className={styles.list}>
        <h3 className={styles.listTitle}>
          告警详情
          <span style={{ fontWeight: 400, color: "var(--color-text-tertiary)" }}>
            {" "}({totalAlerts})
          </span>
        </h3>

        {sortedAlerts.map((alert) => {
          const isExpanded = expandedIds.has(alert.id);
          const cfg = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info;
          const das = alert as DashboardAlert;
          const isSuppressed = das.is_suppressed;

          return (
            <div
              key={alert.id}
              className={`${styles.alertItem} ${isSuppressed ? styles.alertSuppressed : ""}`}
              style={!isSuppressed ? { borderLeftColor: cfg.color } : undefined}
            >
              <div
                className={styles.alertHeader}
                onClick={() => toggleExpand(alert.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggleExpand(alert.id);
                  }
                }}
              >
                <div className={styles.alertLeft}>
                  <span
                    className={styles.severityDot}
                    style={{
                      background: isSuppressed
                        ? "var(--color-text-disabled)"
                        : cfg.color,
                    }}
                  />
                  <div>
                    <div className={styles.alertTitle}>
                      <span
                        className={styles.severityBadge}
                        style={{ background: cfg.bg, color: cfg.color }}
                      >
                        {cfg.label}
                      </span>
                      <span
                        className={
                          isSuppressed
                            ? styles.alertTitleTextSuppressed
                            : styles.alertTitleText
                        }
                      >
                        {alert.title}
                      </span>
                      {isSuppressed && (
                        <span className={styles.suppressTag}>
                          {das.suppress_reason || "3章内重复"}
                        </span>
                      )}
                    </div>
                    <div className={styles.alertMeta}>
                      {das.subplot_name && (
                        <span>子情节: {das.subplot_name}</span>
                      )}
                      {das.chapter_number != null && (
                        <span>当前章节: 第{das.chapter_number}章</span>
                      )}
                      {das.rule && <span>规则: {das.rule}</span>}
                    </div>
                  </div>
                </div>
                <span
                  className={styles.expandIcon}
                  style={{ transform: isExpanded ? "rotate(180deg)" : undefined }}
                >
                  ▼
                </span>
              </div>

              {isExpanded && (
                <div className={styles.alertBody}>
                  <p className={styles.alertDetail}>{alert.detail}</p>
                  {das.suggestion && (
                    <div className={styles.suggestion}>
                      <span className={styles.suggestionLabel}>建议操作:</span>
                      <span>{das.suggestion}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
