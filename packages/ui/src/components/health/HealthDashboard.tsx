"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getProjectHealth, refreshProjectHealth } from "@/lib/http/api";
import {
  AlertTriangle,
  AlertCircle,
  AlertOctagon,
  RefreshCw,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ShieldOff,
} from "lucide-react";
import { useState } from "react";
import type { HealthAlert, AlertSeverity } from "@/lib/types/domain";

interface HealthDashboardProps {
  projectId: string;
}

const SEVERITY_CONFIG: Record<AlertSeverity, { icon: React.ReactNode; label: string; color: string; bg: string }> = {
  R1: {
    icon: <AlertTriangle size={16} />,
    label: "R1 轻度",
    color: "#eab308",
    bg: "rgba(234,179,8,0.12)",
  },
  R2: {
    icon: <AlertCircle size={16} />,
    label: "R2 中度",
    color: "#f97316",
    bg: "rgba(249,115,22,0.12)",
  },
  R3: {
    icon: <AlertOctagon size={16} />,
    label: "R3 严重",
    color: "#ef4444",
    bg: "rgba(239,68,68,0.12)",
  },
};

function AlertItem({ alert }: { alert: HealthAlert }) {
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[alert.severity];

  return (
    <div
      className="rounded-lg border transition-all"
      style={{
        borderColor: alert.suppressed ? "var(--th-border-subtle)" : config.bg,
        background: alert.suppressed ? "var(--th-card)" : "var(--th-bg)",
        opacity: alert.suppressed ? 0.6 : 1,
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
      >
        <span style={{ color: config.color }}>{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="text-xs font-semibold"
              style={{ color: alert.suppressed ? "var(--th-text-3)" : "var(--th-text)" }}
            >
              {alert.rule}
            </span>
            {alert.suppressed && (
              <span
                className="text-[9px] px-1.5 py-0.5 rounded flex items-center gap-1"
                style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}
              >
                <ShieldOff size={9} />
                防疲劳抑制
              </span>
            )}
          </div>
          <p className="text-[11px] mt-0.5" style={{ color: "var(--th-text-3)" }}>
            {alert.subplot_name} · 第 {alert.current_chapter} 章
          </p>
        </div>
        <span
          className="text-[10px] px-2 py-0.5 rounded font-medium"
          style={{ background: config.bg, color: config.color }}
        >
          {config.label}
        </span>
        {expanded ? <ChevronDown size={14} style={{ color: "var(--th-text-3)" }} /> : <ChevronRight size={14} style={{ color: "var(--th-text-3)" }} />}
      </button>

      {expanded && (
        <div className="px-4 pb-3 pt-0 space-y-2">
          <p className="text-[11px] leading-relaxed" style={{ color: "var(--th-text-2)" }}>
            {alert.reason}
          </p>
          <div
            className="rounded-lg p-2.5 text-[11px]"
            style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
          >
            建议：{alert.suggestion}
          </div>
        </div>
      )}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg h-16 animate-shimmer"
          style={{
            background: "linear-gradient(90deg, var(--th-card) 25%, var(--th-hover) 50%, var(--th-card) 75%)",
          }}
        />
      ))}
    </div>
  );
}

export function HealthDashboard({ projectId }: HealthDashboardProps) {
  const queryClient = useQueryClient();
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const {
    data: healthData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["project-health", projectId],
    queryFn: () => getProjectHealth(projectId),
    refetchInterval: 60_000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshProjectHealth(projectId),
    onSuccess: (data) => {
      queryClient.setQueryData(["project-health", projectId], data);
      setLastRefreshed(new Date());
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-1 h-20 rounded-lg animate-shimmer"
              style={{
                background: "linear-gradient(90deg, var(--th-card) 25%, var(--th-hover) 50%, var(--th-card) 75%)",
              }}
            />
          ))}
        </div>
        <Skeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="rounded-lg p-6 text-center"
        style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}
      >
        <AlertOctagon size={32} className="mx-auto mb-3" style={{ color: "var(--th-danger)" }} />
        <p className="text-sm font-medium mb-1" style={{ color: "var(--th-text)" }}>
          加载健康数据失败
        </p>
        <p className="text-xs mb-4" style={{ color: "var(--th-text-3)" }}>
          {error instanceof Error ? error.message : "请稍后重试"}
        </p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 rounded-lg text-xs font-medium transition-colors hover:opacity-80"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          重试
        </button>
      </div>
    );
  }

  if (!healthData) return null;

  const { alerts, summary } = healthData;
  const isEmpty = alerts.length === 0;

  return (
    <div className="space-y-5">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3">
        {([
          { key: "R1", count: summary.r1_count },
          { key: "R2", count: summary.r2_count },
          { key: "R3", count: summary.r3_count },
        ] as const).map(({ key, count }) => {
          const config = SEVERITY_CONFIG[key];
          return (
            <div
              key={key}
              className="rounded-lg p-3"
              style={{ background: config.bg, border: `1px solid ${config.bg}` }}
            >
              <div className="flex items-center gap-2 mb-1">
                {config.icon}
                <span className="text-[10px] font-medium" style={{ color: config.color }}>
                  {config.label}
                </span>
              </div>
              <span className="text-xl font-bold" style={{ color: config.color }}>
                {count}
              </span>
            </div>
          );
        })}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: "var(--th-text)" }}>
            {isEmpty ? "所有子情节健康" : `告警列表 (${alerts.length})`}
          </span>
          <span className="text-[10px] flex items-center gap-1" style={{ color: "var(--th-text-4)" }}>
            <Clock size={10} />
            {lastRefreshed.toLocaleTimeString("zh-CN")}
          </span>
        </div>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:opacity-80 disabled:opacity-50"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          <RefreshCw size={12} className={refreshMutation.isPending ? "animate-spin" : ""} />
          {refreshMutation.isPending ? "刷新中..." : "刷新"}
        </button>
      </div>

      {/* Alert List or Empty State */}
      {isEmpty ? (
        <div
          className="rounded-lg p-8 text-center"
          style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}
        >
          <CheckCircle2 size={40} className="mx-auto mb-3" style={{ color: "var(--th-success)" }} />
          <p className="text-sm font-medium" style={{ color: "var(--th-text)" }}>
            所有子情节健康
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--th-text-3)" }}>
            暂无健康告警，继续保持！
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <AlertItem key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
