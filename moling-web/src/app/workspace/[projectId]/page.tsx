"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useState, useEffect, useCallback } from "react";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import { ChapterSelector } from "@/components/workspace/ChapterSelector";
import { ToolBar } from "@/components/workspace/ToolBar";
import { HealthAlertBanner } from "@/components/workspace/HealthAlert";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useProjectContext } from "@/contexts/ProjectContext";
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
    setCurrentChapter,
  } = useWorkspace();

  const { currentProject, loadProject } = useProjectContext();

  const [cardModalOpen, setCardModalOpen] = useState(false);
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileLeftOpen, setMobileLeftOpen] = useState(false);
  const [mobileRightOpen, setMobileRightOpen] = useState(false);

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

  const handleAddChapter = () => {
    showToast("info", "新增章节功能即将上线");
  };

  const handleDrawCards = async (
    cardIds: string[],
    weights: number[],
    mode: string,
  ) => {
    await drawCards(cardIds, weights, mode);
  };

  const handleRedraw = async () => {
    await redrawCards(projectId);
    showToast("info", "已重新抽取卡牌");
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
          <span className={styles.projectTitle}>
            {currentProject?.title || "加载中..."}
          </span>
          <ChapterSelector
            chapters={chapters}
            currentChapterId={currentChapter?.id}
            onChange={(ch) => setCurrentChapter(ch)}
            onAddChapter={handleAddChapter}
          />
        </div>
        <div className={styles.topRight}>
          <span className={styles.healthIcon}>🛡</span>
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
        <div className={`${styles.leftPanel} ${!leftPanelOpen && !isMobile ? styles.leftPanelCollapsed : ""}`}>
          <LeftPanel />
        </div>

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

        {/* Center: Editor (Obsidian-style centered) */}
        <div className={styles.editorArea}>
          <div className={styles.editorCenter}>
            <Editor />
          </div>
        </div>

        {/* Right Panel - Desktop */}
        <div className={`${styles.rightPanel} ${!rightPanelOpen && !isMobile ? styles.rightPanelCollapsed : ""}`}>
          <RightPanel />
        </div>

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
