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

// ============ 健康监控 ============
export type AlertSeverity = "R1" | "R2" | "R3";

export interface HealthAlert {
  id: string;
  project_id: string;
  severity: AlertSeverity;
  rule: string;
  subplot_name: string;
  current_chapter: number;
  reason: string;
  suggestion: string;
  suppressed: boolean;
  suppressed_reason?: string;
  created_at: string;
}

export interface HealthCheckResp {
  project_id: string;
  status: "healthy" | "warning" | "critical";
  alerts: HealthAlert[];
  last_checked_at: string;
  summary: {
    r1_count: number;
    r2_count: number;
    r3_count: number;
    total: number;
  };
}

// ============ Phase 4 任务 ============
export type Phase4State =
  | "idle"
  | "queued"
  | "locking"
  | "extracting"
  | "verifying"
  | "merging"
  | "committing"
  | "done"
  | "failed"
  | "retry";

export interface Phase4Task {
  id: string;
  project_id: string;
  chapter_id: string;
  state: Phase4State;
  nonce: string;
  retry_count: number;
  retry_at?: string;
  last_error?: string;
  safety_check?: SafetyCheckResult;
  created_at: string;
  updated_at: string;
}

export interface SafetyCheckResult {
  passed: boolean;
  issues: string[];
  summary: string;
}

// ============ Vault 四库 ============
export type VaultType = "characters" | "timeline" | "foreshadowing" | "worldview";

export interface VaultCharacter {
  id: string;
  project_id: string;
  name: string;
  role: "protagonist" | "supporting" | "antagonist" | "minor";
  description: string;
  arc: string;
  chapter_introduced: number;
  traits: string[];
  relationships: string[];
}

export interface VaultTimeline {
  id: string;
  project_id: string;
  chapter: number;
  title: string;
  date_label: string;
  description: string;
  type: "plot" | "character" | "event" | "world";
}

export interface VaultForeshadowing {
  id: string;
  project_id: string;
  description: string;
  status: "active" | "redeemed" | "canceled";
  chapter_planted: number;
  chapter_redeemed?: number;
  target_description?: string;
}

export interface VaultWorldview {
  id: string;
  project_id: string;
  name: string;
  category: "geography" | "history" | "system" | "faction" | "event";
  description: string;
  details: string;
}

export interface VaultSummary {
  characters_count: number;
  timeline_count: number;
  foreshadowing_count: number;
  worldview_count: number;
}

// ============ Card Manager ============
export interface CardPoolItem {
  id: string;
  project_id: string;
  content: string;
  type: "character" | "plot" | "dialogue" | "description";
  retired: boolean;
  retired_reason?: string;
  retired_chapter?: number;
  freshness_period: "new" | "active" | "stale";
  created_at: string;
  updated_at: string;
}
