"use client";

import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { type ToastType, useToast } from "@/stores/useToast";

const TYPE_STYLES: Record<ToastType, { icon: React.ReactNode; bg: string; border: string }> = {
  success: {
    icon: <CheckCircle2 size={14} />,
    bg: "var(--th-success)",
    border: "var(--th-success)",
  },
  error: {
    icon: <AlertCircle size={14} />,
    bg: "var(--th-danger)",
    border: "var(--th-danger)",
  },
  warning: {
    icon: <AlertTriangle size={14} />,
    bg: "var(--th-warning)",
    border: "var(--th-warning)",
  },
  info: {
    icon: <Info size={14} />,
    bg: "var(--th-accent-text)",
    border: "var(--th-accent-text)",
  },
};

export function ToastContainer() {
  const toasts = useToast((s) => s.toasts);
  const removeToast = useToast((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-live="polite"
      role="status"
    >
      {toasts.map((toast) => {
        const style = TYPE_STYLES[toast.type];
        return (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg shadow-lg animate-slide-in-right bg-th-card text-th-text"
            style={{
              borderLeft: `3px solid ${style.border}`,
            }}
          >
            <span className="shrink-0" style={{ color: style.bg }}>
              {style.icon}
            </span>
            <span className="text-xs flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="shrink-0 p-0.5 rounded hover:opacity-70 transition-opacity text-th-text-4"
              aria-label="关闭"
            >
              <X size={12} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
