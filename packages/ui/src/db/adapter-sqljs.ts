/**
 * Web adapter: sql.js (WASM) + OPFS persistence (localStorage fallback).
 *
 * On init: restore DB from OPFS → load into sql.js.
 *          If OPFS unavailable, fall back to localStorage.
 *          Old localStorage data auto-migrates to OPFS.
 * On every mutation: serialize DB → write to OPFS (async, binary, no base64).
 * Auto-save debounced at 500ms; force-save on close().
 */

import initSqlJs from "sql.js";
import type { DBAdapter } from "./adapter";
import type {
  ProjectRow,
  ChapterRow,
  CharacterRow,
  ForeshadowingRow,
  WritingProjectFull,
} from "./schema";
import { MIGRATIONS } from "./schema";

const DB_FILENAME = "moling.db";
const SAVE_DEBOUNCE = 500;

// ── OPFS helpers ────────────────────────────────────────────────────────

async function opfsAvailable(): Promise<boolean> {
  try {
    return typeof navigator !== "undefined" && "storage" in navigator && "getDirectory" in navigator.storage;
  } catch {
    return false;
  }
}

let _root: FileSystemDirectoryHandle | null = null;
async function getRoot(): Promise<FileSystemDirectoryHandle> {
  if (!_root) _root = await navigator.storage.getDirectory();
  return _root;
}

async function readOPFS(name: string): Promise<Uint8Array | null> {
  try {
    const root = await getRoot();
    const handle = await root.getFileHandle(name);
    const file = await handle.getFile();
    const buf = await file.arrayBuffer();
    return new Uint8Array(buf);
  } catch {
    return null;
  }
}

async function writeOPFS(name: string, data: Uint8Array): Promise<void> {
  const root = await getRoot();
  const handle = await root.getFileHandle(name, { create: true });
  const writable = await handle.createWritable();
  await writable.write(data);
  await writable.close();
}

// ── Row mappers ─────────────────────────────────────────────────────────

function projectRow(row: Record<string, unknown>): ProjectRow {
  return {
    id: row.id as string,
    title: row.title as string,
    genre: row.genre as string,
    phase: row.phase as string,
    summary: row.summary as string,
    status: row.status as ProjectRow["status"],
    created_at: row.created_at as string,
    updated_at: row.updated_at as string,
  };
}

function chapterRow(row: Record<string, unknown>): ChapterRow {
  return {
    id: row.id as number,
    project_id: row.project_id as string,
    title: row.title as string,
    summary: row.summary as string,
    content: row.content as string,
    status: row.status as ChapterRow["status"],
    sort_order: row.sort_order as number,
  };
}

function characterRow(row: Record<string, unknown>): CharacterRow {
  return {
    id: row.id as string,
    project_id: row.project_id as string,
    name: row.name as string,
    role: row.role as string,
    description: row.description as string,
    arc: row.arc as string,
  };
}

function foreshadowingRow(row: Record<string, unknown>): ForeshadowingRow {
  return {
    id: row.id as string,
    project_id: row.project_id as string,
    description: row.description as string,
    status: row.status as ForeshadowingRow["status"],
    chapter: row.chapter as number | null,
  };
}

// ── Adapter ─────────────────────────────────────────────────────────────

