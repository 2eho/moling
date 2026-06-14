// API 模块统一导出
export { api, setToken, clearToken } from './client';
export type {
  ApiResponse,
  PaginationParams,
  PaginatedResponse,
  User,
  LoginRequest,
  LoginResponse,
  Project,
  CreateProjectRequest,
  Chapter,
  CardDirection,
  GenerateRequest,
  GenerateResponse,
  GenerationProgress,
  ConfirmRequest,
  ReviseRequest,
  Character,
  CreateCharacterRequest,
  TimelineEvent,
  Commitment,
  WorldviewEntry,
  Notification,
  ImportRequest,
  ImportProgress,
  UserSettings,
  ChangePasswordRequest,
  UpdateProfileRequest,
} from './types';

// Workspace API
export {
  getChapter,
  getCards,
  generateChapter,
  getGenerationProgress,
  confirmChapter,
  reviseChapter,
  cancelGeneration,
  getHealthAlerts,
  saveDraft,
  getSuggestions,
} from './workspace';

// Vault API
export {
  getCharacters,
  getCharacter,
  createCharacter,
  updateCharacter,
  deleteCharacter,
  getTimelineEvents,
  createTimelineEvent,
  updateTimelineEvent,
  deleteTimelineEvent,
  getCommitments,
  createCommitment,
  updateCommitment,
  deleteCommitment,
  getWorldviewEntries,
  createWorldviewEntry,
  updateWorldviewEntry,
  deleteWorldviewEntry,
} from './vault';

// Settings API
export {
  getSettings,
  updateSettings,
  updateGlobalSettings,
  updateProjectSettings,
  changePassword,
  updateProfile,
  getProjectSettings,
} from './settings';

// Notifications API
export {
  getNotifications,
  getUnreadCount,
  markAsRead,
  markAllAsRead,
  deleteNotification,
  deleteAllRead,
} from './notifications';

// Import API
export {
  uploadAndImport,
  startImport,
  getImportProgress,
  getImportResult,
  cancelImport,
  getImportHistory,
} from './import';
