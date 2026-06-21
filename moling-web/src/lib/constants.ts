export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    REFRESH: "/auth/refresh",
    RESET_PASSWORD: "/auth/reset-password",
  },
  PROJECTS: {
    LIST: "/projects",
    CREATE: "/projects",
    DETAIL: (id: string) => `/projects/${id}`,
    UPDATE: (id: string) => `/projects/${id}`,
    DELETE: (id: string) => `/projects/${id}`,
    STATS: (id: string) => `/projects/${id}/stats`,
    HEALTH: (id: string) => `/projects/${id}/health`,
    HEALTH_REFRESH: (id: string) => `/projects/${id}/health/refresh`,
  },
  PHASE4: {
    PROJECT_TASKS: (projectId: string) => `/phase4/projects/${projectId}/tasks`,
    TASK_DETAIL: (taskId: string) => `/phase4/tasks/${taskId}`,
    CHAPTER_TASKS: (chapterId: string) => `/phase4/chapters/${chapterId}/tasks`,
  },
  VAULT: {
    CHARACTERS: (projectId: string) => `/projects/${projectId}/vault/characters`,
    TIMELINE: (projectId: string) => `/projects/${projectId}/vault/timeline`,
    FORESHADOWING: (projectId: string) => `/projects/${projectId}/vault/foreshadowing`,
    WORLDVIEW: (projectId: string) => `/projects/${projectId}/vault/worldview`,
    SUMMARY: (projectId: string) => `/projects/${projectId}/vault/summary`,
  },
  CARDS: {
    LIST: (projectId: string) => `/projects/${projectId}/cards`,
    RETIRE: (projectId: string, cardId: string) => `/projects/${projectId}/cards/${cardId}/retire`,
  },
} as const;

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  writing: "创作中",
  completed: "已完成",
};

export const PROJECT_STATUS_COLORS: Record<string, string> = {
  draft: "default",
  writing: "info",
  completed: "success",
} as const;
