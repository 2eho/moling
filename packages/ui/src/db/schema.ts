/** SQLite schema for local-first writing data.
 *
 *  All data lives in the user's local SQLite database.
 *  This file is shared between Web (sql.js) and Tauri (native SQLite) adapters.
 */

// ── DDL (Data Definition) ──────────────────────────────────────────────

export const MIGRATIONS = [
  // V001 — Initial schema
  `CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    genre       TEXT NOT NULL DEFAULT '',
    phase       TEXT NOT NULL DEFAULT 'ideation',
    summary     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT ''
  )`,

  `CREATE TABLE IF NOT EXISTS chapters (
    id          INTEGER NOT NULL,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id, project_id)
  )`,

  `CREATE TABLE IF NOT EXISTS characters (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    arc         TEXT NOT NULL DEFAULT ''
  )`,

  `CREATE TABLE IF NOT EXISTS foreshadowing (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'planted',
    chapter     INTEGER
  )`,

  `CREATE TABLE IF NOT EXISTS world_rules (
    project_id  TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    content     TEXT NOT NULL DEFAULT ''
  )`,

  `CREATE TABLE IF NOT EXISTS style_notes (
    project_id  TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    content     TEXT NOT NULL DEFAULT ''
  )`,

  // V002 — Indexes for common queries
  `CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id, sort_order)`,
  `CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id)`,
  `CREATE INDEX IF NOT EXISTS idx_foreshadowing_project ON foreshadowing(project_id)`,
] as const;

// ── Entity Types (mirrors DB schema) ───────────────────────────────────

export interface ProjectRow {
  id: string;
  title: string;
  genre: string;
  phase: string;
  summary: string;
  status: "draft" | "completed";
  created_at: string;
  updated_at: string;
}

export interface ChapterRow {
  id: number;
  project_id: string;
  title: string;
  summary: string;
  content: string;
  status: "draft" | "completed";
  sort_order: number;
}

export interface CharacterRow {
  id: string;
  project_id: string;
  name: string;
  role: string;
  description: string;
  arc: string;
}

export interface ForeshadowingRow {
  id: string;
  project_id: string;
  description: string;
  status: "planted" | "resolved";
  chapter: number | null;
}

export interface WritingProjectFull {
  project: ProjectRow;
  chapters: ChapterRow[];
  characters: CharacterRow[];
  foreshadowing: ForeshadowingRow[];
  worldRules: string;
  styleNotes: string;
}
