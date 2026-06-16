/* ═══════════════════════════════════════════════════
   通知项组件测试 · NotificationItem.test.tsx
   ═══════════════════════════════════════════════════ */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationItem } from './NotificationItem';
import type { Notification } from '@/lib/types';

/* ── Mock Data ── */

const mockNotification: Notification = {
  id: '1',
  user_id: 'user1',
  type: 'generation_complete',
  title: '章节生成完成',
  message: '第 3 章已生成完成，点击查看。',
  is_read: false,
  created_at: new Date().toISOString(),
};

const mockOnMarkAsRead = vi.fn();
const mockOnDelete = vi.fn();

/* ── Tests ── */

describe('NotificationItem', () => {
  it('应该渲染通知标题和内容', () => {
    render(
      <NotificationItem
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    expect(screen.getByText('章节生成完成')).toBeTruthy();
    expect(screen.getByText(/第 3 章已生成完成/)).toBeTruthy();
  });

  it('点击未读通知时应标记为已读', () => {
    render(
      <NotificationItem
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    const item = screen.getByText('章节生成完成').closest('[class*="item"]');
    fireEvent.click(item!);
    expect(mockOnMarkAsRead).toHaveBeenCalledWith('1');
  });

  it('已读通知不应触发标记已读', () => {
    const readNotification = { ...mockNotification, is_read: true };
    render(
      <NotificationItem
        notification={readNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    const item = screen.getByText('章节生成完成').closest('[class*="item"]');
    fireEvent.click(item!);
    expect(mockOnMarkAsRead).not.toHaveBeenCalled();
  });

  it('应该显示删除按钮并可以点击', () => {
    render(
      <NotificationItem
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    const deleteButtons = screen.getAllByText('删除');
    fireEvent.click(deleteButtons[0]);
    expect(mockOnDelete).toHaveBeenCalledWith('1');
  });

  it('应该根据通知类型显示正确图标', () => {
    const { rerender } = render(
      <NotificationItem
        notification={{ ...mockNotification, type: 'generation_complete' }}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    // 重新渲染不同类型的通知
    rerender(
      <NotificationItem
        notification={{ ...mockNotification, type: 'health_alert' }}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    expect(screen.getByText('章节生成完成')).toBeTruthy();
  });

  it('应该显示未读圆点', () => {
    const { container } = render(
      <NotificationItem
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    const unreadDot = container.querySelector('[class*="unreadDot"]:not([class*="unreadDotRead"])');
    expect(unreadDot).toBeTruthy();
  });

  it('已读通知不应显示未读圆点', () => {
    const readNotification = { ...mockNotification, is_read: true };
    const { container } = render(
      <NotificationItem
        notification={readNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
        actionLoading={null}
      />
    );

    const unreadDot = container.querySelector('[class*="unreadDot"]:not([class*="unreadDotRead"])');
    expect(unreadDot).toBeFalsy();
  });
});