export function createSqlJsAdapter(): DBAdapter {
  let SQL: any = null;
  let db: any = null;
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let usingOPFS = false;

  const schedulePersist = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => persist(), SAVE_DEBOUNCE);
  };

  const persist = () => {
    if (!db) return;
    const data = db.export() as Uint8Array;
    if (usingOPFS) {
      // OPFS: binary, no base64, no size ceiling
      writeOPFS(DB_FILENAME, data).catch((e) =>
        console.error("[moling-db] OPFS write failed:", e),
      );
    } else {
      // localStorage fallback
      try {
        const base64 = Buffer.from(data).toString("base64");
        localStorage.setItem("moling.db", base64);
      } catch (e) {
        console.error("[moling-db] localStorage write failed:", e);
      }
    }
  };

  const flushPersist = async () => {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    if (!db) return;
    const data = db.export() as Uint8Array;
    if (usingOPFS) {
      await writeOPFS(DB_FILENAME, data);
    } else {
      localStorage.setItem("moling.db", Buffer.from(data).toString("base64"));
    }
  };

  const runMigrations = () => {
    if (!db) return;
    for (const sql of MIGRATIONS) {
      try { db.run(sql); } catch (e) {
        console.warn("[moling-db] Migration:", (e as Error).message);
      }
    }
  };

  const adapter: DBAdapter = {
    async init() {
      SQL = await initSqlJs({
        locateFile: (file: string) => `https://sql.js.org/dist/${file}`,
      });

      // 1) Try OPFS
      if (await opfsAvailable()) {
        const data = await readOPFS(DB_FILENAME);
        if (data) {
          db = new SQL.Database(Array.from(data));
          usingOPFS = true;
        } else {
          // 2) OPFS empty → check for legacy localStorage data
          const legacy = localStorage.getItem("moling.db");
          if (legacy) {
            try {
              db = new SQL.Database(new Uint8Array(Buffer.from(legacy, "base64")));
              // Migrate to OPFS
              await writeOPFS(DB_FILENAME, db.export() as Uint8Array);
              localStorage.removeItem("moling.db");
              usingOPFS = true;
            } catch {
              db = new SQL.Database();
              usingOPFS = true;
            }
          } else {
            db = new SQL.Database();
            usingOPFS = true;
          }
        }
      } else {
        // 3) OPFS not available → localStorage fallback
        const saved = localStorage.getItem("moling.db");
        if (saved) {
          try {
            db = new SQL.Database(new Uint8Array(Buffer.from(saved, "base64")));
          } catch {
            db = new SQL.Database();
          }
        } else {
          db = new SQL.Database();
        }
      }

      runMigrations();
    },

    async close() {
      await flushPersist();
      if (db) {
        db.close();
        db = null;
        SQL = null;
      }
    },

    // ── Projects ───────────────────────────────────────────────────────

    async listProjects() {
      if (!db) throw new Error("DB not initialized");
      const stmt = db.prepare("SELECT * FROM projects ORDER BY updated_at DESC");
      const rows: ProjectRow[] = [];
      while (stmt.step()) rows.push(projectRow(stmt.getAsObject()));
      stmt.free();
      return rows;
    },

    async getProject(id: string) {
      if (!db) throw new Error("DB not initialized");
      const proj = db.exec("SELECT * FROM projects WHERE id = ?", [id]);
      if (!proj.length || !proj[0].values.length) return null;

      const chapters = db.exec("SELECT * FROM chapters WHERE project_id = ? ORDER BY sort_order", [id]);
      const chars = db.exec("SELECT * FROM characters WHERE project_id = ?", [id]);
      const foreshadowing = db.exec("SELECT * FROM foreshadowing WHERE project_id = ?", [id]);
      const world = db.exec("SELECT content FROM world_rules WHERE project_id = ?", [id]);
      const style = db.exec("SELECT content FROM style_notes WHERE project_id = ?", [id]);

      function rows<T>(result: any, mapper: (r: Record<string, unknown>) => T): T[] {
        if (!result.length) return [];
        const cols = result[0].columns as string[];
        return result[0].values.map((vals: unknown[]) => {
          const obj: Record<string, unknown> = {};
          cols.forEach((c: string, i: number) => { obj[c] = vals[i]; });
          return mapper(obj);
        });
      }

      return {
        project: projectRow(rowObj(proj[0].columns, proj[0].values[0] as unknown[])),
        chapters: rows(chapters, chapterRow),
        characters: rows(chars, characterRow),
        foreshadowing: rows(foreshadowing, foreshadowingRow),
        worldRules: world.length ? (world[0].values[0]?.[0] as string) ?? "" : "",
        styleNotes: style.length ? (style[0].values[0]?.[0] as string) ?? "" : "",
      };
    },

    async createProject(p: ProjectRow) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT INTO projects (id,title,genre,phase,summary,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)", [p.id, p.title, p.genre, p.phase, p.summary, p.status, p.created_at, p.updated_at]);
      schedulePersist();
    },

    async updateProject(id, fields) {
      if (!db) throw new Error("DB not initialized");
      const sets: string[] = [];
      const vals: unknown[] = [];
      for (const [k, v] of Object.entries(fields)) {
        if (v !== undefined) { sets.push(`${k} = ?`); vals.push(v); }
      }
      if (sets.length === 0) return;
      sets.push("updated_at = ?");
      vals.push(new Date().toISOString().split("T")[0]);
      vals.push(id);
      db.run(`UPDATE projects SET ${sets.join(", ")} WHERE id = ?`, vals);
      schedulePersist();
    },

    async deleteProject(id) {
      if (!db) throw new Error("DB not initialized");
      db.run("DELETE FROM projects WHERE id = ?", [id]);
      schedulePersist();
    },

    // ── Chapters ───────────────────────────────────────────────────────

    async listChapters(projectId) {
      if (!db) throw new Error("DB not initialized");
      const stmt = db.prepare("SELECT * FROM chapters WHERE project_id = ? ORDER BY sort_order", [projectId]);
      const rows: ChapterRow[] = [];
      while (stmt.step()) rows.push(chapterRow(stmt.getAsObject()));
      stmt.free();
      return rows;
    },

    async getChapter(projectId, chapterId) {
      if (!db) throw new Error("DB not initialized");
      const r = db.exec("SELECT * FROM chapters WHERE project_id = ? AND id = ?", [projectId, chapterId]);
      if (!r.length || !r[0].values.length) return null;
      return chapterRow(rowObj(r[0].columns, r[0].values[0] as unknown[]));
    },

    async createChapter(ch) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT INTO chapters (id,project_id,title,summary,content,status,sort_order) VALUES (?,?,?,?,?,?,?)", [ch.id, ch.project_id, ch.title, ch.summary, ch.content, ch.status, ch.sort_order]);
      schedulePersist();
    },

    async updateChapter(projectId, chapterId, fields) {
      if (!db) throw new Error("DB not initialized");
      const sets: string[] = [];
      const vals: unknown[] = [];
      for (const [k, v] of Object.entries(fields)) {
        if (v !== undefined) { sets.push(`${k} = ?`); vals.push(v); }
      }
      if (sets.length === 0) return;
      vals.push(projectId, chapterId);
      db.run(`UPDATE chapters SET ${sets.join(", ")} WHERE project_id = ? AND id = ?`, vals);
      schedulePersist();
    },

    async deleteChapter(projectId, chapterId) {
      if (!db) throw new Error("DB not initialized");
      db.run("DELETE FROM chapters WHERE project_id = ? AND id = ?", [projectId, chapterId]);
      schedulePersist();
    },

    // ── Characters ─────────────────────────────────────────────────────

    async listCharacters(projectId) {
      if (!db) throw new Error("DB not initialized");
      const stmt = db.prepare("SELECT * FROM characters WHERE project_id = ?", [projectId]);
      const rows: CharacterRow[] = [];
      while (stmt.step()) rows.push(characterRow(stmt.getAsObject()));
      stmt.free();
      return rows;
    },
    async createCharacter(ch) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT INTO characters (id,project_id,name,role,description,arc) VALUES (?,?,?,?,?,?)", [ch.id, ch.project_id, ch.name, ch.role, ch.description, ch.arc]);
      schedulePersist();
    },
    async updateCharacter(id, fields) {
      if (!db) throw new Error("DB not initialized");
      const sets: string[] = [];
      const vals: unknown[] = [];
      for (const [k, v] of Object.entries(fields)) {
        if (v !== undefined) { sets.push(`${k} = ?`); vals.push(v); }
      }
      if (sets.length === 0) return;
      vals.push(id);
      db.run(`UPDATE characters SET ${sets.join(", ")} WHERE id = ?`, vals);
      schedulePersist();
    },
    async deleteCharacter(id) {
      if (!db) throw new Error("DB not initialized");
      db.run("DELETE FROM characters WHERE id = ?", [id]);
      schedulePersist();
    },

    // ── Foreshadowing ──────────────────────────────────────────────────

    async listForeshadowing(projectId) {
      if (!db) throw new Error("DB not initialized");
      const stmt = db.prepare("SELECT * FROM foreshadowing WHERE project_id = ?", [projectId]);
      const rows: ForeshadowingRow[] = [];
      while (stmt.step()) rows.push(foreshadowingRow(stmt.getAsObject()));
      stmt.free();
      return rows;
    },
    async createForeshadowing(item) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT INTO foreshadowing (id,project_id,description,status,chapter) VALUES (?,?,?,?,?)", [item.id, item.project_id, item.description, item.status, item.chapter]);
      schedulePersist();
    },
    async updateForeshadowing(id, fields) {
      if (!db) throw new Error("DB not initialized");
      const sets: string[] = [];
      const vals: unknown[] = [];
      for (const [k, v] of Object.entries(fields)) {
        if (v !== undefined) { sets.push(`${k} = ?`); vals.push(v); }
      }
      if (sets.length === 0) return;
      vals.push(id);
      db.run(`UPDATE foreshadowing SET ${sets.join(", ")} WHERE id = ?`, vals);
      schedulePersist();
    },
    async deleteForeshadowing(id) {
      if (!db) throw new Error("DB not initialized");
      db.run("DELETE FROM foreshadowing WHERE id = ?", [id]);
      schedulePersist();
    },

    // ── World Rules / Style ────────────────────────────────────────────

    async getWorldRules(projectId) {
      if (!db) throw new Error("DB not initialized");
      const r = db.exec("SELECT content FROM world_rules WHERE project_id = ?", [projectId]);
      return r.length ? (r[0].values[0]?.[0] as string) ?? "" : "";
    },
    async setWorldRules(projectId, content) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT OR REPLACE INTO world_rules (project_id, content) VALUES (?,?)", [projectId, content]);
      schedulePersist();
    },
    async getStyleNotes(projectId) {
      if (!db) throw new Error("DB not initialized");
      const r = db.exec("SELECT content FROM style_notes WHERE project_id = ?", [projectId]);
      return r.length ? (r[0].values[0]?.[0] as string) ?? "" : "";
    },
    async setStyleNotes(projectId, content) {
      if (!db) throw new Error("DB not initialized");
      db.run("INSERT OR REPLACE INTO style_notes (project_id, content) VALUES (?,?)", [projectId, content]);
      schedulePersist();
    },
  };

  return adapter;
}

function rowObj(cols: string[], vals: unknown[]): Record<string, unknown> {
  const obj: Record<string, unknown> = {};
  cols.forEach((c, i) => { obj[c] = vals[i]; });
  return obj;
}
