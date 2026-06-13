"use client";

import styles from "./ToolBar.module.css";
import { Button } from "@/components/ui/Button";
import { useWorkspace } from "@/hooks/useWorkspace";

interface ToolBarProps {
  onDraw?: () => void;
}

export function ToolBar({ onDraw }: ToolBarProps) {
  const {
    generationTask,
    generate,
    drawResult,
    confirmChapter,
    reviseChapter,
    cards,
  } = useWorkspace();

  const isGenerating = generationTask?.status === "running";
  const hasCards = cards.length > 0;

  const handleDraw = () => {
    onDraw?.();
  };

  const handleGenerate = () => {
    if (!hasCards) return;
    generate(cards.slice(0, 3).map((c) => c.id));
  };

  const handleConfirm = () => {
    if (!drawResult) return;
    confirmChapter(drawResult.chapter_id);
  };

  const handleRevise = () => {
    if (!drawResult) return;
    reviseChapter(drawResult.chapter_id);
  };

  return (
    <div className={styles.toolbar}>
      <div className={styles.left}>
        <Button variant="secondary" size="sm" onClick={handleDraw}>
          🎴 抽卡
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={handleGenerate}
          loading={isGenerating}
          disabled={!hasCards || isGenerating}
        >
          {isGenerating ? "生成中…" : "✨ 生成"}
        </Button>
      </div>
      <div className={styles.right}>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleConfirm}
          disabled={!drawResult}
        >
          📥 收纳
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRevise}
          disabled={!drawResult}
        >
          📤 拒稿
        </Button>
      </div>
    </div>
  );
}
