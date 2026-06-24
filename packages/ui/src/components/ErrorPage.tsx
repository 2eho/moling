"use client";
import { useEffect } from "react";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
  title?: string;
};

/** Report error to monitoring service when available. */
function reportToMonitoring(error: Error): void {
  if (typeof window === "undefined") return;
  const win = window as Window & { Sentry?: { captureException: (e: Error) => void } };
  win.Sentry?.captureException(error);
}

export function ErrorPage({ error, reset, title = "出错了" }: ErrorPageProps) {
  useEffect(() => {
    reportToMonitoring(error);
  }, [error]);

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-xl font-semibold text-red-600">{title}</h2>
      <p className="text-sm text-gray-500">{error.message || "页面加载异常，请稍后重试"}</p>
      <button
        type="button"
        onClick={reset}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
      >
        重试
      </button>
    </div>
  );
}
