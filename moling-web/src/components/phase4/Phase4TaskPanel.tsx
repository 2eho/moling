"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { phase4Api } from "@/lib/api";
import { Phase4State } from "@/lib/types";
import type { Phase4TaskStatus } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import styles from "./Phase4TaskPanel.module.css";

/* ── State Machine 配置 ── */

const STATE_FLOW: Phase4State[] = [
  Phase4State.IDLE,
  Phase4State.QUEUED,
  Phase4State.LOCKING,
  Phase4State.EXTRACTING,
  Phase4State.VERIFYING,
  Phase4State.MERGING,
  Phase4State.COMMITTING,
  Phase4State.DONE,
];

const STATE_LABELS: Record<Phase4State, string> = {
  [Phase4State.IDLE]: "空闲",
  [Phase4State.QUEUED]: "排队中",
  [Phase4State.LOCKING]: "锁定中",
  [Phase4State.EXTRACTING]: "提取中",
  [Phase4State.VERIFYING]: "验证中",
  [Phase4State.MERGING]: "合并中",
  [Phase4State.COMMITTING]: "提交中",
  [Phase4State.DONE]: "完成",
  [Phase4State.FAILED]: "失败",
  [Phase4State.RETRY]: "重试",
};

const TERMINAL_STATES = new Set([Phase4State.DONE, Phase4State.FAILED]);
const ERROR_STATES = new Set([Phase4State.FAILED, Phase4State.RETRY]);

const STATE_CSS_CLASS: Record<Phase4State, string> = {
  [Phase4State.IDLE]: styles.stateIdle,
  [Phase4State.QUEUED]: styles.stateQueued,
  [Phase4State.LOCKING]: styles.stateLocking,
  [Phase4State.EXTRACTING]: styles.stateExtracting,
  [Phase4State.VERIFYING]: styles.stateVerifying,
  [Phase4State.MERGING]: styles.stateMerging,
  [Phase4State.COMMITTING]: styles.stateCommitting,
  [Phase4State.DONE]: styles.stateDone,
  [Phase4State.FAILED]: styles.stateFailed,
  [Phase4State.RETRY]: styles.stateRetry,
};

const STATE_TEXT_CSS: Record<Phase4State, string> = {
  [Phase4State.IDLE]: styles.textIdle,
  [Phase4State.QUEUED]: styles.textQueued,
  [Phase4State.LOCKING]: styles.textLocking,
  [Phase4State.EXTRACTING]: styles.textExtracting,
  [Phase4State.VERIFYING]: styles.textVerifying,
  [Phase4State.MERGING]: styles.textMerging,
  [Phase4State.COMMITTING]: styles.textCommitting,
  [Phase4State.DONE]: styles.textDone,
  [Phase4State.FAILED]: styles.textFailed,
  [Phase4State.RETRY]: styles.textRetry,
};

/* ── Helpers ── */

function getStateIndex(state: Phase4State): number {
  return STATE_FLOW.indexOf(state);
}

function formatDuration(createdAt: string, updatedAt?: string): string {
  const start = new Date(createdAt).getTime();
  const end = updatedAt ? new Date(updatedAt).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 1000) return "0s";
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  return `${mins}m ${secs % 60}s`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function shortId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) + "..." : id;
}

/* ── Props ── */

interface Phase4TaskPanelProps {
  projectId: string;
  maxTasks?: number;
}

/* ── Component ── */

