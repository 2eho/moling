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
