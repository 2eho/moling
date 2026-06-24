import {
  ArrowLeft,
  Bell,
  CheckCircle,
  ChevronDown,
  Cpu,
  Eye,
  EyeOff,
  Info,
  Loader,
  RotateCcw,
  Shield,
  User,
  Wifi,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";
import { LLM_MODELS, type LLMModelId, useLLMSettings } from "@/stores/useLLMSettings";
import { useToast } from "@/stores/useToast";

export function SettingsPage() {
  const { addToast } = useToast();
  const llm = useLLMSettings();
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saved, setSaved] = useState(false);

  // ── Test connection dialog state ──
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogResult, setDialogResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    addToast({ type: "success", message: "LLM 设置已写入本地存储" });
  };

  const handleReset = () => {
    llm.reset();
    addToast({ type: "info", message: "已恢复默认设置" });
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setDialogOpen(true);
    setDialogResult(null);
    try {
      const res = await fetch(`${llm.baseUrl}/models`, {
        headers: { Authorization: `Bearer ${llm.apiKey}` },
      });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        const models = data?.data?.map((m: { id: string }) => m.id).join(", ") ?? "OK";
        setDialogResult({ ok: true, message: `连接成功\n可用模型: ${models}` });
      } else {
        const body = await res.text().catch(() => "");
        setDialogResult({
          ok: false,
          message: `HTTP ${res.status}${body ? "\n" + body.slice(0, 200) : ""}`,
        });
      }
    } catch {
      setDialogResult({ ok: false, message: "网络错误：无法连接到 API 地址" });
    } finally {
      setTesting(false);
    }
  };

  const inputClass =
    "w-full rounded-lg px-3 py-2 text-sm outline-none transition-all bg-[var(--th-input-bg,var(--th-bg))] text-th-text border border-th-border-subtle";

  const cardClass = "rounded-xl p-5 bg-th-card border border-th-border-subtle";

  return (
    <div className="min-h-screen flex flex-col bg-th-bg text-th-text">
      {/* ── Header ── */}
      <header className="flex items-center gap-3 px-6 py-4">
        <Link to="/projects" className="text-th-text-3 hover:text-th-text-2 transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <span className="text-base font-bold">设置</span>
        <div className="flex-1" />
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-6 space-y-6">
        {/* ── Profile card ── */}
        <div className={cardClass}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-th-accent-dim">
              <User size={20} className="text-th-accent-text" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">用户</p>
              <p className="text-xs truncate text-th-text-3">admin@moling.dev</p>
            </div>
          </div>
        </div>

        {/* ── LLM 配置 ── */}
        <div className={`${cardClass} space-y-5`}>
          {/* Section header */}
          <div className="flex items-center gap-2">
            <Cpu size={15} className="text-th-accent-text" />
            <span className="text-sm font-semibold text-th-text-2">LLM 配置</span>
          </div>

          <div className="space-y-4">
            {/* API Key */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-th-text-3">API Key</label>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={llm.apiKey}
                  onChange={(e) => llm.setApiKey(e.target.value)}
                  placeholder="申请地址: platform.deepseek.com/api_keys"
                  className={`${inputClass} pr-10`}
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-th-text-4 hover:text-th-text-3 transition-colors"
                  aria-label={showKey ? "隐藏 API Key" : "显示 API Key"}
                >
                  {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <p className="text-[11px] text-th-text-4">密钥仅存储于本地浏览器，不会上传到服务器</p>
            </div>

            {/* Base URL */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-th-text-3">API 地址</label>
              <input
                type="text"
                value={llm.baseUrl}
                onChange={(e) => llm.setBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com"
                className={inputClass}
              />
            </div>

            {/* Model */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-th-text-3">模型</label>
              <div className="relative">
                <select
                  value={llm.model}
                  onChange={(e) => llm.setModel(e.target.value as LLMModelId)}
                  className={`${inputClass} appearance-none cursor-pointer pr-8`}
                >
                  {LLM_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={14}
                  className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-th-text-4"
                />
              </div>
              <p className="text-[11px] text-th-text-4">
                {LLM_MODELS.find((m) => m.id === llm.model)?.desc}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing || !llm.apiKey}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-th-accent-text bg-th-accent-dim transition-colors hover:opacity-80 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {testing ? <Loader size={13} className="animate-spin" /> : <Wifi size={13} />}
              测试连接
            </button>
            <div className="flex-1" />
            <button
              type="button"
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-th-text-4 bg-th-hover transition-colors hover:bg-th-hover-strong"
            >
              <RotateCcw size={13} />
              恢复默认
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saved}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all active:scale-95 disabled:opacity-60 text-white ${
                saved ? "bg-[var(--th-success)]" : "bg-th-accent"
              }`}
            >
              {saved ? <CheckCircle size={13} /> : <Zap size={13} />}
              {saved ? "已保存" : "保存配置"}
            </button>
          </div>
        </div>

        {/* ── Theme switcher ── */}
        <div className={`${cardClass} !p-4`}>
          <p className="text-xs font-semibold mb-3 text-th-text-2">主题外观</p>
          <ThemeSwitcher />
        </div>

        {/* ── Status items (stub) ── */}
        <div className="rounded-xl overflow-hidden bg-th-card border border-th-border-subtle">
          {(
            [
              { icon: <Shield size={16} />, label: "修改密码", desc: "更新登录密码 · 即将推出" },
              { icon: <Bell size={16} />, label: "通知设置", desc: "消息通知偏好 · 即将推出" },
              { icon: <Info size={16} />, label: "关于墨灵", desc: "v0.1.0 · Phase 4 四库系统" },
            ] as const
          ).map((item, i) => (
            <div
              key={item.label}
              className={`flex items-center gap-3 px-4 py-3.5 opacity-50 text-th-text-2 ${
                i < 2 ? "border-b border-th-border-subtle" : ""
              }`}
            >
              <span className="shrink-0 text-th-text-3">{item.icon}</span>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium">{item.label}</span>
                <p className="text-[11px] text-th-text-4">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </main>

      {/* ── Test Connection Dialog ── */}
      {dialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          onClick={() => setDialogOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40" />
          {/* Dialog */}
          <div
            className="relative z-10 w-[90vw] max-w-sm rounded-xl p-6 shadow-2xl bg-th-card border border-th-border-subtle text-th-text"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold text-th-text-2">连接测试</span>
              <button
                type="button"
                onClick={() => setDialogOpen(false)}
                className="p-1 rounded-md hover:bg-th-hover text-th-text-4 transition-colors"
                aria-label="关闭连接测试"
              >
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            {!dialogResult ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <Loader size={28} className="animate-spin text-th-accent-text" />
                <span className="text-xs text-th-text-3">正在连接 {llm.baseUrl}...</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 py-4">
                {dialogResult.ok ? (
                  <CheckCircle size={28} className="text-[var(--th-success)]" />
                ) : (
                  <XCircle size={28} className="text-[var(--th-error,var(--th-danger))]" />
                )}
                <div className="text-xs text-center whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto text-th-text-3">
                  {dialogResult.message}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setDialogOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-th-text-2 bg-th-hover transition-colors hover:bg-th-hover-strong"
              >
                {dialogResult ? "关闭" : "取消"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
