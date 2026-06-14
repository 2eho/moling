/* ============================================
   墨灵 (Moling) — Mock System Health
   ============================================ */

import type { SystemHealthStatus } from "@/lib/types";

/** 默认系统健康状态 — 无异常 */
export const mockSystemHealthy: SystemHealthStatus = {
  level: "R3",
  title: "系统正常",
  message: "所有服务运行正常",
  timestamp: new Date().toISOString(),
  dismissable: false,
};

/** 系统降级状态 — 功能受限 */
export const mockSystemDegraded: SystemHealthStatus = {
  level: "R2",
  title: "服务降级",
  message: "部分 LLM API Key 即将过期，部分功能可能受限",
  details: [
    "GPT-4 API Key (key-****-abcd) 将于 3 天后过期",
    "Claude API Key (key-****-efgh) 将于 7 天后过期",
  ],
  timestamp: new Date().toISOString(),
  dismissable: true,
};

/** 系统严重状态 — 服务不可用 */
export const mockSystemCritical: SystemHealthStatus = {
  level: "R1",
  title: "系统异常",
  message: "LLM API Key 全部失效，AI 生成功能不可用",
  details: [
    "GPT-4 API Key (key-****-abcd) 已过期",
    "Claude API Key (key-****-efgh) 已过期",
    "Gemini API Key (key-****-ijkl) 已过期",
  ],
  timestamp: new Date().toISOString(),
  dismissable: false,
};
