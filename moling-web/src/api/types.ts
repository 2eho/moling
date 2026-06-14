// API 类型定义

// 通用响应类型
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页请求
export interface PaginationParams {
  page?: number;
  pageSize?: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// 用户相关
export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  createdAt: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

// 项目相关
export interface Project {
  id: string;
  name: string;
  description?: string;
  genre?: string;
  status: 'draft' | 'active' | 'completed';
  createdAt: string;
  updatedAt: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  genre?: string;
}

// 章节相关
export interface Chapter {
  id: string;
  projectId: string;
  number: number;
  title: string;
  content?: string;
  status: 'draft' | 'generating' | 'completed';
  wordCount: number;
  createdAt: string;
  updatedAt: string;
}

// 卡牌相关
export interface CardDirection {
  id: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  title: string;
  description: string;
  tags: string[];
  weight: number;
}

export interface GenerateRequest {
  chapterId: string;
  cardIds: string[];
  weights: number[];
  mode: 'single' | 'dual' | 'all';
}

export interface GenerateResponse {
  taskId: string;
  estimatedTime: number;
}

// 生成进度
export interface GenerationProgress {
  taskId: string;
  status: 'pending' | 'preprocessing' | 'generating' | 'validating' | 'completed' | 'failed';
  progress: number;
  currentStep?: string;
  result?: {
    content: string;
    wordCount: number;
    timeSpent: number;
  };
  error?: string;
}

// 确认/修订/取消
export interface ConfirmRequest {
  chapterId: string;
  content: string;
}

export interface ReviseRequest {
  chapterId: string;
  feedback: string;
}

// Vault 相关（四库）
export interface Character {
  id: string;
  projectId: string;
  name: string;
  role: 'mc' | 'ally' | 'enemy' | 'neutral';
  status: string;
  emotion: string;
  location: string;
  appearance?: string;
  personality?: string;
  knowledge?: string;
  relationships?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCharacterRequest {
  name: string;
  role: 'mc' | 'ally' | 'enemy' | 'neutral';
  status?: string;
  emotion?: string;
  location?: string;
  appearance?: string;
  personality?: string;
  knowledge?: string;
  relationships?: string;
}

export interface TimelineEvent {
  id: string;
  projectId: string;
  day: number;
  title: string;
  description: string;
  isCurrent: boolean;
}

export interface Commitment {
  id: string;
  projectId: string;
  type: 'foreshadow' | 'arc' | 'subplot' | 'theme';
  title: string;
  status: 'pending' | 'active' | 'recycled' | 'abandoned';
  description?: string;
  relatedCharacters?: string[];
  estimatedRecycleChapter?: number;
}

export interface WorldviewEntry {
  id: string;
  projectId: string;
  category: 'rule' | 'location' | 'item' | 'faction';
  title: string;
  description: string;
}

// 通知相关
export interface Notification {
  id: string;
  userId: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  isRead: boolean;
  createdAt: string;
}

// 导入相关
export interface ImportRequest {
  projectId: string;
  filePath: string;
  options?: {
    analyzeCharacters?: boolean;
    analyzeTimeline?: boolean;
    analyzeCommitments?: boolean;
    analyzeWorldview?: boolean;
  };
}

export interface ImportProgress {
  taskId: string;
  status: 'pending' | 'parsing' | 'analyzing' | 'saving' | 'completed' | 'failed';
  progress: number;
  currentPhase?: string;
  result?: {
    charactersCreated: number;
    eventsCreated: number;
    commitmentsCreated: number;
    entriesCreated: number;
  };
  error?: string;
}

// 设置相关
export interface UserSettings {
  id: string;
  userId: string;
  globalSettings: {
    theme: 'dark' | 'light' | 'system';
    language: string;
    autoSave: boolean;
    draftAutoConfirm: boolean;
    draftAutoConfirmSeconds: number;
  };
  projectSettings: Record<string, {
    aiSpeed: number;
    writingStyle: number;
    notificationEnabled: boolean;
  }>;
}

export interface ChangePasswordRequest {
  oldPassword: string;
  newPassword: string;
}

export interface UpdateProfileRequest {
  username?: string;
  email?: string;
  avatar?: string;
}
