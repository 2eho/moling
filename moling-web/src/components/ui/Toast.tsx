"use client";

import { memo, useEffect, useState, useCallback } from "react";
import styles from "./Toast.module.css";

export type ToastType = "success" | "error" | "warning" | "info";

interface ToastItemData {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;
const listeners: Array<(toast: ToastItemData) => void> = [];

export function showToast(type: ToastType, message: string) {
  const toast: ToastItemData = { id: ++toastId, type, message };
  listeners.forEach((fn) => fn(toast));
}

export const ToastContainer = memo(function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItemData[]>([]);

  const addToast = useCallback((toast: ToastItem) => {
    setToasts((prev) => [...prev, toast]);
  }, []);

  useEffect(() => {
    listeners.push(addToast);
    return () => {
      const idx = listeners.indexOf(addToast);
      if (idx >= 0) listeners.splice(idx, 1);
    };
  }, [addToast]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <div className={styles.container}>
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
});

const ToastItem = memo(function ToastItem({
  toast,
  onRemove,
}: {
  toast: ToastItemData;
  onRemove: (id: number) => void;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), 3000);
    return () => clearTimeout(timer);
  }, [toast.id, onRemove]);

  const icons: Record<ToastType, string> = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ",
  };

  return (
    <div
      className={`${styles.toast} ${styles[toast.type]}`}
      onClick={() => onRemove(toast.id)}
    >
      <span className={styles.icon}>{icons[toast.type]}</span>
      <span className={styles.message}>{toast.message}</span>
    </div>
  );
});
