# 墨灵前后端 API 映射修复报告 V2

> 修复工程师：API 映射修复工程师
> 修复日期：2026-06-13
> 修复范围：第二轮审计发现的 6 个 FAIL 项和 3 个 PARTIAL 项

---

## 修复总结

| 状态 | 数量 | 说明 |
|:----|:----:|------|
| **已修复** | 9 | 6 个 FAIL 项 + 3 个 PARTIAL 项 |
| **修复失败** | 0 | - |

---

## 详细修复情况

### [VERIFY-015-001] HIGH - 密码重置路径不匹配

- **问题**: 前端 `/auth/reset-password` vs 后端 `/auth/password-reset-request`
- **修复方法**: 修改前端 `api.ts` 中的 `resetPassword()` 路径为 `/auth/password-reset-request`（方案A，与文档一致）
- **修改文件**: `moling-web/src/lib/api.ts`
- **验证结果**: 
  - 前端路径: `POST /auth/password-reset-request` ✓
  - 后端路径: `POST /api/v1/auth/password-reset-request` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-002] MEDIUM - Settings health-monitor GET 端点缺失

- **问题**: 后端缺少 `GET /settings/health-monitor` 端点
- **修复方法**: 在 `setting.py` 中添加 `GET /health-monitor` 端点
- **修改文件**: `moling-server/app/router/setting.py`
- **验证结果**: 
  - 前端: `GET /settings/health-monitor` ✓
  - 后端: `GET /api/v1/settings/health-monitor` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-003] MEDIUM - Settings phase4-review GET 端点缺失

- **问题**: 后端缺少 `GET /settings/phase4-review` 端点
- **修复方法**: 在 `setting.py` 中添加 `GET /phase4-review` 端点
- **修改文件**: `moling-server/app/router/setting.py`
- **验证结果**: 
  - 前端: `GET /settings/phase4-review` ✓
  - 后端: `GET /api/v1/settings/phase4-review` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-004] LOW - Secrets getByCharacter 路径参数不匹配

- **问题**: 前端用 `characterId`，后端用 `character name`
- **修复方法**: 统一用 `character_id`（ID），修改后端 `secret.py` 路径参数为 `{character_id}`，并修改 `secret_service.py` 根据 `character_id` 获取角色名称
- **修改文件**: 
  - `moling-server/app/router/secret.py`
  - `moling-server/app/service/secret_service.py`
- **验证结果**: 
  - 前端: `GET /projects/${projectId}/secrets/character/${characterId}` ✓
  - 后端: `GET /api/v1/projects/{project_id}/secrets/character/{character_id}` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-005] LOW - Secrets update HTTP 方法和路径不匹配

- **问题**: 前端用 PUT，后端用 PATCH；前端用 `characterId`，后端用 `secret_id`
- **修复方法**: 修改后端 `secret.py` 为 `PUT /character/{character_id}`，并添加相应的 service 函数
- **修改文件**: 
  - `moling-server/app/router/secret.py`
  - `moling-server/app/service/secret_service.py`
  - `moling-server/app/schemas/secret.py`
- **验证结果**: 
  - 前端: `PUT /projects/${projectId}/secrets/character/${characterId}` ✓
  - 后端: `PUT /api/v1/projects/{project_id}/secrets/character/{character_id}` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-015] LOW - Weave API 路径不匹配

- **问题**: 前端 `/weave/patterns`，后端 `/weave-patterns`
- **修复方法**: 修改后端 `router/__init__.py` 挂载前缀为 `/weave/patterns`（与前端一致）
- **修改文件**: `moling-server/app/router/__init__.py`
- **验证结果**: 
  - 前端: `GET /weave/patterns` ✓
  - 后端: `GET /api/v1/weave/patterns` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-014] PARTIAL - Templates API 后端缺少端点

- **问题**: 后端缺少 `GET /{id}`、`POST /`、`DELETE /{id}` 端点
- **修复方法**: 在 `template.py` 中补充缺少的端点
- **修改文件**: 
  - `moling-server/app/router/template.py`
  - `moling-server/app/schemas/template.py`
