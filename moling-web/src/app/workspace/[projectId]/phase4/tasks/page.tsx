"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { phase4Api } from "@/lib/api";
import { Phase4State } from "@/lib/types";
import type { Phase4TaskStatus } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import styles from "@/components/phase4/Phase4TaskPanel.module.css";

/* ── 过滤选项 ── */

type FilterType = "all" | "running" | "done" | "failed";

const FILTER_OPTIONS: { key: FilterType; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "running", label: "进行中" },
  { key: "done", label: "已完成" },
  { key: "failed", label: "失败" },
];

const RUNNING_STATES = new Set([
  Phase4State.QUEUED,
  Phase4State.LOCKING,
  Phase4State.EXTRACTING,
  Phase4State.VERIFYING,
  Phase4State.MERGING,
  Phase4State.COMMITTING,
  Phase4State.RETRY,
]);

const PAGE_SIZE = 20;

/* ── Helpers ── */

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

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(createdAt: string, updatedAt?: string): string {
  const start = new Date(createdAt).getTime();
  const end = updatedAt ? new Date(updatedAt).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 1000) return "<1s";
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  return `${mins}m ${secs % 60}s`;
}

function applyFilter(tasks: Phase4TaskStatus[], filter: FilterType): Phase4TaskStatus[] {
  switch (filter) {
    case "running":
      return tasks.filter((t) => RUNNING_STATES.has(t.state));
    case "done":
      return tasks.filter((t) => t.state === Phase4State.DONE);
    case "failed":
      return tasks.filter((t) => t.state === Phase4State.FAILED);
    default:
      return tasks;
  }
}

/* ── Page Component ── */

function TaskHistoryContent({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [allTasks, setAllTasks] = useState<Phase4TaskStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [page, setPage] = useState(1);

  const fetchAllTasks = useCallback(async () => {
    try {
      setError(null);
      const res = await phase4Api.getProjectTasks(projectId);
      setAllTasks(res.data ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "获取任务列表失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchAllTasks();
  }, [fetchAllTasks]);

  // 过滤 + 排序
  const filteredTasks = applyFilter(allTasks, filter).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );

  // 分页
  const totalPages = Math.max(1, Math.ceil(filteredTasks.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageTasks = filteredTasks.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  // 统计
  const totalCount = allTasks.length;
  const doneCount = allTasks.filter((t) => t.state === Phase4State.DONE).length;
  const failedCount = allTasks.filter((t) => t.state === Phase4State.FAILED).length;
  const runningCount = allTasks.filter((t) => RUNNING_STATES.has(t.state)).length;

  // 切换过滤器时重置页数
  const handleFilterChange = (f: FilterType) => {
    setFilter(f);
    setPage(1);
  };

  const handleBack = () => {
    router.push(`/workspace/${projectId}`);
  };

  return (
    <div className={styles.pageContainer}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <button
          onClick={handleBack}
          style={{
            fontSize: "var(--font-size-sm)",
            color: "var(--color-text-tertiary)",
            marginBottom: "var(--space-3)",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          ← 返回工作台
        </button>
        <h1 className={styles.pageTitle}>Phase 4 任务历史</h1>
        <p className={styles.pageSubtitle}>
          查看和管理所有 Phase 4 自动处理任务
        </p>
      </div>

      {/* Stats */}
      <div className={styles.statsBar}>
        <div className={styles.statCard}>
          <div className={styles.statValue} style={{ color: "var(--color-text-primary)" }}>
            {totalCount}
          </div>
          <div className={styles.statLabel}>总任务</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue} style={{ color: "#3b82f6" }}>
            {runningCount}
          </div>
          <div className={styles.statLabel}>进行中</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue} style={{ color: "#22c55e" }}>
            {doneCount}
          </div>
          <div className={styles.statLabel}>已完成</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue} style={{ color: "#ef4444" }}>
            {failedCount}
          </div>
          <div className={styles.statLabel}>失败</div>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            className={`${styles.filterBtn} ${filter === opt.key ? styles.filterBtnActive : ""}`}
            onClick={() => handleFilterChange(opt.key)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className={styles.skeletonWrapper}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div className={styles.skeletonRow} key={i}>
              <div className={styles.skeletonDot} />
              <div className={styles.skeletonLines}>
                <Skeleton width="70%" height={14} />
                <Skeleton width="50%" height={10} />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className={styles.errorWrapper}>
          <EmptyState
            icon="⚠️"
            title="加载失败"
            description={error}
            action={{ label: "重试", onClick: fetchAllTasks }}
          />
        </div>
      ) : pageTasks.length === 0 ? (
        <EmptyState
          icon="📋"
          title="暂无任务"
          description={
            filter === "all"
              ? "Phase 4 任务将在生成章节时自动创建"
              : "没有匹配当前过滤条件的任务"
          }
        />
      ) : (
        <>
          {pageTasks.map((task) => {
            const isFailed = task.state === Phase4State.FAILED;
            return (
              <div
                key={task.id}
                className={`${styles.taskDetailCard} ${
                  isFailed ? styles.taskCardFailed : ""
                }`}
              >
                <div className={styles.taskDetailHeader}>
                  <span className={styles.taskDetailId}>#{shortId(task.id)}</span>
                  <span
                    className={`${styles.taskDetailStatus} ${STATE_TEXT_CSS[task.state]}`}
                  >
                    {STATE_LABELS[task.state]}
                  </span>
                </div>
                <div className={styles.taskDetailBody}>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>任务 ID</span>
                    <span className={styles.taskDetailValue}>{task.id}</span>
                  </div>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>章节 ID</span>
                    <span className={styles.taskDetailValue}>{shortId(task.chapterId)}</span>
                  </div>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>创建时间</span>
                    <span className={styles.taskDetailValue}>
                      {formatDateTime(task.createdAt)}
                    </span>
                  </div>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>耗时</span>
                    <span className={styles.taskDetailValue}>
                      {formatDuration(task.createdAt, task.updatedAt)}
                    </span>
                  </div>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>状态</span>
                    <span className={styles.taskDetailValue}>
                      {STATE_LABELS[task.state]}
                    </span>
                  </div>
                  <div className={styles.taskDetailField}>
                    <span className={styles.taskDetailLabel}>重试次数</span>
                    <span className={styles.taskDetailValue}>{task.retryCount}</span>
                  </div>
                  {task.lastError && (
                    <div
                      className={styles.taskDetailField}
                      style={{ gridColumn: "1 / -1" }}
                    >
                      <span className={styles.taskDetailLabel}>错误信息</span>
                      <span
                        className={styles.taskDetailValue}
                        style={{ color: "var(--color-danger)" }}
                      >
                        {task.lastError}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={`${styles.pageBtn} ${safePage <= 1 ? styles.pageBtnDisabled : ""}`}
                onClick={() => setPage(safePage - 1)}
                disabled={safePage <= 1}
              >
                ←
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  className={`${styles.pageBtn} ${p === safePage ? styles.pageBtnActive : ""}`}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              ))}
              <button
                className={`${styles.pageBtn} ${safePage >= totalPages ? styles.pageBtnDisabled : ""}`}
                onClick={() => setPage(safePage + 1)}
                disabled={safePage >= totalPages}
              >
                →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function shortId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) + "..." : id;
}

export default function Phase4TasksPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  return (
    <WorkspaceProvider projectId={projectId}>
      <TaskHistoryContent projectId={projectId} />
    </WorkspaceProvider>
  );
}
