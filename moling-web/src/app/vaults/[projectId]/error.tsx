"use client";
import { useEffect } from "react";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-xl font-semibold text-red-600">出错了</h2>
      <p className="text-sm text-gray-500">{error.message || "页面加载异常，请稍后重试"}</p>
      <button onClick={reset} className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700">重试</button>
    </div>
  );
}
