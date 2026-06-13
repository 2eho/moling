"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { LandingPage } from "@/components/landing/LandingPage";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    // 如果已登录，重定向到项目列表页
    if (!isLoading && isAuthenticated) {
      // 检查是否有最后一个访问的项目
      const lastProjectId = localStorage.getItem("lastProjectId");
      if (lastProjectId) {
        router.push(`/workspace/${lastProjectId}`);
      } else {
        router.push("/projects");
      }
    }
  }, [isLoading, isAuthenticated, router]);

  // 如果正在加载认证状态，显示加载界面
  if (isLoading) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0d0f1a",
        color: "#a0a0a0",
      }}>
        加载中...
      </div>
    );
  }

  // 如果未登录，显示 Landing Page
  if (!isAuthenticated) {
    return <LandingPage />;
  }

  // 已登录的情况会在 useEffect 中重定向，这里返回 null
  return null;
}