export function Phase4TaskPanel({ projectId, maxTasks = 5 }: Phase4TaskPanelProps) {
  const router = useRouter();
  const [tasks, setTasks] = useState<Phase4TaskStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<Set<string>>(new Set());
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const fetchTasks = useCallback(async () => {
    try {
      setError(null);
      const res = await phase4Api.getProjectTasks(projectId);
      if (mountedRef.current) {
        setTasks(res.data ?? []);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : "获取任务列表失败");
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId]);

  // 初始加载 + 每 5 秒轮询
  useEffect(() => {
    mountedRef.current = true;
    fetchTasks();
    pollingRef.current = setInterval(fetchTasks, 5000);
    return () => {
      mountedRef.current = false;
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [fetchTasks]);

  const handleRetry = async (taskId: string) => {
    if (retrying.has(taskId)) return;
    setRetrying((prev) => new Set(prev).add(taskId));
    try {
      await phase4Api.retryTask(taskId);
      await fetchTasks();
    } catch {
      // silent
    } finally {
      setRetrying((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  const handleViewAll = () => {
    router.push(`/workspace/${projectId}/phase4/tasks`);
  };

  /* ── 当前活动任务：非终态的最新任务 ── */
  const activeTask = tasks.find((t) => !TERMINAL_STATES.has(t.state));

  /* ── 最近任务（最多 maxTasks 条，按时间倒序） ── */
  const recentTasks = [...tasks]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, maxTasks);

  /* ── Loading State ── */
  if (loading) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <span className={styles.title}>Phase 4 任务状态</span>
        </div>
        <div className={styles.skeletonWrapper}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div className={styles.skeletonRow} key={i}>
              <div className={styles.skeletonDot} />
              <div className={styles.skeletonLines}>
                <Skeleton width="60%" height={12} />
                <Skeleton width="40%" height={10} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  /* ── Error State ── */
  if (error && tasks.length === 0) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <span className={styles.title}>Phase 4 任务状态</span>
        </div>
        <div className={styles.errorWrapper}>
          <EmptyState
            icon="⚠️"
            title="加载失败"
            description={error}
            action={{ label: "重试", onClick: fetchTasks }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>
          Phase 4 任务状态
          <span
            className={`${styles.titleDot} ${activeTask ? styles.titleDotActive : ""}`}
          />
        </span>
        <button
          className={styles.refreshBtn}
          onClick={fetchTasks}
          title="刷新"
          aria-label="刷新"
        >
          ↻
        </button>
      </div>

      {/* State Machine Flow */}
      <div className={styles.flowSection}>
        <div className={styles.flowLabel}>状态机流转</div>
        <div className={styles.flowContainer}>
          {STATE_FLOW.map((state, idx) => {
            const isActive = activeTask?.state === state;
            const isDone = activeTask
              ? getStateIndex(state) < getStateIndex(activeTask.state)
              : false;
            const dotClass = isActive
              ? `${styles.flowDot} ${styles.flowDotActive} ${STATE_CSS_CLASS[state]}`
              : isDone
                ? `${styles.flowDot} ${styles.flowDotDone} ${STATE_CSS_CLASS[state]}`
                : styles.flowDot;

            const labelClass = isActive
              ? `${styles.flowNodeLabel} ${styles.flowNodeLabelActive}`
              : styles.flowNodeLabel;

            return (
              <div key={state} className={styles.flowNode}>
                <div className={dotClass}>
                  {isDone || state === Phase4State.DONE ? "✓" : isActive ? "●" : ""}
                </div>
                <span className={labelClass}>{STATE_LABELS[state]}</span>
                {idx < STATE_FLOW.length - 1 && (
                  <div
                    className={`${styles.flowArrow} ${
                      activeTask && idx < getStateIndex(activeTask.state)
                        ? styles.flowArrowActive
                        : ""
                    }`}
                  />
                )}
              </div>
            );
          })}

          {/* 错误/重试节点 */}
          {(activeTask?.state === Phase4State.FAILED ||
            activeTask?.state === Phase4State.RETRY) && (
            <>
              <div className={styles.flowArrow} />
              <div className={styles.flowNode}>
                <div
                  className={`${styles.flowDot} ${styles.flowDotFailed} ${
                    STATE_CSS_CLASS[activeTask.state]
                  }`}
                >
                  ✕
                </div>
                <span className={styles.flowNodeLabel}>
                  {STATE_LABELS[activeTask.state]}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recent Tasks */}
      <div className={styles.taskListSection}>
        <div className={styles.taskListHeader}>
          <span className={styles.taskListTitle}>
            最近任务
            <span className={styles.taskCount}>{tasks.length}</span>
          </span>
          <span className={styles.viewAllLink} onClick={handleViewAll} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && handleViewAll()}>
            查看全部
          </span>
        </div>

        {recentTasks.length === 0 ? (
          <div className={styles.emptyWrapper}>
            <EmptyState
              icon="📋"
              title="暂无任务"
              description="Phase 4 任务将在生成章节时自动创建"
            />
          </div>
        ) : (
          recentTasks.map((task) => {
            const isFailed = task.state === Phase4State.FAILED;
            const isRetry = task.state === Phase4State.RETRY;
            const isRetrying = retrying.has(task.id);

            return (
              <div
                key={task.id}
                className={`${styles.taskCard} ${
                  isFailed || isRetry ? styles.taskCardFailed : ""
                }`}
                onClick={() => router.push(`/workspace/${projectId}/phase4/tasks`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && router.push(`/workspace/${projectId}/phase4/tasks`)}
              >
                <div
                  className={`${styles.taskStatusBadge} ${
                    task.state === Phase4State.FAILED
                      ? styles.stateFailed
                      : task.state === Phase4State.RETRY
                        ? styles.stateRetry
                        : STATE_CSS_CLASS[task.state]
                  }`}
                />
                <div className={styles.taskInfo}>
                  <span className={styles.taskId}>{shortId(task.id)}</span>
                  <div className={styles.taskMeta}>
                    <span className={styles.taskMetaItem}>
                      {formatTime(task.createdAt)}
                    </span>
                    <span className={styles.taskMetaItem}>
                      耗时 {formatDuration(task.createdAt, task.updatedAt)}
                    </span>
                    {task.retryCount > 0 && (
                      <span className={styles.taskMetaItem}>
                        重试 {task.retryCount} 次
                      </span>
                    )}
                  </div>
                  {isFailed && task.lastError && (
                    <div className={styles.taskErrorSection}>
                      <span className={styles.taskErrorText}>
                        {task.lastError}
                      </span>
                    </div>
                  )}
                </div>
                <span
                  className={`${styles.taskStatusText} ${STATE_TEXT_CSS[task.state]}`}
                >
                  {STATE_LABELS[task.state]}
                </span>
                {(isFailed || isRetry) && (
                  <button
                    className={styles.retryBtn}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRetry(task.id);
                    }}
                    disabled={isRetrying}
                  >
                    {isRetrying ? "..." : "重试"}
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
