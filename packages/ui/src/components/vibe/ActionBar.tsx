"use client";

import { Download, FastForward, RefreshCw, Save, Undo2 } from "lucide-react";
import { useWritingStore } from "@/stores/useWritingStore";

export function ActionBar() {
  const undo = useWritingStore((s) => s.undo);
  const generateOptions = useWritingStore((s) => s.generateOptions);
  const history = useWritingStore((s) => s.history);
  const selectedOption = useWritingStore((s) => s.selectedOption);
  const isGenerating = useWritingStore((s) => s.isGenerating);

  const actions = [
    {
      label: "上一步",
      icon: <Undo2 size={15} />,
      onClick: undo,
      disabled: history.length === 0 || isGenerating,
      primary: false,
    },
    {
      label: "快进",
      icon: <FastForward size={15} />,
      onClick: () => {},
      disabled: true,
      primary: false,
    },
    {
      label: "重来",
      icon: <RefreshCw size={15} />,
      onClick: generateOptions,
      disabled: isGenerating,
      primary: false,
    },
    { label: "保存", icon: <Save size={15} />, onClick: () => {}, disabled: true, primary: true },
    {
      label: "导出",
      icon: <Download size={15} />,
      onClick: () => {},
      disabled: true,
      primary: true,
    },
  ];

  return (
    <footer
      role="toolbar"
      aria-label="写作操作"
      className="flex items-center justify-between px-6 py-3 border-t border-th-border-subtle bg-[color-mix(in_srgb,var(--th-bg)_80%,transparent)] backdrop-blur-xl"
    >
      <div className="text-[10px] text-th-text-4">
        {history.length > 0 ? `${history.length} 步操作` : "尚未选择"}
      </div>

      <div className="flex items-center gap-1.5">
        {actions.map((action) => (
          <button
            type="button"
            key={action.label}
            onClick={action.onClick}
            disabled={action.disabled}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-medium transition-all duration-200 disabled:opacity-25 disabled:cursor-not-allowed ${
              action.primary
                ? "bg-th-accent-dim text-th-accent-text border border-th-accent-dim"
                : "bg-transparent text-th-text-3"
            }`}
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>

      <div className="text-[10px] text-th-accent-text/50">
        {selectedOption
          ? `已选 ${history[history.length - 1]?.choice ?? ""}`
          : "选择方向或自定义输入"}
      </div>
    </footer>
  );
}
