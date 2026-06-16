"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { adminApi } from "@/lib/api";
import type { AdminUser } from "@/lib/types";
import { showToast } from "@/components/ui/Toast";
import parentStyles from "../../admin.module.css";
import styles from "./UsersTab.module.css";

const PAGE_SIZE = 10;
const FILTER_TABS = ["全部", "管理员", "普通用户", "VIP"];

type SortField = "username" | "email" | "created_at" | "status";
type SortDir = "asc" | "desc";

function getRoleBadge(role: string) {
  switch (role) {
    case "admin":
      return <span className={parentStyles.badgeAdmin}><span className={parentStyles.badgeDot}></span>管理员</span>;
    case "vip":
      return <span className={parentStyles.badgeVip}><span className={parentStyles.badgeDot}></span>VIP</span>;
    default:
      return <span className={parentStyles.badgeUser}><span className={parentStyles.badgeDot}></span>用户</span>;
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case "active":
      return <span className={parentStyles.badgeActive}><span className={parentStyles.badgeDot}></span>活跃</span>;
    case "banned":
      return <span className={parentStyles.badgeBanned}><span className={parentStyles.badgeDot}></span>封禁</span>;
    default:
      return <span className={parentStyles.badgePending}><span className={parentStyles.badgeDot}></span>未激活</span>;
  }
}

function getInitial(name: string): string {
  return name.charAt(0).toUpperCase();
}

