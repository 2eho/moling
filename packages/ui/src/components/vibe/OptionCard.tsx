"use client";

import { Sparkles } from "lucide-react";
import type { Option } from "@/stores/useWritingStore";

interface Props {
  option: Option;
  isSelected: boolean;
  onSelect: (id: string) => void;
}

const OPT_VARS = {
  A: { dim: "var(--th-opt-a-dim)", text: "var(--th-opt-a-text)", border: "var(--th-opt-a-border)" },
  B: { dim: "var(--th-opt-b-dim)", text: "var(--th-opt-b-text)", border: "var(--th-opt-b-border)" },
  C: { dim: "var(--th-opt-c-dim)", text: "var(--th-opt-c-text)", border: "var(--th-opt-c-border)" },
} as const;

const AGENT_LABELS: Record<string, string> = {
  plot: "剧情代理",
  character: "人物代理",
  dialogue: "对话代理",
  style: "风格代理",
  world: "世界观代理",
};

export function OptionCard({ option, isSelected, onSelect }: Props) {
  const vars = OPT_VARS[option.label] ?? OPT_VARS.A;

  return (
    <button
      type="button"
      onClick={() => onSelect(option.id)}
      role="option"
      aria-selected={isSelected}
      className="relative flex flex-col gap-2 p-4 rounded-2xl text-left w-full glass-card cursor-pointer transition-all duration-300 ease-out hover:translate-y-[-2px] border-2"
      style={{
        borderColor: isSelected ? vars.text : vars.border,
        boxShadow: isSelected ? `0 0 20px ${vars.dim}` : undefined,
      }}
    >
      <div
        className="absolute top-0 left-0 right-0 h-[2px] rounded-full opacity-0 transition-opacity duration-300"
        style={{ background: vars.text }}
      />

      <div className="flex items-center gap-2">
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-md tracking-wider"
          style={{ background: vars.dim, color: vars.text }}
        >
          选项 {option.label}
        </span>
        <span className="text-[10px] ml-auto flex items-center gap-1 text-th-text-3">
          <Sparkles size={10} />
          {AGENT_LABELS[option.agent] ?? option.agent}
        </span>
      </div>

      <h3 className="text-sm font-semibold leading-snug">{option.title}</h3>
      <p className="text-[11px] leading-relaxed text-th-text-2">{option.description}</p>

      <div className="mt-1 p-2.5 rounded-lg border bg-th-input border-th-border-subtle">
        <p className="text-[10px] leading-relaxed italic line-clamp-3 text-th-text-3">
          {option.preview}
        </p>
      </div>

      <div className="flex items-center gap-1.5 mt-1">
        <div className="flex-1 h-[3px] rounded-full overflow-hidden bg-th-hover">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${option.confidence * 100}%`,
              background:
                option.confidence > 0.9
                  ? "var(--th-success)"
                  : option.confidence > 0.8
                    ? "var(--th-warning)"
                    : "var(--th-danger)",
            }}
          />
        </div>
        <span className="text-[9px] tabular-nums text-th-text-3">
          {Math.round(option.confidence * 100)}%
        </span>
      </div>

      {isSelected && (
        <div
          className="absolute -top-2 -right-2 w-5 h-5 rounded-full flex items-center justify-center shadow-lg"
          style={{ background: vars.text }}
        >
          <Sparkles size={10} className="text-white" />
        </div>
      )}
    </button>
  );
}
