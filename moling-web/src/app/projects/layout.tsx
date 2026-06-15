"use client";

import { ProjectProvider } from "@/contexts/ProjectContext";
import type { ReactNode } from "react";

/**
 * Projects Layout
 * 
 * 注意：不在子布局中重复 Navbar
 * 所有导航由 Root Layout 的 AppShell 统一管理
 * AppShell 会根据屏幕尺寸自动切换：
 * - Web端（> 768px）：侧边栏导航
 * - 移动端（≤ 768px）：顶部导航 + 底部导航
 */
export default function ProjectsLayout({ children }: { children: ReactNode }) {
  return (
    <ProjectProvider>
      {children}
    </ProjectProvider>
  );
}
