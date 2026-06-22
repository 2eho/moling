"use client";

import { useState } from "react";
import { useWritingStore, type AgentStatus } from "@/stores/useWritingStore";
import { cn } from "@/lib/cn";
import { MOCK_OUTPUTS } from "@/mock/data/agent-outputs";
import {
  Brain,
  GitBranch,
  Users,
  MessageSquare,
  PenTool,
  Globe,
  X,
  Sparkles,
  Activity,
  Clock,
  RefreshCw,
  ChevronDown,
  Settings,
  EyeOff,
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
    (a) => (a.status === "active" || a.status === "thinking") && !disabledAgents.has(a.id)
  ).length;
  const thinkingCount = agents.filter(
    (a) => a.status === "thinking" && !disabledAgents.has(a.id)
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
      className="shrink-0 flex flex-col h-full transition-all duration-300 border-l overflow-hidden border-th-border-subtle bg-th-card"
      style={{ width }}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-th-border-subtle">
        <div className="flex items-center gap-2 min-w-0">
          <Brain size={15} className="shrink-0 text-th-accent-text" />
          <span className="text-[11px] font-semibold tracking-wide uppercase text-th-text-2">
            Agent 调度中心
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setShowSettings((v) => !v)}
            className={`p-1 rounded transition-colors hover:opacity-80 ${showSettings ? "text-th-accent-text" : "text-th-text-3"}`}
            aria-label="Agent 设置"
          >
            <Settings size={13} />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 rounded transition-colors hover:opacity-80 text-th-text-3"
              aria-label="关闭右栏"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {/* 全局状态卡 */}
        <div className="rounded-lg p-3 bg-th-accent-dim border border-th-accent-dim">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles size={11} className="text-th-accent-text" />
              <span className="text-[10px] font-medium text-th-accent-text">
                {isGenerating ? "协作进行中" : activeCount > 0 ? "Agent 就绪" : "已暂停"}
              </span>
            </div>
            <span className="text-[9px] font-medium tabular-nums text-th-accent-text">
              {activeCount} / {visibleAgents.length}
            </span>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full overflow-hidden bg-th-hover">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: visibleAgents.length > 0 ? `${(activeCount / visibleAgents.length) * 100}%` : "0%",
                  background: "linear-gradient(90deg, var(--th-logo-from), var(--th-logo-to))",
                }}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 mt-2 text-[9px] text-th-success">
            <span className="flex items-center gap-1">
              <Activity size={9} />
              活跃 {activeCount - thinkingCount}
            </span>
            <span className="flex items-center gap-1 text-th-warning">
              <Clock size={9} />
              思考 {thinkingCount}
            </span>
          </div>
        </div>

        {/* 设置面板 */}
        {showSettings && (
          <div className="rounded-lg p-3 bg-th-bg border border-th-border-subtle">
            <div className="text-[9px] font-semibold tracking-wider uppercase mb-2 text-th-text-4">
              代理开关
            </div>
            {agents.map((agent) => {
              const isDisabled = disabledAgents.has(agent.id);
              return (
                <div key={agent.id} className="flex items-center justify-between py-1">
                  <span className={`text-[10px] ${isDisabled ? "text-th-text-4" : "text-th-text-2"}`}>
                    {agent.label}
                  </span>
                  <button
                    onClick={() => toggleAgent(agent.id)}
                    className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${isDisabled ? "bg-th-hover text-th-text-4" : "bg-th-accent-dim text-th-accent-text"}`}
                  >
                    {isDisabled ? "已关闭" : "开启"}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Agent 成员标题 */}
        <div className="text-[9px] font-semibold tracking-wider uppercase px-1 mt-1 flex items-center justify-between text-th-text-4">
          <span>代理成员</span>
          {disabledAgents.size > 0 && (
            <span className="font-normal lowercase text-th-text-4">
              {visibleAgents.length}/{agents.length} 活跃
            </span>
          )}
        </div>

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

        {/* 生成脉冲条 */}
        {isGenerating && (
          <div className="rounded-lg p-3 mt-1 border border-th-accent-dim bg-th-bg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-th-accent-text animate-pulse-dot" />
              <span className="text-[10px] font-medium text-th-accent-text">
                Agent 协作中...
              </span>
            </div>
          </div>
        )}

        {/* 提示 */}
        <div className="rounded-lg p-2.5 mt-1 bg-th-bg">
          <p className="text-[9px] leading-relaxed text-th-text-4">
            点击卡片展开分析报告 · ⟳ 重跑当前 Agent
            <br />
            齿轮 ⚙ 管理 Agent 开关
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
  agent: AgentStatus;
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

  const statusGlow = !isDisabled && agent.status === "active"
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

  const cardClassName = cn(
    "rounded-lg transition-all duration-200 overflow-hidden",
    isDisabled
      ? "bg-th-bg opacity-40"
      : agent.status === "active"
        ? "bg-th-hover"
        : agent.status === "thinking"
          ? "bg-th-hover"
          : "bg-th-bg",
  );

  const cardBoxShadow =
    agent.status === "active" && !isDisabled
      ? "0 0 0 1px var(--th-success) inset"
      : agent.status === "thinking" && !isDisabled
        ? "0 0 0 1px var(--th-warning) inset"
        : undefined;

  const outputs = MOCK_OUTPUTS[agent.id] ?? [];
  const borderColorVar = `var(--${meta.color.replace("text-th-", "th-")})`;

  return (
    <div
      className={cardClassName}
      style={cardBoxShadow ? { boxShadow: cardBoxShadow } : undefined}
    >
      {/* 折叠头部 — 始终可见 */}
      <button
        onClick={onToggleExpand}
        disabled={isDisabled}
        className="w-full flex items-center gap-2 p-2.5 text-left transition-colors hover:opacity-80"
        style={{ cursor: isDisabled ? "default" : "pointer" }}
      >
        <div className={`shrink-0 ${isDisabled ? "text-th-text-4" : meta.color}`}>
          {meta.icon}
        </div>
        <span
          className={`text-[10px] font-medium flex-1 truncate ${isDisabled ? "text-th-text-4" : "text-th-text-2"}`}
        >
          {agent.label}
        </span>
        <div className="flex items-center gap-1.5">
          {!isDisabled && (
            <span
              className={`text-[8px] font-medium ${
                agent.status === "active" ? "text-th-success" :
                agent.status === "thinking" ? "text-th-warning" : ""
              }`}
            >
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
        </div>
      </button>

      {/* 展开详情 */}
      {isExpanded && !isDisabled && (
        <div className="px-3 pb-3 flex flex-col gap-2">
          {/* 角色描述 */}
          <p className="text-[9px] leading-relaxed text-th-text-3">
            {meta.role} · {meta.description}
          </p>

          {/* 分析输出 */}
          {outputs.length > 0 && (
            <div
              className="rounded p-2.5 flex flex-col gap-1.5 bg-th-card"
              style={{ borderLeft: `2px solid ${borderColorVar}` }}
            >
              {outputs.map((line, i) => (
                <p
                  key={i}
                  className="text-[9px] leading-relaxed text-th-text-2"
                >
                  {line}
                </p>
              ))}
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex items-center justify-between">
            <span className="text-[8px] text-th-text-4">
              {agent.name}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRerun();
              }}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-medium transition-colors hover:opacity-80 bg-th-hover text-th-text-3"
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
