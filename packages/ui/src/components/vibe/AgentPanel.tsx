"use client";

import { useState } from "react";
import { useWritingStore } from "@/stores/useWritingStore";
import { cn } from "@/lib/cn";
import { MOCK_OUTPUTS } from "@/mock/data/agent-outputs";
import {
  Brain,
  GitBranch,
  Users,
  MessageSquare,
  PenTool,
  Globe,
  Sparkles,
  RefreshCw,
  ChevronDown,
  Settings,
} from "lucide-react";

const AGENT_META: Record<
  string,
  { icon: React.ReactNode; role: string; color: string; description: string }
> = {
  plot: {
    icon: <GitBranch size={14} />,
    role: "叙事架构师",
    color: "text-th-accent-text",
    description: "故事结构设计、冲突管理与节奏编排、情节分支规划",
  },
  character: {
    icon: <Users size={14} />,
    role: "人物设计师",
    color: "text-th-success",
    description: "角色弧光追踪、关系网络维护、言行一致性校验",
  },
  dialogue: {
    icon: <MessageSquare size={14} />,
    role: "对话导演",
    color: "text-th-warning",
    description: "台词风格把控、语气语调适配、潜台词分析",
  },
  style: {
    icon: <PenTool size={14} />,
    role: "风格顾问",
    color: "text-th-accent",
    description: "文风统一检测、修辞手法建议、叙事视角检查",
  },
  world: {
    icon: <Globe size={14} />,
    role: "世界构建师",
    color: "text-th-logo-to",
    description: "世界观一致性校验、设定细节管理、力量体系逻辑",
  },
};

interface AgentPanelProps {
  onClose?: () => void;
  width?: number;
}

