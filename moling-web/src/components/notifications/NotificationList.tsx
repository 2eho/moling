'use client';

import styles from './NotificationList.module.css';
import { NotificationItem } from './NotificationItem';
import type { Notification } from '@/lib/types';

interface NotificationListProps {
  notifications: Notification[];
  loading: boolean;
  actionLoading: string | null;
  onMarkAsRead: (id: string) => void;
  onDelete: (id: string) => void;
}

export function NotificationList({
  notifications,
  loading,
  actionLoading,
  onMarkAsRead,
  onDelete,
}: NotificationListProps) {
  if (loading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <span>加载中...</span>
      </div>
    );
  }

  if (notifications.length === 0) {
    return (
      <div className={styles.empty}>
        <div className={styles.emptyIcon}>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </div>
        <p>暂无通知</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {notifications.map((notification) => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onMarkAsRead={onMarkAsRead}
          onDelete={onDelete}
          actionLoading={actionLoading}
        />
      ))}
    </div>
  );
}
