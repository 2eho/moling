# 墨灵全功能交互审计报告（已修复版）

> 审计时间: 2026-06-17 | 修复时间: 2026-06-17
> 方法: 6 Agent 并行探索 → 5 Agent 并行修复 → 15个文件改动

---

## P0 — 已修复（6个会崩的）

| # | 问题 | 修复方式 | 文件 |
|---|------|---------|------|
| 1 | Cancel job 路径错 | 前端 `/generate/{id}/cancel` → `/generate/jobs/{id}/cancel` | `api.ts` |
| 2 | 抽卡参数被丢 | DrawCardReq 加 `chapter_id`, `draw_count` | `schemas/card.py` |
| 3 | Import 永远400 | 后端同时支持 JSON body + Query | `ingest/router.py` |
| 4 | Payment-history 缺失 | 后端新增 `GET /subscriptions/payment-history` | `subscription.py` |
| 5 | Admin updateUser 缺失 | 后端新增 `PATCH /admin/users/{userId}` | `admin.py` |
| 6 | Admin llm-usage 缺失 | 后端新增 `GET /admin/llm-usage` | `admin.py` |

## P1 — 已修复（8个数据错的）

| # | 问题 | 修复方式 | 文件 |
|---|------|---------|------|
| 7 | `keep_card_ids` 类型 | `list[int]` → `list[str]` | `schemas/card.py` |
| 8 | `creativity`/`word_count` 缺 | GenerateReq 补上两个字段 | `schemas/generation.py` |
| 9 | `card_ids` 类型 | `list[int]` → `list[str]` | `schemas/generation.py` |
| 10 | HealthMonitor 字段全不同 | schema 改为 `r1_enabled/r2_enabled/r3_enabled/anti_fatigue` | `schemas/setting.py`, `setting.py` |
| 11 | Notif `unread_only` 不识别 | 后端加兼容参数映射 `unread_only→is_read` | `notification.py` |
| 12 | Notif read-all 返回值 | 返回加 `updated` 字段 | `notification_service.py` |
| 13 | Notif `message` vs `content` | types.ts 加 `content?`, NotificationResp 加 `message` 自动填充 | `types.ts`, `schemas/notification.py`, `NotificationItem.tsx` |
| 14 | Progress `int` vs 对象 | jobs_store 改为 `{"percent": 0, "stage": "..."}` | `jobs_store.py`, `generation/router.py` |

## 改动统计

| 类别 | 文件数 | 新增行 | 删除行 |
|:----|:-----:|:-----:|:-----:|
| 后端 | 12 | ~200 | ~30 |
| 前端 | 3 | ~15 | ~5 |
| **合计** | **15** | **~215** | **~35** |
