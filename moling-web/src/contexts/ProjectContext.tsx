"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import type { Project } from "@/lib/types";
import { projectApi } from "@/lib/api";

// ---- Types ----

export interface ProjectStats {
  total: number;
  active: number;
  draft: number;
  total_words: number;
}

export interface ProjectContextValue {
  projects: Project[];
  currentProject: Project | null;
  stats: ProjectStats | null;
  isLoading: boolean;
  loadProjects: () => Promise<void>;
  loadProject: (id: string) => Promise<void>;
  loadStats: (projectId?: string) => Promise<void>;
  createProject: (data: Partial<Project>) => Promise<Project>;
  updateProject: (id: string, data: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
}

// ---- Context ----

const ProjectContext = createContext<ProjectContextValue | null>(null);

// ---- Provider ----

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ✅ useRef 保存 currentProject.id，避免 deleteProject 等回调因 currentProject 变化而重建
  const currentProjectIdRef = useRef<string | null>(null);
  useEffect(() => {
    currentProjectIdRef.current = currentProject?.id ?? null;
  }, [currentProject]);

  const loadProjects = useCallback(async () => {
    const res = await projectApi.list();
    setProjects(res.data);
  }, []);

  const loadProject = useCallback(async (id: string) => {
    const res = await projectApi.getById(id);
    setCurrentProject(res.data);
  }, []);

  const loadStats = useCallback(async (projectId?: string) => {
    const id = projectId ?? currentProjectIdRef.current;
    if (!id) return;
    const res = await projectApi.getStats(id);
    setStats(res.data);
  }, []); // ✅ 使用 ref 替代 currentProject state 依赖

  const createProject = useCallback(async (data: Partial<Project>) => {
    const res = await projectApi.create(data);
    setProjects((prev) => [...prev, res.data]);
    return res.data;
  }, []);

  const updateProject = useCallback(async (id: string, data: Partial<Project>) => {
    const res = await projectApi.update(id, data);
    if (res.data) {
      setProjects((prev) => prev.map((p) => (p.id === id ? res.data : p)));
      setCurrentProject((prev) => (prev?.id === id ? res.data : prev));
    }
  }, []);

  const deleteProject = useCallback(async (id: string) => {
    await projectApi.delete(id);
    setProjects((prev) => prev.filter((p) => p.id !== id));
    if (currentProjectIdRef.current === id) {
      setCurrentProject(null);
    }
  }, []); // ✅ 使用 ref 替代 currentProject state 依赖

  // Initial load
  useEffect(() => {
    loadProjects().finally(() =>
      setIsLoading(false),
    );
  }, [loadProjects]);

  const value = useMemo<ProjectContextValue>(() => ({
    projects,
    currentProject,
    stats,
    isLoading,
    loadProjects,
    loadProject,
    loadStats,
    createProject,
    updateProject,
    deleteProject,
  }), [
    projects, currentProject, stats, isLoading,
    loadProjects, loadProject, loadStats,
    createProject, updateProject, deleteProject,
  ]);

  return (
    <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
  );
}

// ---- Hook ----

export function useProjectContext(): ProjectContextValue {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProjectContext must be used within a ProjectProvider");
  }
  return context;
}
