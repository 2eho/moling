"use client";

import { Library, Package, Settings } from "lucide-react";

interface SidebarFooterProps {
  onSettings?: () => void;
}

function FooterMenuItem({
  icon: Icon,
  label,
  badge,
  disabled,
}: {
  icon: typeof Library;
  label: string;
  badge: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs text-th-text-2 hover:bg-th-hover transition-colors disabled:cursor-default disabled:hover:bg-transparent"
      title={disabled ? "功能开发中" : undefined}
    >
      <Icon size={14} className="text-th-text-3 shrink-0" />
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className="shrink-0 text-[9px] px-1.5 py-0.5 rounded font-medium bg-th-hover text-th-text-4">
          {badge}
        </span>
      )}
    </button>
  );
}

export function SidebarFooter({ onSettings }: SidebarFooterProps) {
  return (
    <div className="shrink-0 mt-auto px-3 pb-3 relative z-10">
      {/* 功能组：知识中心 + 插件市场 */}
      <div className="border-t border-th-border-subtle pt-2 space-y-0.5">
        <FooterMenuItem icon={Library} label="知识中心" badge="即将推出" disabled />
        <FooterMenuItem icon={Package} label="插件市场" badge="即将推出" disabled />
      </div>

      {/* 用户组：用户 + 设置 */}
      <div className="flex items-center gap-2 mt-1 pt-2 border-t border-th-border-subtle">
        <button
          type="button"
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg flex-1 min-w-0 hover:bg-th-hover transition-colors"
        >
          <div className="w-5 h-5 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold bg-th-accent-dim text-th-accent-text">
            U
          </div>
          <span className="text-xs truncate text-th-text-2">用户</span>
        </button>
        <button
          type="button"
          onClick={onSettings}
          className="p-1.5 rounded-lg transition-colors text-th-text-3 hover:text-th-text hover:bg-th-hover shrink-0"
          aria-label="设置"
        >
          <Settings size={16} />
        </button>
      </div>
    </div>
  );
}
