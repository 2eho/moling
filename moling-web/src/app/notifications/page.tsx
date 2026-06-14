'use client';

import { useState, useEffect } from 'react';
import styles from './Notifications.module.css';
import {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  deleteNotification,
  deleteAllRead,
} from '@/api';
import type { Notification } from '@/api';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // 加载通知
  const loadNotifications = async () => {
    setLoading(true);
    try {
      const params: any = { page, pageSize };
      if (filter === 'unread') params.isRead = false;
      if (typeFilter) params.type = typeFilter;

      const result = await getNotifications(params);
      setNotifications(result.items);
      setTotal(result.total);
    } catch (error) {
      console.error('加载通知失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载未读计数
  const loadUnreadCount = async () => {
    try {
      const result = await getUnreadCount();
      setUnreadCount(result.count);
    } catch (error) {
      console.error('加载未读计数失败:', error);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, [page, filter, typeFilter]);

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 60000); // 每 60 秒刷新
    return () => clearInterval(interval);
  }, []);

  // 标记已读
  const handleMarkAsRead = async (id: string) => {
    setActionLoading(id);
    try {
      await markAsRead(id);
      await loadNotifications();
      await loadUnreadCount();
    } catch (error) {
      console.error('标记已读失败:', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 标记所有已读
  const handleMarkAllAsRead = async () => {
    setActionLoading('all');
    try {
      await markAllAsRead();
      await loadNotifications();
      await loadUnreadCount();
    } catch (error) {
      console.error('标记所有已读失败:', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 删除通知
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除此通知吗？')) return;

    setActionLoading(id);
    try {
      await deleteNotification(id);
      await loadNotifications();
      await loadUnreadCount();
    } catch (error) {
      console.error('删除通知失败:', error);
    } finally {
      setActionLoading(null);
    }
  };

  // 删除所有已读
  const handleDeleteAllRead = async () => {
    if (!confirm('确定要删除所有已读通知吗？')) return;

    setActionLoading('delete-all');
    try {
      await deleteAllRead();
      await loadNotifications();
    } catch (error) {
      console.error('删除所有已读失败:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'info': return 'ℹ️';
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return 'ℹ️';
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
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>通知</h1>
        <div className={styles.headerActions}>
          <button
            className={styles.actionBtn}
            onClick={handleMarkAllAsRead}
            disabled={actionLoading === 'all' || unreadCount === 0}
          >
            {actionLoading === 'all' ? '处理中...' : '全部标为已读'}
          </button>
          <button
            className={styles.actionBtn}
            onClick={handleDeleteAllRead}
            disabled={actionLoading === 'delete-all'}
          >
            {actionLoading === 'delete-all' ? '处理中...' : '删除已读'}
          </button>
        </div>
      </div>

      <div className={styles.unreadBadge}>
        {unreadCount > 0 && (
          <span>📬 您有 {unreadCount} 条未读通知</span>
        )}
        {unreadCount === 0 && <span>📭 没有未读通知</span>}
      </div>

      <div className={styles.filters}>
        <button
          className={`${styles.filterBtn} ${filter === 'all' ? styles.filterBtnActive : ''}`}
          onClick={() => setFilter('all')}
        >
          全部 ({total})
        </button>
        <button
          className={`${styles.filterBtn} ${filter === 'unread' ? styles.filterBtnActive : ''}`}
          onClick={() => setFilter('unread')}
        >
          未读 ({unreadCount})
        </button>
        {['info', 'success', 'warning', 'error'].map(type => (
          <button
            key={type}
            className={`${styles.filterBtn} ${typeFilter === type ? styles.filterBtnActive : ''}`}
            onClick={() => setTypeFilter(typeFilter === type ? '' : type)}
          >
            {getTypeIcon(type)} {type}
          </button>
        ))}
      </div>

      <div className={styles.list}>
        {loading ? (
          <div className={styles.loading}>加载中...</div>
        ) : notifications.length === 0 ? (
          <div className={styles.empty}>暂无通知</div>
        ) : (
          notifications.map(notification => (
            <div
              key={notification.id}
              className={`${styles.item} ${!notification.isRead ? styles.itemUnread : ''}`}
            >
              <div className={styles.itemIcon}>
                {getTypeIcon(notification.type)}
              </div>
              <div className={styles.itemContent}>
                <div className={styles.itemTitle}>{notification.title}</div>
                <div className={styles.itemMessage}>{notification.message}</div>
                <div className={styles.itemTime}>
                  {formatTime(notification.createdAt)}
                </div>
              </div>
              <div className={styles.itemActions}>
                {!notification.isRead && (
                  <button
                    className={styles.itemActionBtn}
                    onClick={() => handleMarkAsRead(notification.id)}
                    disabled={actionLoading === notification.id}
                  >
                    {actionLoading === notification.id ? '...' : '标为已读'}
                  </button>
                )}
                <button
                  className={`${styles.itemActionBtn} ${styles.itemActionBtnDanger}`}
                  onClick={() => handleDelete(notification.id)}
                  disabled={actionLoading === notification.id}
                >
                  {actionLoading === notification.id ? '...' : '删除'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {total > pageSize && (
        <div className={styles.pagination}>
          <button
            disabled={page === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span>{page} / {Math.ceil(total / pageSize)}</span>
          <button
            disabled={page >= Math.ceil(total / pageSize)}
            onClick={() => setPage(p => p + 1)}
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
