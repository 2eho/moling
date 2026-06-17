"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import type {
  Chapter,
  CardPool,
  DrawRecord,
  GenerationTask,
  TaskStatus,
  VaultCharacter,
  VaultTimeline,
  VaultPlotPromise,
  VaultWorld,
  HealthAlert,
} from "@/lib/types";
import {
  chapterApi,
  cardApi,
  generationApi,
  vaultApi,
  healthApi,
} from "@/lib/api";

// ---- Types ----

export interface VaultData {
  characters: VaultCharacter[];
  timelines: VaultTimeline[];
  plotPromises: VaultPlotPromise[];
  worlds: VaultWorld[];
}

export interface WorkspaceContextValue {
  currentChapter: Chapter | null;
  chapters: Chapter[];
  cards: CardPool[];
  drawResult: DrawRecord | null;
  generationTask: GenerationTask | null;
  vaultData: VaultData | null;
  healthAlerts: HealthAlert[];
  isLoading: boolean;
  loadChapter: (chapterId: string) => Promise<void>;
  loadChapters: (projectId: string) => Promise<void>;
  loadCards: (projectId: string) => Promise<void>;
  drawCards: (
    cardIds: string[],
    weights: number[],
    mode: string,
  ) => Promise<void>;
  redrawCards: (projectId: string) => Promise<void>;
  generate: (cardIds: string[], weights?: number[], mode?: string, creativity?: number, wordCount?: number) => Promise<void>;
  confirmChapter: (chapterId: string) => Promise<void>;
  reviseChapter: (chapterId: string, reason?: string) => Promise<void>;
  createChapter: () => Promise<void>;
  loadVault: (projectId: string) => Promise<void>;
  loadHealthAlerts: (projectId: string) => Promise<void>;
  setCurrentChapter: (chapter: Chapter) => void;
  updateChapterContent: (content: string) => void;
}

// ---- Context ----

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

// ---- Provider ----

