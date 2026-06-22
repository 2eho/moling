import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { useWritingStore } from "@/stores/useWritingStore";

import { FreeInput } from "../FreeInput";

describe("FreeInput", () => {
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

  it("renders textarea with placeholder", () => {
    render(<FreeInput />);

    const textarea = screen.getByPlaceholderText(/让林风在战斗中领悟/);
    expect(textarea).toBeInTheDocument();
    expect(textarea.tagName).toBe("TEXTAREA");
  });

  it("renders custom D label", () => {
    render(<FreeInput />);

    expect(screen.getByText("自定义 D")).toBeInTheDocument();
  });

  it("updates store on typing", () => {
    render(<FreeInput />);

    const textarea = screen.getByLabelText("自由输入");
    fireEvent.change(textarea, { target: { value: "用户自定义内容" } });

    expect(useWritingStore.getState().customInput).toBe("用户自定义内容");
  });

  it("submits and clears input on Enter key", () => {
    useWritingStore.setState({ customInput: "测试提交" });

    render(<FreeInput />);

    const textarea = screen.getByLabelText("自由输入");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    // After submit: customInput should be cleared
    expect(useWritingStore.getState().customInput).toBe("");
    expect(useWritingStore.getState().isGenerating).toBe(true);
  });

  it("does not submit on Shift+Enter", () => {
    useWritingStore.setState({ customInput: "测试多行" });

    render(<FreeInput />);

    const textarea = screen.getByLabelText("自由输入");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    // Should not submit
    expect(useWritingStore.getState().customInput).toBe("测试多行");
    expect(useWritingStore.getState().isGenerating).toBe(false);
  });

  it("disables submit button when input is empty", () => {
    render(<FreeInput />);

    // The submit button should be disabled when input is empty
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons[0]; // The Send button
    expect(sendButton.disabled).toBe(true);
  });

  it("enables submit button when input has content", () => {
    useWritingStore.setState({ customInput: "some text" });

    render(<FreeInput />);

    const buttons = screen.getAllByRole("button");
    const sendButton = buttons[0];
    expect(sendButton.disabled).toBe(false);
  });

  it("shows help text about Enter and Shift+Enter", () => {
    render(<FreeInput />);

    expect(screen.getByText(/Enter 发送/)).toBeInTheDocument();
    expect(screen.getByText(/Shift\+Enter 换行/)).toBeInTheDocument();
  });

  it("does not submit when isGenerating is true", () => {
    useWritingStore.setState({ customInput: "测试", isGenerating: true });

    render(<FreeInput />);

    const textarea = screen.getByLabelText("自由输入");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    // Should not change state since already generating
    expect(useWritingStore.getState().customInput).toBe("测试");
  });
});
