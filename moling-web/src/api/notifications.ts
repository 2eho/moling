// Notifications 相关 API
import { api } from './client';
import type { Notification } from './types';

// 获取通知列表
export async function getNotifications(
  params?: {
    page?: number;
    pageSize?: number;
    isRead?: boolean;
    type?: string;
  }
): Promise<{ items: Notification[]; total: number; unreadCount: number }> {
  const query = new URLSearchParams();
  if (params?.page) query.set('page', params.page.toString());
  if (params?.pageSize) query.set('pageSize', params.pageSize.toString());
  if (params?.isRead !== undefined) query.set('isRead', params.isRead.toString());
  if (params?.type) query.set('type', params.type);

  return api.get<{ items: Notification[]; total: number; unreadCount: number }>(
    `/notifications?${query.toString()}`
  );
}

// 获取未读通知数量
export async function getUnreadCount(): Promise<{ count: number }> {
  return api.get<{ count: number }>('/notifications/unread-count');
}

// 标记通知为已读
export async function markAsRead(notificationId: string): Promise<{ success: boolean }> {
  return api.patch<{ success: boolean }>(`/notifications/${notificationId}/read`);
}

// 标记所有通知为已读
export async function markAllAsRead(): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>('/notifications/mark-all-read');
}

// 删除通知
export async function deleteNotification(
  notificationId: string
): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>(`/notifications/${notificationId}`);
}

// 删除所有已读通知
export async function deleteAllRead(): Promise<{ success: boolean }> {
  return api.delete<{ success: boolean }>('/notifications/delete-read');
}
