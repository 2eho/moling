/* ═══════════════════════════════════════════════════
   通知列表组件测试 · NotificationList.test.tsx
   ═════════════════════════════════════════════════ */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NotificationList } from './NotificationList';
import type { Notification } from '@/lib/types';

/* ── Mock Data ── */

const mockNotifications: Notification[] = [
  {
    id: '1',
    user_id: 'user1',
    type: 'generation_complete',
    title: '章节生成完成',
    message: '第 3 章已生成完成。',
    is_read: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    user_id: 'user1',
    type: 'health_alert',
    title: '健康检测警告',
    message: '检测到剧情漏洞。',
    is_read: true,
    created_at: new Date().toISOString(),
  },
  {
    id: '3',
    user_id: 'user1',
    type: 'system',
    title: '系统通知',
    message: '系统维护已完成。',
    is_read: false,
    created_at: new Date().toISOString(),
  },
];

const mockOnMarkAsRead = vi.fn();
const mockOnDelete = vi.fn();

/* ── Tests ── */

describe('NotificationList', () => {
  it('应该渲染所有通知', () => {
    render(
      <NotificationList
        notifications={mockNotifications}
        loading={false}
        actionLoading={null}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('章节生成完成')).toBeTruthy();
    expect(screen.getByText('健康检测警告')).toBeTruthy();
    expect(screen.getByText('系统通知')).toBeTruthy();
  });

  it('应该显示加载状态', () => {
    render(
      <NotificationList
        notifications={[]}
        loading={true}
        actionLoading={null}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('加载中...')).toBeTruthy();
  });

  it('空列表时应该显示空状态', () => {
    render(
      <NotificationList
        notifications={[]}
        loading={false}
        actionLoading={null}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText('暂无通知')).toBeTruthy();
  });

  it('点击通知项应该触发标记已读', () => {
    render(
      <NotificationList
        notifications={mockNotifications}
        loading={false}
        actionLoading={null}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
      />
    );

    const item = screen.getByText('章节生成完成').closest('[class*="item"]');
    fireEvent.click(item!);
    expect(mockOnMarkAsRead).toHaveBeenCalledWith('1');
  });

  it('应该渲染多个通知项', () => {
    const { container } = render(
      <NotificationList
        notifications={mockNotifications}
        loading={false}
        actionLoading={null}
        onMarkAsRead={mockOnMarkAsRead}
        onDelete={mockOnDelete}
      />
    );

    const items = container.querySelectorAll('[class*="item"]');
    expect(items.length).toBe(3);
  });
});
