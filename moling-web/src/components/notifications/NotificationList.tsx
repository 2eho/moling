'use client';

import styles from './NotificationList.module.css';
import { NotificationItem } from './NotificationItem';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { EmptyState } from '@/components/ui/EmptyState';
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
      <div className={styles.list}>
        {[1, 2, 3, 4, 5].map((i) => (
          <SkeletonCard key={i} lines={2} />
        ))}
      </div>
    );
  }

  if (notifications.length === 0) {
    return (
      <EmptyState
        icon="🔔"
        title="暂无通知"
        description="当有新消息时，会在这里显示"
      />
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
