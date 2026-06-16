import React from 'react';
import LoadingSpinner from './LoadingSpinner';
import styles from './LoadingOverlay.module.css';

export type OverlayVariant = 'dark' | 'light' | 'white';

interface LoadingOverlayProps {
  /** 是否显示 */
  show: boolean;
  /** 加载文字 */
  text?: string;
  /** 背景变体 */
  variant?: OverlayVariant;
  /** 是否全屏（false时为内联覆盖） */
  fullscreen?: boolean;
  /** 自定义类名 */
  className?: string;
}

/**
 * 全屏/局部加载覆盖层组件
 * 支持半透明背景 + 模糊效果
 */
const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  show,
  text = '加载中...',
  variant = 'dark',
  fullscreen = true,
  className = '',
}) => {
  if (!show) return null;

  const overlayClass = [
    styles.overlay,
    styles[variant],
    !fullscreen && styles.inline,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={overlayClass} role="status" aria-live="polite">
      <div className={styles.content}>
        <LoadingSpinner size="lg" color="indigo" />
        {text && <p className={styles.text}>{text}</p>}
      </div>
    </div>
  );
};

export default LoadingOverlay;
