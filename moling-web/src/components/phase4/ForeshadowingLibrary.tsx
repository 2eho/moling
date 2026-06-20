"use client";

import { useQuery } from "@tanstack/react-query";
import { getVaultForeshadowing } from "@/lib/http/api";
import { useState } from "react";
import { Eye, AlertCircle, CheckCircle2, XCircle, Filter } from "lucide-react";
import type { VaultForeshadowing } from "@/lib/types/domain";

interface ForeshadowingLibraryProps {
  projectId: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: "活跃", color: "var(--th-accent-text)", bg: "var(--th-accent-dim)" },
  redeemed: { label: "已兑现", color: "var(--th-success)", bg: "rgba(52,211,153,0.12)" },
  canceled: { label: "已取消", color: "var(--th-text-4)", bg: "var(--th-hover)" },
};

function ForeshadowingCard({ item }: { item: VaultForeshadowing }) {
  const statusConfig = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.active;

  return (
    <div
      className="rounded-lg p-3 border transition-all hover:translate-y-[-1px]"
      style={{
        background: "var(--th-card)",
        borderColor: "var(--th-border-subtle)",
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Eye size={14} style={{ color: statusConfig.color }} />
          <span
            className="text-[9px] px-1.5 py-0.5 rounded font-medium"
            style={{ background: statusConfig.bg, color: statusConfig.color }}
          >
            {statusConfig.label}
          </span>
        </div>
      </div>

      <p className="text-[11px] leading-relaxed mb-2" style={{ color: "var(--th-text-2)" }}>
        {item.description}
      </p>

      <div className="flex items-center gap-3 text-[10px]" style={{ color: "var(--th-text-3)" }}>
        <span>埋设于第 {item.chapter_planted} 章</span>
        {item.chapter_redeemed && <span>· 兑现于第 {item.chapter_redeemed} 章</span>}
      </div>

      {item.target_description && (
        <p className="text-[10px] mt-1 italic" style={{ color: "var(--th-text-4)" }}>
          目标：{item.target_description}
        </p>
      )}
    </div>
  );
}

export function ForeshadowingLibrary({ projectId }: ForeshadowingLibraryProps) {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["vault-foreshadowing", projectId, statusFilter],
    queryFn: () =>
      getVaultForeshadowing(projectId, {
        page: 1,
        page_size: 50,
        status: statusFilter === "all" ? undefined : statusFilter,
      }),
  });

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-20 rounded-lg animate-shimmer"
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
      <div className="rounded-lg p-6 text-center" style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}>
        <AlertCircle size={28} className="mx-auto mb-2" style={{ color: "var(--th-danger)" }} />
        <p className="text-xs font-medium mb-1" style={{ color: "var(--th-text)" }}>加载承诺库失败</p>
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

  const items = data?.items ?? [];

  return (
    <div className="space-y-3">
      {/* Status filter */}
      <div className="flex items-center gap-2">
        <Filter size={12} style={{ color: "var(--th-text-3)" }} />
        {["all", "active", "redeemed", "canceled"].map((status) => {
          const config = STATUS_CONFIG[status];
          const isActive = statusFilter === status;
          return (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className="px-2 py-1 rounded text-[10px] font-medium transition-colors"
              style={{
                background: isActive ? (config?.bg ?? "var(--th-accent-dim)") : "transparent",
                color: isActive ? (config?.color ?? "var(--th-accent-text)") : "var(--th-text-3)",
              }}
            >
              {status === "all" ? "全部" : config?.label ?? status}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {items.length === 0 ? (
        <div className="rounded-lg p-8 text-center" style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}>
          <Eye size={32} className="mx-auto mb-2" style={{ color: "var(--th-text-4)" }} />
          <p className="text-xs font-medium" style={{ color: "var(--th-text)" }}>
            {statusFilter !== "all" ? "该筛选条件下无承诺" : "暂无情节承诺"}
          </p>
          <p className="text-[10px] mt-1" style={{ color: "var(--th-text-3)" }}>
            伏笔和情节承诺将在此处显示
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {items.map((item) => (
            <ForeshadowingCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
