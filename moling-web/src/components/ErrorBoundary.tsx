"use client";

import React from "react";
import styles from "./ErrorBoundary.module.css";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorId: string | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    const errorId =
      `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    console.error(`[ErrorBoundary ${errorId}]:`, error);
    return {
      hasError: true,
      error,
      errorId,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`[ErrorBoundary]:`, error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorId: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className={styles.container}>
          <div className={styles.content}>
            <div className={styles.icon}>⚠️</div>
            <h2 className={styles.title}>抱歉，出现了意外错误</h2>
            <p className={styles.message}>
              我们已经记录了这个问题，请稍后重试。
            </p>

            {this.state.errorId && (
              <p className={styles.errorId}>
                错误ID: {this.state.errorId}
              </p>
            )}

            <div className={styles.actions}>
              <button
                className={styles.retryButton}
                onClick={this.handleRetry}
              >
                🔄 重试
              </button>
              <button
                className={styles.homeButton}
                onClick={() => (window.location.href = "/")}
              >
                🏠 返回首页
              </button>
            </div>

            {process.env.NODE_ENV === "development" && this.state.error && (
              <details className={styles.details}>
                <summary>错误详情（开发模式）</summary>
                <pre className={styles.stack}>
                  {this.state.error.toString()}
                  {"\n\n"}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
