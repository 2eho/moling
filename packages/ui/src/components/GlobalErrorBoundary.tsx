"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(_error: Error, _errorInfo: ErrorInfo) {
    // Error is surfaced in UI via state — no console logging in production
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-th-bg text-th-text">
          <div className="text-center max-w-sm px-6">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 bg-th-accent-dim">
              <AlertTriangle size={28} className="text-[var(--th-warning)]" />
            </div>
            <h2 className="text-base font-semibold mb-2 text-th-text">页面出错了</h2>
            <p className="text-xs leading-relaxed mb-5 text-th-text-3">
              {this.state.error?.message || "发生了一个意外错误，请尝试刷新页面。"}
            </p>
            <button
              type="button"
              onClick={this.handleRetry}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-medium transition-all hover:opacity-90 active:scale-95 bg-th-accent-dim text-th-accent-text"
            >
              <RefreshCw size={13} />
              <span>重试</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
