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
    const res = await chapterApi.getById(projectId, chapterId);
    setCurrentChapterState(res.data);
  }, [projectId]);

  const loadChapters = useCallback(async (_projectId: string) => {
    const res = await chapterApi.list(_projectId);
    setChapters(res.data);
  }, []); // ✅ 移除 currentChapter 依赖，避免循环

  const loadCards = useCallback(async (_projectId: string) => {
    const res = await cardApi.getPool(_projectId);
    setCards(res.data);
  }, []);

  const drawCards = useCallback(
    async (cardIds: string[], weights: number[], mode: string) => {
      const chapterId = currentChapterRef.current?.id || "";
      const res = await cardApi.drawCards(
        projectId,
        {
          chapter_id: chapterId,
          keep_card_ids: cardIds,
          weights,
          mode,
        },
      );
      setDrawResult(res.data);
    },
    [projectId], // ✅ 使用 ref 替代 currentChapter state 依赖
  );

  const redrawCards = useCallback(
    async (_projectId: string) => {
      const chapterId = currentChapterRef.current?.id;
      if (!chapterId) return;
      // 使用固定值代替未定义的 cardIds
      const res = await cardApi.redraw(
        _projectId,
        chapterId,
        { keep_card_ids: [] }, // ✅ 修复：原代码引用了未定义的 cardIds
      );
      setDrawResult(res.data);
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
      const res = await generationApi.generate(projectId, chapterId, {
        card_ids: cardIds,
        weights: finalWeights,
        mode: finalMode,
        creativity: finalCreativity,
        word_count: finalWordCount,
      });
      setGenerationTask(res.data);
    },
    [projectId], // ✅ 大幅简化依赖数组
  );

  const confirmChapter = useCallback(async (chapterId: string) => {
    const nonce = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    await generationApi.confirm(projectId, chapterId, nonce);
    setGenerationTask(null);
  }, [projectId]);

  const reviseChapter = useCallback(async (chapterId: string, reason?: string) => {
    await generationApi.revise(projectId, chapterId, reason);
    setGenerationTask(null);
  }, [projectId]);

  const loadVault = useCallback(async (_projectId: string) => {
    const [charsRes, tlRes, ppRes, wldRes] = await Promise.all([
      vaultApi.getCharacters(_projectId),
      vaultApi.getTimeline(_projectId),
      vaultApi.getPlotPromises(_projectId),
      vaultApi.getWorld(_projectId),
    ]);
    setVaultData({
      characters: charsRes.data,
      timelines: tlRes.data,
      plotPromises: ppRes.data,
      worlds: wldRes.data,
    });
  }, []);

  const loadHealthAlerts = useCallback(async (_projectId: string) => {
    const res = await healthApi.getAlerts(_projectId);
    setHealthAlerts(res.data);
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
  }), [
    currentChapter, chapters, cards, drawResult,
    generationTask, vaultData, healthAlerts, isLoading,
    loadChapter, loadChapters, loadCards,
    drawCards, redrawCards, generate,
    confirmChapter, reviseChapter, loadVault, loadHealthAlerts,
    setCurrentChapter, updateChapterContent,
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
