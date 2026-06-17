"use client";

import { useState } from "react";
import styles from "./ToolBar.module.css";
import { Button } from "@/components/ui/Button";
import { useWorkspace } from "@/hooks/useWorkspace";
import { chapterAgentApi } from "@/lib/api";
import { showToast } from "@/components/ui/Toast";

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
    currentChapter,
  } = useWorkspace();

  const [agentInput, setAgentInput] = useState("");
  const [isRunningAgent, setIsRunningAgent] = useState(false);

  const isGenerating = generationTask?.status === "running";
  const hasCards = cards.length > 0;

  const handleDraw = () => {
    onDraw?.();
  };

  const handleGenerate = async () => {
    if (!hasCards) return;
    try {
      await generate(cards.slice(0, 3).map((c) => c.id));
    } catch (error: any) {
      showToast("error", `生成失败：${error?.message || "未知错误"}`);
    }
  };

  const handleConfirm = async () => {
    if (!drawResult) return;
    try {
      await confirmChapter(drawResult.chapter_id);
    } catch (error: any) {
      showToast("error", `收纳失败：${error?.message || "未知错误"}`);
    }
  };

  const handleRevise = async () => {
    if (!drawResult) return;
    try {
      await reviseChapter(drawResult.chapter_id);
    } catch (error: any) {
      showToast("error", `拒稿失败：${error?.message || "未知错误"}`);
    }
  };

  const handleAgentInput = async () => {
    if (!agentInput.trim() || !currentChapter?.id) return;
    setIsRunningAgent(true);
    try {
      const res = await chapterAgentApi.runAgent(
        currentChapter.project_id,
        currentChapter.id,
        agentInput.trim(),
      );
      const result = res.data;
      showToast("success", `AI 指令已执行: ${result.result ?? "完成"}`);
      setAgentInput("");
    } catch (e) {
      showToast("error", `AI 指令失败: ${(e as Error).message}`);
    } finally {
      setIsRunningAgent(false);
    }
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

      <div className={styles.center}>
        <input
          className={styles.agentInput}
          type="text"
          placeholder="输入 AI 指令，按回车执行…"
          value={agentInput}
          onChange={(e) => setAgentInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAgentInput();
            }
          }}
          disabled={isRunningAgent || !currentChapter}
        />
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
