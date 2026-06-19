// ============ 项目 ============
export type ProjectStatus = "draft" | "writing" | "completed";

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: ProjectStatus;
  word_count: number;
  chapter_count: number;
  cover_url?: string;
  created_at: string;
  updated_at: string;
}

export type CreationMode = "blank" | "ai-assisted" | "import";

export interface CreateProjectPayload {
  name: string;
  description?: string;
  mode: CreationMode;
  template?: string;
}

// ============ 通用 ============
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
