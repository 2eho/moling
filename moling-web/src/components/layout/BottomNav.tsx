"use client";

import { memo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./BottomNav.module.css";

const bottomNavItems = [
  { href: "/projects", label: "项目", icon: "📚" },
  { href: "/characters", label: "角色", icon: "👤" },
  { href: "/chapters", label: "章节", icon: "📝" },
  { href: "/prompts", label: "提示词", icon: "✨" },
  { href: "/settings", label: "设置", icon: "⚙️" },
];

export const BottomNav = memo(function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.bottomNav}>
      {bottomNavItems.map((item) => {
        const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`${styles.navItem} ${isActive ? styles.active : ""}`}
          >
            <span className={styles.navIcon}>{item.icon}</span>
            <span className={styles.navLabel}>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
});
