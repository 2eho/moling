"use client";

import { useState } from "react";
import { Send, RefreshCw } from "lucide-react";
import type { WritingProject, Option } from "@/stores/useWritingStore";
import { MOCK_OPTIONS } from "@/mock/data/workspace";

interface OptionsPanelProps {
  project: WritingProject;
  onDraftStep?: () => void;
}

export function OptionsPanel({ project: _project, onDraftStep }: OptionsPanelProps) {
  const [options] = useState<Option[]>(MOCK_OPTIONS);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [mode, setMode] = useState<"options" | "custom">("options");

  const handleSelect = (optionId: string) => {
    setSelectedOption(optionId);
  };

  const handleConfirm = () => {
    setIsGenerating(true);
    onDraftStep?.();
    setTimeout(() => {
      setIsGenerating(false);
      setSelectedOption(null);
    }, 1200);
  };

  const handleRegenerate = () => {
    setIsGenerating(true);
    setTimeout(() => setIsGenerating(false), 1200);
  };

  return (
    <div
      className="shrink-0 border-t"
      style={{ borderColor: "var(--th-border-subtle)" }}
    >
      <div className="px-4 py-3">
        {/* Mode toggle */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setMode("options")}
              className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
              style={{
                background: mode === "options" ? "var(--th-accent-dim)" : "transparent",
                color: mode === "options" ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              选项
            </button>
            <button
              onClick={() => setMode("custom")}
              className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
              style={{
                background: mode === "custom" ? "var(--th-accent-dim)" : "transparent",
                color: mode === "custom" ? "var(--th-accent-text)" : "var(--th-text-3)",
              }}
            >
              自定义
            </button>
          </div>
          <button
            onClick={handleRegenerate}
            disabled={isGenerating}
            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors hover:opacity-80 disabled:opacity-50"
            style={{ color: "var(--th-text-4)" }}
          >
            <RefreshCw size={11} className={isGenerating ? "animate-spin" : ""} />
            <span>重新生成</span>
          </button>
        </div>

        {mode === "options" ? (
          <div className="space-y-2">
            {options.map((opt) => {
              const isSelected = selectedOption === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => handleSelect(opt.id)}
                  className="w-full text-left px-3 py-2.5 rounded-lg border transition-all"
                  style={{
                    borderColor: isSelected ? "var(--th-accent-text)" : "var(--th-border-subtle)",
                    background: isSelected ? "var(--th-accent-dim)" : "var(--th-card)",
                  }}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className="w-6 h-6 rounded text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5"
                      style={{
                        background: isSelected ? "var(--th-accent-text)" : "var(--th-hover)",
                        color: isSelected ? "#fff" : "var(--th-text-3)",
                      }}
                    >
                      {opt.label}
                    </span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-semibold" style={{ color: "var(--th-text)" }}>
                          {opt.title}
                        </span>
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{
                            background: `hsl(${opt.confidence * 120}, 40%, 90%)`,
                            color: `hsl(${opt.confidence * 120}, 50%, 30%)`,
                          }}
                        >
                          {Math.round(opt.confidence * 100)}%
                        </span>
                      </div>
                      <p
                        className="text-[11px] leading-relaxed mb-1"
                        style={{ color: "var(--th-text-3)" }}
                      >
                        {opt.description}
                      </p>
                      <p className="text-[10px] italic" style={{ color: "var(--th-text-4)" }}>
                        {opt.preview}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}

            <button
              onClick={handleConfirm}
              disabled={!selectedOption || isGenerating}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-40"
              style={{
                background: selectedOption ? "var(--th-accent-text)" : "var(--th-hover)",
                color: selectedOption ? "#fff" : "var(--th-text-4)",
              }}
            >
              {isGenerating ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              <span>
                {isGenerating
                  ? "生成中..."
                  : selectedOption
                    ? "确认选择"
                    : "请先选择一个选项"}
              </span>
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <textarea
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="写下你的想法，或选择上方「选项」让 AI 提供建议..."
              className="w-full h-20 rounded-lg px-3 py-2 text-xs resize-none transition-colors"
              style={{
                background: "var(--th-card)",
                borderColor: "var(--th-border-subtle)",
                color: "var(--th-text-2)",
                border: "1px solid var(--th-border-subtle)",
              }}
            />
            <button
              onClick={() => {
                if (!customInput.trim()) return;
                setIsGenerating(true);
                onDraftStep?.();
                setTimeout(() => {
                  setIsGenerating(false);
                  setCustomInput("");
                }, 1200);
              }}
              disabled={!customInput.trim() || isGenerating}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-all disabled:opacity-40"
              style={{
                background: customInput.trim() ? "var(--th-accent-text)" : "var(--th-hover)",
                color: customInput.trim() ? "#fff" : "var(--th-text-4)",
              }}
            >
              {isGenerating ? (
                <RefreshCw size={13} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              <span>{isGenerating ? "提交中..." : "提交"}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
