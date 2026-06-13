"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import styles from "./Navbar.module.css";

export function Navbar() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className={styles.navbar}>
      <div className={styles.left}>
        <Link href="/projects" className={styles.logo}>
          <span className={styles.logoIcon}>✒</span>
          <span className={styles.logoText}>墨灵</span>
        </Link>
      </div>

      <div className={styles.center}>
        <span className={styles.appName}>AI 小说创作平台</span>
      </div>

      <div className={styles.right}>
        <div className={styles.userSection}>
          <button
            className={styles.avatarBtn}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <span className={styles.avatar}>
              {user?.username?.charAt(0) ?? "U"}
            </span>
          </button>

          {menuOpen && (
            <>
              <div
                className={styles.backdrop}
                onClick={() => setMenuOpen(false)}
              />
              <div className={styles.dropdown}>
                <div className={styles.userInfo}>
                  <span className={styles.userName}>
                    {user?.username ?? "用户"}
                  </span>
                  <span className={styles.userEmail}>
                    {user?.email ?? ""}
                  </span>
                </div>
                <div className={styles.divider} />
                <button
                  className={styles.menuItem}
                  onClick={() => setMenuOpen(false)}
                >
                  个人设置
                </button>
                <button
                  className={`${styles.menuItem} ${styles.danger}`}
                  onClick={logout}
                >
                  退出登录
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
