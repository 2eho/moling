"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import type { AdminStats } from "@/lib/types";
import parentStyles from "../../admin.module.css";
import styles from "./OverviewTab.module.css";

const STAT_ICONS: Record<string, { icon: string; colorClass: string }> = {
  total_users: { icon: "👥", colorClass: parentStyles.statCardIconIndigo },
  active_users: { icon: "✅", colorClass: parentStyles.statCardIconGreen },
  total_projects: { icon: "📚", colorClass: parentStyles.statCardIconBlue },
  api_calls_today: { icon: "🤖", colorClass: parentStyles.statCardIconAmber },
};

const STAT_LABELS: Record<string, string> = {
  total_users: "总用户数",
  active_users: "活跃用户",
  total_projects: "项目总数",
  api_calls_today: "今日 API 调用",
};

function formatStatValue(key: string, value: number): string {
  if (key === "api_calls_today") {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString();
}

// ── Inline SVG charts (same as original design) ──

function DauChart() {
  const points = [130, 110, 120, 95, 75, 85, 60, 70];
  const labels = ["06/04","06/05","06/06","06/07","06/08","06/09","06/10","06/11"];
  const xPositions = [60, 100, 140, 180, 220, 260, 300, 340];

  const pathD = xPositions.map((x, i) =>
    i === 0 ? `M${x},${points[i]}` : `L${x},${points[i]}`
  ).join(" ");

  const areaD = `${pathD} L${xPositions[xPositions.length-1]},145 L${xPositions[0]},145 Z`;

  return (
    <svg viewBox="0 0 400 180" preserveAspectRatio="xMidYMid meet" style={{width:"100%",height:"100%"}}>
      <defs>
        <linearGradient id="dauGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-brand-indigo, #6366f1)" stopOpacity="0.4"/>
          <stop offset="100%" stopColor="var(--color-brand-indigo, #6366f1)" stopOpacity="0"/>
        </linearGradient>
      </defs>
      {[40, 75, 110, 145].map(y => (
        <line key={y} x1="40" y1={y} x2="380" y2={y} stroke="#1e2138" strokeWidth="0.5"/>
      ))}
      <path d={areaD} fill="url(#dauGradient)" opacity="0.3"/>
      <path d={pathD} stroke="var(--color-brand-indigo, #6366f1)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {xPositions.map((x, i) => (
        <circle key={i} cx={x} cy={points[i]} r="3" fill="var(--color-brand-indigo, #6366f1)"/>
      ))}
      {labels.map((d, i) => (
        <text key={i} x={xPositions[i]} y="165" fill="#6b7199" fontSize="9" textAnchor="middle">{d}</text>
      ))}
      {[{y:44,l:"15k"},{y:79,l:"12k"},{y:114,l:"9k"},{y:149,l:"6k"}].map(({y,l}) => (
        <text key={l} x="35" y={y} fill="#6b7199" fontSize="9" textAnchor="end">{l}</text>
      ))}
    </svg>
  );
}

function LlmChart() {
  const bars = [
    {x:60,h:35},{x:108,h:50},{x:156,h:45},{x:204,h:75},{x:252,h:85},{x:300,h:65},{x:348,h:95}
  ];
  const labels = ["06/04","06/05","06/06","06/07","06/08","06/09","06/10"];

  return (
    <svg viewBox="0 0 400 180" preserveAspectRatio="xMidYMid meet" style={{width:"100%",height:"100%"}}>
      {[40, 75, 110, 145].map(y => (
        <line key={y} x1="40" y1={y} x2="380" y2={y} stroke="#1e2138" strokeWidth="0.5"/>
      ))}
      {bars.map((b, i) => (
        <rect key={i} x={b.x} y={145-b.h} width="28" height={b.h} rx="3" fill="var(--color-brand-amber, #d4a843)" opacity="0.85"/>
      ))}
      {labels.map((d, i) => (
        <text key={i} x={[74,122,170,218,266,314,362][i]} y="165" fill="#6b7199" fontSize="9" textAnchor="middle">{d}</text>
      ))}
      {[{y:44,l:"3.0M"},{y:79,l:"2.5M"},{y:114,l:"2.0M"},{y:149,l:"1.5M"}].map(({y,l}) => (
        <text key={l} x="35" y={y} fill="#6b7199" fontSize="9" textAnchor="end">{l}</text>
      ))}
    </svg>
  );
}

