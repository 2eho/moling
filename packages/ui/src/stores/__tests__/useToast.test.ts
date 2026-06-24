import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type Toast, useToast } from "../useToast";

describe("useToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useToast.setState({ toasts: [] });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("has empty toasts array", () => {
      expect(useToast.getState().toasts).toEqual([]);
    });
  });

  describe("addToast", () => {
    it("adds a toast with generated ID", () => {
      useToast.getState().addToast({
        type: "success",
        message: "操作成功",
      });

      const toasts = useToast.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe("success");
      expect(toasts[0].message).toBe("操作成功");
      expect(toasts[0].id).toBeTruthy();
    });

    it("generates unique IDs for each toast", () => {
      useToast.getState().addToast({ type: "info", message: "第一条" });
      useToast.getState().addToast({ type: "info", message: "第二条" });

      const toasts = useToast.getState().toasts;
      expect(toasts).toHaveLength(2);
      expect(toasts[0].id).not.toBe(toasts[1].id);
    });

    it("supports all toast types", () => {
      useToast.getState().addToast({ type: "success", message: "成功" });
      useToast.getState().addToast({ type: "error", message: "错误" });
      useToast.getState().addToast({ type: "info", message: "信息" });
      useToast.getState().addToast({ type: "warning", message: "警告" });

      const toasts = useToast.getState().toasts;
      expect(toasts).toHaveLength(4);
      expect(toasts.map((t) => t.type)).toEqual(["success", "error", "info", "warning"]);
    });

    it("auto-removes toast after default duration (3000ms)", () => {
      useToast.getState().addToast({
        type: "info",
        message: "自动消失",
      });

      expect(useToast.getState().toasts).toHaveLength(1);

      vi.advanceTimersByTime(3000);

      expect(useToast.getState().toasts).toHaveLength(0);
    });

    it("auto-removes toast after custom duration", () => {
      useToast.getState().addToast({
        type: "success",
        message: "自定义时长",
        duration: 5000,
      });

      expect(useToast.getState().toasts).toHaveLength(1);

      vi.advanceTimersByTime(2999);
      expect(useToast.getState().toasts).toHaveLength(1);

      vi.advanceTimersByTime(1);
      expect(useToast.getState().toasts).toHaveLength(1);

      // Actually need to advance to 5000
      vi.advanceTimersByTime(2000);
      expect(useToast.getState().toasts).toHaveLength(0);
    });

    it("does not auto-remove when duration is 0", () => {
      useToast.getState().addToast({
        type: "warning",
        message: "持久通知",
        duration: 0,
      });

      vi.advanceTimersByTime(10000);

      expect(useToast.getState().toasts).toHaveLength(1);
    });
  });

  describe("removeToast", () => {
    it("removes a specific toast by ID", () => {
      useToast.getState().addToast({ type: "info", message: "第一条" });
      useToast.getState().addToast({ type: "info", message: "第二条" });

      const toasts = useToast.getState().toasts;
      const firstId = toasts[0].id;

      useToast.getState().removeToast(firstId);

      const remaining = useToast.getState().toasts;
      expect(remaining).toHaveLength(1);
      expect(remaining[0].id).not.toBe(firstId);
    });

    it("does nothing when removing non-existent ID", () => {
      useToast.getState().addToast({ type: "info", message: "测试" });

      useToast.getState().removeToast("non-existent-id");

      expect(useToast.getState().toasts).toHaveLength(1);
    });
  });

  describe("multiple toasts", () => {
    it("can have multiple toasts simultaneously", () => {
      useToast.getState().addToast({ type: "success", message: "Toast 1" });
      useToast.getState().addToast({ type: "error", message: "Toast 2" });
      useToast.getState().addToast({ type: "info", message: "Toast 3" });

      expect(useToast.getState().toasts).toHaveLength(3);
    });
  });
});
