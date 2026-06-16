import React, { ErrorInfo, useState } from 'react';
import styles from './ErrorBoundary.module.css';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * 全局错误边界组件
 * 捕获所有React渲染错误，显示友好错误提示
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // 记录错误到控制台（便于调试）
    console.error('[ErrorBoundary] 捕获到渲染错误:', error);
    console.error('[ErrorBoundary] 错误堆栈:', errorInfo.componentStack);

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = (): void => {
    window.location.reload();
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <ErrorBoundaryFallback
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onReload={this.handleReload}
          onGoHome={this.handleGoHome}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * 错误边界降级UI组件
 */
interface ErrorBoundaryFallbackProps {
  error: Error | null;
  errorInfo: ErrorInfo | null;
  onReload: () => void;
  onGoHome: () => void;
}

const ErrorBoundaryFallback: React.FC<ErrorBoundaryFallbackProps> = ({
  error,
  errorInfo,
  onReload,
  onGoHome,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className={styles.errorBoundary}>
      <div className={styles.contentWrapper}>
        {/* 错误图标 */}
        <div className={styles.iconWrapper}>
          <span className={styles.icon}>⚠️</span>
        </div>

        {/* 错误标题 */}
        <h1 className={styles.title}>页面出现错误</h1>

        {/* 错误描述 */}
        <p className={styles.description}>
          抱歉，页面渲染时发生意外错误。请尝试重新加载或返回首页。
        </p>

        {/* 错误详情（开发环境下可展开） */}
        {(error || errorInfo) && (
          <div className={styles.errorDetails}>
            <summary
              className={styles.errorDetailsSummary}
              onClick={() => setShowDetails(!showDetails)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  setShowDetails(!showDetails);
                }
              }}
              role="button"
              tabIndex={0}
            >
              {showDetails ? '隐藏错误详情 ▲' : '查看错误详情 ▼'}
            </summary>
            {showDetails && (
              <pre className={styles.errorStack}>
                {error?.toString()}
                {'\n\n'}
                {errorInfo?.componentStack}
              </pre>
            )}
          </div>
        )}

        {/* 按钮组 */}
        <div className={styles.buttonGroup}>
          <button
            className={styles.reloadButton}
            onClick={onReload}
            type="button"
          >
            <svg
              width="20"
              height="20"
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
            重新加载
          </button>

          <button
            className={styles.homeButton}
            onClick={onGoHome}
            type="button"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            返回首页
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorBoundary;
