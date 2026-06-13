"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
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
  loadStats: () => Promise<void>;
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

  const loadProjects = useCallback(async () => {
    const res = await projectApi.list();
    setProjects(res.data);
  }, []);

  const loadProject = useCallback(async (id: string) => {
    const res = await projectApi.getById(id);
    setCurrentProject(res.data);
  }, []);

  const loadStats = useCallback(async () => {
    if (!currentProject?.id) return;
    const res = await projectApi.getStats(currentProject.id);
    setStats(res.data);
  }, [currentProject]);

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
    if (currentProject?.id === id) {
      setCurrentProject(null);
    }
  }, [currentProject]);

  // Initial load
  useEffect(() => {
    Promise.all([loadProjects(), loadStats()]).finally(() =>
      setIsLoading(false),
    );
  }, [loadProjects, loadStats]);

  const value: ProjectContextValue = {
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
  };

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
