/**
 * Database Adapter — abstract interface for local SQLite.
 *
 * Implementations:
 *   - adapter-sqljs.ts  → Web (sql.js WASM + localStorage persistence)
 *   - adapter-tauri.ts  → Tauri desktop (native SQLite via tauri-plugin-sql)
 */

import type {
  ProjectRow,
  ChapterRow,
  CharacterRow,
  ForeshadowingRow,
  WritingProjectFull,
} from "./schema";

export interface DBAdapter {
  /** Open/initialize the database. Must be called once before any query. */
  init(): Promise<void>;

  /** Close and persist. */
  close(): Promise<void>;

  // ── Projects ───────────────────────────────────────────────────────

  listProjects(): Promise<ProjectRow[]>;
  getProject(id: string): Promise<WritingProjectFull | null>;
  createProject(project: ProjectRow): Promise<void>;
  updateProject(id: string, fields: Partial<Pick<ProjectRow, "title" | "genre" | "phase" | "status" | "summary">>): Promise<void>;
  deleteProject(id: string): Promise<void>;

  // ── Chapters ───────────────────────────────────────────────────────

  listChapters(projectId: string): Promise<ChapterRow[]>;
  getChapter(projectId: string, chapterId: number): Promise<ChapterRow | null>;
  createChapter(chapter: ChapterRow): Promise<void>;
  updateChapter(projectId: string, chapterId: number, fields: Partial<Pick<ChapterRow, "title" | "content" | "status" | "summary">>): Promise<void>;
  deleteChapter(projectId: string, chapterId: number): Promise<void>;

  // ── Characters ─────────────────────────────────────────────────────

  listCharacters(projectId: string): Promise<CharacterRow[]>;
  createCharacter(char: CharacterRow): Promise<void>;
  updateCharacter(id: string, fields: Partial<Pick<CharacterRow, "name" | "role" | "description" | "arc">>): Promise<void>;
  deleteCharacter(id: string): Promise<void>;

  // ── Foreshadowing ──────────────────────────────────────────────────

  listForeshadowing(projectId: string): Promise<ForeshadowingRow[]>;
  createForeshadowing(item: ForeshadowingRow): Promise<void>;
  updateForeshadowing(id: string, fields: Partial<Pick<ForeshadowingRow, "description" | "status" | "chapter">>): Promise<void>;
  deleteForeshadowing(id: string): Promise<void>;

  // ── World Rules / Style Notes ──────────────────────────────────────

  getWorldRules(projectId: string): Promise<string>;
  setWorldRules(projectId: string, content: string): Promise<void>;
  getStyleNotes(projectId: string): Promise<string>;
  setStyleNotes(projectId: string, content: string): Promise<void>;
}
