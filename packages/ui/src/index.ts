// @moling/ui — 墨灵共享 UI 层
// Components, hooks, stores, lib — shared between moling-web (Next.js) and moling-desktop (Tauri)

// ── Components ──
export { GlobalErrorBoundary } from "./components/GlobalErrorBoundary";
// Health
export { HealthDashboard } from "./components/health/HealthDashboard";
export { ImportExportButtons } from "./components/ImportExportButtons";
// Phase 4
export { CardManager } from "./components/phase4/CardManager";
export { CharacterLibrary } from "./components/phase4/CharacterLibrary";
export { ForeshadowingLibrary } from "./components/phase4/ForeshadowingLibrary";
export { Phase4TaskPanel } from "./components/phase4/Phase4TaskPanel";
export { TimelineLibrary } from "./components/phase4/TimelineLibrary";
export { WorldviewLibrary } from "./components/phase4/WorldviewLibrary";
export { QueryProvider } from "./components/QueryProvider";
export { ToastContainer } from "./components/ToastContainer";
// Desktop shell
export { UpdateNotification } from "./components/UpdateNotification";
// Vibe Writing
export { ActionBar } from "./components/vibe/ActionBar";
export { AgentPanel } from "./components/vibe/AgentPanel";
export { ContextPanel } from "./components/vibe/ContextPanel";
export { FreeInput } from "./components/vibe/FreeInput";
export { OptionCard } from "./components/vibe/OptionCard";
export { OptionsPanel } from "./components/vibe/OptionsPanel";
export { PhaseNavigator } from "./components/vibe/PhaseNavigator";
export { ProgressBar } from "./components/vibe/ProgressBar";
export { ProjectList } from "./components/vibe/ProjectList";
export { Sidebar } from "./components/vibe/Sidebar";
export { ThemeInitializer } from "./components/vibe/ThemeInitializer";
export { ThemeSwitcher } from "./components/vibe/ThemeSwitcher";

// ── Hooks ──
export { usePanelResize } from "./hooks/usePanelResize";
// ── Lib ──
export { cn } from "./lib/cn";
export { API_ENDPOINTS } from "./lib/constants";
export { env } from "./lib/env";
export { formatDuration, formatRelativeTime, formatWordCount } from "./lib/format";
export {
  getCardPool,
  getProjectHealth,
  getProjectPhase4Tasks,
  getVaultCharacters,
  getVaultForeshadowing,
  getVaultTimeline,
  getVaultWorldview,
  refreshProjectHealth,
} from "./lib/http/api";
export {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  refreshAccessToken,
  setTokens,
} from "./lib/http/auth";
// HTTP
export { ApiError, apiDelete, apiGet, apiPost, apiPut } from "./lib/http/client";
export { setRouterHook, useRouter } from "./lib/navigation";
export { setTauriTitlebarTheme, setWindowBackgroundColor } from "./lib/tauri-theme";
// Types
export type {
  AlertSeverity,
  CardPoolItem,
  HealthAlert,
  Phase4State,
  Phase4Task,
  VaultCharacter,
  VaultForeshadowing,
  VaultTimeline,
  VaultWorldview,
} from "./lib/types/domain";
export { MOCK_OUTPUTS } from "./mock/data/agent-outputs";
// ── Mock ──
export { MOCK_PROJECTS } from "./mock/data/projects";
export { MOCK_OPTIONS } from "./mock/data/workspace";
export type { LLMModelId, LLMSettings } from "./stores/useLLMSettings";
// ── Stores ──
export { LLM_MODELS, useLLMSettings } from "./stores/useLLMSettings";
export type { ThemeId } from "./stores/useTheme";
export { detectSystemTheme, isDarkTheme, THEMES, useTheme } from "./stores/useTheme";
export { type ToastType, useToast } from "./stores/useToast";
export type {
  AgentStatus,
  Chapter,
  Character,
  Foreshadowing,
  Option,
  Phase,
  WritingProject,
} from "./stores/useWritingStore";
export {
  getPhaseProgress,
  getTotalChapters,
  PHASE_LABELS,
  PHASE_ORDER,
  useWritingStore,
} from "./stores/useWritingStore";

// ── Navigation ──
// setRouterHook must be called by the host app before any navigation
