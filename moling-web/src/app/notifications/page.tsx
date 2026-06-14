'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import styles from './notifications.module.css';
import { notificationsApi } from '@/lib/api';
import type { Notification } from '@/lib/types';

const NOTIFICATION_ICONS: Record<string, { svg: React.ReactNode; iconClass: string }> = {
  warning: {
    iconClass: styles.iconWarning,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
  },
  error: {
    iconClass: styles.iconError,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    ),
  },
  success: {
    iconClass: styles.iconSuccess,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
  },
  info: {
    iconClass: styles.iconInfo,
    svg: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
    ),
  },
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState('');

  const toastTimer = useRef<ReturnType<typeof setTimeout>>(null);

  const showToast = useCallback((msg: string) => {
    setToastMsg(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToastMsg(''), 2000);
  }, []);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { page, pageSize };
      const result = await notificationsApi.getNotifications(params);
      setNotifications(result.items);
      setTotal(result.total);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  const loadUnreadCount = useCallback(async () => {
    try {
      const result = await notificationsApi.getUnreadCount();
      setUnreadCount(result.data.count);
    } catch (error) {
      console.error('Failed to load unread count:', error);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 60000);
    return () => clearInterval(interval);
  }, [loadUnreadCount]);

  const handleMarkAsRead = async (id: string) => {
    setActionLoading(id);
    try {
      await notificationsApi.markAsRead(id);
      await loadNotifications();
      await loadUnreadCount();
      showToast('已标记为已读');
    } catch (error) {
      console.error('Failed to mark as read:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAllAsRead = async () => {
    setActionLoading('all');
    try {
      await notificationsApi.markAllAsRead();
      await loadNotifications();
      await loadUnreadCount();
      showToast('全部已读');
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此通知？')) return;
    setActionLoading(id);
    try {
      await notificationsApi.deleteNotification(id);
      await loadNotifications();
      await loadUnreadCount();
    } catch (error) {
      console.error('Failed to delete notification:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const formatTime = (dateStr: string) => {
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
  };

  const getNotifConfig = (type: string) => {
    return NOTIFICATION_ICONS[type] || NOTIFICATION_ICONS.info;
  };

  return (
    <div className={styles.container}>
      {/* Toast */}
      <div className={`${styles.toast} ${toastMsg ? styles.toastVisible : ''}`}>
        {toastMsg}
      </div>

      {/* Header */}
      <header className={styles.header}>
        <button className={styles.headerBack} onClick={() => window.history.back()}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          返回
        </button>
        <h1 className={styles.headerTitle}>通知</h1>
        <div className={styles.headerActions}>
          <button
            className={styles.markAllBtn}
            onClick={handleMarkAllAsRead}
            disabled={actionLoading === 'all' || unreadCount === 0}
          >
            {actionLoading === 'all' ? '...' : '全部已读'}
          </button>
        </div>
      </header>

      {/* Unread Badge */}
      <div className={styles.unreadBadge}>
        {unreadCount > 0 ? (
          <>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 2L11 13" />
              <path d="M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
            你有 {unreadCount} 条未读通知
          </>
        ) : (
          '没有未读通知'
        )}
      </div>

      {/* Notification List */}
      <div className={styles.content}>
        {loading ? (
          <div className={styles.loading}>加载中...</div>
        ) : notifications.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </div>
            <p>暂无通知</p>
          </div>
        ) : (
          notifications.map((notification) => {
            const config = getNotifConfig(notification.type);
            return (
              <div
                key={notification.id}
                className={`${styles.item} ${!notification.is_read ? styles.itemUnread : ''}`}
                onClick={() => !notification.is_read && handleMarkAsRead(notification.id)}
              >
                <div className={`${styles.itemIcon} ${config.iconClass}`}>
                  {config.svg}
                </div>
                <div className={styles.itemContent}>
                  <div className={styles.itemTitle}>{notification.title}</div>
                  <div className={styles.itemBody}>{notification.message}</div>
                  <div className={styles.itemTime}>{formatTime(notification.created_at)}</div>
                </div>
                <div className={`${styles.unreadDot} ${notification.is_read ? styles.unreadDotRead : ''}`} />
              </div>
            );
          })
        )}

        {/* Pagination */}
        {total > pageSize && (
          <div className={styles.pagination}>
            <button
              className={styles.pageBtn}
              disabled={page === 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              上一页
            </button>
            <span className={styles.pageInfo}>
              {page} / {Math.ceil(total / pageSize)}
            </span>
            <button
              className={styles.pageBtn}
              disabled={page >= Math.ceil(total / pageSize)}
              onClick={() => setPage(p => p + 1)}
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
