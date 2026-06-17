/* ═══════════════════════════════════════════════════════
   健康监控仪表盘测试 · HealthDashboard.test.tsx
   ═══════════════════════════════════════════════════════ */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { HealthDashboard } from "./HealthDashboard";
import type { HealthAlert } from "@/lib/types";

/* ── Mock next/navigation ── */

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ projectId: "proj-1" }),
}));

/* ── Mock healthApi ── */

const mockGetAlerts = vi.fn();
const mockRefreshCheck = vi.fn();
vi.mock("@/lib/api", () => ({
  healthApi: {
    getAlerts: (...args: unknown[]) => mockGetAlerts(...args),
    refreshCheck: (...args: unknown[]) => mockRefreshCheck(...args),
  },
}));

/* ── Helper ── */

function makeAlert(overrides: Partial<HealthAlert> & { id?: string }): HealthAlert {
  return {
    id: overrides.id ?? `alert-${Math.random().toString(36).slice(2, 8)}`,
    rule: overrides.rule ?? "character_relationship",
    title: overrides.title ?? "测试告警",
    detail: overrides.detail ?? "这是一个测试告警详情",
    severity: overrides.severity ?? "warning",
    is_active: overrides.is_active ?? true,
  };
}

/* ── Tests ── */

describe("HealthDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. 渲染告警列表
  it("1. 健康仪表盘渲染告警列表", async () => {
    const alerts = [
      makeAlert({ id: "a1", title: "人物关系断裂", severity: "critical" }),
      makeAlert({ id: "a2", title: "情节节奏过快", severity: "warning" }),
      makeAlert({ id: "a3", title: "角色动机不明确", severity: "info" }),
    ];
    mockGetAlerts.mockResolvedValueOnce({
      data: alerts,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("健康监控仪表盘")).toBeTruthy();
    });

    // 标题显示
    expect(screen.getByText("告警详情")).toBeTruthy();
    // 三条告警
    expect(screen.getByText("人物关系断裂")).toBeTruthy();
    expect(screen.getByText("情节节奏过快")).toBeTruthy();
    expect(screen.getByText("角色动机不明确")).toBeTruthy();
    // 验证告警计数（列表标题中显示 "(3)"）
    expect(screen.getByText((content) => content.includes("(3)"))).toBeTruthy();
  });

  // 2. R1/R2/R3 标签显示
  it("2. R1/R2/R3 颜色正确", async () => {
    const alerts = [
      makeAlert({ id: "a1", title: "严重告警", severity: "critical" }),
      makeAlert({ id: "a2", title: "警告告警", severity: "warning" }),
      makeAlert({ id: "a3", title: "信息告警", severity: "info" }),
    ];
    mockGetAlerts.mockResolvedValueOnce({
      data: alerts,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    const { container } = render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getAllByText("R1").length).toBeGreaterThan(0);
    });

    // 严重/警告/信息 名称
    expect(screen.getByText("严重")).toBeTruthy();
    expect(screen.getByText("警告")).toBeTruthy();
    expect(screen.getByText("信息")).toBeTruthy();

    // 每个告警项上有对应的 severity badge
    const severityBadges = container.querySelectorAll('[class*="severityBadge"]');
    expect(severityBadges.length).toBe(3);
  });

  // 3. 空状态显示
  it("3. 空状态显示", async () => {
    mockGetAlerts.mockResolvedValueOnce({
      data: [],
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("所有子情节健康")).toBeTruthy();
    });

    expect(
      screen.getByText("未检测到任何健康告警，所有子情节运行正常"),
    ).toBeTruthy();
  });

  // 4. 刷新按钮触发 API 调用
  it("4. 刷新按钮触发 API 调用", async () => {
    mockGetAlerts.mockResolvedValueOnce({
      data: [makeAlert({ id: "a1", title: "测试告警" })],
      code: 0,
      message: "ok",
      request_id: "req-1",
    });
    mockRefreshCheck.mockResolvedValueOnce({
      data: [],
      code: 0,
      message: "ok",
      request_id: "req-2",
    });
    mockGetAlerts.mockResolvedValueOnce({
      data: [],
      code: 0,
      message: "ok",
      request_id: "req-3",
    });

    render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("测试告警")).toBeTruthy();
    });

    const refreshBtn = screen.getByText("刷新检查");
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(mockRefreshCheck).toHaveBeenCalledWith("proj-1");
    });
  });

  // 5. 防疲劳告警显示灰色标记
  it("5. 防疲劳告警显示灰色标记", async () => {
    const suppressedAlert = {
      ...makeAlert({ id: "a1", title: "重复告警 - 人物关系", severity: "warning" }),
      is_suppressed: true,
      suppress_reason: "3章内重复",
      subplot_name: "主要人物线",
      chapter_number: 3,
    };
    mockGetAlerts.mockResolvedValueOnce({
      data: [suppressedAlert as HealthAlert],
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    const { container } = render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("重复告警 - 人物关系")).toBeTruthy();
    });

    // 应该有"3章内重复"标签
    const suppressTag = screen.getByText("3章内重复");
    expect(suppressTag).toBeTruthy();

    // 告警项应有 suppressed 样式类
    const alertItem = container.querySelector('[class*="alertSuppressed"]');
    expect(alertItem).toBeTruthy();
  });

  // 6. 加载状态骨架屏
  it("6. 加载状态骨架屏", async () => {
    // 保持 pending，不 resolve
    mockGetAlerts.mockReturnValue(new Promise(() => {}));

    const { container } = render(<HealthDashboard projectId="proj-1" />);

    // 加载时有 aria-busy="true"
    const busyContainer = container.querySelector('[aria-busy="true"]');
    expect(busyContainer).toBeTruthy();

    // 应该有骨架屏元素
    const skeletonElements = container.querySelectorAll('[class*="skeleton"]');
    expect(skeletonElements.length).toBeGreaterThan(0);
  });

  // 7. 错误状态+重试
  it("7. 错误状态+重试", async () => {
    mockGetAlerts.mockRejectedValueOnce(new Error("网络错误：无法连接到服务器"));

    render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByText("获取健康告警失败")).toBeTruthy();
    });

    // 错误详情
    expect(screen.getByText("网络错误：无法连接到服务器")).toBeTruthy();

    // 重试按钮存在
    const retryBtn = screen.getByText("重试");
    expect(retryBtn).toBeTruthy();
  });

  // 8. 告警计数正确
  it("8. 告警计数正确", async () => {
    const alerts = [
      makeAlert({ id: "a1", severity: "critical" }),
      makeAlert({ id: "a2", severity: "critical" }),
      makeAlert({ id: "a3", severity: "warning" }),
      makeAlert({ id: "a4", severity: "warning" }),
      makeAlert({ id: "a5", severity: "warning" }),
      makeAlert({ id: "a6", severity: "info" }),
    ];
    mockGetAlerts.mockResolvedValueOnce({
      data: alerts,
      code: 0,
      message: "ok",
      request_id: "req-1",
    });

    const { container } = render(<HealthDashboard projectId="proj-1" />);

    await waitFor(() => {
      expect(
        container.querySelectorAll('[class*="countNumber"]').length,
      ).toBe(3);
    });

    // R1 计数应为 2
    const countNumberElements = container.querySelectorAll('[class*="countNumber"]');
    expect(countNumberElements.length).toBe(3);
    expect(countNumberElements[0].textContent?.trim()).toBe("2"); // R1 = 2 critical
    expect(countNumberElements[1].textContent?.trim()).toBe("3"); // R2 = 3 warning
    expect(countNumberElements[2].textContent?.trim()).toBe("1"); // R3 = 1 info
  });
});
