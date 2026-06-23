/**
 * Database sync — bridges zustand writing store ↔ SQLite.
 *
 * On mount: restore projects from SQLite → populate zustand store
 * On store change: write projects/chapters to SQLite
 */

import { getDB } from "./context";
import type { WritingProject, Chapter, Character } from "../stores/useWritingStore";
import type { ProjectRow, ChapterRow } from "./schema";

type WritingStore = {
  projects: WritingProject[];
  loadProjects: (projects: WritingProject[]) => void;
  loadProject: (project: WritingProject) => void;
};

function toProjectRow(p: WritingProject): ProjectRow {
  return {
    id: p.id,
    title: p.title,
    genre: p.genre,
    phase: p.phase,
    summary: p.summary,
    status: p.status ?? "draft",
    created_at: p.createdAt ?? new Date().toISOString().split("T")[0],
    updated_at: p.updatedAt ?? new Date().toISOString().split("T")[0],
  };
}

function toChapterRow(ch: Chapter, projectId: string, idx: number): ChapterRow {
  return {
    id: ch.id,
    project_id: projectId,
    title: ch.title,
    summary: ch.summary ?? "",
    content: ch.content ?? "",
    status: ch.status ?? "draft",
    sort_order: idx,
  };
}

/** Restore all projects from SQLite into the zustand store. */
export async function restoreFromDB(store: WritingStore): Promise<void> {
  try {
    const db = await getDB();
    const projects = await db.listProjects();
    if (projects.length === 0) return; // fresh DB

    const fullProjects: WritingProject[] = [];

    for (const p of projects) {
      const chapters = await db.listChapters(p.id);
      const characters = await db.listCharacters(p.id);
      const foreshadowing = await db.listForeshadowing(p.id);
      const worldRules = await db.getWorldRules(p.id);
      const styleNotes = await db.getStyleNotes(p.id);

      fullProjects.push({
        id: p.id,
        title: p.title,
        genre: p.genre,
        phase: p.phase as WritingProject["phase"],
        currentChapter: chapters.length,
        totalChapters: chapters.length,
        summary: p.summary,
        status: p.status,
        createdAt: p.created_at,
        updatedAt: p.updated_at,
        chapters: chapters.map((ch) => ({
          id: ch.id,
          title: ch.title,
          summary: ch.summary,
          content: ch.content,
          status: ch.status,
        })),
        characters: characters.map((c) => ({
          id: c.id,
          name: c.name,
          role: c.role as Character["role"],
          description: c.description,
          arc: c.arc,
        })),
        foreshadowing: foreshadowing.map((f) => ({
          id: f.id,
          description: f.description,
          status: f.status,
          chapter: f.chapter ?? undefined,
        })),
        worldRules,
        styleNotes,
      });
    }

    store.loadProjects(fullProjects);
  } catch (e) {
    console.error("[moling-db] Failed to restore from DB:", e);
  }
}

/** Persist a single project to SQLite. */
export async function persistProject(project: WritingProject): Promise<void> {
  try {
    const db = await getDB();
    await db.createProject(toProjectRow(project));

    // Chapters
    for (const [idx, ch] of (project.chapters ?? []).entries()) {
      await db.createChapter(toChapterRow(ch, project.id, idx));
    }

    // Characters
    for (const c of project.characters ?? []) {
      await db.createCharacter({
        id: c.id,
        project_id: project.id,
        name: c.name,
        role: c.role ?? "",
        description: c.description ?? "",
        arc: c.arc ?? "",
      });
    }

    // Foreshadowing
    for (const f of project.foreshadowing ?? []) {
      await db.createForeshadowing({
        id: f.id,
        project_id: project.id,
        description: f.description,
        status: f.status,
        chapter: f.chapter ?? null,
      });
    }

    if (project.worldRules) {
      await db.setWorldRules(project.id, project.worldRules);
    }
    if (project.styleNotes) {
      await db.setStyleNotes(project.id, project.styleNotes);
    }
  } catch (e) {
    console.error("[moling-db] Failed to persist project:", e);
  }
}

/** Delete a project from SQLite. */
export async function deleteProjectFromDB(projectId: string): Promise<void> {
  try {
    const db = await getDB();
    await db.deleteProject(projectId);
  } catch (e) {
    console.error("[moling-db] Failed to delete project:", e);
  }
}

/** Update chapter content in SQLite. */
export async function persistChapter(
  projectId: string,
  chapter: Chapter,
  sortOrder: number,
): Promise<void> {
  try {
    const db = await getDB();
    const existing = await db.getChapter(projectId, chapter.id);
    if (existing) {
      await db.updateChapter(projectId, chapter.id, {
        title: chapter.title,
        content: chapter.content,
        status: chapter.status,
        summary: chapter.summary,
      });
    } else {
      await db.createChapter(toChapterRow(chapter, projectId, sortOrder));
    }
  } catch (e) {
    console.error("[moling-db] Failed to persist chapter:", e);
  }
}
