'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import styles from './notifications.module.css';
import { notificationsApi } from '@/lib/api';
import type { Notification } from '@/lib/types';
import { safePaginatedData } from '@/lib/apiSafety';
import { NotificationList } from '@/components/notifications/NotificationList';

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
      const result = await notificationsApi.list(params);
      // ✅ 修复：使用 safePaginatedData 确保安全
      const { items, total } = safePaginatedData<Notification>(result);
      setNotifications(items);
      setTotal(total);
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
        <NotificationList
          notifications={notifications}
          loading={loading}
          actionLoading={actionLoading}
          onMarkAsRead={handleMarkAsRead}
          onDelete={handleDelete}
        />

        {/* Pagination */}
        {!loading && total > pageSize && (
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
