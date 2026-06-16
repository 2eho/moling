"use client";

import { memo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useProjectContext } from "@/contexts/ProjectContext";
import styles from "./Sidebar.module.css";

const navItems = [
  { href: "/projects", label: "项目", icon: "📚" },
  { href: "/workspace", label: "写作", icon: "✒️" },
  { href: "/vaults", label: "四库", icon: "📖" },
  { href: "/notifications", label: "通知", icon: "🔔" },
];

const bottomNavItems = [{ href: "/settings", label: "设置", icon: "⚙️" }];

export const Sidebar = memo(function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();
  const [projectSwitcherOpen, setProjectSwitcherOpen] = useState(false);
  const { projects, currentProject } = useProjectContext();

  const isActive = (href: string) => {
    return pathname === href || pathname?.startsWith(href + "/");
  };

  // 获取最近工作的项目 ID
  const getDefaultProjectId = () => {
    if (currentProject?.id) return currentProject.id;
    if (projects && projects.length > 0) return projects[0].id;
    return null;
  };

  const defaultProjectId = getDefaultProjectId();

  // 生成带 projectId 的链接
  const getWorkspaceHref = () => {
    if (defaultProjectId) return `/workspace/${defaultProjectId}`;
    return "/projects"; // 没有项目时，跳转到项目列表
  };

  const getVaultsHref = () => {
    if (defaultProjectId) return `/vaults/${defaultProjectId}`;
    return "/projects";
  };

  return (
    <aside className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}>
      {/* Header: Logo + Toggle */}
      <div className={styles.header}>
        {!collapsed && (
          <Link href="/projects" className={styles.logo}>
            <span className={styles.logoIcon}>✒️</span>
            <span className={styles.logoText}>墨灵</span>
          </Link>
        )}
        <button
          className={styles.toggleBtn}
          onClick={onToggle}
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
          aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? "→" : "←"}
        </button>
      </div>

      {/* Project Switcher */}
      {!collapsed && (
        <div className={styles.projectSwitcher}>
          <button
            className={styles.projectSwitcherBtn}
            onClick={() => setProjectSwitcherOpen(!projectSwitcherOpen)}
            title="切换项目"
          >
            <span className={styles.projectName}>
              {currentProject?.title || projects?.[0]?.title || "未选择项目"}
            </span>
            <span className={styles.projectSwitcherArrow}>▾</span>
          </button>
          {projectSwitcherOpen && (
            <div className={styles.projectDropdown}>
              {projects?.map((project) => (
                <Link
                  key={project.id}
                  href={`/workspace/${project.id}`}
                  className={styles.projectDropdownItem}
                  onClick={() => setProjectSwitcherOpen(false)}
                >
                  {project.title}
                </Link>
              ))}
              <div className={styles.projectDropdownDivider} />
              <Link
                href="/projects"
                className={styles.projectDropdownItem}
                onClick={() => setProjectSwitcherOpen(false)}
              >
                管理项目...
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className={styles.nav}>
        <Link
          href="/projects"
          className={`${styles.navItem} ${isActive("/projects") ? styles.active : ""}`}
          title={collapsed ? "项目" : undefined}
        >
          <span className={styles.navIcon}>📚</span>
          {!collapsed && <span className={styles.navLabel}>项目</span>}
        </Link>
        <Link
          href={getWorkspaceHref()}
          className={`${styles.navItem} ${isActive("/workspace") ? styles.active : ""}`}
          title={collapsed ? "写作" : undefined}
        >
          <span className={styles.navIcon}>✒️</span>
          {!collapsed && <span className={styles.navLabel}>写作</span>}
        </Link>
        <Link
          href={getVaultsHref()}
          className={`${styles.navItem} ${isActive("/vaults") ? styles.active : ""}`}
          title={collapsed ? "四库" : undefined}
        >
          <span className={styles.navIcon}>📖</span>
          {!collapsed && <span className={styles.navLabel}>四库</span>}
        </Link>
        <Link
          href="/notifications"
          className={`${styles.navItem} ${isActive("/notifications") ? styles.active : ""}`}
          title={collapsed ? "通知" : undefined}
        >
          <span className={styles.navIcon}>🔔</span>
          {!collapsed && <span className={styles.navLabel}>通知</span>}
        </Link>
      </nav>

      {/* Bottom: Settings */}
      <div className={styles.bottomNav}>
        {bottomNavItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.active : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
            </Link>
          );
        })}
      </div>
    </aside>
  );
});
