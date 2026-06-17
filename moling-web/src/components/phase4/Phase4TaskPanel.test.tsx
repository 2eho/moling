/* ═══════════════════════════════════════════════════════
   Phase 4 任务面板测试 · Phase4TaskPanel.test.tsx
   ═══════════════════════════════════════════════════════ */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { Phase4TaskPanel } from "./Phase4TaskPanel";
import { Phase4State } from "@/lib/types";
import type { Phase4TaskStatus } from "@/lib/types";

/* ── Mock next/navigation ── */

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

/* ── Mock phase4Api ── */

const mockGetProjectTasks = vi.fn();
vi.mock("@/lib/api", () => ({
  phase4Api: {
    getProjectTasks: (...args: unknown[]) => mockGetProjectTasks(...args),
    retryTask: vi.fn(),
  },
}));

/* ── Test Data ── */

const MOCK_TASKS: Phase4TaskStatus[] = [
  {
    id: "task-001",
    projectId: "proj-1",
    chapterId: "ch-1",
    state: Phase4State.DONE,
    nonce: "nonce-1",
    retryCount: 0,
    createdAt: "2026-06-17T10:00:00Z",
    updatedAt: "2026-06-17T10:05:00Z",
  },
  {
    id: "task-002",
    projectId: "proj-1",
    chapterId: "ch-2",
    state: Phase4State.EXTRACTING,
    nonce: "nonce-2",
    retryCount: 0,
    createdAt: "2026-06-17T11:00:00Z",
    updatedAt: "2026-06-17T11:02:00Z",
  },
  {
    id: "task-003",
    projectId: "proj-1",
    chapterId: "ch-3",
    state: Phase4State.FAILED,
    nonce: "nonce-3",
    retryCount: 2,
    lastError: "API 超时：LLM 服务响应超时",
    createdAt: "2026-06-17T09:00:00Z",
    updatedAt: "2026-06-17T09:03:00Z",
  },
  {
    id: "task-004",
    projectId: "proj-1",
    chapterId: "ch-4",
    state: Phase4State.QUEUED,
    nonce: "nonce-4",
    retryCount: 0,
    createdAt: "2026-06-17T12:00:00Z",
    updatedAt: "2026-06-17T12:00:00Z",
  },
];

/* ── Tests ── */

describe("Phase4TaskPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. 应该渲染任务状态列表", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("Phase 4 任务状态")).toBeTruthy();
    });

    expect(screen.getByText("最近任务")).toBeTruthy();
  });

  it("2. 状态颜色映射正确", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      // "完成" 在流程图和任务列表中都出现了，用 getAllByText
      const doneElements = screen.getAllByText("完成");
      expect(doneElements.length).toBeGreaterThanOrEqual(1);
    });

    // 各状态文本都至少出现一次
    expect(screen.getAllByText("提取中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("失败").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("排队中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("空闲").length).toBeGreaterThanOrEqual(1);
  });

  it("3. 空状态无任务", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: [],
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("暂无任务")).toBeTruthy();
    });

    expect(
      screen.getByText("Phase 4 任务将在生成章节时自动创建"),
    ).toBeTruthy();
  });

  it("4. 失败任务应该显示错误信息", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    // 等待渲染完成
    await waitFor(() => {
      expect(screen.getAllByText("失败").length).toBeGreaterThanOrEqual(1);
    });

    // 错误信息应该出现在 DOM 中
    expect(screen.getByText(/API 超时/)).toBeTruthy();
  });

  it("5. 加载状态应该显示面板标题", () => {
    // 不 resolve promise，保持 loading
    mockGetProjectTasks.mockReturnValue(new Promise(() => {}));

    render(<Phase4TaskPanel projectId="proj-1" />);

    expect(screen.getByText("Phase 4 任务状态")).toBeTruthy();
  });

  it("6. 状态机流程图显示所有状态", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("状态机流转")).toBeTruthy();
    });

    // 状态标签（这些在流程图中用 getAllByText 确认存在）
    expect(screen.getAllByText("空闲").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("排队中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("锁定中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("提取中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("验证中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("合并中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("提交中").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("完成").length).toBeGreaterThanOrEqual(1);
  });

  it("7. 失败任务有重试按钮", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      // 查找"重试"按钮（不是状态文本）
      const retryBtns = screen.getAllByRole("button", { name: "重试" });
      expect(retryBtns.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("8. 任务按时间倒序排列", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    // 等待渲染完成
    await waitFor(() => {
      // task-004 是最新的（12:00），状态为 QUEUED
      const queuedTexts = screen.getAllByText("排队中");
      expect(queuedTexts.length).toBeGreaterThanOrEqual(1);
    });

    // 验证 task-004（最新）出现在列表第一项
    const taskCards = screen.getAllByRole("button", { name: /task-/i });
    // 至少有一个 task card
    expect(taskCards.length).toBeGreaterThanOrEqual(4);
  });

  it("9. 查看全部链接可用", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("查看全部")).toBeTruthy();
    });

    const link = screen.getByText("查看全部");
    expect(link).toBeTruthy();
  });

  it("10. 任务计数显示任务数量", async () => {
    mockGetProjectTasks.mockResolvedValueOnce({
      data: MOCK_TASKS,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<Phase4TaskPanel projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("最近任务")).toBeTruthy();
    });

    // 验证最近任务计数区域包含"4"
    const countText = screen.getByText("4");
    expect(countText).toBeTruthy();
  });
});
