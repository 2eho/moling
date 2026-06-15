"use client";

import { memo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";

const navItems = [
  { href: "/projects", label: "项目", icon: "📚" },
  { href: "/characters", label: "角色", icon: "👤" },
  { href: "/chapters", label: "章节", icon: "📝" },
  { href: "/prompts", label: "提示词", icon: "✨" },
  { href: "/settings", label: "设置", icon: "⚙️" },
];

export const Sidebar = memo(function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}>
      <div className={styles.header}>
        {!collapsed && (
          <Link href="/projects" className={styles.logo}>
            <span className={styles.logoIcon}>✒</span>
            <span className={styles.logoText}>墨灵</span>
          </Link>
        )}
        <button
          className={styles.toggleBtn}
          onClick={onToggle}
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? "→" : "←"}
        </button>
      </div>

      <nav className={styles.nav}>
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${isActive ? styles.active : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
});
