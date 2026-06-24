"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, ChevronDown, ChevronRight, Clock, Loader2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { formatRelativeTime } from "@/lib/format";
import { getProjectPhase4Tasks } from "@/lib/http/api";
import type { Phase4State, Phase4Task } from "@/lib/types/domain";

interface Phase4TaskPanelProps {
  projectId: string;
}

/** State → Tailwind class mapping (color-safe across all 8 themes) */
const STATE_STYLES: Record<
  Phase4State,
  {
    label: string;
    order: number;
    text: string;
    bg12: string;
    bg15: string;
    bg50: string;
    border15: string;
  }
> = {
  idle: {
    label: "空闲",
    order: 0,
    text: "text-gray-400",
    bg12: "bg-gray-400/12",
    bg15: "bg-gray-400/15",
    bg50: "bg-gray-400/50",
    border15: "border-gray-400/15",
  },
  queued: {
    label: "排队中",
    order: 1,
    text: "text-blue-500",
    bg12: "bg-blue-500/12",
    bg15: "bg-blue-500/15",
    bg50: "bg-blue-500/50",
    border15: "border-blue-500/15",
  },
  locking: {
    label: "锁定中",
    order: 2,
    text: "text-orange-500",
    bg12: "bg-orange-500/12",
    bg15: "bg-orange-500/15",
    bg50: "bg-orange-500/50",
    border15: "border-orange-500/15",
  },
  extracting: {
    label: "提取中",
    order: 3,
    text: "text-purple-500",
    bg12: "bg-purple-500/12",
    bg15: "bg-purple-500/15",
    bg50: "bg-purple-500/50",
    border15: "border-purple-500/15",
  },
  verifying: {
    label: "验证中",
    order: 4,
    text: "text-cyan-500",
    bg12: "bg-cyan-500/12",
    bg15: "bg-cyan-500/15",
    bg50: "bg-cyan-500/50",
    border15: "border-cyan-500/15",
  },
  merging: {
    label: "合并中",
    order: 5,
    text: "text-pink-500",
    bg12: "bg-pink-500/12",
    bg15: "bg-pink-500/15",
    bg50: "bg-pink-500/50",
    border15: "border-pink-500/15",
  },
  committing: {
    label: "提交中",
    order: 6,
    text: "text-yellow-500",
    bg12: "bg-yellow-500/12",
    bg15: "bg-yellow-500/15",
    bg50: "bg-yellow-500/50",
    border15: "border-yellow-500/15",
  },
  done: {
    label: "完成",
    order: 7,
    text: "text-th-success",
    bg12: "bg-th-success/12",
    bg15: "bg-th-success/15",
    bg50: "bg-th-success/50",
    border15: "border-th-success/15",
  },
  failed: {
    label: "失败",
    order: 8,
    text: "text-th-danger",
    bg12: "bg-th-danger/12",
    bg15: "bg-th-danger/15",
    bg50: "bg-th-danger/50",
    border15: "border-th-danger/15",
  },
  retry: {
    label: "重试中",
    order: 9,
    text: "text-orange-500",
    bg12: "bg-orange-500/12",
    bg15: "bg-orange-500/15",
    bg50: "bg-orange-500/50",
    border15: "border-orange-500/15",
  },
};

const STATE_FLOW: Phase4State[] = [
  "queued",
  "locking",
  "extracting",
  "verifying",
  "merging",
  "committing",
  "done",
];

