import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { WritingProject } from "@/stores/useWritingStore";

import { OptionsPanel } from "../OptionsPanel";

function createProject(overrides: Partial<WritingProject> = {}): WritingProject {
  return {
    id: "proj-1",
    title: "测试项目",
    genre: "科幻",
    phase: "drafting",
    currentChapter: 1,
    totalChapters: 3,
    summary: "测试",
    chapters: [{ id: 1, title: "第1章", summary: "", content: "", status: "draft" }],
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

describe("OptionsPanel", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders A/B/C options from MOCK_OPTIONS", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    expect(screen.getByText("展开宗门试炼")).toBeInTheDocument();
    expect(screen.getByText("神秘老者来访")).toBeInTheDocument();
    expect(screen.getByText("外门试剑大会")).toBeInTheDocument();
  });

  it("renders option labels (A/B/C) with confidence percentages", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });

  it("highlights selected option on click", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    const optionA = screen.getByText("展开宗门试炼").closest("button")!;
    fireEvent.click(optionA);

    // After selection, the button border should change to accent style
    expect(optionA.className).toContain("th-accent-dim");
  });

  it("shows 'confirm' button, disabled when no option selected", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    const confirmBtn = screen.getByText("请先选择一个选项");
    expect(confirmBtn).toBeInTheDocument();
    expect(confirmBtn.closest("button")?.disabled).toBe(true);
  });

  it("enables confirm button after option selection", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    fireEvent.click(screen.getByText("展开宗门试炼").closest("button")!);

    const confirmBtn = screen.getByText("确认选择");
    expect(confirmBtn.closest("button")?.disabled).toBe(false);
  });

  it("triggers generating state on confirm", () => {
    const project = createProject();
    const onDraftStep = vi.fn();
    render(<OptionsPanel project={project} onDraftStep={onDraftStep} />);

    // Select an option first
    fireEvent.click(screen.getByText("展开宗门试炼").closest("button")!);
    fireEvent.click(screen.getByText("确认选择"));

    expect(onDraftStep).toHaveBeenCalledTimes(1);
    expect(screen.getByText("生成中...")).toBeInTheDocument();
  });

  it("completes generation after timeout", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    fireEvent.click(screen.getByText("展开宗门试炼").closest("button")!);
    fireEvent.click(screen.getByText("确认选择"));

    expect(screen.getByText("生成中...")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1200);
    });

    // After timeout, button returns to initial state
    expect(screen.getByText("请先选择一个选项")).toBeInTheDocument();
  });

  it("switches to custom input mode", () => {
    const project = createProject();
    render(<OptionsPanel project={project} />);

    fireEvent.click(screen.getByText("自定义"));

    const textarea = screen.getByPlaceholderText(/写下你的想法/);
    expect(textarea).toBeInTheDocument();
  });
});
