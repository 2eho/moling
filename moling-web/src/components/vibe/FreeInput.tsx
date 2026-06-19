"use client";

import { useState } from "react";
import { useWritingStore } from "@/stores/useWritingStore";
import { Send, PenLine } from "lucide-react";

export function FreeInput() {
  const customInput = useWritingStore((s) => s.customInput);
  const setCustomInput = useWritingStore((s) => s.setCustomInput);
  const submitCustom = useWritingStore((s) => s.submitCustom);
  const isGenerating = useWritingStore((s) => s.isGenerating);
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = () => {
    if (!customInput.trim() || isGenerating) return;
    submitCustom();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className="glass-card p-3 transition-all duration-300"
      style={{
        boxShadow: isFocused ? "0 0 20px var(--th-accent-dim)" : undefined,
        borderColor: isFocused ? "var(--th-accent-border)" : undefined,
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-md tracking-wider"
          style={{ background: "var(--th-hover-strong)", color: "var(--th-text-2)" }}
        >
          自定义 D
        </span>
        <span className="text-[10px]" style={{ color: "var(--th-text-3)" }}>
          或输入你自己的方向...
        </span>
      </div>

      <div className="relative">
        <textarea
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="比如：让林风在战斗中领悟新的剑意，同时柳如烟在一旁观察..."
          rows={2}
          className="w-full rounded-xl px-3 py-2 text-[12px] resize-none transition-all duration-200 outline-none"
          style={{
            background: "var(--th-input)",
            border: `1px solid ${isFocused ? "var(--th-accent)" : "var(--th-border-subtle)"}`,
            color: "var(--th-text)",
          }}
        />

        <button
          onClick={handleSubmit}
          disabled={!customInput.trim() || isGenerating}
          className="absolute right-2 bottom-2 p-1.5 rounded-lg transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed hover:scale-110 active:scale-90"
          style={{ background: "var(--th-accent-dim)", color: "var(--th-accent-text)" }}
        >
          {isGenerating ? (
            <span
              className="block w-3.5 h-3.5 border-2 rounded-full animate-spin"
              style={{
                borderColor: "var(--th-accent-dim)",
                borderTopColor: "var(--th-accent-text)",
              }}
            />
          ) : (
            <Send size={14} />
          )}
        </button>
      </div>

      <div className="flex items-center gap-1 mt-1.5">
        <PenLine size={10} style={{ color: "var(--th-text-4)" }} />
        <span className="text-[9px]" style={{ color: "var(--th-text-4)" }}>
          Enter 发送 · Shift+Enter 换行
        </span>
      </div>
    </div>
  );
}
