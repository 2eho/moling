/* ============================================
   墨灵 (Moling) — Global TypeScript Type Definitions
   ============================================ */

// ---- User ----

export interface User {
  id: string;
  email: string;
  username: string;
  avatar_url?: string;
  status: UserStatus;
  created_at: string;
  updated_at: string;
}

export type UserStatus = "active" | "inactive" | "banned";

// ---- Project ----

export interface Project {
  id: string;
  title: string;
  author: string;
  genre: string;
  tags?: string[];
  synopsis?: string;
  worldview?: string;
  protagonist?: string;
  supporting_chars?: string;
  word_count: number;
  target_words?: number;
  frequency?: string;
  style?: string;
  status: ProjectStatus;
  creation_mode: CreationMode;
  created_at: string;
  updated_at: string;
}

export type ProjectStatus = "draft" | "active" | "completed" | "archived";
export type CreationMode = "from_scratch" | "from_outline" | "from_worldview";

// ---- Chapter ----

export interface Chapter {
  id: string;
  project_id: string;
  title: string;
  content: string;
  chapter_number: number;
  status: ChapterStatus;
  phase4_status?: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export type ChapterStatus = "draft" | "generating" | "completed" | "revised";

// ---- Card Pool / Card ----

export interface CardPool {
  id: string;
  project_id: string;
  name: string;
  description: string;
  rarity: Rarity;
  direction_type: DirectionType;
  direction_text: string;
  status: CardStatus;
  freshness_chapter?: number;
  draw_count?: number;
  /** 退役原因（仅当 status=retired 时有效） */
  retired_reason?: string;
  /** 退役章节（仅当 status=retired 时有效） */
  retired_at_chapter?: number;
}

export type Rarity = "common" | "rare" | "epic" | "legendary";
export type DirectionType = "plot" | "character" | "worldview" | "style" | "conflict";
export type CardStatus = "available" | "drawn" | "used" | "expired" | "retired";

// ---- Draw Record ----

export interface DrawRecord {
  id: string;
  project_id: string;
  chapter_id: string;
  card_ids: string[];
  weights: number[];
  mode: DrawMode;
  draw_round: number;
  remaining_redraws: number;
}

export type DrawMode = "normal" | "double" | "guaranteed";

// ---- Generation Task ----

export interface GenerationTask {
  id: string;
  project_id: string;
  chapter_id: string;
  task_type: TaskType;
  status: TaskStatus;
  progress_stage: string;
  progress_percent: number;
  error_message?: string;
  output_data?: Record<string, unknown>;
}

export type TaskType =
  | "generate_outline"
  | "generate_chapter"
  | "revise_chapter"
  | "analyze";

export type TaskStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

// ---- Vault Types ----

export interface VaultCharacter {
  id: string;
  project_id: string;
  name: string;
  role: string;
  description: string;
  traits: string[];
  background: string;
  arc: string;
  relationships: VaultCharacterRelationship[];
  location?: string;
  appearance?: string;
  personality?: string;
  knowledge?: string;
  confidence?: number;
}

export interface VaultCharacterRelationship {
  character_id: string;
  relationship: string;
  description: string;
}

export interface VaultTimeline {
  id: string;
  project_id: string;
  day?: number;
  title?: string;
  description: string;
  events: VaultTimelineEvent[];
  precedes?: string;
  confidence?: number;
  source_chapter?: number;
}

export interface VaultTimelineEvent {
  chapter_number: number;
  event: string;
  importance: number;
}

export interface VaultPlotPromise {
  id: string;
  project_id: string;
  description: string;
  status: "pending" | "fulfilled" | "broken";
  introduced_at: number;
  resolved_at?: number;
  type?: string;
  urgency?: string;
  title?: string;
  redeem_window?: number;
  confidence?: number;
}

export interface VaultWorld {
  id: string;
  project_id: string;
  name: string;
  term?: string;
  category: string;
  description: string;
  rules: string[];
  factions: VaultWorldFaction[];
  related_entities?: string[];
  source_chapter?: number;
}

export interface VaultWorldFaction {
  name: string;
  description: string;
  influence: number;
}

export interface VaultSummary {
  project_id: string;
  characters_count: number;
  timelines_count: number;
  plot_promises_count: number;
  worlds_count: number;
  recent_characters: VaultCharacter[];
  active_plot_promises: VaultPlotPromise[];
  recent_events: VaultTimelineEvent[];
}

// ---- Notification ----

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  is_read: boolean;
  related_id?: string;
  related_type?: string;
  created_at: string;
}

export type NotificationType =
  | "generation_complete"
  | "health_alert"
  | "system"
  | "subscription"
  | "chapter_ready"
  | "phase4_failed"
  | "phase4_stuck";

// ---- User Settings ----

