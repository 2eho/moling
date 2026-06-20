"use client";

import { useQuery } from "@tanstack/react-query";
import { getVaultCharacters } from "@/lib/http/api";
import { useState } from "react";
import { Search, Users, AlertCircle, Loader2 } from "lucide-react";
import type { VaultCharacter } from "@/lib/types/domain";

interface CharacterLibraryProps {
  projectId: string;
}

const ROLE_CONFIG: Record<string, { label: string; color: string }> = {
  protagonist: { label: "主角", color: "var(--th-accent-text)" },
  supporting: { label: "配角", color: "var(--th-success)" },
  antagonist: { label: "反派", color: "var(--th-danger)" },
  minor: { label: "龙套", color: "var(--th-text-3)" },
};

function CharacterCard({ character }: { character: VaultCharacter }) {
  const roleConfig = ROLE_CONFIG[character.role] ?? ROLE_CONFIG.minor;

  return (
    <div
      className="rounded-lg p-3 border transition-all hover:translate-y-[-1px]"
      style={{
        background: "var(--th-card)",
        borderColor: "var(--th-border-subtle)",
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{ background: roleConfig.color + "20", color: roleConfig.color }}
          >
            {character.name.charAt(0)}
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-semibold truncate" style={{ color: "var(--th-text)" }}>
              {character.name}
            </h4>
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: roleConfig.color + "15", color: roleConfig.color }}
            >
              {roleConfig.label}
            </span>
          </div>
        </div>
      </div>

      <p className="text-[11px] leading-relaxed mb-2 line-clamp-2" style={{ color: "var(--th-text-2)" }}>
        {character.description}
      </p>

      <p className="text-[10px]" style={{ color: "var(--th-text-3)" }}>
        人物弧光：{character.arc}
      </p>

      {character.traits.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {character.traits.map((trait, i) => (
            <span
              key={i}
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{ background: "var(--th-hover)", color: "var(--th-text-3)" }}
            >
              {trait}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function CharacterLibrary({ projectId }: CharacterLibraryProps) {
  const [search, setSearch] = useState("");

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["vault-characters", projectId, search],
    queryFn: () => getVaultCharacters(projectId, { page: 1, page_size: 50, search: search || undefined }),
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
        <p className="text-xs font-medium mb-1" style={{ color: "var(--th-text)" }}>加载角色库失败</p>
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

  const characters = data?.items ?? [];

  return (
    <div className="space-y-3">
      {/* Search */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-lg border"
        style={{ background: "var(--th-input)", borderColor: "var(--th-border-subtle)" }}
      >
        <Search size={14} style={{ color: "var(--th-text-3)" }} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索角色..."
          className="flex-1 bg-transparent text-xs outline-none"
          style={{ color: "var(--th-text)", placeholderColor: "var(--th-text-4)" }}
        />
        {characters.length > 0 && (
          <span className="text-[10px]" style={{ color: "var(--th-text-4)" }}>
            {characters.length}
          </span>
        )}
      </div>

      {/* Content */}
      {characters.length === 0 ? (
        <div className="rounded-lg p-8 text-center" style={{ background: "var(--th-card)", border: "1px solid var(--th-border-subtle)" }}>
          <Users size={32} className="mx-auto mb-2" style={{ color: "var(--th-text-4)" }} />
          <p className="text-xs font-medium" style={{ color: "var(--th-text)" }}>
            {search ? "未找到匹配角色" : "暂无角色"}
          </p>
          <p className="text-[10px] mt-1" style={{ color: "var(--th-text-3)" }}>
            {search ? "尝试其他搜索词" : "在写作中创建角色后将会出现在这里"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {characters.map((char) => (
            <CharacterCard key={char.id} character={char} />
          ))}
        </div>
      )}
    </div>
  );
}
