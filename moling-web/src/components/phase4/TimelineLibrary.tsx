"use client";

import { useQuery } from "@tanstack/react-query";
import { getVaultTimeline } from "@/lib/http/api";
import { Clock, AlertCircle, CalendarDays } from "lucide-react";
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
      className="rounded-lg p-3 border transition-all hover:translate-y-[-1px]"
      style={{
        background: "var(--th-card)",
        borderColor: "var(--th-border-subtle)",
        borderLeft: `3px solid ${typeConfig.color}`,
      }}
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
            <span className="text-xs font-semibold" style={{ color: "var(--th-text)" }}>
              {item.title}
            </span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: typeConfig.color + "15", color: typeConfig.color }}
            >
              {typeConfig.label}
            </span>
          </div>

          <p className="text-[11px] leading-relaxed mb-1" style={{ color: "var(--th-text-2)" }}>
            {item.description}
          </p>

          <div className="flex items-center gap-3 text-[10px]" style={{ color: "var(--th-text-3)" }}>
            <span className="flex items-center gap-1">
              <Clock size={10} />
              第 {item.chapter} 章
            </span>
            <span>{item.date_label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TimelineLibrary({ projectId }: TimelineLibraryProps) {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["vault-timeline", projectId],
    queryFn: () => getVaultTimeline(projectId, { page: 1, page_size: 50 }),
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
        <p className="text-xs font-medium mb-1" style={{ color: "var(--th-text)" }}>加载时间线失败</p>
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

  if (items.length === 0) {
    return (
      <div className="rounded-lg p-8 text-center" style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}>
        <CalendarDays size={32} className="mx-auto mb-2" style={{ color: "var(--th-text-4)" }} />
        <p className="text-xs font-medium" style={{ color: "var(--th-text)" }}>暂无时间线</p>
        <p className="text-[10px] mt-1" style={{ color: "var(--th-text-3)" }}>
          写作过程中将自动记录时间线事件
        </p>
      </div>
    );
  }

  // Sort by chapter
  const sorted = [...items].sort((a, b) => a.chapter - b.chapter);

  return (
    <div className="space-y-2">
      {sorted.map((item) => (
        <TimelineItem key={item.id} item={item} />
      ))}
    </div>
  );
}
