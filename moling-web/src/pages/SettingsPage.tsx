import { Link } from "react-router-dom";
import { ArrowLeft, User, Shield, Bell, Cpu, Info } from "lucide-react";
import { ThemeSwitcher } from "@/components/vibe/ThemeSwitcher";

const SETTING_ITEMS = [
  { icon: <Shield size={16} />, label: "修改密码", desc: "更新登录密码", href: "#", disabled: true },
  { icon: <Bell size={16} />, label: "通知设置", desc: "管理消息通知偏好", href: "#", disabled: true },
  { icon: <Cpu size={16} />, label: "LLM 配置", desc: "模型选择与 API Key 管理", href: "#", disabled: true },
  { icon: <Info size={16} />, label: "关于墨灵", desc: "v0.1.0 · Phase 4 四库系统", href: "#", disabled: true },
] as const;

export function SettingsPage() {
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--th-bg)", color: "var(--th-text)" }}
    >
      <header className="flex items-center gap-3 px-6 py-4">
        <Link to="/projects" style={{ color: "var(--th-text-3)" }}>
          <ArrowLeft size={20} />
        </Link>
        <span className="text-base font-bold">设置</span>
      </header>

      <main className="flex-1 max-w-lg mx-auto w-full px-6 py-6 space-y-6">
        <div
          className="rounded-xl p-5"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
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

        <div
          className="rounded-xl overflow-hidden"
          style={{
            background: "var(--th-card)",
            border: "1px solid var(--th-border-subtle)",
          }}
        >
          {SETTING_ITEMS.map((item, i) => (
            <Link
              key={item.label}
              to={item.disabled ? "#" : item.href}
              className={`flex items-center gap-3 px-4 py-3.5 transition-colors hover:bg-[var(--th-hover)] ${
                item.disabled ? "opacity-50 cursor-default" : ""
              }`}
              style={{
                color: "var(--th-text-2)",
                borderBottom:
                  i < SETTING_ITEMS.length - 1
                    ? "1px solid var(--th-border-subtle)"
                    : "none",
              }}
              onClick={(e) => {
                if (item.disabled) e.preventDefault();
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
              {item.disabled && (
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded"
                  style={{ background: "var(--th-hover)", color: "var(--th-text-4)" }}
                >
                  即将推出
                </span>
              )}
            </Link>
          ))}
        </div>

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
      </main>
    </div>
  );
}
