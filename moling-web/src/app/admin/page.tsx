"use client";

import { useState, useEffect, useCallback, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import styles from "./admin.module.css";
import OverviewTab from "./components/OverviewTab/OverviewTab";
import UsersTab from "./components/UsersTab/UsersTab";
import LlmConfigTab from "./components/LlmConfigTab/LlmConfigTab";

type AdminTab = "overview" | "users" | "llm" | "payments" | "llmconfig";

const TAB_NAMES: Record<AdminTab, string> = {
  overview: "系统概览",
  users: "用户管理",
  llm: "LLM 用量",
  payments: "支付记录",
  llmconfig: "LLM 配置",
};

function OverviewIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7"/>
      <rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/>
      <rect x="3" y="14" width="7" height="7"/>
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  );
}

function LlmIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="10" rx="2"/>
      <circle cx="12" cy="16" r="2"/>
      <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
    </svg>
  );
}

function PaymentsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <path d="M8 12h8"/>
      <path d="M12 8v8"/>
    </svg>
  );
}

function LlmConfigIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

export default function AdminPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/auth");
    }
  }, [isAuthenticated, isLoading, router]);

  // Auto collapse sidebar on small screens
  useEffect(() => {
    function handleResize() {
      if (window.innerWidth < 768 && !sidebarCollapsed) {
        setSidebarCollapsed(true);
      }
    }
    handleResize();
    let timer: ReturnType<typeof setTimeout>;
    const debounced = () => {
      clearTimeout(timer);
      timer = setTimeout(handleResize, 150);
    };
    window.addEventListener("resize", debounced);
    return () => window.removeEventListener("resize", debounced);
  }, [sidebarCollapsed]);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleTabChange = useCallback((tab: AdminTab) => {
    setActiveTab(tab);
  }, []);

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--color-admin-bg, #0a0c14)", color: "var(--color-text-tertiary, #6b7199)" }}>
        加载中...
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const navItems: { id: AdminTab; icon: ReactNode; label: string }[] = [
    { id: "overview", icon: <OverviewIcon />, label: "系统概览" },
    { id: "users", icon: <UsersIcon />, label: "用户管理" },
    { id: "llm", icon: <LlmIcon />, label: "LLM 用量" },
    { id: "payments", icon: <PaymentsIcon />, label: "支付记录" },
    { id: "llmconfig", icon: <LlmConfigIcon />, label: "LLM 配置" },
  ];

  const sidebarItemClass = (tab: AdminTab) =>
    activeTab === tab ? styles.sidebarNavItemActive : styles.sidebarNavItem;

  return (
    <div className={styles.appLayout}>
      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ""}`}>
        <button className={styles.sidebarToggleBtn} onClick={toggleSidebar} aria-label="切换侧边栏">
          <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>

        <div className={styles.sidebarLogo}>
          <div className={styles.sidebarLogoIcon}>墨</div>
          <span className={styles.sidebarLogoText}>墨灵管理</span>
        </div>

        <nav className={styles.sidebarNav}>
          <div className={styles.sidebarNavSection}>
            <span className={styles.sidebarNavLabel}>主菜单</span>
            {navItems.map((item) => (
              <div
                key={item.id}
                className={sidebarItemClass(item.id)}
                data-tooltip={item.label}
                onClick={() => handleTabChange(item.id)}
              >
                <span className={styles.sidebarNavIcon}>{item.icon}</span>
                <span className={styles.sidebarNavText}>{item.label}</span>
              </div>
            ))}
          </div>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.sidebarNavSection}>
            <div className={styles.sidebarNavItem} data-tooltip="系统设置">
              <span className={styles.sidebarNavIcon}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </span>
              <span className={styles.sidebarNavText}>系统设置</span>
            </div>
            <div className={styles.sidebarNavItem} data-tooltip="退出登录">
              <span className={styles.sidebarNavIcon}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
              </span>
              <span className={styles.sidebarNavText}>退出登录</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={styles.mainContent}>
        {/* Header */}
        <header className={styles.adminHeader}>
          <div className={styles.headerLeft}>
            <button className={styles.hamburgerBtn} onClick={toggleSidebar} aria-label="菜单">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
            <div className={styles.headerBreadcrumb}>
              <span className={styles.headerBreadcrumbSep}>/</span>
              <span className={styles.headerBreadcrumbCurrent}>{TAB_NAMES[activeTab]}</span>
            </div>
          </div>

          <div className={styles.headerCenter}></div>

          <div className={styles.headerRight}>
            <button className={styles.headerIconBtn} aria-label="搜索">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.5"/>
                <path d="M12 12l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </button>
            <button className={styles.headerIconBtn} aria-label="通知">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 1.5a5.5 5.5 0 00-5.5 5.5v3l-1.5 2.5h14l-1.5-2.5V7A5.5 5.5 0 009 1.5z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
                <path d="M6.5 13.5a2.5 2.5 0 005 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
              <span className={styles.notificationDot}></span>
            </button>
            <div className={styles.adminAvatar}>管</div>
          </div>
        </header>

        {/* Content Body */}
        <div className={styles.contentBody}>
          {activeTab === "overview" && <OverviewTab />}
          {activeTab === "users" && <UsersTab />}
          {activeTab === "llmconfig" && <LlmConfigTab />}

          {/* ======== TAB: LLM 用量 ======== */}
          {activeTab === "llm" && (
            <LlmUsageContent />
          )}

          {/* ======== TAB: 支付记录 ======== */}
          {activeTab === "payments" && (
            <PaymentsContent />
          )}
        </div>
      </main>
    </div>
  );
}

// ── LLM Usage Tab ──
function LlmUsageContent() {
  const [dateFilter, setDateFilter] = useState("今日");
  const dateFilterOptions = ["今日", "本周", "本月", "自定义"];

  return (
    <div className={styles.tabPanelActive}>
      <div className={styles.pageTitleRow}>
        <div>
          <h1 className={styles.pageTitle}>LLM 用量</h1>
          <p className={styles.pageSubtitle}>AI 模型调用与消耗监控</p>
        </div>
      </div>

      <div className={styles.llmStatCards}>
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <div className={`${styles.statCardIcon} ${styles.statCardIconBlue}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
              </svg>
            </div>
          </div>
          <div className={styles.statCardLabel}>本月 Token 消耗</div>
          <div className={styles.statCardValue}>1.2B</div>
          <div className={styles.statCardMeta}>
            <span className={styles.statCardChangeUp}>↑ 15%</span>
            <span className={styles.statCardPeriod}>较上月</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <div className={`${styles.statCardIcon} ${styles.statCardIconIndigo}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
            </div>
          </div>
          <div className={styles.statCardLabel}>API 调用次数</div>
          <div className={styles.statCardValue}>856K</div>
          <div className={styles.statCardMeta}>
            <span className={styles.statCardChangeUp}>↑ 8%</span>
            <span className={styles.statCardPeriod}>较上月</span>
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statCardHeader}>
            <div className={`${styles.statCardIcon} ${styles.statCardIconAmber}`}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
            </div>
          </div>
          <div className={styles.statCardLabel}>平均响应时间</div>
          <div className={styles.statCardValue}>1.8s</div>
          <div className={styles.statCardMeta}>
            <span className={styles.statCardChangeUp} style={{color:"var(--color-success)"}}>↓ 5%</span>
            <span className={styles.statCardPeriod}>较上月</span>
          </div>
        </div>
      </div>

      <div className={styles.chartCard} style={{marginBottom:"32px"}}>
        <div className={styles.chartCardHeader}>
          <span className={styles.chartCardTitle}>按模型用量趋势</span>
          <div className={styles.dateFilterRow} style={{marginBottom:0}}>
            {dateFilterOptions.map((d) => (
              <button key={d} className={dateFilter === d ? styles.dateFilterBtnActive : styles.dateFilterBtn}
                onClick={() => setDateFilter(d)}>{d}</button>
            ))}
          </div>
        </div>
        <div className={styles.chartContainerTall}>
          <svg viewBox="0 0 500 220" preserveAspectRatio="xMidYMid meet" style={{width:"100%",height:"100%"}}>
            {[40,80,120,160,200].map(y => (
              <line key={y} x1="50" y1={y} x2="480" y2={y} stroke="#1e2138" strokeWidth="0.5"/>
            ))}
            <path d="M70,180 L130,160 L190,140 L250,110 L310,90 L370,100 L430,80" stroke="var(--color-brand-indigo, #6366f1)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M70,170 L130,140 L190,120 L250,100 L310,70 L370,80 L430,60" stroke="var(--color-brand-amber, #d4a843)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="4 3"/>
            <path d="M70,160 L130,150 L190,130 L250,120 L310,95 L370,90 L430,70" stroke="var(--color-success, #34d399)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="2 3"/>
            <circle cx="130" cy="212" r="4" fill="var(--color-brand-indigo, #6366f1)"/><text x="140" y="216" fill="#9ca3c4" fontSize="10">GPT-4</text>
            <circle cx="210" cy="212" r="4" fill="var(--color-brand-amber, #d4a843)"/><text x="220" y="216" fill="#9ca3c4" fontSize="10">GPT-3.5</text>
            <circle cx="300" cy="212" r="4" fill="var(--color-success, #34d399)"/><text x="310" y="216" fill="#9ca3c4" fontSize="10">Claude</text>
            {["周一","周二","周三","周四","周五","周六","周日"].map((d,i) => (
              <text key={i} x={[70,130,190,250,310,370,430][i]} y="208" fill="#6b7199" fontSize="9" textAnchor="middle">{d}</text>
            ))}
            {[{y:44,l:"500M"},{y:84,l:"400M"},{y:124,l:"300M"},{y:164,l:"200M"},{y:204,l:"100M"}].map(({y,l}) => (
              <text key={l} x="45" y={y} fill="#6b7199" fontSize="9" textAnchor="end">{l}</text>
            ))}
          </svg>
        </div>
      </div>
    </div>
  );
}

// ── Payments Tab ──
function PaymentsContent() {
  const [paymentFilterTab, setPaymentFilterTab] = useState("全部");
  const paymentFilterTabs = ["全部", "已支付", "待支付", "已退款", "失败"];

  const payments = [
    { order: "ORD-2025-001", user: "张三", amount: "¥99.00", method: "微信支付", status: "paid" as const, time: "2025-06-10 14:30" },
    { order: "ORD-2025-002", user: "李四", amount: "¥199.00", method: "支付宝", status: "paid" as const, time: "2025-06-10 13:20" },
    { order: "ORD-2025-003", user: "王五", amount: "¥49.00", method: "微信支付", status: "pending" as const, time: "2025-06-09" },
    { order: "ORD-2025-004", user: "赵六", amount: "¥299.00", method: "支付宝", status: "refunded" as const, time: "2025-06-08" },
    { order: "ORD-2025-005", user: "孙七", amount: "¥99.00", method: "微信支付", status: "failed" as const, time: "2025-06-07" },
  ];

  const badgeForStatus = (status: string) => {
    switch (status) {
      case "paid": return <span className={styles.badgePaid}><span className={styles.badgeDot}></span>已支付</span>;
      case "pending": return <span className={styles.badgePending}><span className={styles.badgeDot}></span>待支付</span>;
      case "refunded": return <span className={styles.badgeRefunded}><span className={styles.badgeDot}></span>已退款</span>;
      case "failed": return <span className={styles.badgeFailed}><span className={styles.badgeDot}></span>失败</span>;
      default: return <span className={styles.badge}><span className={styles.badgeDot}></span>{status}</span>;
    }
  };

  return (
    <div className={styles.tabPanelActive}>
      <div className={styles.pageTitleRow}>
        <div>
          <h1 className={styles.pageTitle}>支付记录</h1>
          <p className={styles.pageSubtitle}>平台交易流水与对账</p>
        </div>
      </div>

      <div className={styles.filterPanel}>
        <div className={styles.filterTabs}>
          {paymentFilterTabs.map((t) => (
            <button key={t} className={paymentFilterTab === t ? styles.filterTabActive : styles.filterTab}
              onClick={() => setPaymentFilterTab(t)}>{t}</button>
          ))}
        </div>
        <select className={styles.filterSelect}><option>日期范围</option><option>今天</option><option>本周</option><option>本月</option><option>自定义</option></select>
        <div className={styles.filterSearchWrap}>
          <span className={styles.filterSearchIcon}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </span>
          <input className={styles.filterSearch} type="text" placeholder="搜索订单号/用户..." />
        </div>
      </div>

      <div className={styles.tableCard}>
        <table className={styles.dataTable}>
          <thead>
            <tr>
              <th>订单号</th>
              <th>用户</th>
              <th>金额</th>
              <th>支付方式</th>
              <th>状态</th>
              <th>时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p, i) => (
              <tr key={i}>
                <td className={styles.paymentOrderId}>{p.order}</td>
                <td>{p.user}</td>
                <td className={styles.paymentAmount}>{p.amount}</td>
                <td style={{color:"var(--color-text-secondary)"}}>{p.method}</td>
                <td>{badgeForStatus(p.status)}</td>
                <td style={{color:"var(--color-text-secondary)"}}>{p.time}</td>
                <td><button className={styles.tableActionBtn}>详情</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className={styles.tablePagination}>
          <span className={styles.paginationInfo}>显示 1-5 条，共 128 条</span>
          <div className={styles.paginationBtns}>
            <button className={styles.paginationBtnDisabled}>‹</button>
            <button className={styles.paginationBtnActive}>1</button>
            <button className={styles.paginationBtn}>2</button>
            <button className={styles.paginationBtn}>3</button>
            <button className={styles.paginationBtn}>⋯</button>
            <button className={styles.paginationBtn}>26</button>
            <button className={styles.paginationBtn}>›</button>
          </div>
        </div>
      </div>
    </div>
  );
}
