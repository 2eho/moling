"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CalendarDays, Clock } from "lucide-react";
import { getVaultTimeline } from "@/lib/http/api";
import type { VaultTimeline as VaultTimelineType } from "@/lib/types/domain";

interface TimelineLibraryProps {
  projectId: string;
}

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  plot: { label: "剧情", color: "var(--th-accent-text)" },
  character: { label: "人物", color: "var(--th-success)" },
  event: { label: "事件", color: "var(--th-warning)" },
  world: { label: "世界", color: "var(--th-logo-to)" },
};

function TimelineItem({ item }: { item: VaultTimelineType }) {
  const typeConfig = TYPE_CONFIG[item.type] ?? { label: item.type, color: "var(--th-text-3)" };

  return (
    <div
      role="listitem"
      className="rounded-lg p-3 border border-th-border-subtle bg-th-card transition-all hover:translate-y-[-1px]"
      style={{ borderLeft: `3px solid ${typeConfig.color}` }}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5"
          style={{ background: typeConfig.color + "15" }}
        >
          <CalendarDays size={14} style={{ color: typeConfig.color }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-th-text">{item.title}</span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: typeConfig.color + "15", color: typeConfig.color }}
            >
              {typeConfig.label}
            </span>
          </div>

          <p className="text-[11px] leading-relaxed mb-1 text-th-text-2">{item.description}</p>

          <div className="flex items-center gap-3 text-[10px] text-th-text-3">
            <span className="flex items-center gap-1">
              <Clock size={10} />第 {item.chapter} 章
            </span>
            <span>{item.date_label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <div className="h-20 rounded-lg animate-shimmer bg-gradient-to-r from-th-card via-th-hover to-th-card bg-[length:200%_100%]" />
  );
}

export function TimelineLibrary({ projectId }: TimelineLibraryProps) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["vault-timeline", projectId],
    queryFn: () => getVaultTimeline(projectId, { page: 1, page_size: 50 }),
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
        <p className="text-xs font-medium mb-1 text-th-text">加载时间线失败</p>
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

  // 📭 Empty
  if (items.length === 0) {
    return (
      <div className="rounded-lg p-8 text-center bg-th-card border border-th-border-subtle">
        <CalendarDays size={32} className="mx-auto mb-2 text-th-text-4" />
        <p className="text-xs font-medium text-th-text">暂无时间线</p>
        <p className="text-[10px] mt-1 text-th-text-3">写作过程中将自动记录时间线事件</p>
      </div>
    );
  }

  // Sort by chapter
  const sorted = [...items].sort((a, b) => a.chapter - b.chapter);

  return (
    <div role="list" className="space-y-2">
      {sorted.map((item) => (
        <TimelineItem key={item.id} item={item} />
      ))}
    </div>
  );
}
