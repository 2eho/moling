import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWritingStore } from "@/stores/useWritingStore";

import { ActionBar } from "../ActionBar";

describe("ActionBar", () => {
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

  it("renders all action buttons", () => {
    render(<ActionBar />);

    expect(screen.getByText("上一步")).toBeInTheDocument();
    expect(screen.getByText("快进")).toBeInTheDocument();
    expect(screen.getByText("重来")).toBeInTheDocument();
    expect(screen.getByText("保存")).toBeInTheDocument();
    expect(screen.getByText("导出")).toBeInTheDocument();
  });

  it("shows '尚未选择' when history is empty", () => {
    render(<ActionBar />);

    expect(screen.getByText("尚未选择")).toBeInTheDocument();
  });

  it("shows history step count when history has entries", () => {
    useWritingStore.setState({
      history: [
        { phase: "drafting", chapter: 1, choice: "A" },
        { phase: "drafting", chapter: 1, choice: "B" },
      ],
    });

    render(<ActionBar />);

    expect(screen.getByText("2 步操作")).toBeInTheDocument();
  });

  it("disables 上一步 when history is empty", () => {
    render(<ActionBar />);

    const undoBtn = screen.getByText("上一步").closest("button")!;
    expect(undoBtn.disabled).toBe(true);
  });

  it("enables 上一步 when history has entries", () => {
    useWritingStore.setState({
      history: [{ phase: "drafting", chapter: 1, choice: "A" }],
    });

    render(<ActionBar />);

    const undoBtn = screen.getByText("上一步").closest("button")!;
    expect(undoBtn.disabled).toBe(false);
  });

  it("disables 上一步 when isGenerating is true", () => {
    useWritingStore.setState({
      history: [{ phase: "drafting", chapter: 1, choice: "A" }],
      isGenerating: true,
    });

    render(<ActionBar />);

    const undoBtn = screen.getByText("上一步").closest("button")!;
    expect(undoBtn.disabled).toBe(true);
  });

  it("快进 is always disabled", () => {
    render(<ActionBar />);

    const skipBtn = screen.getByText("快进").closest("button")!;
    expect(skipBtn.disabled).toBe(true);
  });

  it("保存 is always disabled", () => {
    render(<ActionBar />);

    const saveBtn = screen.getByText("保存").closest("button")!;
    expect(saveBtn.disabled).toBe(true);
  });

  it("导出 is always disabled", () => {
    render(<ActionBar />);

    const exportBtn = screen.getByText("导出").closest("button")!;
    expect(exportBtn.disabled).toBe(true);
  });

  it("triggers undo on 上一步 click", () => {
    useWritingStore.setState({
      history: [{ phase: "drafting", chapter: 1, choice: "A" }],
    });

    render(<ActionBar />);

    fireEvent.click(screen.getByText("上一步"));
    expect(useWritingStore.getState().history).toHaveLength(0);
  });

  it("triggers generateOptions on 重来 click", () => {
    render(<ActionBar />);

    fireEvent.click(screen.getByText("重来"));
    expect(useWritingStore.getState().isGenerating).toBe(true);
  });

  it("disables 重来 when isGenerating", () => {
    useWritingStore.setState({ isGenerating: true });

    render(<ActionBar />);

    const regenerateBtn = screen.getByText("重来").closest("button")!;
    expect(regenerateBtn.disabled).toBe(true);
  });

  it("shows selected option info", () => {
    useWritingStore.setState({
      selectedOption: "a",
      history: [{ phase: "drafting", chapter: 1, choice: "A" }],
    });

    render(<ActionBar />);

    expect(screen.getByText(/已选/)).toBeInTheDocument();
    expect(screen.getByText(/A/)).toBeInTheDocument();
  });
});
