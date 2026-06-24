"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Eye, Filter } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { getVaultForeshadowing } from "@/lib/http/api";
import type { VaultForeshadowing } from "@/lib/types/domain";

interface ForeshadowingLibraryProps {
  projectId: string;
}

/** Status → Tailwind class mapping (theme-safe across all 8 themes) */
const STATUS_STYLES: Record<string, { label: string; text: string; bg: string }> = {
  active: { label: "活跃", text: "text-th-accent-text", bg: "bg-th-accent-dim" },
  redeemed: { label: "已兑现", text: "text-th-success", bg: "bg-th-success/12" },
  canceled: { label: "已取消", text: "text-th-text-4", bg: "bg-th-hover" },
  planted: { label: "已埋设", text: "text-th-accent-text", bg: "bg-th-accent-dim" },
  resolved: { label: "已回收", text: "text-th-success", bg: "bg-th-success/12" },
};

function ForeshadowingCard({ item }: { item: VaultForeshadowing }) {
  const statusStyles = STATUS_STYLES[item.status] ?? STATUS_STYLES.active;

  return (
    <div
      role="listitem"
      className="rounded-lg p-3 border border-th-border-subtle bg-th-card transition-all hover:translate-y-[-1px]"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Eye size={14} className={statusStyles.text} />
          <span
            className={cn(
              "text-[9px] px-1.5 py-0.5 rounded font-medium",
              statusStyles.bg,
              statusStyles.text,
            )}
          >
            {statusStyles.label}
          </span>
        </div>
      </div>

      <p className="text-[11px] leading-relaxed mb-2 text-th-text-2">{item.description}</p>

      <div className="flex items-center gap-3 text-[10px] text-th-text-3">
        <span>埋设于第 {item.chapter_planted} 章</span>
        {item.chapter_redeemed && <span>· 兑现于第 {item.chapter_redeemed} 章</span>}
      </div>

      {item.target_description && (
        <p className="text-[10px] mt-1 italic text-th-text-4">目标：{item.target_description}</p>
      )}
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="h-20 rounded-lg animate-shimmer bg-gradient-to-r from-th-card via-th-hover to-th-card bg-[length:200%_100%]" />
  );
}

export function ForeshadowingLibrary({ projectId }: ForeshadowingLibraryProps) {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["vault-foreshadowing", projectId, statusFilter],
    queryFn: () =>
      getVaultForeshadowing(projectId, {
        page: 1,
        page_size: 50,
        status: statusFilter === "all" ? undefined : statusFilter,
      }),
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
        <p className="text-xs font-medium mb-1 text-th-text">加载承诺库失败</p>
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

  const items = data?.items ?? [];

  return (
    <div className="space-y-3">
      {/* Status filter */}
      <div className="flex items-center gap-2">
        <Filter size={12} className="text-th-text-3" />
        {["all", "active", "redeemed", "canceled"].map((status) => {
          const config = STATUS_STYLES[status];
          const isActive = statusFilter === status;
          return (
            <button
              type="button"
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                "px-2 py-1 rounded text-[10px] font-medium transition-colors",
                isActive
                  ? cn(config?.bg ?? "bg-th-accent-dim", config?.text ?? "text-th-accent-text")
                  : "text-th-text-3",
              )}
            >
              {status === "all" ? "全部" : (config?.label ?? status)}
            </button>
          );
        })}
      </div>

      {/* 📭 Empty */}
      {items.length === 0 ? (
        <div className="rounded-lg p-8 text-center bg-th-card border border-th-border-subtle">
          <Eye size={32} className="mx-auto mb-2 text-th-text-4" />
          <p className="text-xs font-medium text-th-text">
            {statusFilter !== "all" ? "该筛选条件下无承诺" : "暂无情节承诺"}
          </p>
          <p className="text-[10px] mt-1 text-th-text-3">伏笔和情节承诺将在此处显示</p>
        </div>
      ) : (
        <div role="list" className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {items.map((item) => (
            <ForeshadowingCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