export default function OverviewTab() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.getStats();
      setStats(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取统计数据失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const statEntries = stats
    ? (Object.keys(STAT_LABELS) as (keyof AdminStats)[])
        .filter((k) => k in stats)
        .map((key) => ({
          key,
          icon: STAT_ICONS[key]?.icon ?? "📊",
          colorClass: STAT_ICONS[key]?.colorClass ?? parentStyles.statCardIconIndigo,
          label: STAT_LABELS[key] ?? key,
          value: formatStatValue(key, stats[key] as number),
        }))
    : [];

  // ── Activities (mock for now) ──
  const activities = [
    { icon: "🆕", text: "用户 张三 注册了账号", time: "2 小时前" },
    { icon: "💰", text: "用户 李四 充值 ¥99", time: "3 小时前" },
    { icon: "🤖", text: "系统完成每日 LLM 用量统计", time: "5 小时前" },
    { icon: "👥", text: "新增 47 名活跃用户", time: "6 小时前" },
    { icon: "⚠️", text: "系统检测到 API 延迟升高", time: "8 小时前" },
  ];

  if (loading) {
    return (
      <div className={`${parentStyles.tabPanelActive}`}>
        <div className={styles.loadingState}>
          <div className={styles.loadingSpinner}></div>
          <span className={styles.loadingText}>加载系统数据...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${parentStyles.tabPanelActive}`}>
        <div className={styles.errorState}>
          <div className={styles.errorIcon}>⚠️</div>
          <div className={styles.errorText}>加载失败</div>
          <div className={styles.errorHint}>{error}</div>
          <button className={styles.retryBtn} onClick={fetchStats}>重新加载</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${parentStyles.tabPanelActive}`}>
      <div className={parentStyles.pageTitleRow}>
        <div>
          <h1 className={parentStyles.pageTitle}>系统概览</h1>
          <p className={parentStyles.pageSubtitle}>MoLing AI 平台运行状态一览</p>
        </div>
      </div>

      <div className={parentStyles.statCards}>
        {statEntries.length > 0 ? (
          statEntries.map((entry) => (
            <div key={entry.key} className={parentStyles.statCard}>
              <div className={parentStyles.statCardHeader}>
                <div className={`${parentStyles.statCardIcon} ${entry.colorClass}`}>
                  {entry.icon}
                </div>
              </div>
              <div className={parentStyles.statCardLabel}>{entry.label}</div>
              <div className={parentStyles.statCardValue}>{entry.value}</div>
            </div>
          ))
        ) : (
          <div className={parentStyles.statCard}>
            <div className={parentStyles.statCardLabel}>暂无数据</div>
            <div className={parentStyles.statCardValue}>--</div>
          </div>
        )}
      </div>

      <div className={parentStyles.chartsRow}>
        <div className={parentStyles.chartCard}>
          <div className={parentStyles.chartCardHeader}>
            <span className={parentStyles.chartCardTitle}>DAU 趋势</span>
            <span className={parentStyles.chartCardPeriod}>最近 7 天</span>
          </div>
          <div className={parentStyles.chartContainer}>
            <DauChart />
          </div>
        </div>
        <div className={parentStyles.chartCard}>
          <div className={parentStyles.chartCardHeader}>
            <span className={parentStyles.chartCardTitle}>LLM 调用量趋势</span>
            <span className={parentStyles.chartCardPeriod}>最近 7 天</span>
          </div>
          <div className={parentStyles.chartContainer}>
            <LlmChart />
          </div>
        </div>
      </div>

      <div className={parentStyles.sectionCard}>
        <div className={parentStyles.sectionCardHeader}>
          <span className={parentStyles.sectionCardTitle}>最近活动</span>
          <span className="text-tertiary" style={{fontSize: 12, color: "var(--color-text-tertiary)"}}>实时更新</span>
        </div>
        <div className={parentStyles.activityFeed}>
          {activities.map((a, i) => (
            <div key={i} className={parentStyles.activityItem}>
              <div className={parentStyles.activityIcon}>{a.icon}</div>
              <div className={parentStyles.activityContent}>
                <div className={parentStyles.activityText}>
                  <span dangerouslySetInnerHTML={{
                    __html: a.text.replace(/ (.*?) /g, ' <strong>$1</strong> ')
                  }} />
                </div>
                <div className={parentStyles.activityTime}>{a.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
