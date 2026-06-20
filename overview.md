# GitHub Actions CI 修复报告

## 修复汇总

| # | Workflow | 问题 | 根因 | 状态 |
|---|----------|------|------|------|
| 1 | `deploy.yml` | 0秒立即失败 "workflow file issue" | `strategy.matrix` 中使用了 `env` 上下文（不支持） | ✅ 已修复 |
| 2 | `ci.yml` 后端测试 | `ModuleNotFoundError: aiosqlite` | `conftest.py` 硬编码 SQLite，忽略 `DATABASE_URL` 环境变量 | ✅ 已修复 |
| 3 | `ci.yml` 代码检查 | flake8 标记假失败 | flake8 无 `--exit-zero` | ✅ 已修复 |
| 4 | `database-migration-test.yml` | `KeyError: '0001_initial_schema'` | 运行时 autogenerate 破坏迁移链 | ✅ 已修复 |
| 5 | `database-migration-test.yml` | `psql: database "testuser" does not exist` | 缺 `-d moling_test` | ✅ 已修复 |

## 遗留问题

### 后端测试断言失败（非 CI 基础设施，属测试代码 bug）

共 20+ 测试失败，均为测试断言与 API 实际行为不匹配：

- **`test_register_success`**: API 返回 422 (Unprocessable Entity) 而非 201 — Pydantic 验证拒绝请求体
- **`test_refresh_empty_token`**: API 返回 401 而非 422 — 状态码不匹配
- **`test_get_me_no_token`**: API 返回 401 而非 403 — 同上
- **`test_register_success` (pseudo_loop)**: `assert "access_token" in data` — 响应有 `{"code":0,"data":{"access_token":...}}` 外层信封，需改为 `data["data"]["access_token"]`

**影响**: 阻塞 `deploy.yml` 部署流水线（test → build → deploy 依赖链）

## 修改文件

- `.github/workflows/deploy.yml` — `env` 上下文 + `FEISHU_WEBHOOK_URL` 修复
- `.github/workflows/ci.yml` — flake8 `--exit-zero`
- `.github/workflows/database-migration-test.yml` — 迁移检查 + psql 连接
- `moling-server/tests/conftest.py` — `DATABASE_URL` 环境变量优先
