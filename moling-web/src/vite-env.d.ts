/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SKIP_AUTH: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_TAURI_BUILD: string;
  readonly VITE_MOCK_ENABLED: string;
  readonly VITE_SENTRY_DSN: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
