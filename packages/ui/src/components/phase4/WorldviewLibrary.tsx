"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Filter, Globe } from "lucide-react";
import { useState } from "react";
import { getVaultWorldview } from "@/lib/http/api";
import type { VaultWorldview as VaultWorldviewType } from "@/lib/types/domain";

interface WorldviewLibraryProps {
  projectId: string;
}

const CATEGORY_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  geography: { label: "地理", color: "var(--th-success)", icon: "🏔" },
  history: { label: "历史", color: "var(--th-warning)", icon: "📜" },
  system: { label: "体系", color: "var(--th-accent-text)", icon: "⚙" },
  faction: { label: "势力", color: "var(--th-danger)", icon: "⚔" },
  event: { label: "事件", color: "var(--th-logo-to)", icon: "💥" },
};

function WorldviewCard({ item }: { item: VaultWorldviewType }) {
  const catConfig = CATEGORY_CONFIG[item.category] ?? {
    label: item.category,
    color: "var(--th-text-3)",
    icon: "📋",
  };

  return (
    <div
      role="listitem"
      className="rounded-lg p-3 border border-th-border-subtle bg-th-card transition-all hover:translate-y-[-1px]"
    >
      <div className="flex items-start gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-base"
          style={{ background: catConfig.color + "15" }}
        >
          {catConfig.icon}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-th-text">{item.name}</span>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: catConfig.color + "15", color: catConfig.color }}
            >
              {catConfig.label}
            </span>
          </div>

          <p className="text-[11px] leading-relaxed mb-1 text-th-text-2">{item.description}</p>

          <p className="text-[10px] text-th-text-3">{item.details}</p>
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

export function WorldviewLibrary({ projectId }: WorldviewLibraryProps) {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["vault-worldview", projectId, categoryFilter],
    queryFn: () =>
      getVaultWorldview(projectId, {
        page: 1,
        page_size: 50,
        category: categoryFilter === "all" ? undefined : categoryFilter,
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
        <p className="text-xs font-medium mb-1 text-th-text">加载世界观库失败</p>
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
      {/* Category filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={12} className="text-th-text-3" />
        {["all", ...Object.keys(CATEGORY_CONFIG)].map((cat) => {
          const config = CATEGORY_CONFIG[cat];
          const isActive = categoryFilter === cat;
          return (
            <button
              type="button"
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className="px-2 py-1 rounded text-[10px] font-medium transition-colors"
              style={{
                background: isActive
                  ? (config?.color ?? "var(--th-accent-text)") + "20"
                  : "transparent",
                color: isActive ? (config?.color ?? "var(--th-accent-text)") : "var(--th-text-3)",
              }}
            >
              {cat === "all" ? "全部" : (config?.label ?? cat)}
            </button>
          );
        })}
      </div>

      {/* 📭 Empty */}
      {items.length === 0 ? (
        <div className="rounded-lg p-8 text-center bg-th-card border border-th-border-subtle">
          <Globe size={32} className="mx-auto mb-2 text-th-text-4" />
          <p className="text-xs font-medium text-th-text">
            {categoryFilter !== "all" ? "该分类下无条目" : "暂无世界观"}
          </p>
          <p className="text-[10px] mt-1 text-th-text-3">世界观信息将在此处展示</p>
        </div>
      ) : (
        <div role="list" className="space-y-2">
          {items.map((item) => (
            <WorldviewCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
