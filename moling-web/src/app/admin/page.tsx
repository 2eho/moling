"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { showToast } from "@/components/ui/Toast";
import styles from "./admin.module.css";

type AdminTab = "overview" | "users" | "llm" | "payments" | "llmconfig";

const TAB_NAMES: Record<AdminTab, string> = {
  overview: "系统概览",
  users: "用户管理",
  llm: "LLM 用量",
  payments: "支付记录",
  llmconfig: "LLM 配置",
};

const TAB_ICONS: Record<AdminTab, string> = {
  overview: "📊",
  users: "👥",
  llm: "🤖",
  payments: "💰",
  llmconfig: "🔑",
};

export default function AdminPage() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userFilterTab, setUserFilterTab] = useState("全部");
  const [paymentFilterTab, setPaymentFilterTab] = useState("全部");
  const [llmDateFilter, setLlmDateFilter] = useState("今日");
  const [checkedRows, setCheckedRows] = useState<Set<number>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // ── LLM Config state ──
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmApiBase, setLlmApiBase] = useState("https://api.deepseek.com");
  const [llmModel, setLlmModel] = useState("deepseek-v4-flash");
  const [llmConfigured, setLlmConfigured] = useState(false);
  const [llmConfigLoading, setLlmConfigLoading] = useState(true);
  const [llmConfigSaving, setLlmConfigSaving] = useState(false);
  const [llmTesting, setLlmTesting] = useState(false);
  const [llmTestResult, setLlmTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

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

  const toggleRowCheck = useCallback((idx: number) => {
    setCheckedRows((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectAll((prev) => !prev);
    if (!selectAll) {
      setCheckedRows(new Set([0, 1, 2, 3, 4]));
    } else {
      setCheckedRows(new Set());
    }
  }, [selectAll]);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

// ── Load LLM config on mount ──
  useEffect(() => {
    fetch(`${API_BASE}/admin/llm-config`)
      .then((r) => r.json())
      .then((data) => {
        setLlmApiBase(data.api_base || "https://api.deepseek.com");
        setLlmModel(data.model || "deepseek-v4-flash");
        setLlmConfigured(data.is_configured);
      })
      .catch(() => {})
      .finally(() => setLlmConfigLoading(false));
  }, []);

  const handleSaveLlmConfig = useCallback(async () => {
    setLlmConfigSaving(true);
    setLlmTestResult(null);
    try {
      const res = await fetch(`${API_BASE}/admin/llm-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: llmApiKey,
          api_base: llmApiBase,
          model: llmModel,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || "保存失败");
      setLlmConfigured(data.is_configured);
      setLlmApiKey("");
      showToast("success", "LLM 配置已保存");
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "保存失败");
    } finally {
      setLlmConfigSaving(false);
    }
  }, [llmApiKey, llmApiBase, llmModel]);

  const handleTestConnection = useCallback(async () => {
    setLlmTesting(true);
    setLlmTestResult(null);
    try {
      // Save first so backend has the key
      const saveRes = await fetch(`${API_BASE}/admin/llm-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: llmApiKey,
          api_base: llmApiBase,
          model: llmModel,
        }),
      });
      if (!saveRes.ok) {
        const d = await saveRes.json();
        throw new Error(d.message || "保存失败");
      }

      // Now test the connection with a simple chat completion
      const testRes = await fetch(`${API_BASE}/admin/llm-config/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const testData = await testRes.json();
      if (testData.success) {
        setLlmConfigured(true);
        setLlmTestResult({ ok: true, msg: testData.message || "连接成功！" });
        setLlmApiKey("");
        showToast("success", "连接测试通过 ✅");
      } else {
        setLlmTestResult({ ok: false, msg: testData.message || "连接失败" });
        showToast("error", "连接测试失败");
      }
    } catch (e) {
      setLlmTestResult({ ok: false, msg: e instanceof Error ? e.message : "连接测试失败" });
      showToast("error", "连接测试失败");
    } finally {
      setLlmTesting(false);
    }
  }, [llmApiKey, llmApiBase, llmModel]);

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "#0a0c14", color: "#6b7199" }}>
        加载中...
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const navItems: { id: AdminTab; icon: string; label: string }[] = [
    { id: "overview", icon: "📊", label: "系统概览" },
    { id: "users", icon: "👥", label: "用户管理" },
    { id: "llm", icon: "🤖", label: "LLM 用量" },
    { id: "payments", icon: "💰", label: "支付记录" },
    { id: "llmconfig", icon: "🔑", label: "LLM 配置" },
  ];

  const sidebarItemClass = (tab: AdminTab) =>
    activeTab === tab ? styles.sidebarNavItemActive : styles.sidebarNavItem;

  const tabPanelClass = (tab: AdminTab) =>
    activeTab === tab ? styles.tabPanelActive : styles.tabPanel;

  const userFilterTabs = ["全部", "管理员", "普通用户", "VIP"];
  const paymentFilterTabs = ["全部", "已支付", "待支付", "已退款", "失败"];
  const dateFilterOptions = ["今日", "本周", "本月", "自定义"];

  const users = [
    { avatar: "张", name: "张三", email: "zhang@example.com", role: "admin" as const, status: "active" as const, date: "2025-01-15" },
    { avatar: "李", name: "李四", email: "li@example.com", role: "user" as const, status: "active" as const, date: "2025-02-20" },
    { avatar: "王", name: "王五", email: "wang@example.com", role: "user" as const, status: "banned" as const, date: "2025-01-08" },
    { avatar: "赵", name: "赵六", email: "zhao@example.com", role: "vip" as const, status: "active" as const, date: "2025-03-12" },
    { avatar: "孙", name: "孙七", email: "sun@example.com", role: "user" as const, status: "active" as const, date: "2025-04-01" },
  ];

  const payments = [
    { order: "ORD-2025-001", user: "张三", amount: "¥99.00", method: "微信支付", status: "paid" as const, time: "2025-06-10 14:30" },
    { order: "ORD-2025-002", user: "李四", amount: "¥199.00", method: "支付宝", status: "paid" as const, time: "2025-06-10 13:20" },
    { order: "ORD-2025-003", user: "王五", amount: "¥49.00", method: "微信支付", status: "pending" as const, time: "2025-06-09" },
    { order: "ORD-2025-004", user: "赵六", amount: "¥299.00", method: "支付宝", status: "refunded" as const, time: "2025-06-08" },
    { order: "ORD-2025-005", user: "孙七", amount: "¥99.00", method: "微信支付", status: "failed" as const, time: "2025-06-07" },
  ];

  const activities = [
    { icon: "🆕", text: "用户 张三 注册了账号", time: "2 小时前" },
    { icon: "💰", text: "用户 李四 充值 ¥99", time: "3 小时前" },
    { icon: "🤖", text: "系统完成每日 LLM 用量统计", time: "5 小时前" },
    { icon: "👥", text: "新增 47 名活跃用户", time: "6 小时前" },
    { icon: "⚠️", text: "系统检测到 API 延迟升高", time: "8 小时前" },
  ];

  const badgeForRole = (role: string) => {
    switch (role) {
      case "admin": return <span className={styles.badgeAdmin}><span className={styles.badgeDot}></span>管理员</span>;
      case "vip": return <span className={styles.badgeVip}><span className={styles.badgeDot}></span>VIP</span>;
      default: return <span className={styles.badgeUser}><span className={styles.badgeDot}></span>用户</span>;
    }
  };

  const badgeForStatus = (status: string) => {
    switch (status) {
      case "active": return <span className={styles.badgeActive}><span className={styles.badgeDot}></span>活跃</span>;
      case "banned": return <span className={styles.badgeBanned}><span className={styles.badgeDot}></span>封禁</span>;
      case "pending": return <span className={styles.badgePending}><span className={styles.badgeDot}></span>待支付</span>;
      case "paid": return <span className={styles.badgePaid}><span className={styles.badgeDot}></span>已支付</span>;
      case "refunded": return <span className={styles.badgeRefunded}><span className={styles.badgeDot}></span>已退款</span>;
      case "failed": return <span className={styles.badgeFailed}><span className={styles.badgeDot}></span>失败</span>;
      default: return <span className={styles.badge}><span className={styles.badgeDot}></span>{status}</span>;
    }
  };

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
              <span className={styles.sidebarNavIcon}>⚙️</span>
              <span className={styles.sidebarNavText}>系统设置</span>
            </div>
            <div className={styles.sidebarNavItem} data-tooltip="退出登录">
              <span className={styles.sidebarNavIcon}>🚪</span>
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
          {/* ======== TAB: 系统概览 ======== */}
          <section className={tabPanelClass("overview")}>
            <div className={styles.pageTitleRow}>
              <div>
                <h1 className={styles.pageTitle}>系统概览</h1>
                <p className={styles.pageSubtitle}>MoLing AI 平台运行状态一览</p>
              </div>
            </div>

            <div className={styles.statCards}>
              <div className={styles.statCard}>
                <div className={styles.statCardHeader}>
                  <div className={`${styles.statCardIcon} ${styles.statCardIconIndigo}`}>👥</div>
                </div>
                <div className={styles.statCardLabel}>日活跃用户 (DAU)</div>
                <div className={styles.statCardValue}>12,847</div>
                <div className={styles.statCardMeta}>
                  <span className={styles.statCardChangeUp}>↑ 12.5%</span>
                  <span className={styles.statCardPeriod}>较昨日</span>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statCardHeader}>
                  <div className={`${styles.statCardIcon} ${styles.statCardIconAmber}`}>💰</div>
                </div>
                <div className={styles.statCardLabel}>今日营收</div>
                <div className={styles.statCardValue}>¥48,296</div>
                <div className={styles.statCardMeta}>
                  <span className={styles.statCardChangeUp}>↑ 8.3%</span>
                  <span className={styles.statCardPeriod}>较昨日</span>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statCardHeader}>
                  <div className={`${styles.statCardIcon} ${styles.statCardIconBlue}`}>🤖</div>
                </div>
                <div className={styles.statCardLabel}>LLM 调用量</div>
                <div className={styles.statCardValue}>2.4M</div>
                <div className={styles.statCardMeta}>
                  <span className={styles.statCardChangeUp}>↑ 23.1%</span>
                  <span className={styles.statCardPeriod}>较昨日</span>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statCardHeader}>
                  <div className={`${styles.statCardIcon} ${styles.statCardIconGreen}`}>📝</div>
                </div>
                <div className={styles.statCardLabel}>今日注册</div>
                <div className={styles.statCardValue}>856</div>
                <div className={styles.statCardMeta}>
                  <span className={styles.statCardChangeDown}>↓ 3.2%</span>
                  <span className={styles.statCardPeriod}>较昨日</span>
                </div>
              </div>
            </div>

            <div className={styles.chartsRow}>
              <div className={styles.chartCard}>
                <div className={styles.chartCardHeader}>
                  <span className={styles.chartCardTitle}>DAU 趋势</span>
                  <span className={styles.chartCardPeriod}>最近 7 天</span>
                </div>
                <div className={styles.chartContainer}>
                  <svg className="chart-svg" viewBox="0 0 400 180" preserveAspectRatio="xMidYMid meet" style={{width:"100%",height:"100%"}}>
                    <line x1="40" y1="40" x2="380" y2="40" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="75" x2="380" y2="75" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="110" x2="380" y2="110" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="145" x2="380" y2="145" stroke="#1e2138" strokeWidth="0.5"/>
                    <path d="M60,130 L100,110 L140,120 L180,95 L220,75 L260,85 L300,60 L340,70 M340,70 L340,145 L60,145 Z" fill="url(#dauGradient)" opacity="0.3"/>
                    <path d="M60,130 L100,110 L140,120 L180,95 L220,75 L260,85 L300,60 L340,70" stroke="var(--color-brand-indigo, #6366f1)" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                    {[60,100,140,180,220,260,300,340].map((x,i) => (
                      <circle key={i} cx={x} cy={[130,110,120,95,75,85,60,70][i]} r="3" fill="var(--color-brand-indigo, #6366f1)"/>
                    ))}
                    {["06/04","06/05","06/06","06/07","06/08","06/09","06/10","06/11"].map((d,i) => (
                      <text key={i} x={[60,100,140,180,220,260,300,340][i]} y="165" fill="#6b7199" fontSize="9" textAnchor="middle">{d}</text>
                    ))}
                    {[{y:44,l:"15k"},{y:79,l:"12k"},{y:114,l:"9k"},{y:149,l:"6k"}].map(({y,l}) => (
                      <text key={l} x="35" y={y} fill="#6b7199" fontSize="9" textAnchor="end">{l}</text>
                    ))}
                    <defs>
                      <linearGradient id="dauGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-brand-indigo, #6366f1)" stopOpacity="0.4"/>
                        <stop offset="100%" stopColor="var(--color-brand-indigo, #6366f1)" stopOpacity="0"/>
                      </linearGradient>
                    </defs>
                  </svg>
                </div>
              </div>

              <div className={styles.chartCard}>
                <div className={styles.chartCardHeader}>
                  <span className={styles.chartCardTitle}>LLM 调用量趋势</span>
                  <span className={styles.chartCardPeriod}>最近 7 天</span>
                </div>
                <div className={styles.chartContainer}>
                  <svg className="chart-svg" viewBox="0 0 400 180" preserveAspectRatio="xMidYMid meet" style={{width:"100%",height:"100%"}}>
                    <line x1="40" y1="40" x2="380" y2="40" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="75" x2="380" y2="75" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="110" x2="380" y2="110" stroke="#1e2138" strokeWidth="0.5"/>
                    <line x1="40" y1="145" x2="380" y2="145" stroke="#1e2138" strokeWidth="0.5"/>
                    {[
                      {x:60,h:35},{x:108,h:50},{x:156,h:45},{x:204,h:75},{x:252,h:85},{x:300,h:65},{x:348,h:95}
                    ].map((b,i) => (
                      <rect key={i} x={b.x} y={145-b.h} width="28" height={b.h} rx="3" fill="var(--color-brand-amber, #d4a843)" opacity="0.85"/>
                    ))}
                    {["06/04","06/05","06/06","06/07","06/08","06/09","06/10"].map((d,i) => (
                      <text key={i} x={[74,122,170,218,266,314,362][i]} y="165" fill="#6b7199" fontSize="9" textAnchor="middle">{d}</text>
                    ))}
                    {[{y:44,l:"3.0M"},{y:79,l:"2.5M"},{y:114,l:"2.0M"},{y:149,l:"1.5M"}].map(({y,l}) => (
                      <text key={l} x="35" y={y} fill="#6b7199" fontSize="9" textAnchor="end">{l}</text>
                    ))}
                  </svg>
                </div>
              </div>
            </div>

            <div className={styles.sectionCard}>
              <div className={styles.sectionCardHeader}>
                <span className={styles.sectionCardTitle}>最近活动</span>
                <span className="text-tertiary" style={{fontSize:12,color:"var(--color-text-tertiary)"}}>实时更新</span>
              </div>
              <div className={styles.activityFeed}>
                {activities.map((a,i) => (
                  <div key={i} className={styles.activityItem}>
                    <div className={styles.activityIcon}>{a.icon}</div>
                    <div className={styles.activityContent}>
                      <div className={styles.activityText}><span dangerouslySetInnerHTML={{__html:a.text.replace(/ (.*?) /g,' <strong>$1</strong> ')}} /></div>
                      <div className={styles.activityTime}>{a.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ======== TAB: 用户管理 ======== */}
          <section className={tabPanelClass("users")}>
            <div className={styles.pageTitleRow}>
              <div>
                <h1 className={styles.pageTitle}>用户管理</h1>
                <p className={styles.pageSubtitle}>查看和管理平台用户</p>
              </div>
            </div>

            <div className={styles.filterPanel}>
              <div className={styles.filterTabs}>
                {userFilterTabs.map((t) => (
                  <button key={t} className={userFilterTab === t ? styles.filterTabActive : styles.filterTab}
                    onClick={() => setUserFilterTab(t)}>{t}</button>
                ))}
              </div>
              <select className={styles.filterSelect}><option>角色</option><option>管理员</option><option>普通用户</option><option>VIP</option></select>
              <select className={styles.filterSelect}><option>状态</option><option>活跃</option><option>封禁</option></select>
              <div className={styles.filterSearchWrap}>
                <span className={styles.filterSearchIcon}>🔍</span>
                <input className={styles.filterSearch} type="text" placeholder="搜索用户昵称/邮箱..." />
              </div>
            </div>

            <div className={styles.tableCard}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th className={styles.colCheckbox}>
                      <span className={selectAll ? styles.customCheckboxChecked : styles.customCheckbox} onClick={toggleSelectAll}>
                        {selectAll && <svg width="10" height="8" viewBox="0 0 10 8" fill="none"><path d="M1 4l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/></svg>}
                      </span>
                    </th>
                    <th className={styles.colAvatar}>头像</th>
                    <th className="sortable">昵称 <span style={{color:"var(--color-text-tertiary)"}}>↓</span></th>
                    <th>邮箱</th>
                    <th>角色</th>
                    <th>状态</th>
                    <th>注册时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u,i) => (
                    <tr key={i}>
                      <td>
                        <span className={checkedRows.has(i) ? styles.customCheckboxChecked : styles.customCheckbox} onClick={() => toggleRowCheck(i)}>
                          {checkedRows.has(i) && <svg width="10" height="8" viewBox="0 0 10 8" fill="none"><path d="M1 4l3 3 5-5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/></svg>}
                        </span>
                      </td>
                      <td><div className={styles.tableAvatar}>{u.avatar}</div></td>
                      <td><span style={{fontWeight:500}}>{u.name}</span></td>
                      <td style={{color:"var(--color-text-secondary)"}}>{u.email}</td>
                      <td>{badgeForRole(u.role)}</td>
                      <td>{badgeForStatus(u.status)}</td>
                      <td style={{color:"var(--color-text-secondary)"}}>{u.date}</td>
                      <td><button className={styles.tableActionBtn}>编辑</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className={styles.tablePagination}>
                <span className={styles.paginationInfo}>显示 1-5 条，共 156 条</span>
                <div className={styles.paginationBtns}>
                  <button className={styles.paginationBtnDisabled}>‹</button>
                  <button className={styles.paginationBtnActive}>1</button>
                  <button className={styles.paginationBtn}>2</button>
                  <button className={styles.paginationBtn}>3</button>
                  <button className={styles.paginationBtn}>⋯</button>
                  <button className={styles.paginationBtn}>32</button>
                  <button className={styles.paginationBtn}>›</button>
                </div>
              </div>
            </div>
          </section>

          {/* ======== TAB: LLM 用量 ======== */}
          <section className={tabPanelClass("llm")}>
            <div className={styles.pageTitleRow}>
              <div>
                <h1 className={styles.pageTitle}>LLM 用量</h1>
                <p className={styles.pageSubtitle}>AI 模型调用与消耗监控</p>
              </div>
            </div>

            <div className={styles.llmStatCards}>
              <div className={styles.statCard}>
                <div className={styles.statCardHeader}>
                  <div className={`${styles.statCardIcon} ${styles.statCardIconBlue}`}>📊</div>
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
                  <div className={`${styles.statCardIcon} ${styles.statCardIconIndigo}`}>🔄</div>
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
                  <div className={`${styles.statCardIcon} ${styles.statCardIconAmber}`}>⚡</div>
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
                    <button key={d} className={llmDateFilter === d ? styles.dateFilterBtnActive : styles.dateFilterBtn}
                      onClick={() => setLlmDateFilter(d)}>{d}</button>
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
          </section>

          {/* ======== TAB: 支付记录 ======== */}
          <section className={tabPanelClass("payments")}>
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
                <span className={styles.filterSearchIcon}>🔍</span>
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
                  {payments.map((p,i) => (
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
          </section>

          {/* ======== TAB: LLM 配置 ======== */}
          <section className={tabPanelClass("llmconfig")}>
            <div className={styles.pageTitleRow}>
              <div>
                <h1 className={styles.pageTitle}>LLM 配置</h1>
                <p className={styles.pageSubtitle}>管理 AI 模型 API 密钥与服务端设置</p>
              </div>
            </div>

            <div className={styles.sectionCard}>
              {llmConfigLoading ? (
                <p style={{ color: "var(--color-text-tertiary)", padding: "20px 0" }}>加载中...</p>
              ) : (
                <>
                  <div className={styles.fieldRow}>
                    <div className={styles.fieldInfo}>
                      <span className={styles.fieldLabel}>API Key</span>
                      <span className={styles.fieldDesc}>
                        {llmConfigured
                          ? "已配置（再次输入将覆盖旧密钥）"
                          : "尚未配置，请输入 DeepSeek API Key"}
                      </span>
                    </div>
                    <input
                      type="password"
                      className={styles.filterSearch}
                      style={{ flex: 1, minWidth: 280 }}
                      value={llmApiKey}
                      onChange={(e) => setLlmApiKey(e.target.value)}
                      placeholder={llmConfigured ? "输入新 Key 以覆盖" : "输入 DeepSeek API Key"}
                    />
                    <span
                      className={`${styles.badge} ${llmConfigured ? styles.badgeActive : styles.badgePending}`}
                      style={{ whiteSpace: "nowrap" }}
                    >
                      {llmConfigured ? "✅ 已配置" : "⏳ 未配置"}
                    </span>
                  </div>

                  <div className={styles.fieldRow}>
                    <div className={styles.fieldInfo}>
                      <span className={styles.fieldLabel}>API Base URL</span>
                      <span className={styles.fieldDesc}>API 服务地址</span>
                    </div>
                    <input
                      className={styles.filterSearch}
                      style={{ flex: 1, minWidth: 280 }}
                      value={llmApiBase}
                      onChange={(e) => setLlmApiBase(e.target.value)}
                      placeholder="https://api.deepseek.com/v1"
                    />
                  </div>

                  <div className={styles.fieldRow}>
                    <div className={styles.fieldInfo}>
                      <span className={styles.fieldLabel}>默认模型</span>
                      <span className={styles.fieldDesc}>AI 生成使用的模型</span>
                    </div>
                    <select
                      className={styles.filterSelect}
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                    >
                      <option value="deepseek-v4-flash">DeepSeek V4 Flash</option>
                      <option value="deepseek-v4-pro">DeepSeek V4 Pro</option>
                      <option value="deepseek-chat">DeepSeek Chat (即将弃用)</option>
                      <option value="deepseek-reasoner">DeepSeek Reasoner (即将弃用)</option>
                    </select>
                  </div>

                  <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
                    {llmTestResult && (
                      <span style={{
                        marginRight: "auto",
                        fontSize: 13,
                        padding: "6px 12px",
                        borderRadius: 6,
                        background: llmTestResult.ok
                          ? "rgba(52,211,153,0.1)"
                          : "rgba(239,68,68,0.1)",
                        color: llmTestResult.ok
                          ? "var(--color-success)"
                          : "var(--color-danger)",
                      }}>
                        {llmTestResult.ok ? "✅ " : "❌ "}{llmTestResult.msg}
                      </span>
                    )}
                    <button
                      className={styles.tableActionBtn}
                      onClick={() => {
                        setLlmApiKey("");
                        setLlmApiBase("https://api.deepseek.com");
                        setLlmModel("deepseek-v4-flash");
                        setLlmTestResult(null);
                      }}
                    >
                      重置
                    </button>
                    <button
                      className={styles.tableActionBtn}
                      disabled={llmTesting || !llmApiKey}
                      onClick={handleTestConnection}
                      style={{ color: "var(--color-brand-amber)" }}
                    >
                      {llmTesting ? "测试中..." : "🔌 测试连接"}
                    </button>
                    <button
                      className={styles.tableActionBtn}
                      style={{ background: "var(--color-brand-indigo-dim)", color: "var(--color-brand-indigo)", fontWeight: 600 }}
                      disabled={llmConfigSaving}
                      onClick={handleSaveLlmConfig}
                    >
                      {llmConfigSaving ? "保存中..." : "保存配置"}
                    </button>
                  </div>
                </>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
