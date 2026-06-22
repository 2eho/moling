"use client";

import { useQuery } from "@tanstack/react-query";
import { getCardPool } from "@/lib/http/api";
import { useState } from "react";
import { Layers, AlertCircle, Sparkles, Archive, RefreshCw } from "lucide-react";
import type { CardPoolItem } from "@/lib/types/domain";
import { formatRelativeTime } from "@/lib/format";

interface CardManagerProps {
  projectId: string;
}

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  character: { label: "角色", color: "var(--th-accent-text)" },
  plot: { label: "剧情", color: "var(--th-success)" },
  dialogue: { label: "对话", color: "var(--th-warning)" },
  description: { label: "描写", color: "var(--th-logo-to)" },
};

const FRESHNESS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  new: { label: "新鲜", color: "var(--th-success)", bg: "rgba(52,211,153,0.12)" },
  active: { label: "活跃", color: "var(--th-accent-text)", bg: "var(--th-accent-dim)" },
  stale: { label: "陈旧", color: "var(--th-text-3)", bg: "var(--th-hover)" },
};

function CardItem({ card }: { card: CardPoolItem }) {
  const typeConfig = TYPE_CONFIG[card.type] ?? { label: card.type, color: "var(--th-text-3)" };
  const freshnessConfig = FRESHNESS_CONFIG[card.freshness_period] ?? FRESHNESS_CONFIG.active;

  return (
    <div
      role="listitem"
      className="rounded-lg p-3 border transition-all hover:translate-y-[-1px]"
      style={{
        background: "var(--th-card)",
        borderColor: card.retired ? "var(--th-border-subtle)" : "var(--th-border-subtle)",
        opacity: card.retired ? 0.6 : 1,
      }}
    >
      <div className="flex items-start gap-3">
        {/* Type icon */}
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: typeConfig.color + "15" }}
        >
          <Sparkles size={14} style={{ color: typeConfig.color }} />
        </div>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold" style={{ color: "var(--th-text)" }}>
              {card.content.slice(0, 40)}{card.content.length > 40 ? "..." : ""}
            </span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: typeConfig.color + "15", color: typeConfig.color }}
            >
              {typeConfig.label}
            </span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: freshnessConfig.bg, color: freshnessConfig.color }}
            >
              {freshnessConfig.label}
            </span>
            {card.retired && (
              <span
                className="text-[9px] px-1.5 py-0.5 rounded font-medium flex items-center gap-1"
                style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}
              >
                <Archive size={9} />
                已退役
              </span>
            )}
          </div>

          {/* Content preview */}
          <p className="text-[11px] leading-relaxed line-clamp-2" style={{ color: "var(--th-text-2)" }}>
            {card.content}
          </p>

          {/* Footer meta */}
          <div className="flex items-center gap-3 mt-1.5 text-[9px]" style={{ color: "var(--th-text-4)" }}>
            <span>{formatRelativeTime(card.created_at)}</span>
            {card.retired && card.retired_reason && (
              <span>退役原因：{card.retired_reason}</span>
            )}
            {card.retired && card.retired_chapter && (
              <span>退役章节：第 {card.retired_chapter} 章</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function CardManager({ projectId }: CardManagerProps) {
  const [retiredFilter, setRetiredFilter] = useState<string>("all");

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["card-pool", projectId, retiredFilter],
    queryFn: () =>
      getCardPool(projectId, {
        page: 1,
        page_size: 50,
        retired: retiredFilter === "all" ? undefined : retiredFilter,
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
        <p className="text-xs font-medium mb-1" style={{ color: "var(--th-text)" }}>加载卡牌池失败</p>
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

  const cards = data?.items ?? [];

  return (
    <div className="space-y-3">
      {/* Filter tabs */}
      <div className="flex items-center gap-2">
        <Layers size={12} style={{ color: "var(--th-text-3)" }} />
        {[
          { value: "all", label: "全部" },
          { value: "false", label: "活跃" },
          { value: "true", label: "已退役" },
        ].map((opt) => {
          const isActive = retiredFilter === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => setRetiredFilter(opt.value)}
              className="px-2.5 py-1 rounded text-[10px] font-medium transition-colors"
              style={{
                background: isActive ? "var(--th-accent-dim)" : "transparent",
                color: isActive ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              {opt.label}
            </button>
          );
        })}
        <div className="flex-1" />
        <button
          onClick={() => refetch()}
          className="p-1.5 rounded hover:opacity-80 transition-opacity"
          style={{ color: "var(--th-text-3)" }}
          title="刷新"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Content */}
      {cards.length === 0 ? (
        <div className="rounded-lg p-8 text-center" style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}>
          <Layers size={32} className="mx-auto mb-2" style={{ color: "var(--th-text-4)" }} />
          <p className="text-xs font-medium" style={{ color: "var(--th-text)" }}>
            {retiredFilter !== "all" ? "该筛选条件下无卡牌" : "暂无卡牌"}
          </p>
          <p className="text-[10px] mt-1" style={{ color: "var(--th-text-3)" }}>
            AI 生成的写作建议将显示为卡牌
          </p>
        </div>
      ) : (
        <div role="list" className="space-y-2">
          {cards.map((card) => (
            <CardItem key={card.id} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}
