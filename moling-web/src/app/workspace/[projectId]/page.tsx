"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
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

  return (
    <div className={styles.page}>
      {/* Top Bar */}
      <div className={styles.topBar}>
        <div className={styles.topLeft}>
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
        <LeftPanel />
        <Editor />
        <RightPanel />
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