export function WorkspaceProvider({
  children,
  projectId,
}: {
  children: ReactNode;
  projectId: string;
}) {
  const [currentChapter, setCurrentChapterState] = useState<Chapter | null>(
    null,
  );
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [cards, setCards] = useState<CardPool[]>([]);
  const [drawResult, setDrawResult] = useState<DrawRecord | null>(null);
  const [generationTask, setGenerationTask] = useState<GenerationTask | null>(
    null,
  );
  const [vaultData, setVaultData] = useState<VaultData | null>(null);
  const [healthAlerts, setHealthAlerts] = useState<HealthAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [generationProgress, setGenerationProgress] = useState<{ percent: number; stage: string }>({ percent: 0, stage: "" });
  const generationPollRef = useRef<NodeJS.Timeout | null>(null);

  // 简单的 toast 实现（后续替换为真正的 toast 库）
  const showToast = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    console.log(`[${type}] ${message}`);
    // TODO: 用真正的 toast 库（react-hot-toast / sonner）替换
  }, []);

  // ✅ 使用 useRef 替代 useState：避免 generate 回调因 generationParams 变化而重建
  const generationParamsRef = useRef<{
    weights?: number[];
    mode?: string;
    creativity?: number;
    wordCount?: number;
  }>({});

  // ✅ 使用 ref 保存最新的 currentChapter，避免闭包过期问题
  const currentChapterRef = useRef<Chapter | null>(null);
  useEffect(() => {
    currentChapterRef.current = currentChapter;
  }, [currentChapter]);

  const loadChapter = useCallback(async (chapterId: string) => {
    try {
      const res = await chapterApi.getById(projectId, chapterId);
      setCurrentChapterState(res.data || null);
    } catch (error) {
      console.error("Failed to load chapter:", error);
      setCurrentChapterState(null);
    }
  }, [projectId]);

  const loadChapters = useCallback(async (_projectId: string) => {
    try {
      const res = await chapterApi.list(_projectId);
      // ✅ 修复：确保 chapters 始终是数组
      setChapters(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error("Failed to load chapters:", error);
      setChapters([]);
    }
  }, []); // ✅ 移除 currentChapter 依赖，避免循环

  const loadCards = useCallback(async (_projectId: string) => {
    try {
      const res = await cardApi.getPool(_projectId);
      // ✅ 修复：确保 cards 始终是数组
      setCards(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error("Failed to load cards:", error);
      setCards([]);
    }
  }, []);

  const drawCards = useCallback(
    async (cardIds: string[], weights: number[], mode: string) => {
      const chapterId = currentChapterRef.current?.id || "";
      try {
        const res = await cardApi.drawCards(
          projectId,
          {
            chapter_id: chapterId,
            keep_card_ids: cardIds,
            weights,
            mode,
          },
        );
        // ✅ 修复：确保 drawResult 不是 undefined
        setDrawResult(res.data || null);
      } catch (error) {
        console.error("Failed to draw cards:", error);
        setDrawResult(null);
      }
    },
    [projectId], // ✅ 使用 ref 替代 currentChapter state 依赖
  );

  const redrawCards = useCallback(
    async (_projectId: string) => {
      const chapterId = currentChapterRef.current?.id;
      if (!chapterId) return;
      try {
        // 使用固定值代替未定义的 cardIds
        const res = await cardApi.redraw(
          _projectId,
          chapterId,
          { keep_card_ids: [] }, // ✅ 修复：原代码引用了未定义的 cardIds
        );
        // ✅ 修复：确保 drawResult 不是 undefined
        setDrawResult(res.data || null);
      } catch (error) {
        console.error("Failed to redraw cards:", error);
        setDrawResult(null);
      }
    },
    [], // ✅ 使用 ref 替代 state 依赖
  );

  const generate = useCallback(
    async (
      cardIds: string[],
      weights?: number[],
      mode?: string,
      creativity?: number,
      wordCount?: number,
    ) => {
      const chapterId = currentChapterRef.current?.id;
      if (!chapterId) return;
      // 从 ref 读取已保存的参数
      const savedParams = generationParamsRef.current;
      const finalWeights = weights ?? savedParams.weights;
      const finalMode = mode ?? savedParams.mode;
      const finalCreativity = creativity ?? savedParams.creativity;
      const finalWordCount = wordCount ?? savedParams.wordCount;
      // 保存本次使用的参数到 ref（不触发重渲染）
      generationParamsRef.current = {
        weights: finalWeights,
        mode: finalMode,
        creativity: finalCreativity,
        wordCount: finalWordCount,
      };
      try {
        const res = await generationApi.generate(projectId, chapterId, {
          card_ids: cardIds,
          weights: finalWeights,
          mode: finalMode,
          creativity: finalCreativity,
          word_count: finalWordCount,
        });

        const jobId = (res.data as { job_id: string }).job_id;
        if (!jobId) throw new Error("后端未返回 job_id，请检查异步生成接口");

        // 立即更新状态为 pending，UI 显示进度条
        setGenerationTask({
          id: jobId,
          project_id: projectId,
          chapter_id: chapterId,
          task_type: "generate_chapter",
          status: "pending",
          progress_stage: "等待队列...",
          progress_percent: 0,
        } as GenerationTask);
        setGenerationProgress({ percent: 0, stage: "" });
        // 开始轮询（每 2 秒）
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await generationApi.getJobStatus(jobId);
            const job = statusRes.data;

            setGenerationProgress(job.progress ?? { percent: 0, stage: "" });
            setGenerationTask(prev => {
              if (!prev) return prev;
              return {
                ...prev,
                status: job.status as TaskStatus,
                progress_stage: job.status === "running" ? "AI 生成中..." : prev.progress_stage,
                progress_percent: job.progress ?? prev.progress_percent,
              } as GenerationTask;
            });

            if (job.status === "completed") {
              clearInterval(pollInterval);
              setGenerationTask(prev => {
                if (!prev) return prev;
                return {
                  ...prev,
                  status: "completed",
                  progress_percent: 100,
                  output_data: job.result ?? null,
                } as GenerationTask;
              });
              showToast("success", "AI 生成完成！");
            } else if (job.status === "failed") {
              clearInterval(pollInterval);
              setGenerationTask(prev => {
                if (!prev) return prev;
                return {
                  ...prev,
                  status: "failed",
                  error_message: job.error ?? "未知错误",
                } as GenerationTask;
              });
              showToast("error", `生成失败：${job.error ?? "未知错误"}`);
            }
          } catch (err) {
            console.error("轮询生成状态失败：", err);
          }
        }, 2000);

        // 组件卸载或下次生成前清理定时器
        generationPollRef.current = pollInterval;
      } catch (error) {
        console.error("Failed to generate:", error);
        setGenerationTask(null);
        showToast("error", `创建生成任务失败：${error instanceof Error ? error.message : "未知错误"}`);
      }
    },
    [projectId], // ✅ 大幅简化依赖数组
  );

  const confirmChapter = useCallback(async (chapterId: string) => {
    // 清理可能还在运行的轮询定时器
    if (generationPollRef.current) {
      clearInterval(generationPollRef.current);
      generationPollRef.current = null;
    }
    const nonce = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    await generationApi.confirm(projectId, chapterId, nonce);
    setGenerationTask(null);
    setGenerationProgress({ percent: 0, stage: "" });
  }, [projectId]);

  const reviseChapter = useCallback(async (chapterId: string, reason?: string) => {
    // 清理可能还在运行的轮询定时器
    if (generationPollRef.current) {
      clearInterval(generationPollRef.current);
      generationPollRef.current = null;
    }
    await generationApi.revise(projectId, chapterId, reason);
    setGenerationTask(null);
    setGenerationProgress({ percent: 0, stage: "" });
  }, [projectId]);

  const createChapter = useCallback(async () => {
    const chapterNumber = chapters.length + 1;
    const newChapter = await chapterApi.create({
      project_id: projectId,
      title: `第${chapterNumber}章`,
    } as any);
    // 追加到章节列表
    setChapters((prev) => [...prev, newChapter.data]);
    // 自动选中新章节
    setCurrentChapterState(newChapter.data);
  }, [projectId]);

  // 组件卸载时清理轮询定时器
  useEffect(() => {
    return () => {
      if (generationPollRef.current) {
        clearInterval(generationPollRef.current);
        generationPollRef.current = null;
      }
    };
  }, []);

  const loadVault = useCallback(async (_projectId: string) => {
    try {
      const [charsRes, tlRes, ppRes, wldRes] = await Promise.all([
        vaultApi.getCharacters(_projectId),
        vaultApi.getTimeline(_projectId),
        vaultApi.getPlotPromises(_projectId),
        vaultApi.getWorld(_projectId),
      ]);
      // ✅ 修复：确保每个字段都是数组（或空数组）
      setVaultData({
        characters: Array.isArray(charsRes.data) ? charsRes.data : [],
        timelines: Array.isArray(tlRes.data) ? tlRes.data : [],
        plotPromises: Array.isArray(ppRes.data) ? ppRes.data : [],
        worlds: Array.isArray(wldRes.data) ? wldRes.data : [],
      });
    } catch (error) {
      console.error("Failed to load vault:", error);
      // ✅ 修复：API 失败时保持 vaultData 为 null 或安全的默认值
      setVaultData(null);
    }
  }, []);

  const loadHealthAlerts = useCallback(async (_projectId: string) => {
    try {
      const res = await healthApi.getAlerts(_projectId);
      // ✅ 修复：确保 healthAlerts 始终是数组
      setHealthAlerts(Array.isArray(res.data) ? res.data : []);
    } catch (error) {
      console.error("Failed to load health alerts:", error);
      setHealthAlerts([]);
    }
  }, []);

  const setCurrentChapter = useCallback((chapter: Chapter) => {
    setCurrentChapterState(chapter);
  }, []);

  const updateChapterContent = useCallback((content: string) => {
    setCurrentChapterState((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        content,
        word_count: content.replace(/\s/g, "").length,
      };
    });
  }, []);

  // Initialize workspace data
  // 根据接口映射文档 4.1：优先使用 GET /chapters/current 加载当前章节
  const initWorkspace = useCallback(async () => {
    setIsLoading(true);
    try {
      // 先尝试加载"当前章节"（不阻塞其他加载）
      chapterApi.getCurrent(projectId).then(res => {
        if (res.data) {
          setCurrentChapterState(res.data);
        }
      }).catch(() => {
        // 忽略错误，loadChapters 会回退到第一个章节
      });

      // 并行加载章节列表、卡牌池、四库、健康告警
      await Promise.all([
        loadChapters(projectId),
        loadCards(projectId),
        loadVault(projectId),
        loadHealthAlerts(projectId),
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    initWorkspace();
  }, [initWorkspace]);

  // ✅ 使用 useMemo 稳定 value 引用，避免所有消费者因父级重渲染而全量重渲染
  const value = useMemo<WorkspaceContextValue>(() => ({
    currentChapter,
    chapters,
    cards,
    drawResult,
    generationTask,
    vaultData,
    healthAlerts,
    isLoading,
    loadChapter,
    loadChapters,
    loadCards,
    drawCards,
    redrawCards,
    generate,
    confirmChapter,
    reviseChapter,
    loadVault,
    loadHealthAlerts,
    setCurrentChapter,
    updateChapterContent,
    createChapter,
  }), [
    currentChapter, chapters, cards, drawResult,
    generationTask, vaultData, healthAlerts, isLoading,
    loadChapter, loadChapters, loadCards,
    drawCards, redrawCards, generate,
    confirmChapter, reviseChapter, loadVault, loadHealthAlerts,
    setCurrentChapter, updateChapterContent, createChapter,
  ]);

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

// ---- Hook ----

export function useWorkspaceContext(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error(
      "useWorkspaceContext must be used within a WorkspaceProvider",
    );
  }
  return context;
}
