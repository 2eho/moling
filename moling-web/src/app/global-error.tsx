"use client";

import * as Sentry from "@sentry/nextjs";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  Sentry.captureException(error);

  return (
    <ErrorBoundary
      fallback={
        <div className="error-container">
          <h2>抱歉，出现了意外错误</h2>
          <p>{error.message || "未知错误"}</p>
          <button onClick={() => reset()}>重试</button>
        </div>
      }
    >
      <div>重新加载中...</div>
    </ErrorBoundary>
  );
}
