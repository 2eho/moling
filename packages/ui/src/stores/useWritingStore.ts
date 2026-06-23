"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { VaultCharacter } from "@/lib/types/domain";

/** 写作阶段 */
export type Phase = "ideation" | "outline" | "character" | "worldbuilding" | "drafting" | "revision";

/** 选项 */
export interface Option {
  id: string;
  label: "A" | "B" | "C";
  title: string;
  description: string;
  preview: string;
  agent: string;
  confidence: number;
}

/** Agent 状态 */
export interface AgentStatus {
  id: string;
  name: string;
  label: string;
  status: "active" | "idle" | "thinking";
}

/** 章节 */
export interface Chapter {
  id: number;
  title: string;
  summary: string;
  content: string;
  status: "draft" | "completed";
}

/** 人物 — 派生自 VaultCharacter，仅保留写作工作区需要的字段 */
export type Character = Pick<
  VaultCharacter,
  "id" | "name" | "role" | "description" | "arc"
>;

/**
 * 伏笔 — 写作工作区专用的伏笔模型。
 * status 使用简写：planted（已埋设）/ resolved（已回收），
 * 与 VaultForeshadowing 的完整 status 联合类型兼容。
 */
export interface Foreshadowing {
  id: string;
  description: string;
  status: "planted" | "resolved";
  chapter?: number;
}

/** 项目（写作工作区模型） */
export interface WritingProject {
  id: string;
  title: string;
  genre: string;
  phase: Phase;
  currentChapter: number;
  totalChapters: number;
  summary: string;
  chapters: Chapter[];
  characters: Character[];
  foreshadowing: Foreshadowing[];
  worldRules: string;
  styleNotes: string;
  /** 项目状态：draft=连载中, completed=已完结 */
  status: "draft" | "completed";
  /** 创建日期 (YYYY-MM-DD) */
  createdAt: string;
  /** 最后修改日期 (YYYY-MM-DD) */
  updatedAt: string;
}

/** 写作 Store */
interface WritingStore {
  /** 所有项目 */
  projects: WritingProject[];
  /** 当前激活项目 ID */
  activeProjectId: string | null;
  /** 当前选中的章节 ID（中心区域正在查看的章节） */
  activeChapterId: number | null;
  /** 当前展开的项目 ID（同一时间只能展开一个） */
  expandedProjectId: string | null;
  /** 当前项目 */
  project: WritingProject | null;
  /** 当前选项列表 */
  options: Option[];
  /** 已选中的选项 ID */
  selectedOption: string | null;
  /** 自定义输入 */
  customInput: string;
  /** Agent 列表 */
  agents: AgentStatus[];
  /** 操作历史 */
  history: { phase: Phase; chapter: number; choice: string }[];
  /** 是否正在生成 */
  isGenerating: boolean;

  /** 加载所有项目 */
  loadProjects: (projects: WritingProject[]) => void;
  /** 加载项目 */
  loadProject: (project: WritingProject) => void;
  /** 切换激活项目 */
  setActiveProject: (projectId: string) => void;
  /** 设置当前查看的章节 */
  setActiveChapter: (chapterId: number) => void;
  /** 添加新项目 */
  addProject: (project: WritingProject) => void;
  /** 切换项目展开/折叠 */
  toggleProjectExpand: (projectId: string) => void;
  /** 设置阶段 */
  setPhase: (phase: Phase) => void;
  /** 选中选项（高亮） */
  setSelectedOption: (id: string | null) => void;
  /** 设置自定义输入 */
  setCustomInput: (input: string) => void;
  /** 确认选择选项 */
  selectOption: (optionId: string) => void;
  /** 提交自定义输入 */
  submitCustom: () => void;
  /** 撤销 */
  undo: () => void;
  /** 重新生成选项 */
  generateOptions: () => void;
  /** 新增章节 — 追加到数组末尾，渲染时倒序后自然置顶 */
  addChapter: (projectId: string, chapter: Chapter) => void;
  /** 完成章节 → 自动创建下一章 */
  completeChapter: (projectId: string, chapterId: number) => void;
  /** 更新 Agent 状态 */
  updateAgents: (agents: AgentStatus[]) => void;
}

/** 阶段中文映射 */
export const PHASE_LABELS: Record<Phase, string> = {
  ideation: "构思",
  outline: "大纲",
  character: "人设",
  worldbuilding: "世界观",
  drafting: "草稿",
  revision: "修订",
};

/** 阶段序号 */
export const PHASE_ORDER: Phase[] = [
  "ideation",
  "outline",
  "character",
  "worldbuilding",
  "drafting",
  "revision",
];

/** 计算阶段进度 (0-100) */
export const getPhaseProgress = (phase: Phase): number => {
  const idx = PHASE_ORDER.indexOf(phase);
  if (idx === -1) return 0;
  return Math.round(((idx + 1) / PHASE_ORDER.length) * 100);
};

