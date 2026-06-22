// @moling/ui — 墨灵共享 UI 层
// Components, hooks, stores, lib — shared between moling-web (Next.js) and moling-desktop (Tauri)

// ── Components ──
export { GlobalErrorBoundary } from "./components/GlobalErrorBoundary";
export { QueryProvider } from "./components/QueryProvider";
export { ToastContainer } from "./components/ToastContainer";

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

// Phase 4
export { CardManager } from "./components/phase4/CardManager";
export { CharacterLibrary } from "./components/phase4/CharacterLibrary";
export { ForeshadowingLibrary } from "./components/phase4/ForeshadowingLibrary";
export { Phase4TaskPanel } from "./components/phase4/Phase4TaskPanel";
export { TimelineLibrary } from "./components/phase4/TimelineLibrary";
export { WorldviewLibrary } from "./components/phase4/WorldviewLibrary";

// Health
export { HealthDashboard } from "./components/health/HealthDashboard";

// ── Hooks ──
export { usePanelResize } from "./hooks/usePanelResize";

// ── Stores ──
export { useTheme, THEMES, isDarkTheme, detectSystemTheme } from "./stores/useTheme";
export type { ThemeId } from "./stores/useTheme";
export { useToast, type ToastType } from "./stores/useToast";
export { useWritingStore, PHASE_LABELS, PHASE_ORDER, getPhaseProgress, getTotalChapters } from "./stores/useWritingStore";
export type {
  Phase,
  Option,
  AgentStatus,
  Chapter,
  Character,
  Foreshadowing,
  WritingProject,
} from "./stores/useWritingStore";

// ── Lib ──
export { cn } from "./lib/cn";
export { API_ENDPOINTS } from "./lib/constants";
export { env } from "./lib/env";
export { formatRelativeTime, formatDuration, formatWordCount } from "./lib/format";
export { setRouterHook, useRouter } from "./lib/navigation";

// HTTP
export { apiGet, apiPost, apiPut, apiDelete, ApiError } from "./lib/http/client";
export { login, register, getCurrentUser } from "./lib/http/auth";
export {
  getProjectHealth,
  refreshProjectHealth,
  getCardPool,
  getProjectPhase4Tasks,
  getVaultCharacters,
  getVaultWorldview,
  getVaultForeshadowing,
  getVaultTimeline,
} from "./lib/http/api";

// Types
export type {
  HealthAlert,
  AlertSeverity,
  CardPoolItem,
  VaultCharacter,
  VaultWorldview,
  VaultForeshadowing,
  VaultTimeline,
  Phase4Task,
  Phase4State,
} from "./lib/types/domain";

// ── Mock ──
export { MOCK_PROJECTS } from "./mock/data/projects";
export { MOCK_OPTIONS } from "./mock/data/workspace";
export { MOCK_OUTPUTS } from "./mock/data/agent-outputs";

// ── Navigation ──
// setRouterHook must be called by the host app before any navigation
