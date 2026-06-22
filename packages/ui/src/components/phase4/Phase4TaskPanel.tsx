"use client";

import { useQuery } from "@tanstack/react-query";
import { getProjectPhase4Tasks } from "@/lib/http/api";
import type { Phase4Task, Phase4State } from "@/lib/types/domain";
import {
  Clock,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";
import { formatRelativeTime, formatDuration } from "@/lib/format";

interface Phase4TaskPanelProps {
  projectId: string;
}

const STATE_CONFIG: Record<Phase4State, { label: string; color: string; bg: string; order: number }> = {
  idle: { label: "空闲", color: "#9ca3af", bg: "rgba(156,163,175,0.12)", order: 0 },
  queued: { label: "排队中", color: "#3b82f6", bg: "rgba(59,130,246,0.12)", order: 1 },
  locking: { label: "锁定中", color: "#f97316", bg: "rgba(249,115,22,0.12)", order: 2 },
  extracting: { label: "提取中", color: "#8b5cf6", bg: "rgba(139,92,246,0.12)", order: 3 },
  verifying: { label: "验证中", color: "#06b6d4", bg: "rgba(6,182,212,0.12)", order: 4 },
  merging: { label: "合并中", color: "#ec4899", bg: "rgba(236,72,153,0.12)", order: 5 },
  committing: { label: "提交中", color: "#eab308", bg: "rgba(234,179,8,0.12)", order: 6 },
  done: { label: "完成", color: "#22c55e", bg: "rgba(34,197,94,0.12)", order: 7 },
  failed: { label: "失败", color: "#ef4444", bg: "rgba(239,68,68,0.12)", order: 8 },
  retry: { label: "重试中", color: "#f97316", bg: "rgba(249,115,22,0.15)", order: 9 },
};

const STATE_FLOW: Phase4State[] = [
  "queued", "locking", "extracting", "verifying", "merging", "committing", "done",
];

function StateFlowChart({ currentState }: { currentState: Phase4State }) {
  const currentIdx = STATE_FLOW.indexOf(currentState);
  if (currentIdx === -1) return null;

  return (
    <div className="space-y-1.5">
      <span className="text-[10px] font-semibold" style={{ color: "var(--th-text-4)" }}>
        状态流程
      </span>
      <div className="flex items-center gap-1">
        {STATE_FLOW.map((state, idx) => {
          const config = STATE_CONFIG[state];
          const isActive = idx === currentIdx;
          const isPast = idx < currentIdx;

          return (
            <div key={state} className="flex items-center gap-1 flex-1">
              <div
                className="flex-1 h-1.5 rounded-full transition-all"
                style={{
                  background: isActive
                    ? config.color
                    : isPast
                      ? config.bg
                      : "var(--th-hover)",
                  opacity: isPast ? 0.5 : 1,
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between">
        {STATE_FLOW.map((state, idx) => {
          const config = STATE_CONFIG[state];
          const isActive = idx === currentIdx;
          return (
            <span
              key={state}
              className="text-[8px] font-medium"
              style={{
                color: isActive ? config.color : "var(--th-text-4)",
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {config.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Phase4Task }) {
  const [expanded, setExpanded] = useState(false);
  const config = STATE_CONFIG[task.state];
  const isRunning = ["queued", "locking", "extracting", "verifying", "merging", "committing"].includes(task.state);

  return (
    <div
      role="listitem"
      className="rounded-lg border transition-all"
      style={{
        borderColor: task.state === "failed" ? config.bg : "var(--th-border-subtle)",
        background: "var(--th-card)",
      }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
      >
        {/* State icon */}
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
          style={{ background: config.bg }}
        >
          {isRunning ? (
            <Loader2 size={13} className="animate-spin" style={{ color: config.color }} />
          ) : task.state === "done" ? (
            <CheckCircle2 size={13} style={{ color: config.color }} />
          ) : task.state === "failed" ? (
            <AlertCircle size={13} style={{ color: config.color }} />
          ) : (
            <Clock size={13} style={{ color: config.color }} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium truncate" style={{ color: "var(--th-text)" }}>
              {task.id.slice(0, 8)}...
            </span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0"
              style={{ background: config.bg, color: config.color }}
            >
              {config.label}
            </span>
          </div>
          <p className="text-[10px] mt-0.5" style={{ color: "var(--th-text-3)" }}>
            {formatRelativeTime(task.created_at)}
            {task.retry_count > 0 && ` · 重试 ${task.retry_count} 次`}
          </p>
        </div>

        {expanded ? (
          <ChevronDown size={13} style={{ color: "var(--th-text-3)" }} />
        ) : (
          <ChevronRight size={13} style={{ color: "var(--th-text-3)" }} />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {/* State flow */}
          <StateFlowChart currentState={task.state} />

          {/* Error info */}
          {task.last_error && (
            <div
              className="rounded-lg p-2 text-[10px] leading-relaxed"
              style={{
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.15)",
                color: "var(--th-danger)",
              }}
            >
              {task.last_error}
            </div>
          )}

          {/* Safety check */}
          {task.safety_check && (
            <div
              className="rounded-lg p-2"
              style={{
                background: task.safety_check.passed
                  ? "rgba(34,197,94,0.08)"
                  : "rgba(239,68,68,0.08)",
                border: `1px solid ${
                  task.safety_check.passed
                    ? "rgba(34,197,94,0.15)"
                    : "rgba(239,68,68,0.15)"
                }`,
              }}
            >
              <span
                className="text-[10px] font-medium"
                style={{
                  color: task.safety_check.passed ? "var(--th-success)" : "var(--th-danger)",
                }}
              >
                安全检查：{task.safety_check.passed ? "通过" : "未通过"}
              </span>
              {task.safety_check.issues.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {task.safety_check.issues.map((issue, i) => (
                    <li key={i} className="text-[9px]" style={{ color: "var(--th-text-3)" }}>
                      · {issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Retry info */}
          {task.retry_at && (
            <p className="text-[9px]" style={{ color: "var(--th-text-4)" }}>
              下次重试：{formatRelativeTime(task.retry_at)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function Phase4TaskPanel({ projectId }: Phase4TaskPanelProps) {
  const {
    data: tasks,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["phase4-tasks", projectId],
    queryFn: () => getProjectPhase4Tasks(projectId),
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 rounded-lg animate-shimmer"
            style={{
              background: "linear-gradient(90deg, var(--th-card) 25%, var(--th-hover) 50%, var(--th-card) 75%)",
            }}
          />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="rounded-lg p-6 text-center"
        style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}
      >
        <AlertCircle size={28} className="mx-auto mb-2" style={{ color: "var(--th-danger)" }} />
        <p className="text-xs font-medium mb-1" style={{ color: "var(--th-text)" }}>
          加载任务失败
        </p>
        <p className="text-[10px] mb-3" style={{ color: "var(--th-text-3)" }}>
          {error instanceof Error ? error.message : "请稍后重试"}
        </p>
        <button
          onClick={() => refetch()}
          className="px-3 py-1.5 rounded-lg text-[10px] font-medium hover:opacity-80"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          重试
        </button>
      </div>
    );
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div
        className="rounded-lg p-8 text-center"
        style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}
      >
        <Clock size={32} className="mx-auto mb-2" style={{ color: "var(--th-text-4)" }} />
        <p className="text-sm font-medium" style={{ color: "var(--th-text)" }}>
          暂无任务
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--th-text-3)" }}>
          当有 Phase 4 任务时，将在此处显示
        </p>
      </div>
    );
  }

  // Sort: running tasks first, then by created_at desc
  const sorted = [...tasks].sort((a, b) => {
    const aRunning = STATE_FLOW.includes(a.state as typeof STATE_FLOW[number]);
    const bRunning = STATE_FLOW.includes(b.state as typeof STATE_FLOW[number]);
    if (aRunning && !bRunning) return -1;
    if (!aRunning && bRunning) return 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div role="list" className="space-y-2">
      {sorted.map((task) => (
        <TaskCard key={task.id} task={task} />
      ))}
    </div>
  );
}