export const useWritingStore = create<WritingStore>()(
  persist(
    (set, get) => ({
      projects: [],
      activeProjectId: null,
      activeChapterId: null,
      expandedProjectId: null,
      project: null,
      options: [],
      selectedOption: null,
      customInput: "",
      agents: [
        { id: "plot", name: "Plot", label: "剧情代理", status: "active" },
        { id: "character", name: "Character", label: "人物代理", status: "active" },
        { id: "dialogue", name: "Dialogue", label: "对话代理", status: "idle" },
        { id: "style", name: "Style", label: "风格代理", status: "active" },
        { id: "world", name: "World", label: "世界观代理", status: "active" },
      ],
      history: [],
      isGenerating: false,

      loadProjects: (projects) =>
        set((s) => ({
          projects,
          project: s.project ?? projects[0] ?? null,
          activeProjectId: s.activeProjectId ?? projects[0]?.id ?? null,
        })),

      loadProject: (project) =>
        set((s) => ({
          project,
          activeProjectId: project.id,
          options: [],
          selectedOption: null,
          history: [],
          projects: s.projects.some((p) => p.id === project.id)
            ? s.projects.map((p) => (p.id === project.id ? project : p))
            : [...s.projects, project],
        })),

      setActiveProject: (projectId) =>
        set((s) => {
          const target = s.projects.find((p) => p.id === projectId);
          return target
            ? { activeProjectId: projectId, project: target, options: [], selectedOption: null }
            : {};
        }),

      setActiveChapter: (chapterId) => set({ activeChapterId: chapterId }),

      addProject: (project) =>
        set((s) => {
          const ch1: Chapter = { id: 1, title: "第1章", summary: "", content: "", status: "draft" };
          const withChapters = { ...project, chapters: [ch1], currentChapter: 1, totalChapters: 1 };
          return {
            projects: [...s.projects, withChapters],
            project: s.project ?? withChapters,
            activeProjectId: s.activeProjectId ?? project.id,
          };
        }),

      toggleProjectExpand: (projectId) =>
        set((s) => ({
          expandedProjectId: s.expandedProjectId === projectId ? null : projectId,
        })),

      setPhase: (phase) =>
        set((s) => ({
          project: s.project ? { ...s.project, phase } : null,
          options: s.options,
          selectedOption: null,
        })),

      setSelectedOption: (id) => set({ selectedOption: id }),

      setCustomInput: (input) => set({ customInput: input }),

      selectOption: (optionId) => {
        const state = get();
        const option = state.options.find((o) => o.id === optionId);
        if (!option) return;

        set((s) => ({
          history: [
            ...s.history,
            { phase: s.project?.phase ?? "drafting", chapter: s.project?.currentChapter ?? 1, choice: option.label },
          ],
          selectedOption: optionId,
          isGenerating: true,
        }));
      },

      submitCustom: () => {
        const state = get();
        if (!state.customInput.trim()) return;

        set((s) => ({
          history: [
            ...s.history,
            { phase: s.project?.phase ?? "drafting", chapter: s.project?.currentChapter ?? 1, choice: "D" },
          ],
          customInput: "",
          isGenerating: true,
        }));
      },

      undo: () => {
        const state = get();
        if (state.history.length === 0) return;
        set((s) => ({
          history: s.history.slice(0, -1),
          selectedOption: null,
        }));
      },

      generateOptions: () => {
        set({ isGenerating: true });
      },

      updateAgents: (agents) => set({ agents }),

      addChapter: (projectId, chapter) =>
        set((s) => ({
          projects: s.projects.map((p) =>
            p.id === projectId
              ? {
                  ...p,
                  chapters: [...p.chapters, chapter],
                  currentChapter: chapter.id,
                  totalChapters: Math.max(p.totalChapters, chapter.id),
                }
              : p,
          ),
          project:
            s.project?.id === projectId
              ? {
                  ...s.project,
                  chapters: [...s.project.chapters, chapter],
                  currentChapter: chapter.id,
                  totalChapters: Math.max(s.project.totalChapters, chapter.id),
                }
              : s.project,
        })),

      completeChapter: (projectId, chapterId) =>
        set((s) => {
          const updateP = (p: WritingProject) => {
            if (p.id !== projectId) return p;
            const chapters = p.chapters.map((ch) =>
              ch.id === chapterId ? { ...ch, status: "completed" as const } : ch,
            );
            const allDone = chapters.length >= p.totalChapters && chapters.every((ch) => ch.status === "completed");
            if (allDone) {
              return { ...p, chapters, currentChapter: chapterId, phase: "revision" as Phase };
            }
            const nextId = chapterId + 1;
            const newChapter: Chapter = {
              id: nextId,
              title: `第${nextId}章`,
              summary: "",
              content: "",
              status: "draft",
            };
            return {
              ...p,
              chapters: [...chapters, newChapter],
              currentChapter: chapterId,
              totalChapters: Math.max(p.totalChapters, nextId),
            };
          };
          return {
            projects: s.projects.map(updateP),
            project: s.project ? updateP(s.project) : s.project,
          };
        }),
    }),
    {
      name: "vibe-writing-store",
      // Do NOT strip `project` from partialize — zustand's rehydration
      // flow applies a `set()` that can reset stripped fields to their
      // initial null value, causing the workspace spinner to spin forever.
      partialize: (state: WritingStore) => ({
        ...state,
        options: [],
        selectedOption: null,
        customInput: "",
        history: [],
        isGenerating: false,
        agents: state.agents,
      }),
      // Keep onRehydrateStorage as a safety net — reconstruct `project`
      // from `projects` + `activeProjectId` in case persisted data is stale.
      onRehydrateStorage: () => {
        return (state, error) => {
          if (error || !state) return;
          if (state.projects.length > 0) {
            state.project =
              state.projects.find((p) => p.id === state.activeProjectId) ??
              state.projects[0] ??
              null;
          }
          if (!state.expandedProjectId && state.activeProjectId) {
            state.expandedProjectId = state.activeProjectId;
          }
        };
      },
    },
  ),
);
