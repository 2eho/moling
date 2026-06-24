"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  RefreshCw,
  ShieldOff,
} from "lucide-react";
import { memo, useState } from "react";
import { getProjectHealth, refreshProjectHealth } from "@/lib/http/api";
import type { AlertSeverity, HealthAlert } from "@/lib/types/domain";

interface HealthDashboardProps {
  projectId: string;
}

const SEVERITY_CONFIG: Record<
  AlertSeverity,
  { icon: React.ReactNode; label: string; colorClass: string; bgClass: string }
> = {
  R1: {
    icon: <AlertTriangle size={16} />,
    label: "R1 轻度",
    colorClass: "text-yellow-500",
    bgClass: "bg-yellow-500/12",
  },
  R2: {
    icon: <AlertCircle size={16} />,
    label: "R2 中度",
    colorClass: "text-orange-500",
    bgClass: "bg-orange-500/12",
  },
  R3: {
    icon: <AlertOctagon size={16} />,
    label: "R3 严重",
    colorClass: "text-red-500",
    bgClass: "bg-red-500/12",
  },
};

const AlertItem = memo(function AlertItem({ alert }: { alert: HealthAlert }) {
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[alert.severity];

  return (
    <div
      className={`rounded-lg border transition-all ${alert.suppressed ? "border-th-border-subtle bg-th-card opacity-60" : `border-current/10 ${config.bgClass}`}`}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left"
        aria-expanded={expanded}
      >
        <span className={config.colorClass}>{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-semibold ${alert.suppressed ? "text-th-text-3" : "text-th-text"}`}
            >
              {alert.rule}
            </span>
            {alert.suppressed && (
              <span className="text-[9px] px-1.5 py-0.5 rounded flex items-center gap-1 bg-th-hover text-th-text-4">
                <ShieldOff size={9} />
                防疲劳抑制
              </span>
            )}
          </div>
          <p className="text-[11px] mt-0.5 text-th-text-3">
            {alert.subplot_name} · 第 {alert.current_chapter} 章
          </p>
        </div>
        <span
          className={`text-[10px] px-2 py-0.5 rounded font-medium ${config.bgClass} ${config.colorClass}`}
        >
          {config.label}
        </span>
        {expanded ? (
          <ChevronDown size={14} className="text-th-text-3 shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-th-text-3 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-3 pt-0 space-y-2">
          <p className="text-[11px] leading-relaxed text-th-text-2">{alert.reason}</p>
          <div className="rounded-lg p-2.5 text-[11px] bg-th-accent-dim text-th-accent-text">
            建议：{alert.suggestion}
          </div>
        </div>
      )}
    </div>
  );
});

function AlertSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg h-16 animate-shimmer bg-gradient-to-r from-th-card via-th-hover to-th-card bg-[length:200%_100%]"
        />
      ))}
    </div>
  );
}

export function HealthDashboard({ projectId }: HealthDashboardProps) {
  const queryClient = useQueryClient();
  const [lastRefreshed] = useState<Date>(new Date());

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
    staleTime: 30_000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => refreshProjectHealth(projectId),
    onSuccess: (data) => {
      queryClient.setQueryData(["project-health", projectId], data);
    },
  });

  // 🔄 Loading
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-1 h-20 rounded-lg animate-shimmer bg-gradient-to-r from-th-card via-th-hover to-th-card bg-[length:200%_100%]"
            />
          ))}
        </div>
        <AlertSkeleton />
      </div>
    );
  }

  // ❌ Error
  if (isError) {
    return (
      <div className="rounded-lg p-6 text-center bg-th-card border border-th-border-subtle">
        <AlertOctagon size={32} className="mx-auto mb-3 text-th-danger" />
        <p className="text-sm font-medium mb-1 text-th-text">加载健康数据失败</p>
        <p className="text-xs mb-4 text-th-text-3">
          {error instanceof Error ? error.message : "请稍后重试"}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-4 py-2 rounded-lg text-xs font-medium transition-colors hover:opacity-80 bg-th-accent-dim text-th-accent-text"
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
        {[
          { key: "R1" as const, count: summary.r1_count },
          { key: "R2" as const, count: summary.r2_count },
          { key: "R3" as const, count: summary.r3_count },
        ].map(({ key, count }) => {
          const cfg = SEVERITY_CONFIG[key];
          return (
            <div key={key} className={`rounded-lg p-3 border ${cfg.bgClass}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={cfg.colorClass}>{cfg.icon}</span>
                <span className={`text-[10px] font-medium ${cfg.colorClass}`}>{cfg.label}</span>
              </div>
              <span className={`text-xl font-bold ${cfg.colorClass}`}>{count}</span>
            </div>
          );
        })}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-th-text">
            {isEmpty ? "所有子情节健康" : `告警列表 (${alerts.length})`}
          </span>
          <span className="text-[10px] flex items-center gap-1 text-th-text-4">
            <Clock size={10} />
            {lastRefreshed.toLocaleTimeString("zh-CN")}
          </span>
        </div>
        <button
          type="button"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:opacity-80 disabled:opacity-50 bg-th-accent-dim text-th-accent-text"
          aria-label="刷新健康数据"
        >
          <RefreshCw size={12} className={refreshMutation.isPending ? "animate-spin" : ""} />
          {refreshMutation.isPending ? "刷新中..." : "刷新"}
        </button>
      </div>

      {/* Alert List or Empty State */}
      {isEmpty ? (
        <div className="rounded-lg p-8 text-center bg-th-card border border-th-border-subtle">
          <CheckCircle2 size={40} className="mx-auto mb-3 text-[var(--th-success)]" />
          <p className="text-sm font-medium text-th-text">所有子情节健康</p>
          <p className="text-xs mt-1 text-th-text-3">暂无健康告警，继续保持！</p>
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
