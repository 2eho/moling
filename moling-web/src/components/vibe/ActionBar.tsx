"use client";

import { useWritingStore } from "@/stores/useWritingStore";
import { Undo2, FastForward, RefreshCw, Save, Download } from "lucide-react";

export function ActionBar() {
  const undo = useWritingStore((s) => s.undo);
  const generateOptions = useWritingStore((s) => s.generateOptions);
  const history = useWritingStore((s) => s.history);
  const selectedOption = useWritingStore((s) => s.selectedOption);
  const isGenerating = useWritingStore((s) => s.isGenerating);

  const actions = [
    { label: "上一步", icon: <Undo2 size={15} />, onClick: undo, disabled: history.length === 0 || isGenerating, primary: false },
    { label: "快进", icon: <FastForward size={15} />, onClick: () => {}, disabled: true, primary: false },
    { label: "重来", icon: <RefreshCw size={15} />, onClick: generateOptions, disabled: isGenerating, primary: false },
    { label: "保存", icon: <Save size={15} />, onClick: () => {}, disabled: true, primary: true },
    { label: "导出", icon: <Download size={15} />, onClick: () => {}, disabled: true, primary: true },
  ];

  return (
    <footer
      className="flex items-center justify-between px-6 py-3"
      style={{
        borderTop: "1px solid var(--th-border-subtle)",
        background: "color-mix(in srgb, var(--th-bg) 80%, transparent)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      }}
    >
      <div className="text-[10px]" style={{ color: "var(--th-text-4)" }}>
        {history.length > 0 ? `${history.length} 步操作` : "尚未选择"}
      </div>

      <div className="flex items-center gap-1.5">
        {actions.map((action) => (
          <button
            key={action.label}
            onClick={action.onClick}
            disabled={action.disabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-medium transition-all duration-200 disabled:opacity-25 disabled:cursor-not-allowed"
            style={
              action.primary
                ? { background: "var(--th-accent-dim)", color: "var(--th-accent-text)", border: "1px solid var(--th-accent-dim)" }
                : { background: "transparent", color: "var(--th-text-3)" }
            }
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>

      <div className="text-[10px]" style={{ color: "var(--th-accent-text)", opacity: 0.5 }}>
        {selectedOption
          ? `已选 ${history[history.length - 1]?.choice ?? ""}`
          : "选择方向或自定义输入"}
      </div>
    </footer>
  );
}
