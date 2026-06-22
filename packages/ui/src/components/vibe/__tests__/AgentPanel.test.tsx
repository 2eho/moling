import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWritingStore } from "@/stores/useWritingStore";

import { AgentPanel } from "../AgentPanel";

describe("AgentPanel", () => {
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

  it("renders all 5 agent tabs", () => {
    render(<AgentPanel />);

    expect(screen.getByText("剧情代理")).toBeInTheDocument();
    expect(screen.getByText("人物代理")).toBeInTheDocument();
    expect(screen.getByText("对话代理")).toBeInTheDocument();
    expect(screen.getByText("风格代理")).toBeInTheDocument();
    expect(screen.getByText("世界观代理")).toBeInTheDocument();
  });

  it("shows header with Agent 调度中心 title", () => {
    render(<AgentPanel />);

    expect(screen.getByText("Agent 调度中心")).toBeInTheDocument();
  });

  it("expands agent detail on click and shows mock outputs", () => {
    render(<AgentPanel />);

    // Click the first agent (剧情代理)
    const plotAgent = screen.getByText("剧情代理").closest("button")!;
    fireEvent.click(plotAgent);

    // Should show expanded content with mock outputs
    expect(screen.getByText(/叙事架构师/)).toBeInTheDocument();
    expect(screen.getByText(/已分析第3章剑骨觉醒上下文/)).toBeInTheDocument();
    expect(screen.getByText(/生成 3 个剧情方向/)).toBeInTheDocument();
  });

  it("collapses agent detail on second click", () => {
    render(<AgentPanel />);

    const plotAgent = screen.getByText("剧情代理").closest("button")!;
    // Expand
    fireEvent.click(plotAgent);
    expect(screen.getByText("叙事架构师")).toBeInTheDocument();

    // Collapse
    fireEvent.click(plotAgent);
    expect(screen.queryByText("叙事架构师")).not.toBeInTheDocument();
  });

  it("shows agent status labels (active/idle/thinking)", () => {
    render(<AgentPanel />);

    // Active agents show status
    const statusLabels = screen.getAllByText("活跃");
    expect(statusLabels.length).toBeGreaterThanOrEqual(2);
  });

  it("toggles settings panel to disable/enable agents", () => {
    render(<AgentPanel />);

    // Open settings
    fireEvent.click(screen.getByLabelText("Agent 设置"));
    expect(screen.getByText("代理开关")).toBeInTheDocument();

    // Disable an agent
    const enableButtons = screen.getAllByText("开启");
    fireEvent.click(enableButtons[0]);

    // The agent should now show "已关闭" badge
    const closedLabels = screen.getAllByText("已关闭");
    expect(closedLabels.length).toBeGreaterThanOrEqual(1);
  });

  it("shows global status card with active agent count", () => {
    render(<AgentPanel />);

    expect(screen.getByText(/Agent 就绪/)).toBeInTheDocument();
    // 4 active out of 5
    expect(screen.getByText(/4/)).toBeInTheDocument();
  });

  it("shows generating pulse when isGenerating is true", () => {
    useWritingStore.setState({ isGenerating: true });

    render(<AgentPanel />);

    expect(screen.getByText("Agent 协作中...")).toBeInTheDocument();
    expect(screen.getByText("协作进行中")).toBeInTheDocument();
  });

  it("renders help tip at bottom", () => {
    render(<AgentPanel />);

    expect(screen.getByText(/点击卡片展开分析报告/)).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<AgentPanel onClose={onClose} />);

    fireEvent.click(screen.getByLabelText("关闭右栏"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows a rerun button in expanded agent", () => {
    render(<AgentPanel />);

    // Expand first agent
    fireEvent.click(screen.getByText("剧情代理").closest("button")!);

    expect(screen.getByText("重跑")).toBeInTheDocument();
  });
});
