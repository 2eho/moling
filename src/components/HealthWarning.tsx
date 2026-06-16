import React, { useState, useEffect, useCallback } from 'react';
import healthCheckService from '../lib/healthCheck';
import styles from './HealthWarning.module.css';

interface HealthWarningProps {
  /** 是否显示关闭按钮 */
  closable?: boolean;
}

/**
 * 后端离线警告条组件
 * 当后端离线时，在顶部显示警告条
 */
const HealthWarning: React.FC<HealthWarningProps> = ({ closable = true }) => {
  const [isOnline, setIsOnline] = useState(true);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  // 处理健康检查状态变化
  const handleStatusChange = useCallback(
    (status: { isOnline: boolean }) => {
      setIsOnline(status.isOnline);
      if (!status.isOnline) {
        setIsVisible(true);
      }
    },
    []
  );

  // 订阅健康检查状态
  useEffect(() => {
    const unsubscribe = healthCheckService.subscribe(handleStatusChange);
    return unsubscribe;
  }, [handleStatusChange]);

  // 启动健康检查
  useEffect(() => {
    healthCheckService.start();
    return () => {
      healthCheckService.stop();
    };
  }, []);

  // 处理重试
  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await healthCheckService.check();
    } finally {
      setIsRetrying(false);
    }
  };

  // 处理关闭
  const handleClose = () => {
    setIsVisible(false);
  };

  // 如果在线或不可见，不渲染
  if (isOnline || !isVisible) {
    return null;
  }

  return (
    <div className={styles.warningBar} role="alert" aria-live="assertive">
      {/* 警告图标 */}
      <span className={styles.icon}>⚠️</span>

      {/* 警告文字 */}
      <p className={styles.text}>
        后端服务离线，部分功能可能不可用。请检查网络连接或稍后重试。
      </p>

      {/* 重试按钮 */}
      <button
        className={styles.retryButton}
        onClick={handleRetry}
        disabled={isRetrying}
        type="button"
        aria-label="重试连接"
      >
        <svg
          className={isRetrying ? styles.spinning : ''}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
        {isRetrying ? '连接中...' : '重试连接'}
      </button>

      {/* 关闭按钮 */}
      {closable && (
        <button
          className={styles.closeButton}
          onClick={handleClose}
          type="button"
          aria-label="关闭警告"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
};

export default HealthWarning;
