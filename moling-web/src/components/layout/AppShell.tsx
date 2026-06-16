"use client";

import { memo, useState, useEffect, useCallback, Suspense } from "react";
import { usePathname } from "next/navigation";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";
import { BottomNav } from "./BottomNav";
import { useTouchGesture } from "@/hooks/useTouchGesture";
import styles from "./AppShell.module.css";

const SIDEBAR_COLLAPSED_KEY = "moling-sidebar-collapsed";

// 加载状态组件
function LoadingFallback() {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      height: '100vh',
      background: 'var(--color-bg)'
    }}>
      <div>加载中...</div>
    </div>
  );
}

// 专注模式检测组件（使用 window.location 而非 useSearchParams）
function FocusModeDetector({ focusMode, onFocusModeChange }: { 
  focusMode: boolean; 
  onFocusModeChange: (mode: boolean) => void;
}) {
  // 客户端检测 URL 参数
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const focus = params.get("focus") === "true";
      onFocusModeChange(focus);
    }
  }, []);

  return null;
}

export const AppShell = memo(function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [focusMode, setFocusMode] = useState(false);

  // 客户端初始化：从 localStorage 读取折叠状态
  useEffect(() => {
    setIsClient(true);
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (saved !== null) {
      setSidebarCollapsed(JSON.parse(saved));
    }
  }, []);

  // 持久化折叠状态到 localStorage
  useEffect(() => {
    if (isClient) {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(sidebarCollapsed));
    }
  }, [sidebarCollapsed, isClient]);

  // 检测屏幕尺寸
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);
    return () => window.removeEventListener("resize", checkScreenSize);
  }, []);

  // 键盘快捷键：Esc 切换专注模式
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        const newFocusMode = !focusMode;
        setFocusMode(newFocusMode);
        // 更新 URL（不刷新页面）
        const url = new URL(window.location.href);
        if (newFocusMode) {
          url.searchParams.set("focus", "true");
        } else {
          url.searchParams.delete("focus");
        }
        window.history.pushState(null, "", url.toString());
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [focusMode]);

  // 手势操作
  useTouchGesture(
    {
      onSwipeLeft: () => {
        // 左滑 → 打开参考面板（如果在工作台）
        if (pathname?.startsWith("/workspace")) {
          window.dispatchEvent(new CustomEvent("open-reference-panel"));
        }
      },
      onSwipeRight: () => {
        // 右滑 → 打开 AI 面板（如果在工作台）
        if (pathname?.startsWith("/workspace")) {
          window.dispatchEvent(new CustomEvent("open-ai-panel"));
        }
      },
      onSwipeUp: () => {
        // 上滑 → 显示导航
        if (focusMode) {
          setFocusMode(false);
          const url = new URL(window.location.href);
          url.searchParams.delete("focus");
          window.history.pushState(null, "", url.toString());
        }
      },
      onSwipeDown: () => {
        // 下滑 → 隐藏导航（如果在编辑器）
        if (pathname?.startsWith("/workspace") || pathname?.startsWith("/editor")) {
          setFocusMode(true);
          const url = new URL(window.location.href);
          url.searchParams.set("focus", "true");
          window.history.pushState(null, "", url.toString());
        }
      },
    },
    { swipeThreshold: 50 },
  );

  const isSimplePage =
    pathname === "/" ||
    pathname?.startsWith("/landing") ||
    pathname?.startsWith("/auth");

  if (isSimplePage) return <>{children}</>;

  // 移动端：根据 focusMode 决定是否显示导航
  if (isMobile) {
    return (
      <div className={styles.shell}>
        <Suspense fallback={null}>
          <FocusModeDetector focusMode={focusMode} onFocusModeChange={setFocusMode} />
        </Suspense>
        {!focusMode && <Navbar />}
        <main className={`${styles.main} ${focusMode ? styles.mainFullscreen : ""}`}>
          {children}
        </main>
        {!focusMode && <BottomNav />}
      </div>
    );
  }

  // Web端：根据 focusMode 决定是否显示侧边栏
  return (
    <div className={styles.layoutWithSidebar}>
      <Suspense fallback={null}>
        <FocusModeDetector focusMode={focusMode} onFocusModeChange={setFocusMode} />
      </Suspense>
      {!focusMode && (
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      )}
      <main className={`${styles.main} ${focusMode ? styles.mainFullscreen : ""} ${sidebarCollapsed && !focusMode ? styles.mainCollapsed : ""}`}>
        {children}
      </main>
    </div>
  );
});
