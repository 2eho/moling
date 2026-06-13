"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import { WorkspaceProvider } from "@/contexts/WorkspaceContext";
import { LeftPanel } from "@/components/workspace/LeftPanel";
import { Editor } from "@/components/workspace/Editor";
import { RightPanel } from "@/components/workspace/RightPanel";
import { ChapterSelector } from "@/components/workspace/ChapterSelector";
import { ToolBar } from "@/components/workspace/ToolBar";
import { CardModal } from "@/components/workspace/CardModal";
import { GenerationProgress } from "@/components/workspace/GenerationProgress";
import { HealthAlertBanner } from "@/components/workspace/HealthAlert";
import { useWorkspace } from "@/hooks/useWorkspace";
import { useProjectContext } from "@/contexts/ProjectContext";
import { showToast } from "@/components/ui/Toast";
import styles from "./workspace.module.css";

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
          generate(cardIds);
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
