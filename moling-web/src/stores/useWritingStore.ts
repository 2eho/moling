"use client";

import { create } from "zustand";

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

/** 人物 */
export interface Character {
  id: string;
  name: string;
  role: "protagonist" | "supporting" | "antagonist" | "minor";
  description: string;
  arc: string;
}

/** 伏笔 */
export interface Foreshadowing {
  id: string;
  description: string;
  status: "planted" | "resolved";
  chapter?: number;
}

/** 项目 */
export interface Project {
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
}

/** 写作 Store */
interface WritingStore {
  /** 所有项目 */
  projects: Project[];
  /** 当前激活项目 ID */
  activeProjectId: string | null;
  /** 已展开的项目 ID 集合 */
  expandedProjects: Set<string>;
  /** 当前项目 */
  project: Project | null;
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
  loadProjects: (projects: Project[]) => void;
  /** 加载项目 */
  loadProject: (project: Project) => void;
  /** 切换激活项目 */
  setActiveProject: (projectId: string) => void;
  /** 添加新项目 */
  addProject: (project: Project) => void;
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

export const useWritingStore = create<WritingStore>((set, get) => ({
  projects: [],
  activeProjectId: null,
  expandedProjects: new Set<string>(),
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

  addProject: (project) =>
    set((s) => ({
      projects: [...s.projects, project],
      project: s.project ?? project,
      activeProjectId: s.activeProjectId ?? project.id,
    })),

  toggleProjectExpand: (projectId) =>
    set((s) => {
      const next = new Set(s.expandedProjects);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return { expandedProjects: next };
    }),

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

    setTimeout(() => {
      set({ isGenerating: false });
    }, 1500);
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

    setTimeout(() => {
      set({ isGenerating: false });
    }, 1500);
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
    setTimeout(() => {
      set({ isGenerating: false });
    }, 1200);
  },

  updateAgents: (agents) => set({ agents }),
}));
