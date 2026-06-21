import type { Metadata } from "next";
import { ThemeInitializer } from "@/components/vibe/ThemeInitializer";
import { GlobalErrorBoundary } from "@/components/GlobalErrorBoundary";
import { ToastContainer } from "@/components/ToastContainer";
import { QueryProvider } from "@/components/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "墨灵 — Vibe Writing",
  description: "墨灵 · 智能创作引擎 — 选择推进，灵感不中断",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" data-theme="moling" suppressHydrationWarning>
      <body>
        <ThemeInitializer />
        <QueryProvider>
          <GlobalErrorBoundary>{children}</GlobalErrorBoundary>
        </QueryProvider>
        <ToastContainer />
      </body>
    </html>
  );
}
