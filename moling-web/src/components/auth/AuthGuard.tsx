"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Spinner } from "@/components/ui/Spinner";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard — 路由级认证守卫。
 * 未登录用户自动重定向到 /auth，避免闪现受保护页面内容。
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/auth");
    }
  }, [isAuthenticated, isLoading, router]);

  // 认证状态未就绪时，显示加载（不闪烁受保护内容）
  if (isLoading || !isAuthenticated) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--color-bg, #0d0f1a)",
        }}
      >
        <Spinner />
      </div>
    );
  }

  return <>{children}</>;
}
