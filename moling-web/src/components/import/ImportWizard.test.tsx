/* ══════════════════════════════════════════════════════
   导入向导组件测试 · ImportWizard.test.tsx
   ══════════════════════════════════════════════════════ */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImportWizard from './ImportWizard';

/* ── Mock Steps ── */

const createMockSteps = (count: number) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `step-${i}`,
    label: `步骤 ${i + 1}`,
    content: <div key={i}>步骤 {i + 1} 内容</div>,
    canProceed: true,
  }));
};

/* ── Tests ── */

describe('ImportWizard', () => {
  it('应该渲染步骤指示器', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={0} />);

    expect(screen.getByText('步骤 1')).toBeTruthy();
    expect(screen.getByText('步骤 2')).toBeTruthy();
    expect(screen.getByText('步骤 3')).toBeTruthy();
  });

  it('应该渲染当前步骤的内容', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={0} />);

    expect(screen.getByText('步骤 1 内容')).toBeTruthy();
  });

  it('应该在高步数时显示下一步按钮', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={0} />);

    expect(screen.getByText('下一步')).toBeTruthy();
  });

  it('在最后一步应该显示完成按钮', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={2} />);

    expect(screen.getByText('完成')).toBeTruthy();
  });

  it('在第一一步不应该显示上一步按钮', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={0} />);

    expect(screen.queryByText('上一步')).toBeNull();
  });

  it('在后续步骤应该显示上一步按钮', () => {
    const steps = createMockSteps(3);
    render(<ImportWizard steps={steps} currentStep={1} />);

    expect(screen.getByText('上一步')).toBeTruthy();
  });

  it('点击下一步应该触发 onStepChange', () => {
    const onStepChange = vi.fn();
    const steps = createMockSteps(3);
    render(
      <ImportWizard
        steps={steps}
        currentStep={0}
        onStepChange={onStepChange}
      />
    );

    fireEvent.click(screen.getByText('下一步'));
    expect(onStepChange).toHaveBeenCalledWith(1);
  });

  it('点击上一步应该触发 onStepChange', () => {
    const onStepChange = vi.fn();
    const steps = createMockSteps(3);
    render(
      <ImportWizard
        steps={steps}
        currentStep={1}
        onStepChange={onStepChange}
      />
    );

    fireEvent.click(screen.getByText('上一步'));
    expect(onStepChange).toHaveBeenCalledWith(0);
  });

  it('点击完成应该触发 onComplete', () => {
    const onComplete = vi.fn();
    const steps = createMockSteps(3);
    render(
      <ImportWizard
        steps={steps}
        currentStep={2}
        onComplete={onComplete}
      />
    );

    fireEvent.click(screen.getByText('完成'));
    expect(onComplete).toHaveBeenCalledOnce();
  });

  it('应该使用自定义按钮标签', () => {
    const steps = createMockSteps(3);
    render(
      <ImportWizard
        steps={steps}
        currentStep={0}
        nextLabel="继续"
        backLabel="返回"
        completeLabel="确认"
      />
    );

    expect(screen.getByText('继续')).toBeTruthy();
  });

  it('在最后一步应该显示自定义完成标签', () => {
    const steps = createMockSteps(3);
    render(
      <ImportWizard
        steps={steps}
        currentStep={2}
        completeLabel="确认"
      />
    );

    expect(screen.getByText('确认')).toBeTruthy();
  });

  it('当 canProceed 为 false 时应该禁用下一步按钮', () => {
    const steps = [
      {
        id: 'step-0',
        label: '步骤 1',
        content: <div>内容</div>,
        canProceed: false,
      },
      {
        id: 'step-1',
        label: '步骤 2',
        content: <div>内容2</div>,
      },
    ];
    render(<ImportWizard steps={steps} currentStep={0} />);

    const nextButton = screen.getByText('下一步');
    expect(nextButton.hasAttribute('disabled')).toBeTruthy();
  });

  it('should not show step indicator when showStepIndicator is false', () => {
    const steps = createMockSteps(3);
    const { container } = render(
      <ImportWizard steps={steps} currentStep={0} showStepIndicator={false} />
    );

    const stepIndicator = container.querySelector('[class*="stepIndicator"]');
    expect(stepIndicator).toBeNull();
  });

  it('should not show navigation when showNavigation is false', () => {
    const steps = createMockSteps(3);
    const { container } = render(
      <ImportWizard steps={steps} currentStep={0} showNavigation={false} />
    );

    const navigation = container.querySelector('[class*="navigation"]');
    expect(navigation).toBeNull();
  });
});
