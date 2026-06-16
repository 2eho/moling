"use client";

import { memo, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjectContext } from "@/contexts/ProjectContext";
import styles from "./BottomNav.module.css";

const mainNavItems = [
  { href: "/workspace", label: "写作", icon: "✒️" },
  { href: "/vaults", label: "四库", icon: "📖" },
];

const moreMenuItems = [
  { href: "/projects", label: "切换项目", icon: "📚" },
  { href: "/notifications", label: "通知", icon: "🔔" },
  { href: "/settings", label: "设置", icon: "⚙️" },
  { href: "/profile", label: "个人资料", icon: "👤" },
];

export const BottomNav = memo(function BottomNav() {
  const pathname = usePathname();
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const { currentProject, projects } = useProjectContext();

  // 获取默认项目 ID
  const getDefaultProjectId = () => {
    if (currentProject?.id) return currentProject.id;
    if (projects && projects.length > 0) return projects[0].id;
    return null;
  };

  const defaultProjectId = getDefaultProjectId();

  // 生成带 projectId 的链接
  const getWorkspaceHref = () => {
    if (defaultProjectId) return `/workspace/${defaultProjectId}`;
    return "/projects";
  };

  const getVaultsHref = () => {
    if (defaultProjectId) return `/vaults/${defaultProjectId}`;
    return "/projects";
  };

  // 点击外部区域关闭更多菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        moreMenuRef.current &&
        !moreMenuRef.current.contains(event.target as Node)
      ) {
        setMoreMenuOpen(false);
      }
    };

    if (moreMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside as any);
      document.addEventListener("touchstart", handleClickOutside as any);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside as any);
      document.removeEventListener("touchstart", handleClickOutside as any);
    };
  }, [moreMenuOpen]);

  // 检查当前页面是否活跃
  const isActive = (href: string) => {
    return pathname === href || pathname?.startsWith(href + "/");
  };

  return (
    <nav className={styles.bottomNav}>
      {/* 主导航项（2个） */}
      <Link
        href={getWorkspaceHref()}
        className={`${styles.navItem} ${isActive("/workspace") ? styles.active : ""}`}
      >
        <span className={styles.navIcon}>✒️</span>
        <span className={styles.navLabel}>写作</span>
      </Link>

      <Link
        href={getVaultsHref()}
        className={`${styles.navItem} ${isActive("/vaults") ? styles.active : ""}`}
      >
        <span className={styles.navIcon}>📖</span>
        <span className={styles.navLabel}>四库</span>
      </Link>

      {/* 更多菜单按钮 */}
      <button
        className={`${styles.navItem} ${styles.moreBtn} ${moreMenuOpen ? styles.active : ""}`}
        onClick={() => setMoreMenuOpen(!moreMenuOpen)}
        aria-label="更多功能"
      >
        <span className={styles.navIcon}>⋮</span>
        <span className={styles.navLabel}>更多</span>
      </button>

      {/* 更多菜单弹出层 */}
      {moreMenuOpen && (
        <div className={styles.moreMenu} ref={moreMenuRef}>
          {moreMenuItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={styles.moreMenuItem}
              onClick={() => setMoreMenuOpen(false)}
            >
              <span className={styles.moreMenuIcon}>{item.icon}</span>
              <span className={styles.moreMenuLabel}>{item.label}</span>
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
});
