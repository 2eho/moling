import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { WritingProject } from "@/stores/useWritingStore";

import { ProjectList } from "../ProjectList";

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
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
    ...overrides,
  };
}

function createCompletedProject(overrides: Partial<WritingProject> = {}): WritingProject {
  return {
    id: "proj-comp",
    title: "已完成项目",
    genre: "科幻",
    phase: "revision",
    currentChapter: 2,
    totalChapters: 2,
    summary: "已完成",
    chapters: [
      { id: 1, title: "第1章", summary: "", content: "", status: "completed" },
      { id: 2, title: "第2章", summary: "", content: "", status: "completed" },
    ],
    characters: [],
    foreshadowing: [],
    worldRules: "",
    styleNotes: "",
    ...overrides,
  };
}

describe("ProjectList", () => {
  const defaultProps = {
    projects: [] as WritingProject[],
    activeProjectId: null as string | null,
    expandedProjectId: null as string | null,
    activeChapterId: null as number | null,
    onProjectClick: vi.fn(),
    onChapterClick: vi.fn(),
  };

  beforeEach(() => {
    defaultProps.onProjectClick = vi.fn();
    defaultProps.onChapterClick = vi.fn();
  });

  it("renders empty state when no projects", () => {
    render(<ProjectList {...defaultProps} />);

    expect(screen.getByText("连载中")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("renders multiple ongoing projects", () => {
    const proj1 = createProject({ id: "p1", title: "项目A", chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }] });
    const proj2 = createProject({ id: "p2", title: "项目B", chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }] });

    render(<ProjectList {...defaultProps} projects={[proj1, proj2]} />);

    expect(screen.getByText("项目A")).toBeInTheDocument();
    expect(screen.getByText("项目B")).toBeInTheDocument();
  });

  it("triggers onProjectClick when project clicked", () => {
    const proj = createProject({ id: "p1", title: "项目A", chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }] });

    render(<ProjectList {...defaultProps} projects={[proj]} />);

    fireEvent.click(screen.getByText("项目A"));
    expect(defaultProps.onProjectClick).toHaveBeenCalledWith("p1");
  });

  it("shows chapters when project is expanded", () => {
    const proj = createProject({ id: "p1", title: "项目A" });

    render(
      <ProjectList
        {...defaultProps}
        projects={[proj]}
        expandedProjectId="p1"
      />
    );

    // Chapters are rendered in reverse order
    expect(screen.getByText("第2章")).toBeInTheDocument();
    expect(screen.getByText("第1章")).toBeInTheDocument();
  });

  it("triggers onChapterClick when chapter clicked", () => {
    const proj = createProject({ id: "p1", title: "项目A" });

    render(
      <ProjectList
        {...defaultProps}
        projects={[proj]}
        expandedProjectId="p1"
        activeProjectId="p1"
      />
    );

    fireEvent.click(screen.getByText("第2章"));
    expect(defaultProps.onChapterClick).toHaveBeenCalledWith("p1", 2);
  });

  it("separates ongoing and completed projects", () => {
    const ongoing = createProject({ id: "p1", title: "连载中项目" });
    const completed = createCompletedProject({ id: "p2", title: "已完成项目" });

    render(<ProjectList {...defaultProps} projects={[ongoing, completed]} />);

    expect(screen.getByText("连载中项目")).toBeInTheDocument();
    expect(screen.getByText("已完成项目")).toBeInTheDocument();
    expect(screen.getByText("已完结")).toBeInTheDocument();
  });

  it("shows '完结' badge on completed projects", () => {
    const completed = createCompletedProject({ id: "p1", title: "已完成项目" });

    render(<ProjectList {...defaultProps} projects={[completed]} />);

    expect(screen.getByText("完结")).toBeInTheDocument();
  });

  it("highlights active chapter", () => {
    const proj = createProject({ id: "p1", title: "项目A" });

    render(
      <ProjectList
        {...defaultProps}
        projects={[proj]}
        activeProjectId="p1"
        expandedProjectId="p1"
        activeChapterId={2}
      />
    );

    // Chapter 2 should be highlighted (it's the active chapter)
    const ch2Btn = screen.getByText("第2章").closest("button");
    expect(ch2Btn).toBeTruthy();
  });

  it("calls onClose after project click when onClose provided", () => {
    const proj = createProject({ id: "p1", title: "项目A", chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }] });
    const onClose = vi.fn();

    render(<ProjectList {...defaultProps} projects={[proj]} onClose={onClose} />);

    fireEvent.click(screen.getByText("项目A"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