function StateFlowChart({ currentState }: { currentState: Phase4State }) {
  const currentIdx = STATE_FLOW.indexOf(currentState);
  if (currentIdx === -1) return null;

  return (
    <div className="space-y-1.5">
      <span className="text-[10px] font-semibold text-th-text-4">状态流程</span>
      <div className="flex items-center gap-1">
        {STATE_FLOW.map((state, idx) => {
          const styles = STATE_STYLES[state];
          const isActive = idx === currentIdx;
          const isPast = idx < currentIdx;

          return (
            <div key={state} className="flex items-center gap-1 flex-1">
              <div
                className={cn(
                  "flex-1 h-1.5 rounded-full transition-all",
                  isActive && styles.text.replace("text-", "bg-"),
                  isPast && styles.bg50,
                  !isActive && !isPast && "bg-th-hover",
                )}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-center justify-between">
        {STATE_FLOW.map((state, idx) => {
          const styles = STATE_STYLES[state];
          const isActive = idx === currentIdx;
          return (
            <span
              key={state}
              className={cn(
                "text-[8px]",
                isActive ? cn(styles.text, "font-semibold") : "text-th-text-4",
              )}
            >
              {styles.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Phase4Task }) {
  const [expanded, setExpanded] = useState(false);
  const styles = STATE_STYLES[task.state];
  const isRunning = [
    "queued",
    "locking",
    "extracting",
    "verifying",
    "merging",
    "committing",
  ].includes(task.state);

  return (
    <div
      role="listitem"
      className={cn(
        "rounded-lg border transition-all bg-th-card",
        task.state === "failed" ? styles.border15 : "border-th-border-subtle",
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
      >
        {/* State icon */}
        <div
          className={cn(
            "w-7 h-7 rounded-full flex items-center justify-center shrink-0",
            styles.bg12,
          )}
        >
          {isRunning ? (
            <Loader2 size={13} className={cn("animate-spin", styles.text)} />
          ) : task.state === "done" ? (
            <CheckCircle2 size={13} className={styles.text} />
          ) : task.state === "failed" ? (
            <AlertCircle size={13} className={styles.text} />
          ) : (
            <Clock size={13} className={styles.text} />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium truncate text-th-text">
              {task.id.slice(0, 8)}...
            </span>
            <span
              className={cn(
                "text-[9px] px-1.5 py-0.5 rounded font-medium shrink-0",
                styles.bg12,
                styles.text,
              )}
            >
              {styles.label}
            </span>
          </div>
          <p className="text-[10px] mt-0.5 text-th-text-3">
            {formatRelativeTime(task.created_at)}
            {task.retry_count > 0 && ` · 重试 ${task.retry_count} 次`}
          </p>
        </div>

        {expanded ? (
          <ChevronDown size={13} className="text-th-text-3" />
        ) : (
          <ChevronRight size={13} className="text-th-text-3" />
        )}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {/* State flow */}
          <StateFlowChart currentState={task.state} />

          {/* Error info */}
          {task.last_error && (
            <div className="rounded-lg p-2 text-[10px] leading-relaxed bg-th-danger/8 border border-th-danger/15 text-th-danger">
              {task.last_error}
            </div>
          )}

          {/* Safety check */}
          {task.safety_check && (
            <div
              className={cn(
                "rounded-lg p-2",
                task.safety_check.passed
                  ? "bg-th-success/8 border border-th-success/15"
                  : "bg-th-danger/8 border border-th-danger/15",
              )}
            >
              <span
                className={cn(
                  "text-[10px] font-medium",
                  task.safety_check.passed ? "text-th-success" : "text-th-danger",
                )}
              >
                安全检查：{task.safety_check.passed ? "通过" : "未通过"}
              </span>
              {task.safety_check.issues.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {task.safety_check.issues.map((issue, i) => (
                    <li key={i} className="text-[9px] text-th-text-3">
                      · {issue}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Retry info */}
          {task.retry_at && (
            <p className="text-[9px] text-th-text-4">
              下次重试：{formatRelativeTime(task.retry_at)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="h-16 rounded-lg animate-shimmer bg-gradient-to-r from-th-card via-th-hover to-th-card bg-[length:200%_100%]" />
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

  // 🔄 Loading
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    );
  }

  // ❌ Error
  if (isError) {
    return (
      <div className="rounded-lg p-6 text-center bg-th-card border border-th-border-subtle">
        <AlertCircle size={28} className="mx-auto mb-2 text-th-danger" />
        <p className="text-xs font-medium mb-1 text-th-text">加载任务失败</p>
        <p className="text-[10px] mb-3 text-th-text-3">
          {error instanceof Error ? error.message : "请稍后重试"}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="px-3 py-1.5 rounded-lg text-[10px] font-medium hover:opacity-80 bg-th-accent-dim text-th-accent-text transition-colors"
        >
          重试
        </button>
      </div>
    );
  }

  // 📭 Empty
  if (!tasks || tasks.length === 0) {
    return (
      <div className="rounded-lg p-8 text-center bg-th-card border border-th-border-subtle">
        <Clock size={32} className="mx-auto mb-2 text-th-text-4" />
        <p className="text-sm font-medium text-th-text">暂无任务</p>
        <p className="text-xs mt-1 text-th-text-3">当有 Phase 4 任务时，将在此处显示</p>
      </div>
    );
  }

  // ✅ Success
  // Sort: running tasks first, then by created_at desc
  const sorted = [...tasks].sort((a, b) => {
    const aRunning = STATE_FLOW.includes(a.state);
    const bRunning = STATE_FLOW.includes(b.state);
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
