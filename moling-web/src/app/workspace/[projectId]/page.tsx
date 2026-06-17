"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import { ChapterSelector } from "@/components/workspace/ChapterSelector";
import { ToolBar } from "@/components/workspace/ToolBar";
import { HealthAlertBanner } from "@/components/workspace/HealthAlert";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useProjectContext } from "@/contexts/ProjectContext";
import { useAuth } from "@/hooks/useAuth";
import { useResizablePanel } from "@/hooks/useResizablePanel";
import { ResizableHandle } from "@/components/ui/ResizableHandle";
import { showToast } from "@/components/ui/Toast";
import { Spinner } from "@/components/ui/Spinner";
import styles from "./workspace.module.css";

// ✅ 动态导入：三个主面板和卡牌弹窗 — 减小初始包体积
const LeftPanel = dynamic(
  () => import("@/components/workspace/LeftPanel").then((mod) => mod.LeftPanel),
  { loading: () => <div className={styles.panelPlaceholder}><Spinner size="sm" /></div> },
);
const Editor = dynamic(
  () => import("@/components/workspace/Editor").then((mod) => mod.Editor),
  { loading: () => <div className={styles.editorPlaceholder}><Spinner size="sm" /></div> },
);
const RightPanel = dynamic(
  () => import("@/components/workspace/RightPanel").then((mod) => mod.RightPanel),
  { loading: () => <div className={styles.panelPlaceholder}><Spinner size="sm" /></div> },
);
const GenerationProgress = dynamic(
  () => import("@/components/workspace/GenerationProgress").then((mod) => mod.GenerationProgress),
  { ssr: false },
);
const CardModal = dynamic(
  () => import("@/components/workspace/CardModal").then((mod) => mod.CardModal),
  { ssr: false },
);

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

  // 监听手势事件：打开参考面板和 AI 面板
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

  // 移动端关闭抽屉时重置状态
  const closeMobileLeft = useCallback(() => setMobileLeftOpen(false), []);
  const closeMobileRight = useCallback(() => setMobileRightOpen(false), []);

  // Load project details
  useEffect(() => {
    if (projectId && !currentProject) {
      loadProject(projectId);
    }
  }, [projectId, currentProject, loadProject]);

  // 可拖拽面板宽度
  const leftResizable = useResizablePanel({
    storageKey: "leftPanelWidth",
    defaultWidth: 280,
    minWidth: 200,
    maxWidth: 400,
    side: "left",
  });
  const rightResizable = useResizablePanel({
    storageKey: "rightPanelWidth",
    defaultWidth: 300,
    minWidth: 220,
    maxWidth: 450,
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

  // 桌面端：切换面板可见性
  const toggleLeftPanel = () => setLeftPanelOpen(!leftPanelOpen);
  const toggleRightPanel = () => setRightPanelOpen(!rightPanelOpen);

  // 移动端：打开/关闭抽屉
  const openMobileLeft = () => setMobileLeftOpen(true);
  const openMobileRight = () => setMobileRightOpen(true);

  return (
    <div className={styles.page}>
      {/* Top Bar */}
      <div className={styles.topBar}>
        <div className={styles.topLeft}>
          {/* 左面板切换按钮 */}
          {isMobile ? (
            <button
              className={styles.panelToggle}
              onClick={openMobileLeft}
              title="打开左侧面板"
            >
              ☰
            </button>
          ) : (
            <button
              className={`${styles.panelToggle} ${leftPanelOpen ? styles.panelToggleActive : ""}`}
              onClick={toggleLeftPanel}
              title={leftPanelOpen ? "折叠左侧面板" : "展开左侧面板"}
            >
              ☰
            </button>
          )}
          {/* 返回项目列表 */}
          <button
            className={styles.iconBtn}
            onClick={() => router.push("/projects")}
            title="返回项目列表"
            aria-label="返回项目列表"
          >
            ←
          </button>
          {/* 项目切换下拉 */}
          <div className={styles.projectSwitcher}>
            <button
              className={styles.projectSwitcherBtn}
              onClick={() => setProjectMenuOpen(!projectMenuOpen)}
              title="切换项目"
            >
              <span className={styles.projectTitle}>
                {currentProject?.title || "加载中..."}
              </span>
              <span className={styles.projectSwitcherArrow}>▾</span>
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
          <ChapterSelector
            chapters={chapters}
            currentChapterId={currentChapter?.id}
            onChange={(ch) => setCurrentChapter(ch)}
            onAddChapter={handleAddChapter}
          />
        </div>
        <div className={styles.topRight}>
          {/* 健康状态 */}
          <span className={styles.healthIcon} title="系统健康状态">🛡</span>
          {/* 设置 */}
          <button
            className={styles.iconBtn}
            onClick={() => router.push("/settings")}
            title="设置"
            aria-label="设置"
          >
            ⚙
          </button>
          {/* 用户菜单 */}
          {user && (
            <div className={styles.userSection}>
              <button
                className={styles.userAvatarBtn}
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                title="用户菜单"
              >
                <span className={styles.userAvatar}>
                  {user.username?.charAt(0)?.toUpperCase() || "U"}
                </span>
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
          {/* 右面板切换按钮 */}
          {isMobile ? (
            <button
              className={styles.panelToggle}
              onClick={openMobileRight}
              title="打开右侧面板"
            >
              ✦
            </button>
          ) : (
            <button
              className={`${styles.panelToggle} ${rightPanelOpen ? styles.panelToggleActive : ""}`}
              onClick={toggleRightPanel}
              title={rightPanelOpen ? "折叠右侧面板" : "展开右侧面板"}
            >
              ✦
            </button>
          )}
        </div>
      </div>

      {/* Health Alerts */}
      <HealthAlertBanner alerts={healthAlerts} />

      {/* Generation Progress */}
      {generationTask && (
        <div className={styles.progressBar}>
          <GenerationProgress
            percent={generationTask.progress_percent}
            stage={generationTask.progress_stage}
          />
        </div>
      )}

      {/* Three-column Layout */}
      <div className={styles.main}>
        {/* Left Panel - Desktop */}
        {!isMobile && (
          <div
            className={`${styles.leftPanel} ${!leftPanelOpen ? styles.leftPanelCollapsed : ""}`}
            style={leftPanelOpen ? { width: leftResizable.width, minWidth: leftResizable.width } : undefined}
          >
            <LeftPanel />
          </div>
        )}

        {/* Left Panel - Mobile Drawer */}
        {isMobile && (
          <>
            <div
              className={`${styles.overlay} ${mobileLeftOpen ? styles.overlayVisible : ""}`}
              onClick={closeMobileLeft}
            />
            <div className={`${styles.leftPanel} ${mobileLeftOpen ? styles.leftPanelOpen : ""}`}>
              <LeftPanel />
            </div>
          </>
        )}

        {/* Resizable Handle: Left ↔ Editor */}
        {!isMobile && leftPanelOpen && (
          <ResizableHandle
            onMouseDown={leftResizable.onResizeStart}
            active={leftResizable.isResizing}
          />
        )}

        {/* Center: Editor (Obsidian-style centered) */}
        <div className={styles.editorArea}>
          <div className={styles.editorCenter}>
            <Editor />
          </div>
        </div>

        {/* Resizable Handle: Editor ↔ Right */}
        {!isMobile && rightPanelOpen && (
          <ResizableHandle
            onMouseDown={rightResizable.onResizeStart}
            active={rightResizable.isResizing}
          />
        )}

        {/* Right Panel - Desktop */}
        {!isMobile && (
          <div
            className={`${styles.rightPanel} ${!rightPanelOpen ? styles.rightPanelCollapsed : ""}`}
            style={rightPanelOpen ? { width: rightResizable.width, minWidth: rightResizable.width } : undefined}
          >
            <RightPanel />
          </div>
        )}

        {/* Right Panel - Mobile Drawer */}
        {isMobile && (
          <>
            <div
              className={`${styles.overlay} ${mobileRightOpen ? styles.overlayVisible : ""}`}
              onClick={closeMobileRight}
            />
            <div className={`${styles.rightPanel} ${mobileRightOpen ? styles.rightPanelOpen : ""}`}>
              <RightPanel />
            </div>
          </>
        )}
      </div>

      {/* Tool Bar */}
      <ToolBar onDraw={() => setCardModalOpen(true)} />

      {/* Card Modal */}
      <CardModal
        isOpen={cardModalOpen}
        onClose={() => setCardModalOpen(false)}
        cards={cards}
        remainingRedraws={drawResult?.remaining_redraws ?? 3}
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

export default function WorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // 路由守卫：未登录时重定向到 /auth
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

  // 保存最后访问的项目ID
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
