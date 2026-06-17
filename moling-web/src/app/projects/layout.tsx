"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import type { ReactNode } from "react";

/**
 * Projects Layout
 * 
 * 路由守卫：未登录用户重定向到 /auth
 * 
 * 注意：不在子布局中重复 ProjectProvider
 * - 根 Providers 已包含 ProjectProvider（全局单例）
 * - 内层 Provider 会导致状态隔离 → 创建作品后在 workspace 更新 state，
 *   返回 projects 时内层 Provider 独立初始化，列表不同步
 * - 所有页面共享根布局的同一 ProjectProvider，创建/更新操作即时反映
 */
export default function ProjectsLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  );
}
