'use client';

import styles from './NotificationItem.module.css';
import type { Notification } from '@/lib/types';

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead: (id: string) => void;
  onDelete: (id: string) => void;
  actionLoading: string | null;
}

const NOTIFICATION_ICONS: Record<string, { svg: React.ReactNode; iconClass: string }> = {
  generation_complete: {
    iconClass: styles.iconSuccess,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
  },
  health_alert: {
    iconClass: styles.iconWarning,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  system: {
    iconClass: styles.iconInfo,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  },
  subscription: {
    iconClass: styles.iconSuccess,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
        <line x1="1" y1="10" x2="23" y2="10" />
      </svg>
    ),
  },
  chapter_ready: {
    iconClass: styles.iconSuccess,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
  },
  phase4_failed: {
    iconClass: styles.iconError,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
  },
  phase4_stuck: {
    iconClass: styles.iconWarning,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
  },
};

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;
  return date.toLocaleDateString('zh-CN');
}

function getNotifConfig(type: string) {
  return NOTIFICATION_ICONS[type] || NOTIFICATION_ICONS.system;
}

export function NotificationItem({ notification, onMarkAsRead, onDelete, actionLoading }: NotificationItemProps) {
  const config = getNotifConfig(notification.type);
  const isLoading = actionLoading === notification.id;

  const handleClick = () => {
    if (!notification.is_read) {
      onMarkAsRead(notification.id);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(notification.id);
  };

  return (
    <div
      className={`${styles.item} ${!notification.is_read ? styles.itemUnread : ''}`}
      onClick={handleClick}
    >
      <div className={`${styles.itemIcon} ${config.iconClass}`}>
        {config.svg}
      </div>
      <div className={styles.itemContent}>
        <div className={styles.itemTitle}>{notification.title}</div>
        <div className={styles.itemBody}>{notification.message}</div>
        <div className={styles.itemTime}>{formatTime(notification.created_at)}</div>
      </div>
      <div className={styles.itemActions}>
        {!notification.is_read && (
          <button
            className={styles.actionBtn}
            onClick={(e) => {
              e.stopPropagation();
              onMarkAsRead(notification.id);
            }}
            disabled={isLoading}
            title="标记为已读"
          >
            {isLoading ? '...' : '已读'}
          </button>
        )}
        <button
          className={`${styles.actionBtn} ${styles.deleteBtn}`}
          onClick={handleDelete}
          disabled={isLoading}
          title="删除"
        >
          删除
        </button>
      </div>
      <div className={`${styles.unreadDot} ${notification.is_read ? styles.unreadDotRead : ''}`} />
    </div>
  );
}
