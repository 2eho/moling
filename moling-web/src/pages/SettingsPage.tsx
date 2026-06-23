import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  User,
  Shield,
  Bell,
  Cpu,
  Info,
  Eye,
  EyeOff,
  RotateCcw,
  CheckCircle,
  ChevronDown,
  Zap,
  Wifi,
  Loader,
  XCircle,
  X,
} from "lucide-react";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";
import { useLLMSettings, LLM_MODELS, type LLMModelId } from "@/stores/useLLMSettings";
import { useToast } from "@/stores/useToast";

export function SettingsPage() {
  const { addToast } = useToast();
  const llm = useLLMSettings();
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);

  // ── Test connection dialog state ──
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogResult, setDialogResult] = useState<{
    ok: boolean;
    message: string;
  } | null>(null);

  const [saved, setSaved] = useState(false);

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
    } catch (e) {
      setDialogResult({ ok: false, message: "网络错误：无法连接到 API 地址" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      {/* ── Header ── */}
      <header className="flex items-center gap-3 px-6 py-4">
        <Link to="/projects" style={{ color: "var(--th-text-3)" }}>
          <ArrowLeft size={20} />
        </Link>
        <span className="text-base font-bold">设置</span>
        <div className="flex-1" />
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-6 space-y-6">
        {/* ── Profile card ── */}
        <div
          className="rounded-xl p-5"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
              style={{ background: "var(--th-accent-dim)" }}
            >
              <User size={20} style={{ color: "var(--th-accent-text)" }} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">用户</p>
              <p className="text-xs truncate" style={{ color: "var(--th-text-3)" }}>
                admin@moling.dev
              </p>
            </div>
          </div>
        </div>

        {/* ── LLM 配置 ── */}
        <div
          className="rounded-xl p-5 space-y-5"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          {/* Section header */}
          <div className="flex items-center gap-2">
            <Cpu size={15} style={{ color: "var(--th-accent-text)" }} />
            <span className="text-sm font-semibold" style={{ color: "var(--th-text-2)" }}>
              LLM 配置
            </span>
          </div>

          <div className="space-y-4">
            {/* API Key */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: "var(--th-text-3)" }}>
                API Key
              </label>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={llm.apiKey}
                  onChange={(e) => llm.setApiKey(e.target.value)}
                  placeholder="申请地址: platform.deepseek.com/api_keys"
                  className="w-full pr-10 rounded-lg px-3 py-2 text-sm outline-none transition-all"
                  style={{
                    background: "var(--th-input-bg, var(--th-bg))",
                    color: "var(--th-text)",
                    border: "1px solid var(--th-border-subtle)",
                  }}
                />
                <button
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2"
                  style={{ color: "var(--th-text-4)" }}
                  aria-label={showKey ? "隐藏" : "显示"}
                >
                  {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <p className="text-[11px]" style={{ color: "var(--th-text-4)" }}>
                密钥仅存储于本地浏览器，不会上传到服务器
              </p>
            </div>

            {/* Base URL */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: "var(--th-text-3)" }}>
                API 地址
              </label>
              <input
                type="text"
                value={llm.baseUrl}
                onChange={(e) => llm.setBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com"
                className="w-full rounded-lg px-3 py-2 text-sm outline-none transition-all"
                style={{
                  background: "var(--th-input-bg, var(--th-bg))",
                  color: "var(--th-text)",
                  border: "1px solid var(--th-border-subtle)",
                }}
              />
            </div>

            {/* Model */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: "var(--th-text-3)" }}>
                模型
              </label>
              <div className="relative">
                <select
                  value={llm.model}
                  onChange={(e) => llm.setModel(e.target.value as LLMModelId)}
                  className="w-full rounded-lg px-3 py-2 text-sm outline-none appearance-none cursor-pointer transition-all"
                  style={{
                    background: "var(--th-input-bg, var(--th-bg))",
                    color: "var(--th-text)",
                    border: "1px solid var(--th-border-subtle)",
                  }}
                >
                  {LLM_MODELS.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ))}
                </select>
                <ChevronDown
                  size={14}
                  className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  style={{ color: "var(--th-text-4)" }}
                />
              </div>
              <p className="text-[11px]" style={{ color: "var(--th-text-4)" }}>
                {LLM_MODELS.find((m) => m.id === llm.model)?.desc}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleTestConnection}
              disabled={testing || !llm.apiKey}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                color: "var(--th-accent-text)",
                background: "var(--th-accent-dim)",
              }}
            >
              {testing ? <Loader size={13} className="animate-spin" /> : <Wifi size={13} />}
              测试连接
            </button>
            <div className="flex-1" />
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
              style={{
                color: "var(--th-text-4)",
                background: "var(--th-hover)",
              }}
            >
              <RotateCcw size={13} />
              恢复默认
            </button>
            <button
              onClick={handleSave}
              disabled={saved}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all active:scale-95 disabled:opacity-60"
              style={{
                background: saved ? "var(--th-success)" : "var(--th-accent)",
                color: "#fff",
              }}
            >
              {saved ? <CheckCircle size={13} /> : <Zap size={13} />}
              {saved ? "已保存" : "保存配置"}
            </button>
          </div>
        </div>

        {/* ── Theme switcher ── */}
        <div
          className="rounded-xl p-4"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          <p className="text-xs font-semibold mb-3" style={{ color: "var(--th-text-2)" }}>
            主题外观
          </p>
          <ThemeSwitcher />
        </div>

        {/* ── Status items (stub) ── */}
        <div
          className="rounded-xl overflow-hidden"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          {([
            { icon: <Shield size={16} />, label: "修改密码", desc: "更新登录密码 · 即将推出" },
            { icon: <Bell size={16} />, label: "通知设置", desc: "消息通知偏好 · 即将推出" },
            { icon: <Info size={16} />, label: "关于墨灵", desc: "v0.1.0 · Phase 4 四库系统" },
          ] as const).map((item, i) => (
            <div
              key={item.label}
              className="flex items-center gap-3 px-4 py-3.5 opacity-50"
              style={{
                color: "var(--th-text-2)",
                borderBottom:
                  i < 2 ? "1px solid var(--th-border-subtle)" : "none",
              }}
            >
              <span className="shrink-0" style={{ color: "var(--th-text-3)" }}>
                {item.icon}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium">{item.label}</span>
                <p className="text-[11px]" style={{ color: "var(--th-text-4)" }}>
                  {item.desc}
                </p>
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
            className="relative z-10 w-[90vw] max-w-sm rounded-xl p-6 shadow-2xl"
            style={{
              background: "var(--th-card)",
              border: "1px solid var(--th-border-subtle)",
              color: "var(--th-text)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-semibold" style={{ color: "var(--th-text-2)" }}>
                连接测试
              </span>
              <button
                onClick={() => setDialogOpen(false)}
                className="p-1 rounded-md hover:bg-[var(--th-hover)]"
                style={{ color: "var(--th-text-4)" }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            {!dialogResult ? (
              <div className="flex flex-col items-center gap-3 py-6">
                <Loader size={28} className="animate-spin" style={{ color: "var(--th-accent-text)" }} />
                <span className="text-xs" style={{ color: "var(--th-text-3)" }}>
                  正在连接 {llm.baseUrl}...
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 py-4">
                {dialogResult.ok ? (
                  <CheckCircle size={28} style={{ color: "var(--th-success)" }} />
                ) : (
                  <XCircle size={28} style={{ color: "var(--th-error, #ef4444)" }} />
                )}
                <div
                  className="text-xs text-center whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto"
                  style={{ color: "var(--th-text-3)" }}
                >
                  {dialogResult.message}
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setDialogOpen(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium transition-colors"
                style={{
                  color: "var(--th-text-2)",
                  background: "var(--th-hover)",
                }}
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
