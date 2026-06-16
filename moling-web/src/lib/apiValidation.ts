/**
 * Zod schemas for API response validation
 * 
 * 确保所有 API 响应都符合预期格式，
 * 在开发模式下提供清晰的错误信息。
 */

import { z } from "zod";

// ── Base API Response Schema ──
// 后端返回格式：{ code: number, message: string, data: T }
export const baseResponseSchema = z.object({
  code: z.number(),
  message: z.string(),
  data: z.unknown(),  // 具体类型由调用方指定
  meta: z.record(z.unknown()).optional(),
});

// ── Paginated Response Schema ──
export const paginatedResponseSchema = <T extends z.ZodTypeAny>(
  itemSchema: T,
) =>
  baseResponseSchema.extend({
    data: z.object({
      items: z.array(itemSchema),
      total: z.number(),
    }),
  });

// ── Array Response Schema ──
export const arrayResponseSchema = <T extends z.ZodTypeAny>(
  itemSchema: T,
) =>
  baseResponseSchema.extend({
    data: z.array(itemSchema),
  });

// ── Object Response Schema ──
export const objectResponseSchema = <T extends z.ZodTypeAny>(
  objectSchema: T,
) =>
  baseResponseSchema.extend({
    data: objectSchema,
  });

// ── Common Data Schemas ──

export const projectSchema = z.object({
  id: z.string(),
  title: z.string(),
  genre: z.string().optional(),
  description: z.string().optional(),
  creation_mode: z.string().optional(),
  word_count: z.number().optional(),
  chapter_count: z.number().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export const chapterSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  title: z.string(),
  content: z.string().optional(),
  word_count: z.number().optional(),
  order: z.number().optional(),
  created_at: z.string().optional(),
});

export const userSettingsSchema = z.object({
  nickname: z.string().optional(),
  email: z.string().optional(),
  bio: z.string().optional(),
  theme: z.enum(["dark", "light", "system"]).optional(),
  auto_save_interval: z.number().optional(),
  editor_font_size: z.number().optional(),
  generation_preference: z.object({
    default_mode: z.string().optional(),
    default_weights: z.record(z.number()).optional(),
    auto_confirm: z.boolean().optional(),
  }).optional(),
  health_rules: z.object({
    r1_enabled: z.boolean().optional(),
    r2_enabled: z.boolean().optional(),
    r3_enabled: z.boolean().optional(),
    anti_fatigue: z.boolean().optional(),
  }).optional(),
  phase4_review_mode: z.enum(["manual", "auto"]).optional(),
});

// ── Validation Functions ──

/**
 * 验证 API 响应是否符合预期 schema
 * @param response - API 响应
 * @param schema - 预期的 Zod schema
 * @returns 验证后的数据
 * 
 * @example
 * const validated = validateResponse(res, objectResponseSchema(projectSchema));
 * // validated.data 现在是类型安全的
 */
export function validateResponse<T>(
  response: unknown,
  schema: z.ZodSchema<T>,
): T {
  try {
    return schema.parse(response);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("[Zod] API response validation failed:", error.errors);
      throw new Error(`API response validation failed: ${error.message}`);
    }
    throw error;
  }
}

/**
 * 安全地验证 API 响应（失败时返回 null）
 * @param response - API 响应
 * @param schema - 预期的 Zod schema
 * @returns 验证后的数据或 null
 */
export function safeValidateResponse<T>(
  response: unknown,
  schema: z.ZodSchema<T>,
): T | null {
  try {
    return schema.parse(response);
  } catch (error) {
    if (process.env.NODE_ENV === "development") {
      console.warn("[Zod] API response validation failed (non-blocking):", error);
    }
    return null;
  }
}

export { z as zod };
