"use client";

import { useState, useEffect, useCallback } from "react";
import { adminApi } from "@/lib/api";
import { showToast } from "@/components/ui/Toast";
import parentStyles from "../../admin.module.css";
import styles from "./LlmConfigTab.module.css";

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  enabled: boolean;
  created_at: string;
}

interface PoolInfo {
  total: number;
  used: number;
  available: number;
  status: "healthy" | "degraded" | "down";
}

export default function LlmConfigTab() {
  // ── Config form state ──
  const [apiBase, setApiBase] = useState("https://api.deepseek.com");
  const [model, setModel] = useState("deepseek-v4-flash");
  const [configured, setConfigured] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [configSaving, setConfigSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // ── API Key management ──
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [addingKey, setAddingKey] = useState(false);
  const [keyLoading, setKeyLoading] = useState(false);

  // ── Pool status ──
  const [proPool, setProPool] = useState<PoolInfo | null>(null);
  const [flashPool, setFlashPool] = useState<PoolInfo | null>(null);
  const [poolLoading, setPoolLoading] = useState(false);

  // ── Error states ──
  const [configError, setConfigError] = useState<string | null>(null);
  const [poolError, setPoolError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setConfigLoading(true);
    setConfigError(null);
    setPoolLoading(true);
    setPoolError(null);

    try {
      const configRes = await adminApi.getLlmConfig();
      const configData = configRes.data;
      setApiBase(configData.api_base || "https://api.deepseek.com");
      setModel(configData.model || "deepseek-v4-flash");
      setConfigured(configData.api_key_configured);
      if (configData.api_keys) {
        setApiKeys(configData.api_keys);
      }
    } catch (e) {
      setConfigError(e instanceof Error ? e.message : "获取配置失败");
    } finally {
      setConfigLoading(false);
    }

    // TODO: 后端暂未实现 LLM Pools 端点，跳过池状态获取
    // try {
    //   const poolRes = await adminApi.getLlmPools();
    //   setProPool(poolRes.data.pro_pool);
    //   setFlashPool(poolRes.data.flash_pool);
    // } catch (e) {
    //   setPoolError(e instanceof Error ? e.message : "获取池状态失败");
    // } finally {
    //   setPoolLoading(false);
    // }
    setPoolLoading(false);
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Save config ──
  const handleSaveConfig = useCallback(async () => {
    setConfigSaving(true);
    setTestResult(null);
    try {
      const res = await adminApi.saveLlmConfig({
        api_key: undefined,
        api_base: apiBase,
        model,
      });
      setConfigured(res.data.is_configured);
      showToast("success", "LLM 配置已保存");
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "保存失败");
    } finally {
      setConfigSaving(false);
    }
  }, [apiBase, model]);

  // ── Test connection ──
  const handleTestConnection = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await adminApi.testLlmConnection();
      if (res.data.success) {
        setConfigured(true);
        setTestResult({ ok: true, msg: res.data.message || "连接成功！" });
        showToast("success", "连接测试通过");
      } else {
        setTestResult({ ok: false, msg: res.data.message || "连接失败" });
        showToast("error", "连接测试失败");
      }
    } catch (e) {
      setTestResult({ ok: false, msg: e instanceof Error ? e.message : "连接测试失败" });
      showToast("error", "连接测试失败");
    } finally {
      setTesting(false);
    }
  }, []);

  // ── Add API Key ──
  const handleAddKey = useCallback(async () => {
    if (!newKeyName.trim() || !newKeyValue.trim()) {
      showToast("error", "请填写密钥名称和值");
      return;
    }
    setAddingKey(true);
    try {
      // TODO: 后端暂未实现 addApiKey 端点
      showToast("error", "添加 API Key 功能暂未实现");
      // await adminApi.addApiKey({ name: newKeyName.trim(), key: newKeyValue.trim() });
      // showToast("success", "API Key 已添加");
      // setNewKeyName("");
      // setNewKeyValue("");
      // fetchAll();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "添加失败");
    } finally {
      setAddingKey(false);
    }
  }, [newKeyName, newKeyValue, fetchAll]);

  // ── Delete API Key ──
  const handleDeleteKey = useCallback(async (keyId: string) => {
    setKeyLoading(true);
    try {
      // TODO: 后端暂未实现 deleteApiKey 端点
      showToast("error", "删除 API Key 功能暂未实现");
      // await adminApi.deleteApiKey(keyId);
      // showToast("success", "API Key 已删除");
      // fetchAll();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "删除失败");
    } finally {
      setKeyLoading(false);
    }
  }, [fetchAll]);

  // ── Toggle API Key ──
  const handleToggleKey = useCallback(async (keyId: string, enabled: boolean) => {
    setKeyLoading(true);
    try {
      // TODO: 后端暂未实现 toggleApiKey 端点
      showToast("error", "切换 API Key 状态功能暂未实现");
      // await adminApi.toggleApiKey(keyId, enabled);
      // showToast("success", `密钥已${enabled ? "启用" : "禁用"}`);
      // fetchAll();
    } catch (e) {
      showToast("error", e instanceof Error ? e.message : "操作失败");
    } finally {
      setKeyLoading(false);
    }
  }, [fetchAll]);

  // ── Pool progress helper ──
  const poolUsagePercent = (pool: PoolInfo) =>
    pool.total > 0 ? Math.round((pool.used / pool.total) * 100) : 0;

  const poolColorClass = (pool: PoolInfo) => {
    const pct = poolUsagePercent(pool);
    if (pct >= 90) return styles.poolProgressRed;
    if (pct >= 70) return styles.poolProgressAmber;
    return styles.poolProgressGreen;
  };

  const poolStatusClass = (pool: PoolInfo) => {
    switch (pool.status) {
      case "healthy": return styles.poolStatusBadgeHealthy;
      case "degraded": return styles.poolStatusBadgeDegraded;
      case "down": return styles.poolStatusBadgeDown;
      default: return styles.poolStatusBadgeDegraded;
    }
  };

  return (
    <div className={`${parentStyles.tabPanelActive}`}>
      <div className={parentStyles.pageTitleRow}>
        <div>
          <h1 className={parentStyles.pageTitle}>LLM 配置</h1>
          <p className={parentStyles.pageSubtitle}>管理 AI 模型 API 密钥与服务端设置</p>
        </div>
      </div>

      {/* ── Pool Status ── */}
      <div className={styles.poolCards}>
        {poolError ? (
          <div className={styles.errorState} style={{gridColumn:"1/-1"}}>
            <div className={styles.errorIcon}>⚠️</div>
            <div className={styles.errorText}>获取池状态失败</div>
            <div className={styles.errorHint}>{poolError}</div>
            <button className={styles.retryBtn} onClick={fetchAll}>重试</button>
          </div>
        ) : poolLoading ? (
          <>
            {[1, 2].map((i) => (
              <div key={i} className={styles.poolCard}>
                <div className={styles.poolCardHeader}>
                  <span className={styles.poolCardTitle}>{i === 1 ? "Pro Pool" : "Flash Pool"}</span>
                  <span style={{color:"var(--color-text-tertiary)",fontSize:12}}>加载中...</span>
                </div>
              </div>
            ))}
          </>
        ) : (
          <>
            {proPool && (
              <div className={styles.poolCard}>
                <div className={styles.poolCardHeader}>
                  <span className={styles.poolCardTitle}>🚀 Pro Pool</span>
                  <span className={poolStatusClass(proPool)}>
                    {proPool.status === "healthy" ? "健康" : proPool.status === "degraded" ? "降级" : "离线"}
                  </span>
                </div>
                <div className={styles.poolProgressWrap}>
                  <div className={poolColorClass(proPool)} style={{width:`${poolUsagePercent(proPool)}%`}}></div>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>使用率</span>
                  <span className={styles.poolStatValue}>{poolUsagePercent(proPool)}%</span>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>已用 / 总量</span>
                  <span className={styles.poolStatValue}>{proPool.used.toLocaleString()} / {proPool.total.toLocaleString()}</span>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>可用</span>
                  <span className={styles.poolStatValue}>{proPool.available.toLocaleString()}</span>
                </div>
              </div>
            )}
            {flashPool && (
              <div className={styles.poolCard}>
                <div className={styles.poolCardHeader}>
                  <span className={styles.poolCardTitle}>⚡ Flash Pool</span>
                  <span className={poolStatusClass(flashPool)}>
                    {flashPool.status === "healthy" ? "健康" : flashPool.status === "degraded" ? "降级" : "离线"}
                  </span>
                </div>
                <div className={styles.poolProgressWrap}>
                  <div className={poolColorClass(flashPool)} style={{width:`${poolUsagePercent(flashPool)}%`}}></div>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>使用率</span>
                  <span className={styles.poolStatValue}>{poolUsagePercent(flashPool)}%</span>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>已用 / 总量</span>
                  <span className={styles.poolStatValue}>{flashPool.used.toLocaleString()} / {flashPool.total.toLocaleString()}</span>
                </div>
                <div className={styles.poolStatRow}>
                  <span className={styles.poolStatLabel}>可用</span>
                  <span className={styles.poolStatValue}>{flashPool.available.toLocaleString()}</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── LLM Config Form ── */}
      <div className={parentStyles.sectionCard}>
        {configLoading ? (
          <div className={styles.loadingState}>
            <div className={styles.loadingSpinner}></div>
            <span className={styles.loadingText}>加载配置...</span>
          </div>
        ) : configError ? (
          <div className={styles.errorState}>
            <div className={styles.errorIcon}>⚠️</div>
            <div className={styles.errorText}>加载配置失败</div>
            <div className={styles.errorHint}>{configError}</div>
            <button className={styles.retryBtn} onClick={fetchAll}>重试</button>
          </div>
        ) : (
          <>
            {/* API Base URL */}
            <div className={parentStyles.fieldRow}>
              <div className={parentStyles.fieldInfo}>
                <span className={parentStyles.fieldLabel}>API Base URL</span>
                <span className={parentStyles.fieldDesc}>API 服务地址</span>
              </div>
              <input
                className={parentStyles.filterSearch}
                style={{ flex: 1, minWidth: 280 }}
                value={apiBase}
                onChange={(e) => setApiBase(e.target.value)}
                placeholder="https://api.deepseek.com/v1"
              />
            </div>

            {/* Model Select */}
            <div className={parentStyles.fieldRow}>
              <div className={parentStyles.fieldInfo}>
                <span className={parentStyles.fieldLabel}>默认模型</span>
                <span className={parentStyles.fieldDesc}>AI 生成使用的模型</span>
              </div>
              <select
                className={parentStyles.filterSelect}
                value={model}
                onChange={(e) => setModel(e.target.value)}
                style={{ flex: 1, minWidth: 280 }}
              >
                <option value="deepseek-v4-flash">DeepSeek V4 Flash</option>
                <option value="deepseek-v4-pro">DeepSeek V4 Pro</option>
                <option value="deepseek-chat">DeepSeek Chat (即将弃用)</option>
                <option value="deepseek-reasoner">DeepSeek Reasoner (即将弃用)</option>
              </select>
            </div>

            {/* Config status */}
            <div className={parentStyles.fieldRow}>
              <div className={parentStyles.fieldInfo}>
                <span className={parentStyles.fieldLabel}>状态</span>
                <span className={parentStyles.fieldDesc}>API 连接状态</span>
              </div>
              <span
                className={`${parentStyles.badge} ${configured ? parentStyles.badgeActive : parentStyles.badgePending}`}
              >
                ● {configured ? "已配置" : "未配置"}
              </span>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 24 }}>
              {testResult && (
                <span style={{
                  marginRight: "auto",
                  fontSize: 13,
                  padding: "6px 12px",
                  borderRadius: 6,
                  background: testResult.ok
                    ? "rgba(52,211,153,0.1)"
                    : "rgba(239,68,68,0.1)",
                  color: testResult.ok
                    ? "var(--color-success)"
                    : "var(--color-danger)",
                }}>
                  {testResult.ok ? "✅ " : "❌ "}{testResult.msg}
                </span>
              )}
              <button
                className={parentStyles.tableActionBtn}
                style={{ color: "var(--color-brand-amber)" }}
                disabled={testing}
                onClick={handleTestConnection}
              >
                {testing ? "测试中..." : "🔌 测试连接"}
              </button>
              <button
                className={parentStyles.tableActionBtn}
                style={{ background: "var(--color-brand-indigo-dim)", color: "var(--color-brand-indigo)", fontWeight: 600 }}
                disabled={configSaving}
                onClick={handleSaveConfig}
              >
                {configSaving ? "保存中..." : "保存配置"}
              </button>
            </div>
          </>
        )}
      </div>

      {/* ── API Key Management ── */}
      <div className={parentStyles.sectionCard}>
        <div className={parentStyles.sectionCardHeader}>
          <span className={parentStyles.sectionCardTitle}>🔑 API Key 管理</span>
          <span className="text-tertiary" style={{fontSize:12,color:"var(--color-text-tertiary)"}}>
            {apiKeys.length} 个密钥
          </span>
        </div>

        {apiKeys.length > 0 ? (
          <div className={styles.keyList}>
            {apiKeys.map((key) => (
              <div key={key.id} className={styles.keyItem}>
                <div className={styles.keyInfo}>
                  <span className={styles.keyName}>{key.name}</span>
                  <span className={styles.keyPrefix}>
                    {key.prefix}... · 创建于 {new Date(key.created_at).toLocaleDateString("zh-CN")}
                  </span>
                </div>
                <div className={styles.keyActions}>
                  <button
                    className={key.enabled ? styles.keyToggleOn : styles.keyToggleOff}
                    onClick={() => handleToggleKey(key.id, !key.enabled)}
                    disabled={keyLoading}
                    aria-label={key.enabled ? "禁用密钥" : "启用密钥"}
                  />
                  <button
                    className={styles.keyDeleteBtn}
                    onClick={() => handleDeleteKey(key.id)}
                    disabled={keyLoading}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{color:"var(--color-text-tertiary)",fontSize:13,padding:"8px 0"}}>
            暂无 API Key，请添加
          </p>
        )}

        <div className={styles.addKeyRow}>
          <input
            className={styles.addKeyInput}
            style={{ minWidth: 160 }}
            type="text"
            placeholder="密钥名称"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
          />
          <input
            className={styles.addKeyInput}
            type="password"
            placeholder="输入 API Key"
            value={newKeyValue}
            onChange={(e) => setNewKeyValue(e.target.value)}
          />
          <button
            className={styles.addKeyBtn}
            disabled={addingKey || !newKeyName.trim() || !newKeyValue.trim()}
            onClick={handleAddKey}
          >
            {addingKey ? "添加中..." : "添加 Key"}
          </button>
        </div>
      </div>
    </div>
  );
}
