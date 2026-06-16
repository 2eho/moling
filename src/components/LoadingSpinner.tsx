import React from 'react';
import styles from './LoadingSpinner.module.css';

export type SpinnerSize = 'sm' | 'md' | 'lg' | 'xl';
export type SpinnerColor = 'indigo' | 'amber' | 'white';

interface LoadingSpinnerProps {
  /** 尺寸 */
  size?: SpinnerSize;
  /** 颜色 */
  color?: SpinnerColor;
  /** 自定义类名 */
  className?: string;
  /** 无障碍标签 */
  ariaLabel?: string;
}

/**
 * 统一加载 spinner 组件
 * 支持多种尺寸和品牌色
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  color = 'indigo',
  className = '',
  ariaLabel = '加载中...',
}) => {
  const spinnerClass = [
    styles.spinner,
    styles[size],
    styles[color],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={styles.spinnerContainer} role="status" aria-label={ariaLabel}>
      <div className={spinnerClass} />
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
};

export default LoadingSpinner;
