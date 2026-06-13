# 墨灵 (Moling) 补充集成测试报告

**生成时间**: 2026-06-14 05:03:27

## 摘要

| 指标 | 数值 |
|------|------|
| 总测试场景数 | 2 |
| 通过 | 1 |
| 失败 | 1 |

## 测试场景结果

### ❌ 失败 — complete_user_flow (成功率: 0.0%)

- ❌ **register**: HTTP 400: {"detail":"greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)"}

### ✅ 通过 — token_invalidation (成功率: 100.0%)

- ✅ **invalid_token**: HTTP 401
- ✅ **no_token**: HTTP 401

## 测试环境信息

- 后端 URL: http://localhost:8000
- API 前缀: /api/v1
- 测试用户: integration_flow@example.com
