"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import { ChapterSelector } from "@/components/workspace/ChapterSelector";
import { HealthAlertBanner } from "@/components/workspace/HealthAlert";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useProjectContext } from "@/contexts/ProjectContext";
import { useAuth } from "@/hooks/useAuth";
import { useResizablePanel } from "@/hooks/useResizablePanel";
import { ResizableHandle } from "@/components/ui/ResizableHandle";
import { showToast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";
import styles from "./workspace.module.css";

// ✅ 动态导入
const Editor = dynamic(
  () => import("@/components/workspace/Editor").then((mod) => mod.Editor),
  { loading: () => <div className={styles.editorPlaceholder}><Spinner size="sm" /></div> },
);
const GenerationProgress = dynamic(
  () => import("@/components/workspace/GenerationProgress").then((mod) => mod.GenerationProgress),
  { ssr: false },
);
const CardModal = dynamic(
  () => import("@/components/workspace/CardModal").then((mod) => mod.CardModal),
  { ssr: false },
);

/* ── 四库面板：内联构建 ── */
function LibraryPanel() {
  return (
    <>
      {/* 人物库 */}
      <div className={styles.libDrawer}>
        <div className={styles.libDrawerHeader}>
          <span className={styles.libDrawerTitle}>👤 人物库</span>
          <span className={styles.libDrawerCount}>—</span>
        </div>
        <div className={styles.libHint}>
          暂无人物数据。导入小说或手动添加角色。
        </div>
      </div>

      {/* 情节承诺库 */}
      <div className={styles.libDrawer}>
        <div className={styles.libDrawerHeader}>
          <span className={styles.libDrawerTitle}>🔗 情节承诺库</span>
          <span className={styles.libDrawerCount}>—</span>
        </div>
        <div className={styles.libHint}>
          暂无情节数据。AI 生成章节时会自动提取。
        </div>
      </div>

      {/* 世界观库 */}
      <div className={styles.libDrawer}>
        <div className={styles.libDrawerHeader}>
          <span className={styles.libDrawerTitle}>🗺 世界观库</span>
          <span className={styles.libDrawerCount}>—</span>
        </div>
        <div className={styles.libHint}>
          暂无世界观数据。导入小说可自动提取。
        </div>
      </div>

      {/* 伏笔库 */}
      <div className={styles.libDrawer}>
        <div className={styles.libDrawerHeader}>
          <span className={styles.libDrawerTitle}>🎯 伏笔库</span>
          <span className={styles.libDrawerCount}>—</span>
        </div>
        <div className={styles.libHint}>
          暂无伏笔数据。AI 生成章节时会自动追踪。
        </div>
      </div>

      {/* 底部操作 */}
      <div className={styles.libFooter}>
        <Link href={`/import`} className={styles.libFooterBtn} style={{ textDecoration: "none" }}>
          📥 导入素材
        </Link>
        <Link href={`/vaults`} className={`${styles.libFooterBtn} ${styles.libFooterBtnPrimary}`} style={{ textDecoration: "none" }}>
          ⚙ 四库管理
        </Link>
      </div>
    </>
  );
}

/* ── AI 工具箱：内联构建 ── */
function AIToolbox({
  onOpenCardModal,
  onRedraw,
  remainingRedraws,
  drawResult,
}: {
  onOpenCardModal: () => void;
  onRedraw: () => void;
  remainingRedraws: number;
  drawResult: any;
}) {
  return (
    <>
      {/* 抽卡区 */}
      <div className={styles.toolSection}>
        <div className={styles.toolSectionTitle}>
          <span className={styles.toolSectionDot} style={{ background: "var(--color-brand-amber)" }} />
          灵感抽卡
        </div>

        {/* 快捷抽卡网格 */}
        <div className={styles.cardGrid}>
          <button className={styles.cardBtn} onClick={onOpenCardModal}>
            <div className={styles.cardRarity} style={{ color: "#67e8f9" }}>✦ 罕见</div>
            <div className={styles.cardIcon}>⚔</div>
            <div className={styles.cardName}>临阵突破</div>
            <div className={styles.cardDesc}>战斗中发现新力量</div>
          </button>
          <button className={styles.cardBtn} onClick={onOpenCardModal}>
            <div className={styles.cardRarity} style={{ color: "#9ca3af" }}>✦ 普通</div>
            <div className={styles.cardIcon}>🔥</div>
            <div className={styles.cardName}>情绪爆发</div>
            <div className={styles.cardDesc}>压抑情感瞬间释放</div>
          </button>
          <button className={styles.cardBtn} onClick={onOpenCardModal}>
            <div className={styles.cardRarity} style={{ color: "#a855f7" }}>✦ 史诗</div>
            <div className={styles.cardIcon}>🌀</div>
            <div className={styles.cardName}>命运转折</div>
            <div className={styles.cardDesc}>关键选择改变一切</div>
          </button>
          <button className={styles.cardBtn} onClick={onOpenCardModal}>
            <div className={styles.cardRarity} style={{ color: "#67e8f9" }}>✦ 稀有</div>
            <div className={styles.cardIcon}>💫</div>
            <div className={styles.cardName}>意外援手</div>
            <div className={styles.cardDesc}>意想不到的外援</div>
          </button>
        </div>

        {/* AI 思考状态（有抽卡结果时显示） */}
        {drawResult && (
          <div className={styles.agentInline}>
            <div className={`${styles.agentStepRow} ${styles.agentStepRowDone}`}>
              <span className={styles.agentStepDot} />
              读取四库数据
            </div>
            <div className={`${styles.agentStepRow} ${styles.agentStepRowActive}`}>
              <span className={styles.agentStepDot} />
              匹配文风指纹
            </div>
            <div className={styles.agentStepRow}>
              <span className={styles.agentStepDot} />
              等待操作...
            </div>
          </div>
        )}
      </div>

      {/* AI 操作 */}
      <div className={styles.toolSection}>
        <div className={styles.toolSectionTitle}>
          <span className={styles.toolSectionDot} style={{ background: "var(--color-brand-indigo)" }} />
          AI 操作
        </div>

        <button className={`${styles.actionBtn} ${styles.actionBtnDraw}`} onClick={onOpenCardModal}>
          <span className={styles.actionBtnIcon}>🎴</span>
          <div>
            <div className={styles.actionBtnLabel}>打开抽卡面板</div>
            <div className={styles.actionBtnHint}>
              剩余重抽 {remainingRedraws} 次
            </div>
          </div>
        </button>

        <button
          className={`${styles.actionBtn} ${styles.actionBtnDraw}`}
          onClick={onRedraw}
          disabled={remainingRedraws <= 0}
          style={remainingRedraws <= 0 ? { opacity: 0.4, cursor: "not-allowed" } : undefined}
        >
          <span className={styles.actionBtnIcon}>🔄</span>
          <div>
            <div className={styles.actionBtnLabel}>重新抽卡</div>
            <div className={styles.actionBtnHint}>不满意？重新抽取卡牌组合</div>
          </div>
        </button>

        <button className={`${styles.actionBtn} ${styles.actionBtnGenerate}`} onClick={onOpenCardModal}>
          <span className={styles.actionBtnIcon}>✏</span>
          <div>
            <div className={styles.actionBtnLabel}>AI 生文</div>
            <div className={styles.actionBtnHint} style={{ opacity: 0.7 }}>基于卡牌 + 四库记忆生成</div>
          </div>
        </button>
      </div>

      {/* 快捷操作 */}
      <div className={styles.toolSection}>
        <div className={styles.toolSectionTitle}>
          <span className={styles.toolSectionDot} style={{ background: "var(--color-success)" }} />
          快捷操作
        </div>
        <div className={styles.quickActions}>
          <button className={`${styles.quickBtn} ${styles.quickBtnSuggested}`} onClick={onOpenCardModal}>
            🎴 抽卡生文
          </button>
          <button className={styles.quickBtn} onClick={onOpenCardModal}>
            📋 大纲优化
          </button>
          <button className={styles.quickBtn}>
            🎭 语气校准
          </button>
          <button className={styles.quickBtn}>
            📖 前章摘要
          </button>
          <button className={styles.quickBtn}>
            ⚡ 节奏分析
          </button>
          <button className={styles.quickBtn}>
            🎯 伏笔检查
          </button>
        </div>
      </div>
    </>
  );
}

/* ── 主内容 ── */
function WorkspaceContent({ projectId }: { projectId: string }) {
  const {
    currentChapter,
    chapters,
    cards,
    generationTask,
    healthAlerts,
    drawResult,
    drawCards,
    redrawCards,
    generate,
    createChapter,
    setCurrentChapter,
  } = useWorkspace();

  const { currentProject, loadProject, projects } = useProjectContext();
  const { user, logout } = useAuth();
  const router = useRouter();

  const [cardModalOpen, setCardModalOpen] = useState(false);
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);
  const [projectMenuOpen, setProjectMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // 检测移动端
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // 手势事件
  useEffect(() => {
    const handleOpenReference = () => {
      if (isMobile) {
        setMobileLeftOpen(true);
      } else {
        setLeftPanelOpen(true);
      }
    };
    const handleOpenAI = () => {
      if (isMobile) {
        setMobileRightOpen(true);
      } else {
        setRightPanelOpen(true);
      }
    };
    window.addEventListener("open-reference-panel", handleOpenReference);
    window.addEventListener("open-ai-panel", handleOpenAI);
    return () => {
      window.removeEventListener("open-reference-panel", handleOpenReference);
      window.removeEventListener("open-ai-panel", handleOpenAI);
    };
  }, [isMobile]);

  const closeMobileLeft = useCallback(() => setMobileLeftOpen(false), []);
  const closeMobileRight = useCallback(() => setMobileRightOpen(false), []);

  // 加载项目详情
  useEffect(() => {
    if (projectId && !currentProject) {
      loadProject(projectId);
    }
  }, [projectId, currentProject, loadProject]);

  const leftResizable = useResizablePanel({
    storageKey: "leftPanelWidth",
    defaultWidth: 280,
    minWidth: 200,
    maxWidth: 400,
    side: "left",
  });
  const rightResizable = useResizablePanel({
    storageKey: "rightPanelWidth",
    defaultWidth: 320,
    minWidth: 260,
    maxWidth: 480,
    side: "right",
  });

  const handleAddChapter = async () => {
    try {
      await createChapter();
      showToast("success", "新章节已创建");
    } catch (error: any) {
      showToast("error", `创建章节失败：${error?.message || "未知错误"}`);
    }
  };

  const handleDrawCards = async (
    cardIds: string[],
    weights: number[],
    mode: string,
  ) => {
    try {
      await drawCards(cardIds, weights, mode);
    } catch (error: any) {
      showToast("error", `抽卡失败：${error?.message || "未知错误"}`);
    }
  };

  const handleRedraw = async () => {
    try {
      await redrawCards(projectId);
    } catch (error: any) {
      showToast("error", `重抽失败：${error?.message || "未知错误"}`);
    }
  };

  const toggleLeftPanel = () => setLeftPanelOpen(!leftPanelOpen);
  const toggleRightPanel = () => setRightPanelOpen(!rightPanelOpen);
  const openMobileLeft = () => setMobileLeftOpen(true);
  const openMobileRight = () => setMobileRightOpen(true);

  const remainingRedraws = drawResult?.remaining_redraws ?? 3;

  return (
    <div className={styles.page}>
      {/* ── Top Bar ── */}
      <div className={styles.topBar}>
        <div className={styles.topLeft}>
          {/* 左面板切换 */}
          {isMobile ? (
            <button className={styles.iconBtn} onClick={openMobileLeft} title="打开参考面板">
              ☰
            </button>
          ) : (
            <button
              className={styles.iconBtn}
              onClick={toggleLeftPanel}
              title={leftPanelOpen ? "折叠左面板" : "展开左面板"}
              style={leftPanelOpen ? { color: "var(--color-brand-indigo)", background: "var(--color-brand-indigo-dim)" } : undefined}
            >
              ☰
            </button>
          )}

          {/* 面包屑导航 */}
          <div className={styles.breadcrumb}>
            <Link href="/projects" className={styles.breadcrumbLink}>
              我的作品
            </Link>
            <span className={styles.breadcrumbSep}>/</span>
            <div className={styles.projectSwitcher}>
              <button
                className={styles.projectSwitcherBtn}
                onClick={() => setProjectMenuOpen(!projectMenuOpen)}
              >
                {currentProject?.title || "加载中..."}
              </button>
              {projectMenuOpen && (
                <>
                  <div className={styles.dropdownBackdrop} onClick={() => setProjectMenuOpen(false)} />
                  <div className={styles.projectDropdown}>
                    {projects?.map((p) => (
                      <button
                        key={p.id}
                        className={`${styles.projectDropdownItem} ${p.id === projectId ? styles.projectDropdownItemActive : ""}`}
                        onClick={() => {
                          setProjectMenuOpen(false);
                          if (p.id !== projectId) {
                            router.push(`/workspace/${p.id}`);
                          }
                        }}
                      >
                        {p.title}
                      </button>
                    ))}
                    <div className={styles.dropdownDivider} />
                    <button
                      className={styles.projectDropdownItem}
                      onClick={() => {
                        setProjectMenuOpen(false);
                        router.push("/projects");
                      }}
                    >
                      管理项目...
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* 章节快速切换 */}
          <ChapterSelector
            chapters={chapters}
            currentChapterId={currentChapter?.id}
            onChange={(ch) => setCurrentChapter(ch)}
            onAddChapter={handleAddChapter}
          />
        </div>

        <div className={styles.topRight}>
          {/* 健康状态 */}
          {healthAlerts && healthAlerts.length > 0 && (
            <span className={styles.iconBtn} title="系统健康状态">
              🛡
            </span>
          )}

          {/* 右面板切换 */}
          {isMobile ? (
            <button className={styles.iconBtn} onClick={openMobileRight} title="打开 AI 工具箱">
              ✦
            </button>
          ) : (
            <button
              className={styles.iconBtn}
              onClick={toggleRightPanel}
              title={rightPanelOpen ? "折叠 AI 工具箱" : "展开 AI 工具箱"}
              style={rightPanelOpen ? { color: "var(--color-brand-indigo)", background: "var(--color-brand-indigo-dim)" } : undefined}
            >
              ✦
            </button>
          )}

          {/* 用户菜单 */}
          {user && (
            <div className={styles.userSection}>
              <button
                className={styles.userAvatarBtn}
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                title="用户菜单"
              >
                {user.username?.charAt(0)?.toUpperCase() || "U"}
              </button>
              {userMenuOpen && (
                <>
                  <div className={styles.dropdownBackdrop} onClick={() => setUserMenuOpen(false)} />
                  <div className={styles.userDropdown}>
                    <div className={styles.userInfo}>
                      <span className={styles.userName}>{user.username || "用户"}</span>
                      <span className={styles.userEmail}>{user.email}</span>
                    </div>
                    <div className={styles.dropdownDivider} />
                    <button
                      className={styles.dropdownItem}
                      onClick={() => {
                        setUserMenuOpen(false);
                        router.push("/settings");
                      }}
                    >
                      个人设置
                    </button>
                    <button
                      className={`${styles.dropdownItem} ${styles.dropdownDanger}`}
                      onClick={() => {
                        setUserMenuOpen(false);
                        logout();
                      }}
                    >
                      退出登录
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Health Alerts ── */}
      <div className={styles.healthBanner}>
        <HealthAlertBanner alerts={healthAlerts} />
      </div>

      {/* ── Generation Progress ── */}
      {generationTask && (
        <div className={styles.progressBar}>
          <GenerationProgress
            percent={generationTask.progress_percent}
            stage={generationTask.progress_stage}
          />
        </div>
      )}

      {/* ── Three-column Layout ── */}
      <div className={styles.main}>
        {/* Left Panel — Desktop */}
        {!isMobile && (
          <div
            className={`${styles.leftPanel} ${!leftPanelOpen ? styles.leftPanelCollapsed : ""}`}
            style={leftPanelOpen ? { width: leftResizable.width, minWidth: leftResizable.width } : undefined}
          >
            <LibraryPanel />
          </div>
        )}

        {/* Left Panel — Mobile Drawer */}
        {isMobile && (
          <>
            <div
              className={`${styles.overlay} ${mobileLeftOpen ? styles.overlayVisible : ""}`}
              onClick={closeMobileLeft}
            />
            <div className={`${styles.leftPanel} ${mobileLeftOpen ? styles.leftPanelOpen : ""}`}>
              <LibraryPanel />
            </div>
          </>
        )}

        {/* Resize Handle */}
        {!isMobile && leftPanelOpen && (
          <ResizableHandle
            onMouseDown={leftResizable.onResizeStart}
            active={leftResizable.isResizing}
          />
        )}

        {/* Center: Editor */}
        <div className={styles.editorArea}>
          <div className={styles.editorCenter}>
            <Editor />
          </div>
        </div>

        {/* Resize Handle */}
        {!isMobile && rightPanelOpen && (
          <ResizableHandle
            onMouseDown={rightResizable.onResizeStart}
            active={rightResizable.isResizing}
          />
        )}

        {/* Right Panel — Desktop */}
        {!isMobile && (
          <div
            className={`${styles.rightPanel} ${!rightPanelOpen ? styles.rightPanelCollapsed : ""}`}
            style={rightPanelOpen ? { width: rightResizable.width, minWidth: rightResizable.width } : undefined}
          >
            <AIToolbox
              onOpenCardModal={() => setCardModalOpen(true)}
              onRedraw={handleRedraw}
              remainingRedraws={remainingRedraws}
              drawResult={drawResult}
            />
          </div>
        )}

        {/* Right Panel — Mobile Drawer */}
        {isMobile && (
          <>
            <div
              className={`${styles.overlay} ${mobileRightOpen ? styles.overlayVisible : ""}`}
              onClick={closeMobileRight}
            />
            <div className={`${styles.rightPanel} ${mobileRightOpen ? styles.rightPanelOpen : ""}`}>
              <AIToolbox
                onOpenCardModal={() => setCardModalOpen(true)}
                onRedraw={handleRedraw}
                remainingRedraws={remainingRedraws}
                drawResult={drawResult}
              />
            </div>
          </>
        )}
      </div>

      {/* ── Status Bar ── */}
      <div className={styles.statusBar}>
        <span className={styles.statusDot} />
        <span className={styles.statusText}>
          {generationTask ? "墨灵 · 生成中..." : "墨灵 · 就绪"}
        </span>
        {currentChapter && (
          <span className={styles.statusMeta}>
            {currentChapter.title || `第 ${currentChapter.chapter_number || "?"} 章`}
          </span>
        )}
      </div>

      {/* ── Card Modal ── */}
      <CardModal
        isOpen={cardModalOpen}
        onClose={() => setCardModalOpen(false)}
        cards={cards}
        remainingRedraws={remainingRedraws}
        onDraw={handleDrawCards}
        onRedraw={handleRedraw}
        onConfirm={(cardIds, weights, mode) => {
          generate(cardIds, weights, mode);
          setCardModalOpen(false);
          showToast("info", "正在同步世界设定…");
        }}
      />
    </div>
  );
}

/* ── Page Export ── */
export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/auth");
    }
  }, [authLoading, isAuthenticated, router]);

  if (authLoading || !isAuthenticated) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--color-bg, #0d0f1a)"
      }}>
        <Spinner />
      </div>
    );
  }

  useEffect(() => {
    if (projectId) {
      localStorage.setItem("lastProjectId", projectId);
    }
  }, [projectId]);

  return (
    <WorkspaceProvider projectId={projectId}>
      <WorkspaceContent projectId={projectId} />
    </WorkspaceProvider>
  );
}
