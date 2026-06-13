/* ============================================
   墨灵 (Moling) — Mock Health Alerts
   ============================================ */

import type { HealthAlert } from "@/lib/types";

export const mockHealthAlerts: HealthAlert[] = [
  {
    id: "1",
    rule: "plot_hole",
    title: "剧情漏洞检测",
    detail: "第3章中，林星辰从练气一层直接击败了三阶妖兽，战力跨度不合理。建议增加修炼突破的情节铺垫。",
    severity: "warning",
    is_active: true,
  },
  {
    id: "2",
    rule: "character_consistency",
    title: "角色一致性提醒",
    detail: "苏月瑶在第2章中表现出对修真一无所知，但在第3章却能认出上古阵法秘纹。请检查角色认知的前后一致性。",
    severity: "info",
    is_active: true,
  },
  {
    id: "3",
    rule: "timeline_conflict",
    title: "时间线冲突",
    detail: `第3章的试炼描述中出现了"月光"，但在第1章的时间设定中当天应为新月。时间描写存在矛盾。`,
    severity: "critical",
    is_active: true,
  },
];