- **验证结果**: 
  - 前端: `GET /templates/${templateId}` ✓
  - 前端: `POST /templates` ✓
  - 前端: `DELETE /templates/${templateId}` ✓
  - 后端: 已实现相应端点 ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-016] PARTIAL - Admin API HTTP 方法不匹配

- **问题**: 前端用 PUT，后端用 PATCH
- **修复方法**: 修改后端 `admin.py` 为 `PUT /users/{user_id}`（与前端一致）
- **修改文件**: `moling-server/app/router/admin.py`
- **验证结果**: 
  - 前端: `PUT /admin/users/${userId}` ✓
  - 后端: `PUT /api/v1/admin/users/{user_id}` ✓
  - **前后端已对齐** ✓

---

### [VERIFY-015-017] PARTIAL - Phase4 API 后端缺少端点

- **问题**: 后端缺少 `approve` 和 `reject` 端点
- **修复方法**: 在 `phase4.py` 中补充 `POST /reviews/{id}/approve`、`POST /reviews/{id}/reject` 端点
- **修改文件**: `moling-server/app/router/phase4.py`
- **验证结果**: 
  - 前端: `POST /phase4/reviews/${reviewId}/approve` ✓
  - 前端: `POST /phase4/reviews/${reviewId}/reject` ✓
  - 后端: 已实现相应端点 ✓
  - **前后端已对齐** ✓

---

## 修改的文件列表

### 前端文件
1. `moling-web/src/lib/api.ts` - 修改 `resetPassword()` 路径

### 后端文件
1. `moling-server/app/router/setting.py` - 添加 GET /health-monitor 和 GET /phase4-review 端点
2. `moling-server/app/router/secret.py` - 修改路径参数和 HTTP 方法
3. `moling-server/app/service/secret_service.py` - 修改 `get_secrets_by_character` 和添加 `update_secrets_by_character` 函数
4. `moling-server/app/schemas/secret.py` - 添加 `UpdateSecretsByCharacterReq` 和 `SecretItemUpdate` schema
5. `moling-server/app/router/__init__.py` - 修改 weave 挂载前缀
6. `moling-server/app/router/template.py` - 添加缺少的端点
7. `moling-server/app/schemas/template.py` - 添加 `CreateTemplateReq` 和 `UpdateTemplateReq` schema
8. `moling-server/app/router/admin.py` - 修改 HTTP 方法从 PATCH 到 PUT
9. `moling-server/app/router/phase4.py` - 添加缺少的端点

---

## 验证结果总结

所有 9 个问题均已修复，前后端 API 映射已对齐。

| 问题编号 | 问题类型 | 修复状态 | 验证结果 |
|:---------|:---------|:---------|:---------|
| VERIFY-015-001 | FAIL (HIGH) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-002 | FAIL (MEDIUM) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-003 | FAIL (MEDIUM) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-004 | FAIL (LOW) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-005 | FAIL (LOW) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-015 | FAIL (LOW) | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-014 | PARTIAL | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-016 | PARTIAL | 已修复 | 前后端对齐 ✓ |
| VERIFY-015-017 | PARTIAL | 已修复 | 前后端对齐 ✓ |

---

## 注意事项

1. **Secrets API 修改**: 修改了后端的逻辑，使其根据 `character_id` 获取角色名称，然后查询 secrets。这可能会影响现有的前端调用，需要确保前端传入的是正确的 `characterId`。

2. **Phase4 API 简化实现**: `approve` 和 `reject` 端点的实现是简化的，只更新了 `phase4_status` 字段。可能需要进一步实现拒绝原因的存储逻辑。

3. **Templates API 新增端点**: 添加了模板的创建和删除端点，但需要相应的前端页面来支持这些功能。

---

> **修复完成时间**: 2026-06-13
> **修复工程师**: API 映射修复工程师
> **下次审计重点**: 验证本次修复是否真实有效，确保前后端 API 映射完全对齐
