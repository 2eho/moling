# 🌿 墨灵 Git 工作流指南

> 版本：v1.0 | 最后更新：2026-06-17 | 适用团队：5人（郝交付、贝洛奇、贾思敏、严过关、卜宕机）

---

## 目录

1. [核心理念](#1-核心理念)
2. [分支策略](#2-分支策略)
3. [分支命名规范](#3-分支命名规范)
4. [提交规范](#4-提交规范)
5. [完整工作流](#5-完整工作流)
6. [分支保护规则](#6-分支保护规则)
7. [PR 流程](#7-pr-流程)
8. [CI 配置优化](#8-ci-配置优化)
9. [常用操作用例](#9-常用操作用例)
10. [故障恢复](#10-故障恢复)

---

## 1. 核心理念

```
┌─────────────────────────────────────────────────────┐
│              Git 工作流铁律                          │
├─────────────────────────────────────────────────────┤
│  • main 永远是可部署的                                │
│  • 每个提交原子化（一个提交一件事）                     │
│  • feature 分支存活不超过 2 天                         │
│  • 合入 main 前必须通过 CI                            │
│  • 绝不直接推送 main                                  │
│  • 绝不 force-push 共享分支（用 --force-with-lease）    │
└─────────────────────────────────────────────────────┘
```

---

## 2. 分支策略

### 方案：Trunk-Based Development（推荐）

对于 5 人团队 + 持续部署需求，**Trunk-Based Development** 是最优解。它比 Git Flow 简单，比 GitHub Flow 多了 develop 缓冲。

```
main ─────●─────────────●─────────────●──── (生产，永远可部署)
           \            /             /
            ●─────────●─────────────●─── (develop，集成分支)
             \        /      \      /
              ●──────●       ●────●── (feat/xxx, 短命特性分支)
```

### 分支角色

| 分支 | 生命周期 | 谁可以推 | 保护级别 |
|------|----------|----------|----------|
| `main` | 永久 | ❌ 任何人（仅通过 PR merge） | ⭐⭐⭐ 最高 |
| `develop` | 永久 | ❌ 任何人（仅通过 PR merge） | ⭐⭐ 中 |
| `feat/*` | 1-2 天 | 开发者本人 | ⭐ 低 |
| `fix/*` | 1-2 天 | 开发者本人 | ⭐ 低 |
| `chore/*` | 1 天 | 开发者本人 | ⭐ 低 |

### 为什么选 Trunk-Based 而不是 Git Flow？

| 对比维度 | Trunk-Based | Git Flow |
|----------|-------------|----------|
| 复杂度 | 低（2 条永久分支） | 高（5+ 条永久分支） |
| 5 人团队效率 | ✅ 高度匹配 | ❌ 太重 |
| 发布频率 | 任意频率 | 固定版本节奏 |
| merge 冲突 | ✅ 低（短分支及时合并） | ❌ 高（长命分支） |
| CI 负担 | 轻 | 重 |

> **结论**：墨灵目前只有 5 人、每日有持续开发，Trunk-Based 最合适。如果未来发布版本需要隔离，可以在 `main` 上打 tag 代替 release 分支。

---

## 3. 分支命名规范

### 格式

```
<类型>/<简短描述>
```

### 类型

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat/` | 新功能 | `feat/card-drawing-algorithm` |
| `fix/` | Bug 修复 | `fix/login-token-expire` |
| `chore/` | 杂务（依赖、配置、CI） | `chore/upgrade-nextjs-15` |
| `refactor/` | 重构 | `refactor/api-client-cleanup` |
| `docs/` | 文档 | `docs/api-alignment-report` |
| `test/` | 测试 | `test/add-migration-rollback` |
| `style/` | 样式 | `style/unify-button-radius` |

### 好例子 vs 坏例子

| ✅ 好 | ❌ 不好 |
|-------|---------|
| `feat/user-auth` | `feature-branch` |
| `fix/login-redirect` | `fix-bug` |
| `chore/deps-update` | `update-stuff` |
| `refactor/api-client` | `my-branch-2` |

### 分支名原则

- **小写 + 短横线分隔**（kebab-case）
- **控制在 3-5 个词**，太长说明 scope 太大
- **体现具体改动**，而非模糊意图

---

## 4. 提交规范

### 格式

```
<类型>(<范围>): <描述>

<可选：详细说明>

<可选：关闭 issue>
```

### 提交类型

| 类型 | 用途 | 说明 |
|------|------|------|
| `feat` | 新功能 | 对外可见的功能新增 |
| `fix` | 修复 bug | 修复生产/测试环境的 bug |
| `chore` | 杂务 | 依赖升级、CI 配置、构建工具 |
| `refactor` | 重构 | 不改变行为的代码调整 |
| `docs` | 文档 | 仅文档变更 |
| `test` | 测试 | 新增或修改测试 |
| `style` | 样式 | 不影响逻辑的格式调整 |
| `perf` | 性能 | 性能优化 |
| `revert` | 回滚 | 回滚之前的提交 |

### 范围（scope）

建议的 scope 值（与项目结构对齐）：

| scope | 说明 | 对应目录 |
|-------|------|----------|
| `api` | 后端 API 变更 | `moling-server/app/router/` |
| `service` | 后端业务逻辑 | `moling-server/app/service/` |
| `model` | 数据模型 | `moling-server/app/models/` |
| `ingest` | 导入管线 | `moling-web/app/ingest/` |
| `genre` | 拆书管线 | `moling-web/app/genre/` |
| `ui` | 前端 UI | `moling-web/src/components/` |
| `page` | 前端页面 | `moling-web/src/app/` |
| `ci` | CI/CD | `.github/workflows/` |
| `deps` | 依赖 | `package.json`, `requirements.txt` |

### 好例子 vs 坏例子

```
✅ feat(ui): 添加卡牌抽取动画效果
✅ fix(auth): 修复 token 刷新竞态条件
✅ chore(ci): 升级 actions/checkout 到 v4
✅ refactor(service): 提取卡牌组合算法为独立模块
✅ test(ingest): 添加 Phase 0 分章测试用例
✅ docs: 更新 API 对齐报告

❌ update code
❌ fix bug
❌ 修改了一些东西
❌ wip
```

### 原子化提交原则

```
一个提交 = 一个逻辑变更 = 可以独立 revert

✅ 正确做法：
  commit 1: feat(card): 添加卡牌权重计算函数
  commit 2: feat(ui): 卡牌抽取页面集成权重调整滑块
  commit 3: test(card): 添加权重计算单元测试

❌ 错误做法：
  commit 1: "添加卡牌功能和页面和测试"
  （无法单独 revert 某个部分）
```

---

## 5. 完整工作流

### 5.1 开始新功能

```bash
# 1. 同步最新的 develop
git fetch origin
git checkout develop
git pull --rebase origin develop

# 2. 创建特性分支（从 develop 切出）
git checkout -b feat/card-weight-adjustment
```

> **为什么要从 develop 切？** 确保你的特性基于最新集成代码，减少合入时的冲突。

### 5.2 每日开发

```bash
# 每天开始前，同步 develop 的更新到你的分支
git fetch origin
git rebase origin/develop

# 如果冲突了，冷静处理：
# 1. 解决冲突文件
# 2. git add <resolved-file>
# 3. git rebase --continue
```

### 5.3 提交代码

```bash
# 原子化提交
git add src/components/CardWeightSlider.tsx
git commit -m "feat(ui): 添加卡牌权重滑块组件"

# 再次提交
git add src/lib/cardWeight.ts
git commit -m "feat(card): 实现卡牌权重计算逻辑"
```

### 5.4 推送并创建 PR

```bash
# 推送前先 rebase 确保干净
git fetch origin
git rebase origin/develop

# 推送（首次用 -u 建立追踪）
git push -u origin feat/card-weight-adjustment

# 在 GitHub 上创建 Pull Request
# target: develop
```

### 5.5 PR 合入后的清理

```bash
# 回到 develop 删除本地分支
git checkout develop
git pull --rebase
git branch -d feat/card-weight-adjustment

# 远程分支
git push origin --delete feat/card-weight-adjustment
```

### 5.6 发布到生产

```bash
# 在 develop 验证通过后，合入 main
git checkout main
git pull --rebase
git merge --no-ff develop
git push origin main

# 打 tag
git tag v1.2.0
git push origin v1.2.0
```

---

## 6. 分支保护规则

### main 分支保护（GitHub Settings > Branches）

| 规则 | 说明 | 严格程度 |
|------|------|----------|
| ✅ Require pull request before merging | 必须通过 PR 合入 | 强制 |
| ✅ Require approvals (至少 1 人) | 至少 1 人 Code Review | 推荐 |
| ✅ Dismiss stale reviews | 新提交后旧 review 自动失效 | 推荐 |
| ✅ Require status checks | CI 必须全部通过 | 强制 |
| ✅ Require branches to be up to date | 合入前必须 rebase develop | 推荐 |
| ❌ Include administrators | 管理员也受保护 | 推荐启用 |
| ✅ Do not allow bypass | 不允许跳过保护 | 强制 |

### develop 分支保护

| 规则 | 说明 | 严格程度 |
|------|------|----------|
| ✅ Require pull request before merging | 必须通过 PR 合入 | 强制 |
| ✅ Require status checks | CI 必须通过 | 推荐 |
| ❌ Require approvals | 可选（团队内部可放宽） | 宽松也可以 |

---

## 7. PR 流程

### 7.1 PR 标题规范

与提交消息格式一致：

```
<类型>(<范围>): <描述>
```

示例：
- `feat(ui): 添加卡牌权重调整滑块`
- `fix(auth): 修复 token 刷新竞态条件`
- `chore(ci): 合并 workflow 文件`

### 7.2 PR 描述模板

创建 `.github/PULL_REQUEST_TEMPLATE.md`：

```markdown
## 概述

<!-- 简要描述这次改动的目的 -->

## 改动内容

- [ ] 功能新增
- [ ] Bug 修复
- [ ] 重构
- [ ] 文档
- [ ] 测试

## 具体改动

<!-- 列出关键改动点，方便 reviewer 聚焦 -->

## 测试验证

- [ ] 本地构建通过
- [ ] 单元测试通过
- [ ] 手动测试完成

## 截图（UI 改动时必填）

<!-- 插入前后对比截图 -->

## 相关 Issue

Closes #
```

### 7.3 Code Review 流程

```
开发者创建 PR
    │
    ▼
CI 自动运行 ✅ 测试 + ✅ 构建
    │
    ├── CI 失败 → 开发者修复 → 推送新 commit → 重新触发 CI
    │
    ▼
CI 通过
    │
    ▼
指派的 Reviewer 进行 Code Review
    │
    ├── 请求修改 → 开发者修复 → 推送 → Reviewer 重新审核
    │
    ▼
Approve
    │
    ▼
开发者 squash merge 到 develop
```

### 7.4 合入策略

| 分支 | 合入策略 | 说明 |
|------|----------|------|
| `feat/*` → `develop` | **Squash merge** | 将整个功能压缩为一个提交，保持 develop 历史干净 |
| `develop` → `main` | **Merge commit** (`--no-ff`) | 保留集成时间线的 merge 节点，方便回滚 |

> **为什么用不同策略？**
> - 特性分支合入 develop：squash 可以压缩修复性提交（"fix typo"、"fix test"），让 develop 历史清晰
> - develop 合入 main：merge commit 可以保留发布版本的时间线锚点，一目了然

---

## 8. CI 配置优化

### 8.1 当前问题

审查了 `.github/workflows/` 下的 6 个文件，发现如下问题：

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| 🔴 Workflow 文件过多 | 高 | 6 个文件分散管理，触发条件不一致 |
| 🔴 冗余的 CI 配置 | 中 | `ci.yml` 和 `ci-cd.yml` 功能高度重叠 |
| 🟡 触发分支不一致 | 中 | 有的监听 `main, master, develop`，有的只监听 `main` |
| 🟡 宽松模式过度 | 中 | 大量 `|| true` 导致 CI 几乎不会失败 |
| 🔵 缺少自动 label | 低 | PR 没有按类型自动打标签 |

### 8.2 建议合并方案

将 6 个 workflow 合并为 3 个：

| 新文件 | 原来合并自 | 触发条件 |
|--------|-----------|----------|
| `ci.yml` | `ci.yml` + `ci-cd.yml` + `openapi-check.yml` | push/PR 到 `develop`, `main` |
| `database.yml` | `database-migration-test.yml` + `backup-test.yml` | 修改 `models/` `alembic/` 或 定时 |
| `deploy.yml` | 新建（部署专用） | `workflow_dispatch` 手动触发 |

### 8.3 关键优化

**核心检查必须阻断（不再用 `|| true`）：**
```yaml
# 改之前
python -m pytest tests/ -v || true

# 改之后
python -m pytest tests/ -v --junitxml=report.xml
```

**路径过滤精确触发：**
```yaml
on:
  push:
    paths:
      - 'moling-server/**'
    # 前端变动不触发后端 CI
```

---

## 9. 常用操作用例

### 9.1 开始任务

```bash
git fetch origin
git checkout develop
git pull --rebase
git checkout -b feat/my-feature
```

### 9.2 同步上游更新

```bash
# 在你的特性分支上
git fetch origin
git rebase origin/develop
# 如果有冲突 -> 解决 -> git add -> git rebase --continue
```

### 9.3 整理提交历史（合入 PR 前）

```bash
# 把 "fix typo"、"fix test" 等修复提交合并到功能提交中
git rebase -i origin/develop

# 交互式界面中：
# pick 第一个提交
# fixup 或 squash 后面的修复提交
```

### 9.4 紧急修复（Hotfix）

```bash
# 从 main 直接切 hotfix 分支
git checkout main
git checkout -b fix/critical-auth-bug

# 修复并提交
git add .
git commit -m "fix(auth): 修复未授权访问漏洞"

# 直接合入 main 和 develop
git checkout main
git merge --no-ff fix/critical-auth-bug
git tag v1.2.1
git push origin main --tags

git checkout develop
git merge --no-ff fix/critical-auth-bug
git push origin develop

# 清理
git branch -d fix/critical-auth-bug
```

### 9.5 安全的 force push

```bash
# 永远不要用 git push --force
# 用这个：
git push --force-with-lease
```

> `--force-with-lease` 会检查远程分支是否被你之外的其他人推送过新提交。如果是，它会拒绝推送，防止你覆盖别人的工作。

---

## 10. 故障恢复

### 10.1 提交到错误的分支

```bash
# 场景：在 develop 上直接提交了，实际上应该在新分支
git checkout -b feat/my-feature
git checkout develop
git reset --hard HEAD~1  # 移除 develop 上的错误提交
git checkout feat/my-feature  # 提交在新分支上完好
```

### 10.2 恢复误删的分支

```bash
# 场景：不小心删了还没合并的分支
git reflog  # 找到最近的 HEAD 记录
git checkout -b feat/my-feature <commit-hash>
```

### 10.3 恢复误删的提交

```bash
# 场景：git reset --hard 导致丢失提交
git reflog  # 找到丢失的 commit hash
git cherry-pick <lost-commit-hash>
```

### 10.4 reset 后恢复

```bash
# 恢复被 reset 掉的内容
git reflog
# 输出示例：
# abc1234 HEAD@{0}: reset: moving to HEAD~2
# def5678 HEAD@{1}: commit: feat(card): 添加权重计算
git cherry-pick def5678
```

### 10.5 撤销已推送的提交

```bash
# 场景：不小心推送了错误的提交到 feat 分支
git revert <bad-commit-hash>  # 创建反向提交
git push origin feat/my-feature  # 安全推送
```

> **绝对不要用 `git reset --hard` + `git push --force` 来撤销已推送的提交。** 用 `git revert` 更安全。

---

## 附录 A：Git 配置建议

### 全局 Git 配置

```bash
# 基本信息
git config --global user.name "你的名字"
git config --global user.email "your@email.com"

# 别名（提高效率）
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'
git config --global alias.lg "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit --date=relative"

# rebase 时自动 stash
git config --global rebase.autostash true
# pull 默认用 rebase
git config --global pull.rebase true

# 中文路径显示
git config --global core.quotepath false
```

### 墨灵项目级 Git 配置

```bash
# 在项目根目录执行
git config pull.rebase true
git config rebase.autostash true
```

---

## 附录 B：快速参考卡

```
┌─────────────────────────────────────────────────────────────┐
│                    一天 Git 工作流速查                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  早上                      下午                    收工      │
│  ┌─────┐                  ┌─────┐                ┌─────┐   │
│  │fetch│                  │开发 +│               │push │   │
│  │rebase│                  │提交  │               │创建 │   │
│  │develop│                  │      │               │PR   │   │
│  └─────┘                  └─────┘                └─────┘   │
│                                                             │
│  git fetch origin         git add <file>       git push     │
│  git rebase origin/dev    git commit -m "..."  → GitHub PR  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

> **最后的话**：工作流是团队的约定，不是枷锁。如果某个步骤让团队效率下降，就调整它。关键是保证 `main` 永远可部署、历史可追溯、协作不打架。

> 有疑问随时找我 🌿
