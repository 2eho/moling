"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
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
  generate: (cardIds: string[]) => Promise<void>;
  confirmChapter: (chapterId: string) => Promise<void>;
  reviseChapter: (chapterId: string) => Promise<void>;
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

  const loadChapter = useCallback(async (chapterId: string) => {
    const res = await chapterApi.getById(projectId, chapterId);
    setCurrentChapterState(res.data);
  }, [projectId]);

  const loadChapters = useCallback(async (_projectId: string) => {
    const res = await chapterApi.list(_projectId);
    setChapters(res.data);
    if (res.data.length > 0 && !currentChapter) {
      setCurrentChapterState(res.data[0]);
    }
  }, [currentChapter]);

  const loadCards = useCallback(async (_projectId: string) => {
    const res = await cardApi.getPool(_projectId);
    setCards(res.data);
  }, []);

  const drawCards = useCallback(
    async (cardIds: string[], weights: number[], mode: string) => {
      const res = await cardApi.drawCards(
        projectId,
        cardIds,
        weights,
        mode,
      );
      setDrawResult(res.data);
    },
    [projectId],
  );

  const redrawCards = useCallback(
    async (_projectId: string) => {
      if (!currentChapter?.id) return;
      const res = await cardApi.redraw(_projectId, currentChapter.id);
      setDrawResult(res.data);
    },
    [currentChapter],
  );

  const generate = useCallback(
    async (cardIds: string[]) => {
      if (!currentChapter?.id) return;
      const res = await generationApi.generate(projectId, currentChapter.id, cardIds);
      setGenerationTask(res.data);
    },
    [projectId, currentChapter],
  );

  const confirmChapter = useCallback(async (chapterId: string) => {
    await generationApi.confirm(projectId, chapterId);
    setGenerationTask(null);
  }, [projectId]);

  const reviseChapter = useCallback(async (chapterId: string) => {
    await generationApi.revise(projectId, chapterId);
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
  const initWorkspace = useCallback(async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        loadChapters(projectId),
        loadCards(projectId),
        loadVault(projectId),
        loadHealthAlerts(projectId),
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, loadChapters, loadCards, loadVault, loadHealthAlerts]);

  useEffect(() => {
    initWorkspace();
  }, [initWorkspace]);

  const value: WorkspaceContextValue = {
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
  };

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
