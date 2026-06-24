import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  type Chapter,
  type Option,
  type Phase,
  useWritingStore,
  type WritingProject,
} from "../useWritingStore";

/** 构造测试用项目 */
function createProject(overrides: Partial<WritingProject> = {}): WritingProject {
  const defaultChapters: Chapter[] = [
    { id: 1, title: "第1章", summary: "开头", content: "", status: "draft" },
  ];
  return {
    id: "proj-1",
    title: "测试项目",
    genre: "科幻",
    phase: "drafting",
    currentChapter: 1,
    totalChapters: 1,
    summary: "一个测试项目",
    chapters: [...defaultChapters],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
    status: "draft",
    createdAt: "2025-01-01",
    updatedAt: "2025-01-01",
    ...overrides,
  };
}

/** 构造测试用选项 */
function createOption(overrides: Partial<Option> = {}): Option {
  return {
    id: "opt-1",
    label: "A",
    title: "主角发现秘密",
    description: "主角意外发现了一个惊天秘密",
    preview: "秘密...",
    agent: "plot",
    confidence: 0.85,
    ...overrides,
  };
}

describe("useWritingStore", () => {
  // 每个测试前重置 store
  beforeEach(() => {
    useWritingStore.setState({
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
    });
  });

  describe("初始状态", () => {
    it("应该使用默认初始值", () => {
      const state = useWritingStore.getState();
      expect(state.projects).toEqual([]);
      expect(state.activeProjectId).toBeNull();
      expect(state.project).toBeNull();
      expect(state.options).toEqual([]);
      expect(state.selectedOption).toBeNull();
      expect(state.customInput).toBe("");
      expect(state.history).toEqual([]);
      expect(state.isGenerating).toBe(false);
    });
  });

  describe("loadProjects", () => {
    it("应该加载项目列表并设置第一个项目为活跃项目", () => {
      const p1 = createProject({ id: "proj-1", title: "项目A" });
      const p2 = createProject({ id: "proj-2", title: "项目B" });

      useWritingStore.getState().loadProjects([p1, p2]);

      const state = useWritingStore.getState();
      expect(state.projects).toHaveLength(2);
      expect(state.activeProjectId).toBe("proj-1");
      expect(state.project?.title).toBe("项目A");
    });

    it("应该保持已有的活跃项目不变", () => {
      const p1 = createProject({ id: "proj-1", title: "项目A" });
      const p2 = createProject({ id: "proj-2", title: "项目B" });

      useWritingStore.setState({ activeProjectId: "proj-2" });
      useWritingStore.getState().loadProjects([p1, p2]);

      const state = useWritingStore.getState();
      expect(state.activeProjectId).toBe("proj-2");
    });
  });

  describe("setActiveProject", () => {
    it("应该切换活跃项目", () => {
      const p1 = createProject({ id: "proj-1", title: "项目A" });
      const p2 = createProject({ id: "proj-2", title: "项目B" });
      useWritingStore.getState().loadProjects([p1, p2]);

      useWritingStore.getState().setActiveProject("proj-2");

      const state = useWritingStore.getState();
      expect(state.activeProjectId).toBe("proj-2");
      expect(state.project?.title).toBe("项目B");
    });

    it("切换时应清空选项", () => {
      const p1 = createProject({ id: "proj-1" });
      const p2 = createProject({ id: "proj-2" });
      useWritingStore.getState().loadProjects([p1, p2]);
      useWritingStore.setState({ options: [createOption()] });

      useWritingStore.getState().setActiveProject("proj-2");

      expect(useWritingStore.getState().options).toEqual([]);
    });

    it("项目不存在时不应更改状态", () => {
      const p1 = createProject({ id: "proj-1" });
      useWritingStore.getState().loadProjects([p1]);

      useWritingStore.getState().setActiveProject("non-existent");

      const state = useWritingStore.getState();
      expect(state.activeProjectId).toBe("proj-1");
    });
  });

  describe("addProject", () => {
    it("应该添加新项目并自动创建第1章", () => {
      const newProj = createProject({ id: "proj-new", title: "新项目" });

      useWritingStore.getState().addProject(newProj);

      const state = useWritingStore.getState();
      expect(state.projects).toHaveLength(1);
      expect(state.projects[0].title).toBe("新项目");
      expect(state.projects[0].chapters).toHaveLength(1);
      expect(state.projects[0].chapters[0]).toMatchObject({
        id: 1,
        title: "第1章",
        status: "draft",
      });
      expect(state.projects[0].currentChapter).toBe(1);
      expect(state.projects[0].totalChapters).toBe(1);
    });

    it("添加第一个项目时自动设为活跃项目", () => {
      const newProj = createProject({ id: "proj-new" });

      useWritingStore.getState().addProject(newProj);

      const state = useWritingStore.getState();
      expect(state.activeProjectId).toBe("proj-new");
      expect(state.project?.id).toBe("proj-new");
    });
  });

  describe("selectOption", () => {
    it("应该选中选项并记录历史", () => {
      const option = createOption();
      const project = createProject();
      useWritingStore.setState({
        project,
        options: [option],
      });

      useWritingStore.getState().selectOption("opt-1");

      const state = useWritingStore.getState();
      expect(state.selectedOption).toBe("opt-1");
      expect(state.history).toHaveLength(1);
      expect(state.history[0]).toMatchObject({
        phase: "drafting",
        chapter: 1,
        choice: "A",
      });
      expect(state.isGenerating).toBe(true);
    });

    it("选项不存在时应忽略", () => {
      useWritingStore.setState({ options: [createOption()] });

      useWritingStore.getState().selectOption("non-existent");

      expect(useWritingStore.getState().history).toHaveLength(0);
    });
  });

  describe("undo", () => {
    it("应该撤销上一次操作", () => {
      const option = createOption();
      const project = createProject();
      useWritingStore.setState({ project, options: [option] });
      useWritingStore.getState().selectOption("opt-1");

      useWritingStore.getState().undo();

      const state = useWritingStore.getState();
      expect(state.history).toHaveLength(0);
      expect(state.selectedOption).toBeNull();
    });

    it("历史为空时不应出错", () => {
      expect(() => {
        useWritingStore.getState().undo();
      }).not.toThrow();
    });
  });

  describe("setCustomInput / submitCustom", () => {
    it("应该设置自定义输入内容", () => {
      useWritingStore.getState().setCustomInput("测试输入");

      expect(useWritingStore.getState().customInput).toBe("测试输入");
    });

    it("提交自定义输入应记录历史并清空输入", () => {
      const project = createProject();
      useWritingStore.setState({ project, customInput: "用户自定义内容" });

      useWritingStore.getState().submitCustom();

      const state = useWritingStore.getState();
      expect(state.history).toHaveLength(1);
      expect(state.history[0]).toMatchObject({
        choice: "D",
      });
      expect(state.customInput).toBe("");
      expect(state.isGenerating).toBe(true);
    });

    it("空输入不应提交", () => {
      useWritingStore.setState({ customInput: "   " });

      useWritingStore.getState().submitCustom();

      expect(useWritingStore.getState().history).toHaveLength(0);
    });
  });

  describe("completeChapter", () => {
    it("应该完成指定章节", () => {
      const project = createProject({
        totalChapters: 3,
        chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }],
      });
      useWritingStore.setState({ projects: [project], project });

      useWritingStore.getState().completeChapter("proj-1", 1);

      const state = useWritingStore.getState();
      const completedChapter = state.projects[0].chapters.find((ch) => ch.id === 1);
      expect(completedChapter?.status).toBe("completed");
    });

    it("完成章节后应自动创建下一章", () => {
      const project = createProject({
        totalChapters: 3,
        chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }],
      });
      useWritingStore.setState({ projects: [project], project });

      useWritingStore.getState().completeChapter("proj-1", 1);

      const state = useWritingStore.getState();
      expect(state.projects[0].chapters).toHaveLength(2);
      const newChapter = state.projects[0].chapters.find((ch) => ch.id === 2);
      expect(newChapter).toBeDefined();
      expect(newChapter?.title).toBe("第2章");
      expect(newChapter?.status).toBe("draft");
      expect(state.projects[0].totalChapters).toBe(3); // 不会超过预设总章节
    });

    it("当所有章节完成时应切换到 revision 阶段", () => {
      const project = createProject({
        totalChapters: 1,
        chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }],
      });
      useWritingStore.setState({ projects: [project], project });

      useWritingStore.getState().completeChapter("proj-1", 1);

      const state = useWritingStore.getState();
      expect(state.project?.phase).toBe("revision");
      // 不应自动创建新章节
      expect(state.projects[0].chapters).toHaveLength(1);
    });
  });

  describe("setPhase", () => {
    it("应该切换项目阶段", () => {
      const project = createProject({ phase: "ideation" });
      useWritingStore.setState({ project });

      useWritingStore.getState().setPhase("outline");

      expect(useWritingStore.getState().project?.phase).toBe("outline");
    });

    it("切换阶段时应清空选项选中状态", () => {
      const project = createProject();
      useWritingStore.setState({
        project,
        options: [createOption()],
        selectedOption: "opt-1",
      });

      useWritingStore.getState().setPhase("revision");

      expect(useWritingStore.getState().selectedOption).toBeNull();
    });
  });

  describe("addChapter", () => {
    it("应该向项目追加新章节", () => {
      const project = createProject();
      useWritingStore.setState({ projects: [project], project });

      const newChapter: Chapter = {
        id: 2,
        title: "新增章节",
        summary: "",
        content: "",
        status: "draft",
      };
      useWritingStore.getState().addChapter("proj-1", newChapter);

      const state = useWritingStore.getState();
      expect(state.projects[0].chapters).toHaveLength(2);
      expect(state.project?.chapters).toHaveLength(2);
      expect(state.projects[0].currentChapter).toBe(2);
    });
  });

  describe("generateOptions", () => {
    it("应该设置 isGenerating 为 true", () => {
      useWritingStore.getState().generateOptions();

      expect(useWritingStore.getState().isGenerating).toBe(true);
    });
  });

  describe("updateAgents", () => {
    it("应该更新 Agent 列表", () => {
      const newAgents = [
        { id: "plot", name: "Plot", label: "剧情代理", status: "thinking" as const },
      ];

      useWritingStore.getState().updateAgents(newAgents);

      expect(useWritingStore.getState().agents).toEqual(newAgents);
    });
  });

  describe("setActiveChapter", () => {
    it("应该设置当前查看的章节", () => {
      useWritingStore.getState().setActiveChapter(3);

      expect(useWritingStore.getState().activeChapterId).toBe(3);
    });
  });

  describe("toggleProjectExpand", () => {
    it("应该切换项目展开状态", () => {
      useWritingStore.getState().toggleProjectExpand("proj-1");

      expect(useWritingStore.getState().expandedProjectId).toBe("proj-1");

      useWritingStore.getState().toggleProjectExpand("proj-1");

      expect(useWritingStore.getState().expandedProjectId).toBeNull();
    });
  });
});