export default function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [filterTab, setFilterTab] = useState("全部");
  const [sortField] = useState<SortField>("created_at");
  const [sortDir] = useState<SortDir>("desc");
  const [actingUserId, setActingUserId] = useState<string | null>(null);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Debounced search ──
  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPage(1);
    }, 300);
  }, []);

  // ── Fetch users ──
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.listUsers({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
      });
      const usersData = res.data as AdminUser[] | { items: AdminUser[]; total: number };
      if (Array.isArray(usersData)) {
        setUsers(usersData);
        // If total is in a response wrapper, try to get it
        setTotalCount((res as unknown as { total?: number }).total ?? usersData.length);
      } else if (usersData && "items" in usersData) {
        setUsers(usersData.items);
        setTotalCount(usersData.total);
      } else {
        setUsers([]);
        setTotalCount(0);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "获取用户列表失败");
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, [page, debouncedSearch]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // ── Sort (client-side for simplicity) ──
  const sortedUsers = [...users].sort((a, b) => {
    const aVal = String(a[sortField] ?? "");
    const bVal = String(b[sortField] ?? "");
    const cmp = aVal.localeCompare(bVal);
    return sortDir === "asc" ? cmp : -cmp;
  });

  // ── Filter (client-side role filter) ──
  const filteredUsers = filterTab === "全部"
    ? sortedUsers
    : sortedUsers.filter((u) => {
        if (filterTab === "管理员") return u.role === "admin";
        if (filterTab === "VIP") return u.role === "vip";
        return u.role === "user";
      });

  // ── Toggle user status ──
  const toggleUserStatus = useCallback(async (user: AdminUser) => {
    setActingUserId(user.id);
    try {
      // TODO: 后端暂未实现 updateUser 端点
      const newStatus = user.status === "active" ? "banned" : "active";
      showToast("error", "用户状态切换功能暂未实现");
      // await adminApi.updateUser(user.id, { status: newStatus } as Partial<AdminUser>);
      // showToast("success", `用户 ${user.username} 已${newStatus === "active" ? "启用" : "禁用"}`);
      // Refresh list
      // fetchUsers();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "操作失败");
    } finally {
      setActingUserId(null);
    }
  }, [fetchUsers]);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const renderPagination = () => {
    const pages: (number | "ellipsis")[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (page > 3) pages.push("ellipsis");
      for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
        pages.push(i);
      }
      if (page < totalPages - 2) pages.push("ellipsis");
      pages.push(totalPages);
    }

    return (
      <div className={parentStyles.tablePagination}>
        <span className={parentStyles.paginationInfo}>
          显示 {users.length > 0 ? `${(page - 1) * PAGE_SIZE + 1}-${Math.min(page * PAGE_SIZE, totalCount)}` : "0"} 条，共 {totalCount} 条
        </span>
        <div className={parentStyles.paginationBtns}>
          <button
            className={page <= 1 ? parentStyles.paginationBtnDisabled : parentStyles.paginationBtn}
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            ‹
          </button>
          {pages.map((p, i) =>
            p === "ellipsis" ? (
              <span key={`e${i}`} className={parentStyles.paginationBtn} style={{cursor:"default", color:"var(--color-text-disabled)"}}>⋯</span>
            ) : (
              <button
                key={p}
                className={p === page ? parentStyles.paginationBtnActive : parentStyles.paginationBtn}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            )
          )}
          <button
            className={page >= totalPages ? parentStyles.paginationBtnDisabled : parentStyles.paginationBtn}
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            ›
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className={`${parentStyles.tabPanelActive}`}>
      <div className={parentStyles.pageTitleRow}>
        <div>
          <h1 className={parentStyles.pageTitle}>用户管理</h1>
          <p className={parentStyles.pageSubtitle}>查看和管理平台用户</p>
        </div>
      </div>

      <div className={parentStyles.filterPanel}>
        <div className={parentStyles.filterTabs}>
          {FILTER_TABS.map((t) => (
            <button
              key={t}
              className={filterTab === t ? parentStyles.filterTabActive : parentStyles.filterTab}
              onClick={() => setFilterTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className={parentStyles.filterSearchWrap}>
          <span className={parentStyles.filterSearchIcon}>🔍</span>
          <input
            className={parentStyles.filterSearch}
            type="text"
            placeholder="搜索用户昵称/邮箱..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className={parentStyles.tableCard}>
          <div className={styles.loadingState}>
            <div className={styles.loadingSpinner}></div>
            <span className={styles.loadingText}>加载用户列表...</span>
          </div>
        </div>
      ) : error ? (
        <div className={parentStyles.tableCard}>
          <div className={styles.errorState}>
            <div className={styles.errorIcon}>⚠️</div>
            <div className={styles.errorText}>加载失败</div>
            <div className={styles.errorHint}>{error}</div>
            <button className={styles.retryBtn} onClick={fetchUsers}>重新加载</button>
          </div>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className={parentStyles.tableCard}>
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>👥</div>
            <div className={styles.emptyText}>
              {debouncedSearch ? "未找到匹配的用户" : "暂无用户数据"}
            </div>
            <div className={styles.emptyHint}>
              {debouncedSearch ? "尝试修改搜索关键词" : "等待用户注册"}
            </div>
          </div>
        </div>
      ) : (
        <div className={parentStyles.tableCard}>
          <table className={parentStyles.dataTable}>
            <thead>
              <tr>
                <th className={parentStyles.colAvatar}>头像</th>
                <th className="sortable">昵称</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>项目数</th>
                <th>注册时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((u) => (
                <tr key={u.id} className={actingUserId === u.id ? styles.actingOn : ""}>
                  <td>
                    <div className={parentStyles.tableAvatar}>
                      {u.avatar_url ? (
                        <img src={u.avatar_url} alt="" style={{width:"100%",height:"100%",borderRadius:"50%",objectFit:"cover"}} />
                      ) : (
                        getInitial(u.username)
                      )}
                    </div>
                  </td>
                  <td><span style={{fontWeight: 500}}>{u.username}</span></td>
                  <td style={{color:"var(--color-text-secondary)"}}>{u.email}</td>
                  <td>{getRoleBadge(u.role)}</td>
                  <td>{getStatusBadge(u.status)}</td>
                  <td style={{color:"var(--color-text-secondary)"}}>{(u as AdminUser).project_count ?? "-"}</td>
                  <td style={{color:"var(--color-text-secondary)"}}>
                    {new Date(u.created_at).toLocaleDateString("zh-CN")}
                  </td>
                  <td>
                    <div className={styles.actionBtnGroup}>
                      <button
                        className={parentStyles.tableActionBtn}
                        disabled={actingUserId === u.id}
                        onClick={() => {}}
                      >
                        编辑
                      </button>
                      {u.status === "active" ? (
                        <button
                          className={styles.disableBtn}
                          disabled={actingUserId === u.id}
                          onClick={() => toggleUserStatus(u)}
                        >
                          {actingUserId === u.id ? "处理中..." : "禁用"}
                        </button>
                      ) : (
                        <button
                          className={styles.enableBtn}
                          disabled={actingUserId === u.id}
                          onClick={() => toggleUserStatus(u)}
                        >
                          {actingUserId === u.id ? "处理中..." : "启用"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {renderPagination()}
        </div>
      )}
    </div>
  );
}
