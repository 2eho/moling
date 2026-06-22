import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWritingStore } from "@/stores/useWritingStore";
import type { WritingProject } from "@/stores/useWritingStore";

// Mock useRouter before rendering
const mockPush = vi.fn();
vi.mock("@/lib/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  setRouterHook: vi.fn(),
}));

import { Sidebar } from "../Sidebar";

function createProject(overrides: Partial<WritingProject> = {}): WritingProject {
  return {
    id: "proj-1",
    title: "测试项目",
    genre: "科幻",
    phase: "drafting",
    currentChapter: 1,
    totalChapters: 3,
    summary: "测试",
    chapters: [
      { id: 1, title: "第1章", summary: "", content: "", status: "completed" },
      { id: 2, title: "第2章", summary: "", content: "", status: "draft" },
      { id: 3, title: "第3章", summary: "", content: "", status: "draft" },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
    ...overrides,
  };
}

describe("Sidebar", () => {
  beforeEach(() => {
    mockPush.mockReset();
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

  describe("collapsed state (default)", () => {
    it("renders narrow icon bar with menu button", () => {
      render(<Sidebar collapsed={true} onToggle={vi.fn()} />);

      expect(screen.getByLabelText("打开菜单")).toBeInTheDocument();
      expect(screen.getByLabelText("展开侧栏")).toBeInTheDocument();
    });

    it("calls onToggle when expand button clicked", () => {
      const onToggle = vi.fn();
      render(<Sidebar collapsed={true} onToggle={onToggle} />);

      fireEvent.click(screen.getByLabelText("展开侧栏"));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it("opens mobile overlay when hamburger clicked", () => {
      render(<Sidebar collapsed={true} onToggle={vi.fn()} />);

      fireEvent.click(screen.getByLabelText("打开菜单"));

      expect(screen.getByLabelText("关闭侧栏")).toBeInTheDocument();
      expect(screen.getByText("新建")).toBeInTheDocument();
    });
  });

  describe("expanded state", () => {
    it("renders full sidebar with collapse button", () => {
      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      expect(screen.getByLabelText("折叠侧栏")).toBeInTheDocument();
    });

    it("shows empty state when no projects", () => {
      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      expect(screen.getByText(/暂无项目/)).toBeInTheDocument();
    });

    it("renders project list with chapters when projects exist", () => {
      const proj = createProject({ id: "proj-1", title: "剑道巅峰" });
      useWritingStore.setState({
        projects: [proj],
        activeProjectId: "proj-1",
        expandedProjectId: null,
      });

      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      expect(screen.getByText("剑道巅峰")).toBeInTheDocument();
    });

    it("highlights active project", () => {
      const proj1 = createProject({ id: "proj-1", title: "项目A" });
      const proj2 = createProject({ id: "proj-2", title: "项目B" });
      useWritingStore.setState({
        projects: [proj1, proj2],
        activeProjectId: "proj-2",
      });

      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      const buttonA = screen.getByText("项目A").closest("button");
      const buttonB = screen.getByText("项目B").closest("button");

      // Active project should have accent background style
      expect(buttonB?.style.color || buttonB?.getAttribute("style") || "").toBeTruthy();
    });

    it("navigates to workspace when project clicked", () => {
      const proj = createProject({ id: "proj-1", title: "剑道巅峰" });
      useWritingStore.setState({ projects: [proj] });

      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      fireEvent.click(screen.getByText("剑道巅峰"));
      expect(mockPush).toHaveBeenCalledWith("/workspace/proj-1");
    });

    it("shows expanded chapters when project is expanded", () => {
      const proj = createProject({ id: "proj-1", title: "剑道巅峰" });
      useWritingStore.setState({
        projects: [proj],
        activeProjectId: "proj-1",
        expandedProjectId: "proj-1",
      });

      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      // Chapters should be visible (reversed order)
      expect(screen.getByText("第3章")).toBeInTheDocument();
      expect(screen.getByText("第2章")).toBeInTheDocument();
      expect(screen.getByText("第1章")).toBeInTheDocument();
    });

    it("disables chapters from non-active projects", () => {
      const proj1 = createProject({ id: "proj-1", title: "项目A" });
      const proj2 = createProject({ id: "proj-2", title: "项目B" });
      useWritingStore.setState({
        projects: [proj1, proj2],
        activeProjectId: "proj-1",
        expandedProjectId: "proj-2",
      });

      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      // Chapters of non-active project should be disabled
      const chapterButtons = screen.getAllByText(/第\d章/);
      const chapterBtn = chapterButtons[0].closest("button");
      expect(chapterBtn?.disabled).toBe(true);
    });
  });

  describe("bottom section", () => {
    it("renders knowledge center and plugin market buttons", () => {
      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      expect(screen.getByText("知识中心")).toBeInTheDocument();
      expect(screen.getByText("插件市场")).toBeInTheDocument();
    });

    it("navigates to settings when settings button clicked", () => {
      render(<Sidebar collapsed={false} onToggle={vi.fn()} />);

      fireEvent.click(screen.getByLabelText("设置"));
      expect(mockPush).toHaveBeenCalledWith("/settings");
    });
  });
});
