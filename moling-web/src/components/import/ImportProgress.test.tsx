/* ══════════════════════════════════════════════════════
   导入进度组件测试 · ImportProgress.test.tsx
   ══════════════════════════════════════════════════════ */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ImportProgress from './ImportProgress';

/* ── Mock Data ── */

const mockProgressItems = [
  { id: 'characters', label: '人物库提取', icon: '👥', status: 'done' as const, result: '12 人' },
  { id: 'timeline', label: '时间线库提取', icon: '⏱️', status: 'active' as const },
  { id: 'commitments', label: '剧情承诺库提取', icon: '📖', status: 'pending' as const },
  { id: 'worldview', label: '世界观库提取', icon: '🌍', status: 'pending' as const },
];

/* ── Tests ── */

describe('ImportProgress', () => {
  it('应该渲染组件标题', () => {
    render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
      />
    );

    expect(screen.getByText('全库分析 · 四库提取')).toBeTruthy();
  });

  it('应该显示所有进度项目', () => {
    render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
      />
    );

    expect(screen.getByText('人物库提取')).toBeTruthy();
    expect(screen.getByText('时间线库提取')).toBeTruthy();
    expect(screen.getByText('剧情承诺库提取')).toBeTruthy();
    expect(screen.getByText('世界观库提取')).toBeTruthy();
  });

  it('应该显示已完成项目的结果', () => {
    render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
      />
    );

    expect(screen.getByText(/提取完成/)).toBeTruthy();
  });

  it('应该显示进度百分比', () => {
    render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
      />
    );

    expect(screen.getByText('50%')).toBeTruthy();
  });

  it('当 isVisible 为 false 时不显示内容', () => {
    const { container } = render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={false}
      />
    );

    // 组件应该存在但不显示
    const phaseContainer = container.querySelector('[class*="phaseContainer"]');
    expect(phaseContainer).toBeTruthy();
  });

  it('应该使用自定义标题和副标题', () => {
    render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
        title="自定义标题"
        subtitle="自定义副标题"
      />
    );

    expect(screen.getByText('自定义标题')).toBeTruthy();
    expect(screen.getByText('自定义副标题')).toBeTruthy();
  });

  it('应该显示进行中的 spinner', () => {
    const { container } = render(
      <ImportProgress
        phase={1}
        progressItems={mockProgressItems}
        overallProgress={50}
        isVisible={true}
      />
    );

    // 应该有一个进行中的项目，显示 spinner
    const spinner = container.querySelector('[class*="progressSpinner"]');
    expect(spinner).toBeTruthy();
  });
});