export interface UserSettings {
  id: string;
  user_id: string;
  // 用户资料字段
  nickname?: string;
  bio?: string;
  email?: string;
  avatar_url?: string;
  // 界面设置
  theme: "light" | "dark" | "system";
  language: string;
  editor_font_size: number;
  editor_line_height: number;
  auto_save_interval: number;
  // 创作偏好
  generation_preference: GenerationPreference;
  // 通知设置
  notification_settings: NotificationSettings;
  // 健康监控规则
  health_rules?: HealthRules;
  // Phase 4 审核模式
  phase4_review_mode?: "manual" | "auto";
  created_at: string;
  updated_at: string;
}

export interface HealthRules {
  r1_enabled: boolean;
  r2_enabled: boolean;
  r3_enabled: boolean;
  anti_fatigue: boolean;
}

export interface GenerationPreference {
  default_mode: string;
  default_weights: Record<string, number>;
  auto_confirm: boolean;
}

export interface NotificationSettings {
  email_enabled: boolean;
  push_enabled: boolean;
  types: Record<NotificationType, boolean>;
}

// ---- Subscription ----

export interface Subscription {
  id: string;
  user_id: string;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  created_at: string;
}

export type SubscriptionPlan = "free" | "pro" | "team";
export type SubscriptionStatus = "active" | "canceled" | "past_due" | "trialing";

export interface SubscriptionPlanDetails {
  id: SubscriptionPlan;
  name: string;
  price_monthly: number;
  price_yearly: number;
  description: string;
  features: string[];
  limits: {
    projects: number;
    words_per_month: number;
    cards_per_project: number;
  };
}

// ---- Secrets ----

export interface SecretMatrix {
  id: string;
  project_id: string;
  character_id: string;
  character_name: string;
  secrets: SecretItem[];
  relationships: SecretRelationship[];
}

export interface SecretItem {
  id: string;
  content: string;
  related_characters: string[];
  confidence: number;
  source_chapter?: number;
}

export interface SecretRelationship {
  from_character_id: string;
  to_character_id: string;
  secret_count: number;
  tension_level: number;
}

// ---- Weave Pattern ----

export interface WeavePattern {
  id: string;
  name: string;
  description: string;
  type: WeavePatternType;
  structure: WeaveStructure;
  applicable_genres: string[];
}

export type WeavePatternType = "causal_chain" | "parallel" | "main_and_sub";
export interface WeaveStructure {
  threads: WeaveThread[];
  convergence_points: number[];
}

export interface WeaveThread {
  id: string;
  name: string;
  thread_type: string;
  importance: number;
}

// ---- Template ----

export interface Template {
  id: string;
  name: string;
  description: string;
  genre: string;
  structure: TemplateChapter[];
  created_at: string;
  is_official: boolean;
  icon?: string;
  worldSuggestion?: string;
}

export interface TemplateChapter {
  title: string;
  outline: string;
  word_count_target: number;
  chapter_type: string;
}

// ---- Draw History ----

export interface DrawHistory {
  id: string;
  project_id: string;
  chapter_id: string;
  draw_round: number;
  cards_drawn: CardSnapshot[];
  mode: DrawMode;
  created_at: string;
}

export interface CardSnapshot {
  card_id: string;
  card_name: string;
  rarity: Rarity;
  direction_type: DirectionType;
}

// ---- Admin ----

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_projects: number;
  total_words: number;
  api_calls_today: number;
  error_rate: number;
}

export type UserRole = "user" | "admin" | "vip";

export interface AdminUser extends User {
  role: UserRole;
  project_count: number;
  total_words: number;
  last_active_at: string;
}

export interface AdminProject extends Project {
  user_email: string;
  chapter_count: number;
  health_score: number;
}

// ---- Health Alert ----

export interface HealthAlert {
  id: string;
  rule: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "critical";
  is_active: boolean;
}

// ---- System Health ----

export type SystemHealthLevel = "R1" | "R2" | "R3";

export interface SystemHealthStatus {
  level: SystemHealthLevel;
  title: string;
  message: string;
  details?: string[];
  timestamp: string;
  // R1: 不可手动消除，R2: 可点击关闭，R3: 自动消失
  dismissable: boolean;
}

// ---- API Response Envelopes ----

// ---- Phase 4 Task ----

export interface SafetyCheckResult {
  passed: boolean;
  checks: string[];
  warnings: string[];
}

export interface Phase4TaskStatus {
  id: string;
  projectId: string;
  chapterId: string;
  state: Phase4State;
  nonce: string;
  retryCount: number;
  retryAt?: string;
  lastError?: string;
  safetyCheck?: SafetyCheckResult;
  createdAt: string;
  updatedAt: string;
}

export enum Phase4State {
  IDLE = "idle",
  QUEUED = "queued",
  LOCKING = "locking",
  EXTRACTING = "extracting",
  VERIFYING = "verifying",
  MERGING = "merging",
  COMMITTING = "committing",
  DONE = "done",
  FAILED = "failed",
  RETRY = "retry",
}

// ---- API Response Envelopes ----

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  request_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
