"use client";

import { memo, useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { BottomNav } from "./BottomNav";
import styles from "./AppShell.module.css";

export const AppShell = memo(function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 检测屏幕尺寸
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, []);

  const isSimplePage =
    pathname === "/" ||
    pathname?.startsWith("/landing") ||
    pathname?.startsWith("/auth");

  if (isSimplePage) return <>{children}</>;

  // 移动端：顶部导航栏 + 底部导航栏
  if (isMobile) {
    return (
      <div className={styles.shell}>
        <Navbar />
        <main className={styles.main}>{children}</main>
        <BottomNav />
      </div>
    );
  }

  // Web端：侧边栏 + 主内容区
  return (
    <div className={styles.layoutWithSidebar}>
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <main className={`${styles.main} ${sidebarCollapsed ? styles.mainCollapsed : ""}`}>
        {children}
      </main>
    </div>
  );
});
