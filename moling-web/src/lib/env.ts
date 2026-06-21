export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "/api/v1",
  skipAuth: process.env.NEXT_PUBLIC_SKIP_AUTH === "true",
  mockEnabled: process.env.NEXT_PUBLIC_MOCK_ENABLED === "true",
  isDev: process.env.NODE_ENV === "development",
  isProd: process.env.NODE_ENV === "production",
  sentryDsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",
} as const;
