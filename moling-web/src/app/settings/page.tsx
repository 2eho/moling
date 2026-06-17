'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import styles from './Settings.module.css';
import { settingsApi } from '@/lib/api';
import type { UserSettings, HealthRules } from '@/lib/types';
import { safeObject } from '@/lib/apiSafety';
import { validateForm, clearFieldError, parseApiError } from '@/lib/formValidation';
import { FormError, FieldError } from '@/components/FormError';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/Spinner';

const ACCENT_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b', '#10b981'];

const TAB_LABELS: Record<string, string> = {
  profile: '个人信息',
  defaults: '创作默认设置',
  theme: '主题设置',
  security: '安全设置',
  data: '数据管理',
};

export default function SettingsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  // 路由守卫：未登录时重定向到 /auth（hooks 必须放在顶部）
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace("/auth");
    }
  }, [authLoading, isAuthenticated, router]);

  const [activeTab, setActiveTab] = useState<'profile' | 'defaults' | 'theme' | 'security' | 'data'>('profile');
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Profile
  const [nickname, setNickname] = useState('');
  const [bio, setBio] = useState('');
  const [email, setEmail] = useState('');
  const [avatarInitial, setAvatarInitial] = useState('U');

  // Creation defaults
  const [fontSize, setFontSize] = useState<number>(14);
  const [autoSave, setAutoSave] = useState(true);
  const [generationMode, setGenerationMode] = useState('balanced');

  // Theme
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('dark');
  const [accentColor, setAccentColor] = useState('#6366f1');

  // Health monitor
  const [healthRules, setHealthRules] = useState<HealthRules>({
    r1_enabled: true,
    r2_enabled: true,
    r3_enabled: true,
    anti_fatigue: false,
  });

  // Phase 4 review mode
  const [phase4ReviewMode, setPhase4ReviewMode] = useState<'manual' | 'auto'>('manual');

  // Password change
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});
  const [passwordApiError, setPasswordApiError] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  // Data management
  const [storageStats, setStorageStats] = useState({ totalWords: 0, projects: 0, chapters: 0, cards: 0 });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messageTimer = useRef<ReturnType<typeof setTimeout>>(null);

  const showMessage = useCallback((type: 'success' | 'error', text: string) => {
    if (messageTimer.current) clearTimeout(messageTimer.current);
    setMessage({ type, text });
    messageTimer.current = setTimeout(() => setMessage(null), 3000);
  }, []);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const res = await settingsApi.get();
        // ✅ 修复：使用 safeObject 确保 data 不会是 undefined
        const data = safeObject<UserSettings>(res.data, {} as UserSettings)!;
        setSettings(data);
        setTheme(data.theme || 'dark');
        setAutoSave(data.auto_save_interval > 0);
        setNickname(data.nickname || '');
        setEmail(data.email || '');
        setAvatarInitial(data.nickname?.charAt(0)?.toUpperCase() || 'U');
        setBio(data.bio || '');
        setFontSize(data.editor_font_size || 14);
        setGenerationMode(data.generation_preference?.default_mode || 'balanced');
        setAccentColor('#6366f1'); // 暂时硬编码，后续从设置读取

        // 健康监控规则
        if (data.health_rules) {
          setHealthRules(data.health_rules);
        }

        // Phase 4 审核模式
        if (data.phase4_review_mode) {
          setPhase4ReviewMode(data.phase4_review_mode);
        }
      } catch (error) {
        console.error('Failed to load settings:', error);
        showMessage('error', '加载设置失败');
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
    // Load mock storage stats
    setStorageStats({ totalWords: 1284500, projects: 3, chapters: 47, cards: 18 });
  }, [showMessage]);

  const handleSaveGlobalSettings = async () => {
    setSaving(true);
    try {
      const updateData: Partial<UserSettings> = {
        nickname,
        bio,
        email,
        theme,
        language: 'zh-CN',
        editor_font_size: fontSize,
        auto_save_interval: autoSave ? 6 : 0,
        generation_preference: {
          default_mode: generationMode,
          default_weights: { plot: 0.4, character: 0.3, worldview: 0.3 },
          auto_confirm: false,
        },
      };

      await settingsApi.update(updateData);
      showMessage('success', '设置已保存');

      // 保存健康监控设置
      await settingsApi.updateHealthMonitor({
        r1_enabled: healthRules.r1_enabled,
        r2_enabled: healthRules.r2_enabled,
        r3_enabled: healthRules.r3_enabled,
        anti_fatigue: healthRules.anti_fatigue,
      });

      // 保存 Phase 4 审核模式
      await settingsApi.updatePhase4Review({ mode: phase4ReviewMode });
    } catch (error) {
      console.error('Failed to save:', error);
      showMessage('error', `保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      showMessage('success', '头像已上传（模拟）');
    }
  };

  const handleExportData = async () => {
    try {
      await settingsApi.exportData();
      showMessage('success', '数据导出已开始');
    } catch (error) {
      showMessage('error', '导出失败');
    }
  };

  const handleClearCache = async () => {
    if (window.confirm('确认清除缓存？')) {
      try {
        await settingsApi.clearCache();
        showMessage('success', '缓存已清除');
      } catch (error) {
        showMessage('error', '清除缓存失败');
      }
    }
  };

  // 修改密码
  const passwordValidationRules: Record<string, {
    required?: boolean;
    min?: number;
    validate?: (value: unknown) => boolean;
    message: string;
  }[]> = {
    oldPassword: [
      { required: true, message: '当前密码不能为空' },
    ],
    newPassword: [
      { required: true, message: '新密码不能为空' },
      { min: 8, message: '新密码至少 8 个字符' },
      {
        validate: (v) => typeof v === 'string' && v.length >= 8,
        message: '新密码至少 8 个字符',
      },
    ],
    confirmPassword: [
      { required: true, message: '请再次输入新密码' },
      {
        validate: (v) => v === newPassword,
        message: '两次输入的新密码不一致',
      },
    ],
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordApiError('');

    const formData: Record<string, unknown> = {
      oldPassword,
      newPassword,
      confirmPassword,
    };
    const errors = validateForm(formData, passwordValidationRules);
    if (Object.keys(errors).length > 0) {
      setPasswordErrors(errors);
      return;
    }

    setPasswordSaving(true);
    try {
      await settingsApi.changePassword(oldPassword, newPassword);
      showMessage('success', '密码修改成功，请重新登录');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordErrors({});
    } catch (error: unknown) {
      const err = error as any;
      setPasswordApiError(err?.message || (error instanceof Error ? error.message : '密码修改失败'));
      if (err?.errors) {
        setPasswordErrors(err.errors);
      }
    } finally {
      setPasswordSaving(false);
    }
  };

  // 认证守卫：未登录时不渲染受保护内容
  if (authLoading || !isAuthenticated) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
        background: "var(--color-bg, #0d0f1a)"
      }}>
        <Spinner />
      </div>
    );
  }

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      {/* Top Navigation */}
      <nav className={styles.topNav}>
        <span className={styles.navTitle}>设置</span>
        <div className={styles.navSpacer} />
        <div className={styles.navTabs}>
          <button
            className={`${styles.navTab} ${activeTab === 'profile' ? styles.navTabActive : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <span>个人信息</span>
          </button>
          <button
            className={`${styles.navTab} ${activeTab === 'defaults' ? styles.navTabActive : ''}`}
            onClick={() => setActiveTab('defaults')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            <span>创作默认设置</span>
          </button>
          <button
            className={`${styles.navTab} ${activeTab === 'theme' ? styles.navTabActive : ''}`}
            onClick={() => setActiveTab('theme')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
            <span>主题设置</span>
          </button>
          <button
            className={`${styles.navTab} ${activeTab === 'data' ? styles.navTabActive : ''}`}
            onClick={() => setActiveTab('data')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <span>数据管理</span>
          </button>

          {/* 安全设置 Tab */}
          <button
            className={`${styles.navTab} ${activeTab === 'security' ? styles.navTabActive : ''}`}
            onClick={() => setActiveTab('security')}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>安全设置</span>
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className={styles.mainContent}>
        {message && (
          <div className={`${styles.message} ${message.type === 'success' ? styles.messageSuccess : styles.messageError}`}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              {message.type === 'success'
                ? <><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></>
                : <><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></>
              }
            </svg>
            {message.text}
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>个人信息</div>

            <div className={styles.profileRow}>
              <div className={styles.avatarWrap}>
                <div className={styles.avatarUpload}>
                  <div className={styles.avatar}>{avatarInitial}</div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleAvatarUpload}
                  />
                </div>
                <span className={styles.avatarChangeLabel} onClick={() => fileInputRef.current?.click()}>
                  更换头像
                </span>
              </div>

              <div className={styles.profileFields}>
                <div className={styles.fieldGroup}>
                  <label className={styles.fieldLabel}>昵称</label>
                  <input
                    className={styles.fieldInput}
                    type="text"
                    value={nickname}
                    onChange={(e) => {
                      setNickname(e.target.value);
                      setAvatarInitial(e.target.value.charAt(0).toUpperCase() || 'U');
                    }}
                    placeholder="输入昵称"
                  />
                </div>
                <div className={styles.fieldGroup}>
                  <label className={styles.fieldLabel}>个人简介</label>
                  <textarea
                    className={styles.fieldTextarea}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="简短的个人介绍..."
                    rows={2}
                  />
                </div>
                <div className={styles.fieldGroup}>
                  <label className={styles.fieldLabel}>邮箱</label>
                  <input
                    className={styles.fieldInput}
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="输入邮箱"
                  />
                </div>
              </div>
            </div>

            <button className={styles.saveBtn} onClick={handleSaveGlobalSettings} disabled={saving}>
              {saving ? '保存中...' : '保存修改'}
            </button>
          </div>
        )}

        {/* Creation Defaults Tab */}
        {activeTab === 'defaults' && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>创作默认设置</div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>编辑器字体大小</span>
                <span className={styles.settingDesc}>调整编辑器的字号大小（像素）</span>
              </div>
              <div className={styles.fontSizeGroup}>
                {([12, 14, 16, 18, 20] as const).map((size) => (
                  <button
                    key={size}
                    className={`${styles.fontSizeBtn} ${fontSize === size ? styles.fontSizeBtnActive : ''}`}
                    onClick={() => setFontSize(size)}
                  >
                    {size}px
                  </button>
                ))}
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>自动保存草稿</span>
                <span className={styles.settingDesc}>自动保存 AI 生成的草稿</span>
              </div>
              <div
                className={`${styles.toggle} ${autoSave ? styles.toggleOn : ''}`}
                onClick={() => setAutoSave(!autoSave)}
              >
                <div className={styles.toggleKnob} />
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>默认生成模式</span>
                <span className={styles.settingDesc}>AI 创作策略</span>
              </div>
              <select
                className={styles.fieldSelect}
                value={generationMode}
                onChange={(e) => setGenerationMode(e.target.value)}
                style={{ width: 150 }}
              >
                <option value="conservative">保守</option>
                <option value="balanced">均衡</option>
                <option value="creative">创意</option>
              </select>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>健康监控 - R1 规则</span>
                <span className={styles.settingDesc}>检测角色崩坏</span>
              </div>
              <div
                className={`${styles.toggle} ${healthRules.r1_enabled ? styles.toggleOn : ''}`}
                onClick={() => setHealthRules({ ...healthRules, r1_enabled: !healthRules.r1_enabled })}
              >
                <div className={styles.toggleKnob} />
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>健康监控 - R2 规则</span>
                <span className={styles.settingDesc}>检测剧情矛盾</span>
              </div>
              <div
                className={`${styles.toggle} ${healthRules.r2_enabled ? styles.toggleOn : ''}`}
                onClick={() => setHealthRules({ ...healthRules, r2_enabled: !healthRules.r2_enabled })}
              >
                <div className={styles.toggleKnob} />
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>健康监控 - R3 规则</span>
                <span className={styles.settingDesc}>检测伏笔丢失</span>
              </div>
              <div
                className={`${styles.toggle} ${healthRules.r3_enabled ? styles.toggleOn : ''}`}
                onClick={() => setHealthRules({ ...healthRules, r3_enabled: !healthRules.r3_enabled })}
              >
                <div className={styles.toggleKnob} />
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>防疲劳模式</span>
                <span className={styles.settingDesc}>长时间写作时提醒休息</span>
              </div>
              <div
                className={`${styles.toggle} ${healthRules.anti_fatigue ? styles.toggleOn : ''}`}
                onClick={() => setHealthRules({ ...healthRules, anti_fatigue: !healthRules.anti_fatigue })}
              >
                <div className={styles.toggleKnob} />
              </div>
            </div>

            <div className={styles.settingRow}>
              <div className={styles.settingInfo}>
                <span className={styles.settingName}>Phase 4 审核模式</span>
                <span className={styles.settingDesc}>控制质检阶段的审核方式</span>
              </div>
              <select
                className={styles.fieldSelect}
                value={phase4ReviewMode}
                onChange={(e) => setPhase4ReviewMode(e.target.value as 'manual' | 'auto')}
                style={{ width: 150 }}
              >
                <option value="manual">手动审核</option>
                <option value="auto">自动审核</option>
              </select>
            </div>

            <button className={styles.saveBtn} onClick={handleSaveGlobalSettings} disabled={saving}>
              {saving ? '保存中...' : '保存修改'}
            </button>
          </div>
        )}

        {/* Theme Tab */}
        {activeTab === 'theme' && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>主题设置</div>

            <div className={styles.themeOptions}>
              {(['dark', 'light', 'system'] as const).map((t) => (
                <button
                  key={t}
                  className={`${styles.themeOption} ${theme === t ? styles.themeOptionActive : ''}`}
                  onClick={() => setTheme(t)}
                >
                  <span className={styles.themeIcon}>
                    {t === 'dark' && (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                      </svg>
                    )}
                    {t === 'light' && (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="5" />
                        <line x1="12" y1="1" x2="12" y2="3" />
                        <line x1="12" y1="21" x2="12" y2="23" />
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                        <line x1="1" y1="12" x2="3" y2="12" />
                        <line x1="21" y1="12" x2="23" y2="12" />
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                      </svg>
                    )}
                    {t === 'system' && (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                      </svg>
                    )}
                  </span>
                  <span className={styles.themeLabel}>
                    {t === 'dark' ? '深色' : t === 'light' ? '浅色' : '跟随系统'}
                  </span>
                </button>
              ))}
            </div>

            <div className={styles.accentRow}>
              <span className={styles.accentLabel}>强调色</span>
              <div className={styles.accentColors}>
                {ACCENT_COLORS.map((color) => (
                  <div
                    key={color}
                    className={`${styles.accentColor} ${accentColor === color ? styles.accentColorActive : ''}`}
                    style={{ background: color }}
                    onClick={() => setAccentColor(color)}
                  />
                ))}
              </div>
            </div>

            <button className={styles.saveBtn} onClick={handleSaveGlobalSettings} disabled={saving}>
              {saving ? '保存中...' : '保存修改'}
            </button>
          </div>
        )}

        {/* Data Management Tab */}
        {activeTab === 'data' && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>数据管理</div>

            <div className={styles.actionBtnGroup}>
              <button className={styles.actionBtnOutline} onClick={handleExportData}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                导出数据
              </button>
              <button className={styles.actionBtnDanger} onClick={handleClearCache}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                清除缓存
              </button>
            </div>

            <hr className={styles.sectionDivider} />

            <div className={styles.statsBar}>
              <div className={styles.statItem}>
                <span className={styles.statValue}>{storageStats.totalWords.toLocaleString()}</span>
                <span className={styles.statLabel}>总字数</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>{storageStats.projects}</span>
                <span className={styles.statLabel}>项目数</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>{storageStats.chapters}</span>
                <span className={styles.statLabel}>已完成章节</span>
              </div>
              <div className={styles.statItem}>
                <span className={styles.statValue}>{storageStats.cards}</span>
                <span className={styles.statLabel}>收集的卡牌</span>
              </div>
            </div>
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && (
          <div className={styles.section}>
            <div className={styles.sectionTitle}>安全设置</div>

            <div className={styles.profileFields}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>当前密码 *</label>
                <input
                  className={styles.fieldInput}
                  type="password"
                  value={oldPassword}
                  onChange={(e) => {
                    setOldPassword(e.target.value);
                    setPasswordErrors(clearFieldError(passwordErrors, 'oldPassword'));
                  }}
                  placeholder="输入当前密码"
                />
                <FieldError error={passwordErrors.oldPassword} />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>新密码 *</label>
                <input
                  className={styles.fieldInput}
                  type="password"
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    setPasswordErrors(clearFieldError(passwordErrors, 'newPassword'));
                  }}
                  placeholder="至少 8 个字符"
                />
                <FieldError error={passwordErrors.newPassword} />
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>确认新密码 *</label>
                <input
                  className={styles.fieldInput}
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setPasswordErrors(clearFieldError(passwordErrors, 'confirmPassword'));
                  }}
                  placeholder="再次输入新密码"
                />
                <FieldError error={passwordErrors.confirmPassword} />
              </div>

              <FormError error={passwordApiError} />

              <button
                type="button"
                className={styles.saveBtn}
                onClick={handleChangePassword}
                disabled={passwordSaving}
              >
                {passwordSaving ? '修改中...' : '修改密码'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