export function AgentPanel({ onClose, width = 260 }: AgentPanelProps) {
  const agents = useWritingStore((s) => s.agents);
  const isGenerating = useWritingStore((s) => s.isGenerating);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [disabledAgents, setDisabledAgents] = useState<Set<string>>(new Set());
  const [showSettings, setShowSettings] = useState(false);

  const visibleAgents = agents.filter((a) => !disabledAgents.has(a.id));
  const activeCount = agents.filter(
    (a) => (a.status === "active" || a.status === "thinking") && !disabledAgents.has(a.id),
  ).length;

  const toggleAgent = (id: string) => {
    setDisabledAgents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const rerunAgent = (_id: string) => {
    // 对接真实 API 后触发单个 Agent 重跑
  };

  return (
    <aside
      className="shrink-0 flex flex-col h-full border-l overflow-hidden border-th-border-subtle bg-th-card relative"
      style={{ width }}
    >
      {/* 5% 灰度遮罩 — 与左栏一致 */}
      <div className="absolute inset-0 bg-black/5 pointer-events-none" />

      {/* ── Header ── */}
      <div className="relative shrink-0 flex items-center justify-between px-3 py-3 border-b border-th-border-subtle z-10">
        <div className="flex items-center gap-2 min-w-0">
          <Brain size={15} className="shrink-0 text-th-accent-text" />
          <span className="text-[13px] font-semibold text-th-text-2">
            Agent 调度中心
          </span>
          {activeCount > 0 && (
            <span className="text-[10px] font-medium text-th-text-4 tabular-nums ml-1">
              {activeCount}/{visibleAgents.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setShowSettings((v) => !v)}
            className={`p-1 rounded transition-colors ${showSettings ? "text-th-accent-text bg-th-accent-dim" : "text-th-text-3 hover:bg-th-hover"}`}
            aria-label="Agent 设置"
          >
            <Settings size={13} />
          </button>
        </div>
      </div>
      <div className="relative flex-1 overflow-y-auto px-2 py-1.5 flex flex-col gap-0.5 z-10">
        {/* 全局状态条 */}
        <div className="flex items-center gap-2 px-2.5 py-2">
          <Sparkles size={11} className="text-th-accent-text shrink-0" />
          <span className="text-[10px] text-th-text-3 flex-1">
            {isGenerating ? "Agent 协作中..." : activeCount > 0 ? "Agent 就绪" : "已暂停"}
          </span>
          {isGenerating && (
            <div className="w-1.5 h-1.5 rounded-full bg-th-accent-text animate-pulse-dot shrink-0" />
          )}
        </div>

        {/* 设置面板 — 折叠区域 */}
        {showSettings && (
          <div className="mx-1 rounded-lg p-3 bg-th-bg border border-th-border-subtle">
            <div className="text-[10px] font-semibold text-th-text-4 mb-2">
              代理开关
            </div>
            {agents.map((agent) => {
              const isDisabled = disabledAgents.has(agent.id);
              return (
                <div key={agent.id} className="flex items-center justify-between py-1">
                  <span className={`text-[11px] ${isDisabled ? "text-th-text-4" : "text-th-text-2"}`}>
                    {agent.label}
                  </span>
                  <button
                    onClick={() => toggleAgent(agent.id)}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${isDisabled ? "bg-th-hover text-th-text-4" : "bg-th-accent-dim text-th-accent-text"}`}
                  >
                    {isDisabled ? "已关闭" : "开启"}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Agent 列表标题 */}
        <div className="px-2.5 pt-2 pb-1">
          <span className="text-[10px] font-semibold tracking-wider uppercase text-th-text-4">
            代理成员
          </span>
        </div>

        {/* Agent 卡片 */}
        {agents.map((agent) => (
          <AgentItem
            key={agent.id}
            agent={agent}
            isDisabled={disabledAgents.has(agent.id)}
            isExpanded={expandedAgent === agent.id}
            onToggleExpand={() =>
              setExpandedAgent(expandedAgent === agent.id ? null : agent.id)
            }
            onRerun={() => rerunAgent(agent.id)}
          />
        ))}

        {/* 底部提示 */}
        <div className="mt-auto pt-3">
          <p className="text-[9px] leading-relaxed text-th-text-4 px-2.5">
            点击卡片展开分析报告 · ⟳ 重跑
          </p>
        </div>
      </div>
    </aside>
  );
}

function AgentItem({
  agent,
  isDisabled,
  isExpanded,
  onToggleExpand,
  onRerun,
}: {
  agent: { id: string; label: string; name: string; status: string };
  isDisabled: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onRerun: () => void;
}) {
  const meta = AGENT_META[agent.id] ?? {
    icon: <Brain size={14} />,
    role: "代理",
    color: "text-th-text-2",
    description: "",
  };

  const statusDotBg = isDisabled
    ? "bg-th-text-4"
    : agent.status === "active"
      ? "bg-th-success"
      : agent.status === "thinking"
        ? "bg-th-warning"
        : "bg-th-text-4";

  const statusGlow =
    !isDisabled && agent.status === "active"
      ? "0 0 6px var(--th-success)"
      : !isDisabled && agent.status === "thinking"
        ? "0 0 6px var(--th-warning)"
        : undefined;

  const statusLabel =
    agent.status === "active"
      ? "活跃"
      : agent.status === "thinking"
        ? "思考中"
        : isDisabled
          ? "已关闭"
          : "待命";

  const isActive = agent.status === "active" || agent.status === "thinking";

  const outputs = MOCK_OUTPUTS[agent.id] ?? [];
  const borderColorVar = `var(--${meta.color.replace("text-th-", "th-")})`;

  return (
    <div>
      {/* Agent row — 参考 ChapterItem 风格 */}
      <button
        onClick={onToggleExpand}
        disabled={isDisabled}
        className="w-full flex items-center text-left rounded-lg transition-colors disabled:cursor-not-allowed border-l-[3px] border-transparent relative"
        style={{
          color: isDisabled
            ? "var(--th-text-4)"
            : isActive
              ? "var(--th-accent-text)"
              : "var(--th-text-2)",
          background: isActive ? "var(--th-accent-dim)" : "transparent",
          opacity: isDisabled ? 0.5 : 1,
          borderRadius: 8,
          cursor: isDisabled ? "default" : "pointer",
        }}
      >
        {/* Active pill */}
        {isActive && (
          <div
            className="absolute left-0.5 top-1.5 bottom-1.5 w-[5px] z-10"
            style={{ background: "var(--th-accent-text)", borderRadius: 9999 }}
          />
        )}

        {/* 左侧间距 */}
        <span className="inline-block w-[5px] shrink-0 overflow-hidden">&nbsp;</span>

        {/* 图标 */}
        <span className={`shrink-0 ${isDisabled ? "text-th-text-4" : meta.color}`}>
          {meta.icon}
        </span>

        {/* 标签 */}
        <span className="flex-1 truncate text-[13px] py-2.5 md:py-2 leading-snug pl-2">
          {agent.label}
        </span>

        {/* 状态指示 */}
        <span className="flex items-center gap-1.5 shrink-0 mr-[8px]">
          {!isDisabled && (
            <span className="text-[10px] text-th-text-4">
              {statusLabel}
            </span>
          )}
          <div
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${agent.status === "thinking" && !isDisabled ? "animate-pulse" : ""} ${statusDotBg}`}
            style={statusGlow ? { boxShadow: statusGlow } : undefined}
          />
          <ChevronDown
            size={10}
            className="text-th-text-4 transition-transform duration-200"
            style={{ transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)" }}
          />
        </span>
      </button>

      {/* 展开详情 */}
      {isExpanded && !isDisabled && (
        <div className="px-3 pb-3 flex flex-col gap-2" style={{ marginLeft: 20 }}>
          {/* 角色描述 */}
          <p className="text-[11px] leading-relaxed text-th-text-3 mt-1">
            {meta.role} · {meta.description}
          </p>

          {/* 分析输出 */}
          {outputs.length > 0 && (
            <div
              className="rounded-lg p-2.5 flex flex-col gap-1.5 bg-th-card"
              style={{ borderLeft: `2px solid ${borderColorVar}` }}
            >
              {outputs.map((line, i) => (
                <p key={i} className="text-[11px] leading-relaxed text-th-text-2">
                  {line}
                </p>
              ))}
            </div>
          )}

          {/* 操作 */}
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-th-text-4">{agent.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRerun();
              }}
              className="flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-medium transition-colors hover:opacity-80 bg-th-hover text-th-text-3"
            >
              <RefreshCw size={9} />
              重跑
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
