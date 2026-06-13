"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { showToast } from "@/components/ui/Toast";
import { notificationsApi } from "@/lib/api";
import type { Notification, NotificationType } from "@/lib/types";
import styles from "./page.module.css";

/* ============================================
   通知类型 → 图标 / 样式类
   ============================================ */

const TYPE_CONFIG: Partial<
  Record<NotificationType, { icon: string; cls: "warning" | "error" | "success" | "info" }>
> = {
  phase4_failed: { icon: "⚠️", cls: "warning" },
  phase4_stuck: { icon: "🚫", cls: "error" },
  health_alert: { icon: "🏥", cls: "warning" },
  subscription: { icon: "✅", cls: "success" },
  system: { icon: "📢", cls: "info" },
};

/* ============================================
   工具：相对时间
   ============================================ */

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}

/* ============================================
   页面组件
   ============================================ */

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load notifications
  const loadNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await notificationsApi.list();
      setNotifications(res.data);
    } catch (error) {
      showToast("error", "加载通知失败");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const markRead = useCallback(
    async (id: string) => {
      try {
        await notificationsApi.markAsRead(id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
        );
        showToast("success", "已标记为已读");
      } catch (error) {
        showToast("error", "操作失败");
        console.error(error);
      }
    },
    [],
  );

  const markAllRead = useCallback(async () => {
    try {
      await notificationsApi.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      showToast("success", "全部已读");
    } catch (error) {
      showToast("error", "操作失败");
      console.error(error);
    }
  }, []);

  const hasUnread = notifications.some((n) => !n.is_read);

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div>加载中...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/workspace/project_001" className={styles.headerBack}>
          ← 返回
        </Link>
        <h1 className={styles.headerTitle}>🔔 通知</h1>
        <div className={styles.headerActions}>
          <button onClick={markAllRead} disabled={!hasUnread}>
            全部已读
          </button>
        </div>
      </header>

      {/* Content */}
      <div className={styles.container}>
        {notifications.length === 0 ? (
          <div className={styles.emptyState}>
            <span className={styles.emptyIcon}>🔔</span>
            <p className={styles.emptyText}>暂无通知</p>
          </div>
        ) : (
          <div className={styles.notifList}>
            {notifications.map((n) => {
              const cfg = TYPE_CONFIG[n.type] ?? {
                icon: "📌",
                cls: "info" as const,
              };
              return (
                <div
                  key={n.id}
                  className={`${styles.notifItem} ${n.is_read ? "" : styles.unread}`}
                  onClick={() => markRead(n.id)}
                >
                  <div className={`${styles.notifIcon} ${styles[cfg.cls]}`}>
                    {cfg.icon}
                  </div>
                  <div className={styles.notifContent}>
                    <div className={styles.notifTitle}>{n.title}</div>
                    <div className={styles.notifBody}>{n.message}</div>
                    <div className={styles.notifTime}>{timeAgo(n.created_at)}</div>
                  </div>
                  <div
                    className={`${styles.notifDot} ${n.is_read ? styles.read : styles.unread}`}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
