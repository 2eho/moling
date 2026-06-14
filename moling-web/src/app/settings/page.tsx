'use client';

import { useState, useEffect } from 'react';
import styles from './Settings.module.css';
import {
  getSettings,
  updateGlobalSettings,
  updateProjectSettings,
  changePassword,
  updateProfile,
  getProjectSettings,
} from '@/api';
import type { UserSettings, ChangePasswordRequest, UpdateProfileRequest } from '@/api';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'global' | 'project' | 'password' | 'profile'>('global');
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 全局设置表单
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('dark');
  const [language, setLanguage] = useState('zh-CN');
  const [autoSave, setAutoSave] = useState(true);
  const [draftAutoConfirm, setDraftAutoConfirm] = useState(true);
  const [draftAutoConfirmSeconds, setDraftAutoConfirmSeconds] = useState(6);

  // 项目设置表单
  const [projectId, setProjectId] = useState('current-project-id');
  const [aiSpeed, setAiSpeed] = useState(3);
  const [writingStyle, setWritingStyle] = useState(2);
  const [notificationEnabled, setNotificationEnabled] = useState(true);

  // 修改密码表单
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // 个人资料表单
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [avatar, setAvatar] = useState('');

  // 加载设置
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await getSettings();
        setSettings(data);
        setTheme(data.globalSettings.theme);
        setLanguage(data.globalSettings.language);
        setAutoSave(data.globalSettings.autoSave);
        setDraftAutoConfirm(data.globalSettings.draftAutoConfirm);
        setDraftAutoConfirmSeconds(data.globalSettings.draftAutoConfirmSeconds);
      } catch (error) {
        console.error('加载设置失败:', error);
        showMessage('error', '加载设置失败');
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleSaveGlobalSettings = async () => {
    setSaving(true);
    try {
      await updateGlobalSettings({
        theme,
        language,
        autoSave,
        draftAutoConfirm,
        draftAutoConfirmSeconds,
      });
      showMessage('success', '全局设置已保存');
    } catch (error) {
      console.error('保存失败:', error);
      showMessage('error', `保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveProjectSettings = async () => {
    setSaving(true);
    try {
      await updateProjectSettings(projectId, {
        aiSpeed,
        writingStyle,
        notificationEnabled,
      });
      showMessage('success', '项目设置已保存');
    } catch (error) {
      console.error('保存失败:', error);
      showMessage('error', `保存失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      showMessage('error', '新密码和确认密码不一致');
      return;
    }

    setSaving(true);
    try {
      await changePassword({ oldPassword, newPassword });
      showMessage('success', '密码已修改');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('修改密码失败:', error);
      showMessage('error', `修改密码失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateProfile = async () => {
    setSaving(true);
    try {
      await updateProfile({ username, email, avatar });
      showMessage('success', '个人资料已更新');
    } catch (error) {
      console.error('更新失败:', error);
      showMessage('error', `更新失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>设置</h1>
      </div>

      <div className={styles.content}>
        {/* 侧边栏 */}
        <div className={styles.sidebar}>
          <button
            className={`${styles.tabBtn} ${activeTab === 'global' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('global')}
          >
            ⚙️ 全局设置
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'project' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('project')}
          >
            📁 项目设置
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'password' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('password')}
          >
            🔒 修改密码
          </button>
          <button
            className={`${styles.tabBtn} ${activeTab === 'profile' ? styles.tabBtnActive : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            👤 个人资料
          </button>
        </div>

        {/* 主内容区 */}
        <div className={styles.main}>
          {message && (
            <div className={`${styles.message} ${styles[`message${message.type.charAt(0).toUpperCase() + message.type.slice(1)}`]}`}>
              {message.text}
            </div>
          )}

          {/* 全局设置 */}
          {activeTab === 'global' && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>全局设置</h2>

              <div className={styles.formGroup}>
                <label className={styles.label}>主题</label>
                <select
                  className={styles.select}
                  value={theme}
                  onChange={(e) => setTheme(e.target.value as any)}
                >
                  <option value="dark">深色</option>
                  <option value="light">浅色</option>
                  <option value="system">跟随系统</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>语言</label>
                <select
                  className={styles.select}
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="zh-CN">简体中文</option>
                  <option value="en">English</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.checkbox}>
                  <input
                    type="checkbox"
                    checked={autoSave}
                    onChange={(e) => setAutoSave(e.target.checked)}
                  />
                  <span>自动保存</span>
                </label>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.checkbox}>
                  <input
                    type="checkbox"
                    checked={draftAutoConfirm}
                    onChange={(e) => setDraftAutoConfirm(e.target.checked)}
                  />
                  <span>草稿自动确认</span>
                </label>
                {draftAutoConfirm && (
                  <input
                    type="number"
                    className={styles.input}
                    value={draftAutoConfirmSeconds}
                    onChange={(e) => setDraftAutoConfirmSeconds(parseInt(e.target.value))}
                    min={1}
                    max={30}
                    style={{ width: 80, marginLeft: 12 }}
                  />
                )}
              </div>

              <button
                className={styles.saveBtn}
                onClick={handleSaveGlobalSettings}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存设置'}
              </button>
            </div>
          )}

          {/* 项目设置 */}
          {activeTab === 'project' && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>项目设置</h2>

              <div className={styles.formGroup}>
                <label className={styles.label}>项目 ID</label>
                <input
                  type="text"
                  className={styles.input}
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>AI 速度 ({aiSpeed})</label>
                <input
                  type="range"
                  className={styles.range}
                  min={1}
                  max={5}
                  value={aiSpeed}
                  onChange={(e) => setAiSpeed(parseInt(e.target.value))}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>写作风格 ({writingStyle})</label>
                <input
                  type="range"
                  className={styles.range}
                  min={1}
                  max={5}
                  value={writingStyle}
                  onChange={(e) => setWritingStyle(parseInt(e.target.value))}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.checkbox}>
                  <input
                    type="checkbox"
                    checked={notificationEnabled}
                    onChange={(e) => setNotificationEnabled(e.target.checked)}
                  />
                  <span>启用通知</span>
                </label>
              </div>

              <button
                className={styles.saveBtn}
                onClick={handleSaveProjectSettings}
                disabled={saving}
              >
                {saving ? '保存中...' : '保存设置'}
              </button>
            </div>
          )}

          {/* 修改密码 */}
          {activeTab === 'password' && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>修改密码</h2>

              <div className={styles.formGroup}>
                <label className={styles.label}>当前密码</label>
                <input
                  type="password"
                  className={styles.input}
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>新密码</label>
                <input
                  type="password"
                  className={styles.input}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>确认新密码</label>
                <input
                  type="password"
                  className={styles.input}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              <button
                className={styles.saveBtn}
                onClick={handleChangePassword}
                disabled={saving}
              >
                {saving ? '修改中...' : '修改密码'}
              </button>
            </div>
          )}

          {/* 个人资料 */}
          {activeTab === 'profile' && (
            <div className={styles.section}>
              <h2 className={styles.sectionTitle}>个人资料</h2>

              <div className={styles.formGroup}>
                <label className={styles.label}>用户名</label>
                <input
                  type="text"
                  className={styles.input}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>邮箱</label>
                <input
                  type="email"
                  className={styles.input}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>头像 URL</label>
                <input
                  type="text"
                  className={styles.input}
                  value={avatar}
                  onChange={(e) => setAvatar(e.target.value)}
                />
              </div>

              <button
                className={styles.saveBtn}
                onClick={handleUpdateProfile}
                disabled={saving}
              >
                {saving ? '更新中...' : '更新资料'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
