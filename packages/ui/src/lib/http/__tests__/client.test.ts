import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiDelete, apiGet, apiPost, apiPut } from "../client";

// Mock the env module
vi.mock("@/lib/env", () => ({
  env: {
    apiBaseUrl: "http://test-api.com/api/v1",
  },
}));

describe("HTTP Client", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
    global.fetch = mockFetch as unknown as typeof fetch;
  });

  describe("apiGet", () => {
    it("应该成功获取 JSON 数据", async () => {
      const responseData = { id: 1, name: "test-project" };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(responseData),
      });

      const result = await apiGet("/projects");

      expect(result).toEqual(responseData);
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://test-api.com/api/v1/projects",
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
    });

    it("应该携带 credentials: include（httpOnly cookie 鉴权）", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await apiGet("/projects");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          credentials: "include",
        }),
      );
    });
  });

  describe("apiPost", () => {
    it("应该发送 POST 请求并附带 JSON body", async () => {
      const body = { name: "新项目", genre: "科幻" };
      const responseData = { id: "1", ...body };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve(responseData),
      });

      const result = await apiPost("/projects", body);

      expect(result).toEqual(responseData);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://test-api.com/api/v1/projects",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
    });

    it("不带 body 时应该发送 POST 请求", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await apiPost("/auth/refresh");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          body: undefined,
        }),
      );
    });
  });

  describe("apiPut", () => {
    it("应该发送 PUT 请求并更新数据", async () => {
      const body = { name: "更新后的项目" };
      const responseData = { id: "1", ...body };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(responseData),
      });

      const result = await apiPut("/projects/1", body);

      expect(result).toEqual(responseData);
      expect(mockFetch).toHaveBeenCalledWith(
        "http://test-api.com/api/v1/projects/1",
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify(body),
        }),
      );
    });
  });

  describe("apiDelete", () => {
    it("应该发送 DELETE 请求", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: () => Promise.resolve(),
      });

      const result = await apiDelete("/projects/1");

      expect(result).toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        "http://test-api.com/api/v1/projects/1",
        expect.objectContaining({
          method: "DELETE",
        }),
      );
    });
  });

  describe("204 No Content", () => {
    it("应该返回 undefined", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: () => Promise.resolve(),
      });

      const result = await apiGet("/empty");

      expect(result).toBeUndefined();
    });
  });

  describe("错误处理", () => {
    it("401 未认证时应该抛出 ApiError", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: () => Promise.resolve({ detail: "未认证" }),
      });

      const error = await apiGet("/projects").catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(401);
      expect((error as ApiError).data).toEqual({ detail: "未认证" });
    });

    it("404 时应该抛出 ApiError", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: () => Promise.resolve({ detail: "资源不存在" }),
      });

      const error = await apiGet("/projects/999").catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(404);
    });

    it("500 时应该抛出 ApiError", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        text: () => Promise.resolve("服务器内部错误"),
        json: () => Promise.reject(new Error("not json")),
      });

      const error = await apiGet("/projects").catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(500);
      expect((error as ApiError).data).toBe("服务器内部错误");
    });

    it("网络错误时应该抛出 ApiError（status=0）", async () => {
      mockFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));

      const error = await apiGet("/projects").catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(0);
    });

    it("超时时应该抛出 ApiError（status=408）", async () => {
      // 模拟 fetch 不返回（永不 resolve），由 AbortController 中断
      mockFetch.mockImplementationOnce((_url: string, options?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          const signal = options?.signal;
          if (signal) {
            const onAbort = () => {
              signal.removeEventListener("abort", onAbort);
              reject(new DOMException("The operation was aborted", "AbortError"));
            };
            signal.addEventListener("abort", onAbort);
          }
        });
      });

      const error = await apiGet("/slow-endpoint", { timeout: 100 }).catch((e) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(408);
    });
  });

  describe("自定义 headers", () => {
    it("应该合并自定义 headers", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      });

      await apiGet("/projects", {
        headers: { "X-Custom": "custom-value" },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "X-Custom": "custom-value",
          }),
        }),
      );
    });
  });
});
