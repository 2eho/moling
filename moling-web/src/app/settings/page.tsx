"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { showToast } from "@/components/ui/Toast";
import { settingsApi } from "@/lib/api";
import type { UserSettings } from "@/lib/types";
import styles from "./settings.module.css";

type SettingsTab = "general" | "ai" | "cards" | "data" | "about";

const NAV_ITEMS: { id: SettingsTab; label: string; icon: string }[] = [
  { id: "general", label: "通用设置", icon: "⚙" },
  { id: "ai", label: "AI创作", icon: "🤖" },
  { id: "cards", label: "卡牌管理", icon: "🃏" },
  { id: "data", label: "数据管理", icon: "📊" },
  { id: "about", label: "关于墨灵", icon: "ℹ" },
];

const MODEL_OPTIONS = [
  { value: "deepseek-v4-flash", label: "DeepSeek V4 Flash" },
  { value: "deepseek-v4-pro", label: "DeepSeek V4 Pro" },
  { value: "deepseek-chat", label: "DeepSeek Chat (即将弃用)" },
  { value: "deepseek-reasoner", label: "DeepSeek Reasoner (即将弃用)" },
];

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // ── Settings state ──
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [model, setModel] = useState("deepseek-chat");
  const [temperature, setTemperature] = useState(0.7);
  const [apiKeyConfigured] = useState(true); // 后端 .env 中配置，前端不可见

  // Load settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const res = await settingsApi.get();
        const settings = res.data;
        setUsername(settings.theme || ""); // 临时：使用 theme 字段存储昵称
        setEmail("author@moling.ai"); // 临时：从 user 对象获取
        setModel("deepseek-chat"); // 临时：从 settings 获取
        setTemperature(settings.editor_font_size / 14 || 0.7); // 临时：使用字体大小计算
      } catch (error) {
        showToast("error", "加载设置失败");
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, []);

  const handleSave = useCallback(async () => {
    try {
      setIsSaving(true);
      await settingsApi.update({
        theme: username, // 临时：使用 theme 字段存储昵称
        editor_font_size: Math.round(temperature * 14), // 临时：使用字体大小存储
      });
      showToast("success", "设置已保存");
    } catch (error) {
      showToast("error", "保存失败");
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  }, [username, temperature]);

  const renderContent = () => {
    switch (activeTab) {
      case "general":
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>通用设置</h2>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>昵称</span>
                <span className={styles.fieldDesc}>你的显示名称</span>
              </div>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="输入昵称"
                className={styles.fieldInput}
              />
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>邮箱</span>
                <span className={styles.fieldDesc}>登录邮箱，不可修改</span>
              </div>
              <Input
                value={email}
                readOnly
                className={styles.fieldInput}
              />
            </div>

            <div className={styles.actions}>
              <Button onClick={handleSave}>保存修改</Button>
            </div>
          </section>
        );

      case "ai":
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>AI 创作设置</h2>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>LLM API Key</span>
                <span className={styles.fieldDesc}>由管理员在服务器端配置，前端不可见</span>
              </div>
              <div className={styles.apiKeyRow}>
                <span className={styles.apiKeyStatus}>
                  ✅ 已配置（服务器端）
                </span>
              </div>
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>AI 模型</span>
                <span className={styles.fieldDesc}>选择生成使用的模型</span>
              </div>
              <select
                className={styles.select}
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                {MODEL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>生成温度</span>
                <span className={styles.fieldDesc}>
                  控制输出的创造性（0=保守，1=创意）
                </span>
              </div>
              <div className={styles.sliderWrap}>
                <input
                  type="range"
                  className={styles.slider}
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                />
                <span className={styles.sliderValue}>
                  {temperature.toFixed(1)}
                </span>
              </div>
            </div>

            <div className={styles.actions}>
              <Button onClick={handleSave}>保存 AI 设置</Button>
            </div>
          </section>
        );

      case "cards":
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>卡牌管理</h2>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>每日免费抽卡</span>
                <span className={styles.fieldDesc}>每天可免费抽取的卡牌次数</span>
              </div>
              <select className={styles.select} defaultValue="3">
                <option value="1">1 次</option>
                <option value="3">3 次</option>
                <option value="5">5 次</option>
                <option value="10">10 次</option>
              </select>
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>卡牌动画</span>
                <span className={styles.fieldDesc}>抽卡时展示动画效果</span>
              </div>
              <label className={`${styles.toggle} ${styles.toggleOn}`}>
                <span className={styles.toggleKnob} />
              </label>
            </div>

            <div className={styles.actions}>
              <Button variant="secondary">重置为默认</Button>
            </div>
          </section>
        );

      case "data":
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>数据管理</h2>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>导出所有项目</span>
                <span className={styles.fieldDesc}>将所有项目导出为 JSON 格式</span>
              </div>
              <Button
                variant="secondary"
                onClick={() => showToast("info", "数据导出功能开发中")}
              >
                导出数据
              </Button>
            </div>

            <div className={styles.fieldRow}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel}>导入项目</span>
                <span className={styles.fieldDesc}>从 JSON 文件导入项目数据</span>
              </div>
              <Button
                variant="secondary"
                onClick={() => showToast("info", "数据导入功能开发中")}
              >
                选择文件
              </Button>
            </div>

            <div className={styles.fieldRow} style={{ borderBottom: "none" }}>
              <div className={styles.fieldInfo}>
                <span className={styles.fieldLabel} style={{ color: "var(--color-danger)" }}>
                  危险操作
                </span>
                <span className={styles.fieldDesc}>删除所有项目数据，不可恢复</span>
              </div>
              <Button
                variant="danger"
                onClick={() => {
                  if (confirm("确定要删除所有数据吗？此操作不可恢复！")) {
                    showToast("error", "功能开发中");
                  }
                }}
              >
                删除所有数据
              </Button>
            </div>
          </section>
        );

      case "about":
        return (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>关于墨灵</h2>
            <div className={styles.aboutCard}>
              <div className={styles.aboutVersion}>v1.0.0</div>
              <p className={styles.aboutDesc}>
                墨灵是一款 AI 辅助创作平台，帮助你更高效地进行小说创作。灵感如墨，灵性如泉。
              </p>
            </div>
          </section>
        );
    }
  };

  return (
    <div className={styles.page}>
      {/* Header Shell */}
      <header className={styles.header}>
        <button className={styles.backBtn} onClick={() => router.back()}>
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span>返回</span>
        </button>
        <h1 className={styles.headerTitle}>设置</h1>
        <div className={styles.headerSpacer} />
        <Button size="sm" onClick={handleSave}>
          保存
        </Button>
      </header>

      {/* Body: Left Nav + Content */}
      <div className={styles.body}>
        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`${styles.navItem} ${
                activeTab === item.id ? styles.navItemActive : ""
              }`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <main className={styles.content}>{renderContent()}</main>
      </div>
    </div>
  );
}
