# 墨灵(Moling) 新开发者快速上手指南

> **文档版本**: 1.2.0  
> **最后更新**: 2026-06-21  
> **维护者**: Moling Team  
> **适用人员**: 新加入的开发人员

---

## 目录

1. [欢迎加入团队](#欢迎加入团队)
2. [环境要求](#环境要求)
3. [克隆项目](#克隆项目)
4. [安装依赖](#安装依赖)
5. [配置环境变量](#配置环境变量)
6. [启动开发环境](#启动开发环境)
7. [运行测试](#运行测试)
8. [代码规范](#代码规范)
9. [提交规范](#提交规范)
10. [获取帮助](#获取帮助)

---

## 欢迎加入团队

欢迎加入墨灵(Moling) 开发团队！本指南将帮助你快速搭建开发环境，熟悉项目结构，并开始贡献代码。

### 项目简介

**墨灵(Moling)** 是一个 AI 辅助小说创作平台，帮助用户通过 AI 能力进行小说创作、角色设定、情节设计等。

- **后端技术栈**: FastAPI>=0.115 + PostgreSQL 16 + Redis 7 + Celery>=5.5
- **前端技术栈**: Next.js ^15.1 + React ^19.0 + TypeScript ^5.7
- **部署方式**: Docker Compose
- **监控组件**: Prometheus + Grafana + Sentry
- **代码仓库**: `[请填写实际的 Git 仓库地址]`

---

## 环境要求

### 必需软件

| 软件 | 最低版本 | 推荐版本 | 下载链接 |
|------|----------|----------|----------|
| **Python** | 3.10.0 | 3.12.0 | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18.0.0 | 22.0.0 | [nodejs.org](https://nodejs.org/) |
| **PostgreSQL** | 14.0 | 16.0 | [postgresql.org](https://www.postgresql.org/download/) |
| **Redis** | 6.0 | 7.0 | [redis.io](https://redis.io/docs/getting-started/) |
| **Git** | 2.30.0 | 2.45.0 | [git-scm.com](https://git-scm.com/downloads) |
| **Docker** | 20.10.0 | 26.0.0 | [docker.com](https://www.docker.com/get-started) |
| **Docker Compose** | 2.0.0 | 2.24.0 | 随 Docker Desktop 自动安装 |

### 推荐工具

| 工具 | 用途 | 下载链接 |
|------|------|----------|
| **VS Code** | 代码编辑器 | [code.visualstudio.com](https://code.visualstudio.com/) |
| **Postman** | API 测试 | [postman.com](https://www.postman.com/downloads/) |
| **DBeaver** | 数据库管理 | [dbeaver.io](https://dbeaver.io/download/) |
| **RedisInsight** | Redis 管理 | [redis.com](https://redis.com/redis-enterprise/redis-insight/) |

### 推荐 VS Code 插件

```
# Python 开发
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)

# TypeScript/React 开发
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- TypeScript Vue Plugin (Vue.volar)

# 通用
- GitLens (eamodio.gitlens)
- Thunder Client (rangav.vscode-thunder-client)  # API 测试
- Docker (ms-azuretools.vscode-docker)
```

### 操作系统支持

| 操作系统 | 支持状态 | 说明 |
|----------|----------|------|
| **Windows 10/11** | ✅ 完全支持 | 需要 WSL2（推荐 Ubuntu 22.04） |
| **macOS** | ✅ 完全支持 | 使用 Homebrew 安装依赖 |
| **Ubuntu 22.04** | ✅ 完全支持 | 推荐的生产环境 |
| **Debian 11+** | ✅ 完全支持 | - |

---

## 克隆项目

### 步骤 1：克隆代码仓库

```bash
# HTTPS 方式（需要输入用户名和密码）
git clone https://github.com/[your-org]/MolingProject.git

# SSH 方式（推荐，需要配置 SSH Key）
git clone git@github.com:[your-org]/MolingProject.git

# 进入项目目录
cd MolingProject
```

### 步骤 2：配置 Git（首次使用）

```bash
# 配置用户名和邮箱
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"

# 配置换行符（Windows 用户必须配置）
git config --global core.autocrlf input  # Linux/macOS
git config --global core.autocrlf true   # Windows

# 配置别名（可选，但推荐）
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
```

---

## 安装依赖

### 后端依赖安装

#### 方法 1：使用 venv（推荐）

```bash
# 进入后端目录
cd moling-server

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 升级 pip
pip install --upgrade pip

# 安装项目依赖（包括开发依赖）
pip install -e ".[dev]"

# 验证安装
pip list | grep fastapi
python -c "import fastapi; print(fastapi.__version__)"
```

#### 方法 2：使用 conda

```bash
# 创建 conda 环境
conda create -n moling python=3.12

# 激活环境
conda activate moling

# 安装依赖
cd moling-server
pip install -e ".[dev]"
```

#### 方法 3：使用 Docker（无需本地安装 PostgreSQL/Redis）

```bash
# 启动数据库和 Redis
docker compose up -d db redis

# 在另一个终端，进入后端目录
cd moling-server

# 创建 .env 文件（见下一节）
cp .env.example .env

# 修改 .env 文件，使用 localhost 连接数据库
# DATABASE_URL=postgresql+asyncpg://moling:moling@localhost:5432/moling

# 安装依赖
pip install -e ".[dev]"

# 运行后端
uvicorn app.main:app --reload
```

### 前端依赖安装

```bash
# 进入前端目录
cd moling-web

# 使用 npm 安装依赖
npm ci

# 或者使用 yarn（如果项目使用 yarn.lock）
yarn install

# 或者使用 pnpm（如果项目使用 pnpm-lock.yaml）
pnpm install

# 验证安装
npm list next
npm list react
```

### 常见问题

#### 问题 1：pip install 速度慢

```bash
# 使用国内镜像源（阿里云）
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# 或者临时使用
pip install -i https://mirrors.aliyun.com/pypi/simple/ -e ".[dev]"
```

#### 问题 2：npm install 速度慢

```bash
# 使用国内镜像源（淘宝）
npm config set registry https://registry.npmmirror.com

# 或者临时使用
npm install --registry=https://registry.npmmirror.com
```

#### 问题 3：psycopg 安装失败

```bash
# psycopg 需要 PostgreSQL 客户端库
# Ubuntu/Debian:
sudo apt-get install libpq-dev

# macOS (Homebrew):
brew install postgresql@16

# Windows: 使用 psycopg[binary]（已在 pyproject.toml 中配置）
pip install psycopg[binary]
```

#### 问题 4：Windows 下 greenlet 兼容问题

墨灵后端在 Windows 上通过 `app/dependencies.py` 内置的 greenlet 猴子补丁自动适配。
如果遇到 `greenlet_spawn` 相关错误：
- 确保使用 SQLite（`sqlite+aiosqlite:///./moling.db`），这会触发 `_SyncAsyncSessionWrapper` 包装
- 确保 Python 版本 ≥ 3.10
- 技术原理：Windows 缺少原生 greenlet 支持，补丁将 `greenlet_spawn` 替换为 `ThreadPoolExecutor` 实现

#### 问题 5：Celery Worker 无法启动

```bash
# 检查 Redis 是否运行
redis-cli ping  # 应返回 PONG

# 检查环境变量
echo $CELERY_BROKER_URL  # 应为 redis://localhost:6379/1

# 启动 Worker（开发环境）
celery -A app.worker.celery_app worker -Q default,llm --loglevel=info

# 验证健康检查
curl http://localhost:8000/api/v1/health
# 应返回 {"status":"ok","database":"ok","redis":"ok","celery":"ok"}
```

---

## 配置环境变量

### 后端环境变量

```bash
# 进入后端目录
cd moling-server

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vim .env  # 或者使用 VS Code: code .env
```

**必需配置的环境变量**：

```bash
# .env 文件示例

# --- 数据库 ---
# 本地开发用 SQLite（Windows 绿色线程兼容）
DATABASE_URL=sqlite+aiosqlite:///./moling.db
# 生产环境用 PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://moling:moling@localhost:5432/moling

# --- Redis ---
REDIS_URL=redis://localhost:6379/0
# REDIS_PASSWORD=your-redis-password       # 生产环境必须设置

# --- Celery ---
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# --- JWT 安全 ---
SECRET_KEY=your-secret-key-here            # openssl rand -hex 32 生成

# --- LLM 配置 ---
LLM_MODEL=deepseek-chat                    # 默认模型
LLM_PROVIDER=deepseek                      # deepseek / openai / custom
LLM_API_KEY=sk-your-api-key                # API Key（也可通过后台管理页面配置）
LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_PRO_KEYS=sk-key1,sk-key2             # Pro Key Pool（逗号分隔）
# LLM_FLASH_KEYS=sk-fast1,sk-fast2         # Flash Key Pool

# --- 安全 ---
MAX_BODY_SIZE=10485760                     # 10MB 请求体限制
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# --- 监控（可选） ---
# SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# --- 环境标识 ---
ENVIRONMENT=development
APP_VERSION=0.1.0
```

### 前端环境变量

```bash
# 进入前端目录
cd moling-web

# 复制环境变量模板（如果有）
cp .env.example .env.local

# 编辑 .env.local 文件
vim .env.local
```

**必需配置的环境变量**：

```bash
# .env.local 文件示例

# API 基础地址（本地开发）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Sentry DSN（可选）
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# 环境标识
NODE_ENV=development
```

### 创建数据库和用户

```bash
# 进入 PostgreSQL 命令行
sudo -u postgres psql

# 创建数据库用户（如果不存在）
CREATE USER moling WITH PASSWORD 'moling';

# 创建数据库
CREATE DATABASE moling OWNER moling;

# 授权
GRANT ALL PRIVILEGES ON DATABASE moling TO moling;

# 退出
\q
```

---

## 启动开发环境

### 启动后端服务

#### 方法 1：使用 uvicorn（推荐）

```bash
# 进入后端目录
cd moling-server

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 启动后端（启用热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 输出示例：
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using statreload
```

**验证后端启动成功**：

```bash
# 浏览器访问 API 文档
open http://localhost:8000/api/v1/docs

# 或者命令行测试
curl http://localhost:8000/api/v1/health
```

#### 方法 2：使用 Docker Compose

```bash
# 启动所有服务（包括数据库、Redis、后端）
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 启动前端服务

```bash
# 进入前端目录
cd moling-web

# 启动开发服务器（启用热重载）
npm run dev

# 输出示例：
#  ▲ Next.js 15.x.x
#  - Local:        http://localhost:3000
#  - Network:      http://192.168.1.100:3000
#  ✓ Ready in 2.3s
```

**验证前端启动成功**：

```bash
# 浏览器访问前端页面
open http://localhost:3000/moling/
```

### 启动 Celery Worker（可选）

```bash
# 进入后端目录
cd moling-server

# 激活虚拟环境
source venv/bin/activate

# 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# 输出示例：
# [2026-06-16 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
# [2026-06-16 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
```

### 完整开发环境启动检查清单

- [ ] 后端服务运行在 `http://localhost:8000`
- [ ] 前端服务运行在 `http://localhost:3000`
- [ ] 数据库可连接（`pg_isready -U moling -d moling`）
- [ ] Redis 可连接（`redis-cli ping` 返回 `PONG`）
- [ ] Celery Worker 已启动（如果使用异步任务）
- [ ] 浏览器访问 `http://localhost:3000/moling/` 能看到页面
- [ ] API 文档可访问 `http://localhost:8000/api/v1/docs`

---

## 运行测试

### 后端测试

```bash
# 进入后端目录
cd moling-server

# 激活虚拟环境
source venv/bin/activate

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_api.py

# 运行特定测试函数
pytest tests/test_api.py::test_create_novel

# 显示详细输出
pytest -v

# 显示打印输出（调试时有用）
pytest -s

# 生成测试覆盖率报告
pytest --cov=app --cov-report=html

# 打开覆盖率报告
open htmlcov/index.html  # macOS
# 或 xdg-open htmlcov/index.html  # Linux
# 或 start htmlcov/index.html  # Windows
```

### 前端测试

```bash
# 进入前端目录
cd moling-web

# 运行单元测试
npm run test

# 运行 E2E 测试（Playwright）
npm run test:e2e

# 运行 lint 检查
npm run lint

# 修复 lint 错误
npm run lint:fix
```

### 集成测试

```bash
# 确保后端和前端都在运行
# 然后运行集成测试

# 后端集成测试
cd moling-server
pytest tests/integration/

# 前端 E2E 测试
cd moling-web
npm run test:e2e
```

---

## 代码规范

### Python 代码规范

#### 格式化工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| **Black** | 代码格式化 | `pyproject.toml` |
| **isort** | import 语句排序 | `pyproject.toml` |
| **Flake8** | 代码风格检查 | `.flake8` |
| **mypy** | 类型检查 | `pyproject.toml` |

#### 配置示例

```toml
# pyproject.toml

[tool.black]
line-length = 88
target-version = ['py312']
include = '\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
```

#### 使用前格式化代码

```bash
# 格式化所有 Python 文件
black moling-server/app/

# 排序 import 语句
isort moling-server/app/

# 类型检查
mypy moling-server/app/

# 或者一次性运行所有检查
black --check moling-server/app/
isort --check-only moling-server/app/
mypy moling-server/app/
```

### TypeScript/JavaScript 代码规范

#### 格式化工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| **Prettier** | 代码格式化 | `.prettierrc.json` |
| **ESLint** | 代码风格检查 | `.eslintrc.json` |
| **TypeScript** | 类型检查 | `tsconfig.json` |

#### 配置示例

```json
// .prettierrc.json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5"
}
```

```json
// .eslintrc.json
{
  "extends": ["next/core-web-vitals", "plugin:@typescript-eslint/recommended"],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error"
  }
}
```

#### 使用前格式化代码

```bash
# 进入前端目录
cd moling-web

# 格式化所有文件
npm run format  # 需要在 package.json 中配置

# 运行 lint 检查
npm run lint

# 自动修复 lint 错误
npm run lint:fix

# TypeScript 类型检查
npm run type-check  # 需要在 package.json 中配置
```

### Git 钩子（可选但推荐）

使用 `pre-commit` 在提交前自动格式化代码：

```bash
# 安装 pre-commit
pip install pre-commit

# 创建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.0
    hooks:
      - id: isort
EOF

# 安装 Git 钩子
pre-commit install

# 现在每次 git commit 前会自动运行 Black 和 isort
```

---

## 提交规范

### Conventional Commits

项目使用 **Conventional Commits** 规范，提交消息格式如下：

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **feat** | 新功能 | `feat(auth): 添加用户注册功能` |
| **fix** | 修复 bug | `fix(api): 修复 500 错误` |
| **docs** | 文档更新 | `docs(README): 更新安装说明` |
| **style** | 代码格式（不影响功能） | `style(auth): 格式化代码` |
| **refactor** | 重构（既不是新功能也不是修复） | `refactor(api): 优化数据库查询` |
| **perf** | 性能优化 | `perf(api): 添加 Redis 缓存` |
| **test** | 添加或修改测试 | `test(auth): 添加登录测试` |
| **chore** | 构建过程或辅助工具变更 | `chore(deps): 升级 fastapi 到 0.115.0` |

#### Scope 范围

| 范围 | 说明 |
|------|------|
| **auth** | 认证相关 |
| **api** | API 相关 |
| **db** | 数据库相关 |
| **ui** | 前端 UI 相关 |
| **config** | 配置文件 |
| **deps** | 依赖更新 |

#### 示例

```bash
# 新功能
git commit -m "feat(auth): 添加用户注册功能"

# 修复 bug
git commit -m "fix(api): 修复 500 错误

详细信息：当用户输入非法字符时，API 返回 500 错误。
已修复为返回 400 错误和友好提示。"

# 文档更新
git commit -m "docs(README): 更新安装说明"

# 性能优化
git commit -m "perf(api): 添加 Redis 缓存

- 缓存用户会话信息
- 缓存热点数据
- TTL 设置为 300 秒"

# 重大变更（在 footer 中添加 BREAKING CHANGE）
git commit -m "feat(api): 重构用户 API

BREAKING CHANGE: 用户 API 的响应格式已变更，需要前端同步更新。"
```

### Git 分支策略

| 分支 | 用途 | 说明 |
|------|------|------|
| **main/master** | 生产环境 | 保护分支，只允许通过 PR 合并 |
| **develop** | 开发环境 | 集成各功能分支 |
| **feature/xxx** | 新功能开发 | 从 develop 分支创建，完成后合并回 develop |
| **bugfix/xxx** | Bug 修复 | 从 develop 分支创建，完成后合并回 develop |
| **hotfix/xxx** | 生产环境紧急修复 | 从 main 分支创建，完成后合并回 main 和 develop |

#### 分支命名示例

```bash
# 新功能
git checkout -b feature/user-registration

# Bug 修复
git checkout -b bugfix/api-500-error

# 生产环境紧急修复
git checkout -b hotfix/critical-security-fix
```

---

## 获取帮助

### 团队联系方式

| 角色 | 姓名 | 邮箱 | 备注 |
|------|------|------|------|
| 技术负责人 | - | - | 请补充 |
| 后端负责人 | - | - | 请补充 |
| 前端负责人 | - | - | 请补充 |
| 新开发者导师 | - | - | 请补充 |

> **注意**：请在实际使用时填写上表中的联系信息。

### 文档链接

| 文档 | 路径 | 说明 |
|------|------|------|
| **项目介绍** | `README.md` | 项目概述和功能介绍 |
| **部署指南** | `docs/DEPLOYMENT_GUIDE.md` | 生产环境部署步骤 |
| **故障处理 SOP** | `docs/RUNBOOK.md` | 常见故障和处理步骤 |
| **系统架构说明** | `docs/ARCHITECTURE.md` | 系统架构和技术栈 |
| **监控配置指南** | `docs/MONITORING_SETUP.md` | Prometheus + Grafana 配置 |
| **安全加固指南** | `docs/SECURITY_HARDENING.md` | 安全配置建议 |

### 常见问题 (FAQ)

#### Q1：后端启动失败，报错"database connection failed"

**解决方法**：

```bash
# 1. 检查数据库是否运行
pg_isready -U moling -d moling

# 2. 如果数据库未启动，启动数据库
sudo systemctl start postgresql  # Linux
# 或 brew services start postgresql  # macOS

# 3. 检查 .env 文件中的 DATABASE_URL 是否正确
cat moling-server/.env | grep DATABASE_URL
```

#### Q2：前端启动失败，报错"Cannot find module"

**解决方法**：

```bash
# 1. 删除 node_modules 和锁文件
cd moling-web
rm -rf node_modules package-lock.json

# 2. 重新安装依赖
npm install

# 3. 重新启动
npm run dev
```

#### Q3：Git 提交时提示"pre-commit hook failed"

**解决方法**：

```bash
# 1. 查看具体错误
git commit -m "xxx"  # 会显示具体哪个检查失败

# 2. 手动运行格式化工具
black moling-server/app/
isort moling-server/app/

# 3. 重新提交
git add .
git commit -m "xxx"
```

### 在线资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Next.js 官方文档](https://nextjs.org/docs)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [Redis 官方文档](https://redis.io/docs/)
- [Docker 官方文档](https://docs.docker.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## 下一步

恭喜！你已经完成了新开发者上手流程。接下来可以：

1. **阅读代码**：熟悉项目结构和代码风格
2. **运行测试**：确保测试全部通过
3. **修复小 bug**：从小任务开始熟悉代码库
4. **参与 Code Review**：学习团队的代码规范
5. **阅读文档**：深入了解系统架构和设计决策

---

## 附录：快速参考

### 常用命令速查

```bash
# 后端启动
cd moling-server && source venv/bin/activate && uvicorn app.main:app --reload

# 前端启动
cd moling-web && npm run dev

# 运行后端测试
cd moling-server && pytest

# 运行前端测试
cd moling-web && npm run test

# 格式化 Python 代码
black moling-server/app/ && isort moling-server/app/

# 格式化 TypeScript 代码
cd moling-web && npm run lint:fix
```

### 项目目录结构速查

```
MolingProject/
├── moling-server/          # 后端项目
├── moling-web/             # 前端项目
├── docker/                 # Docker 配置
├── docs/                   # 项目文档
└── README.md              # 项目说明
```

---

**文档版本**: 1.0.0  
**最后更新**: 2026-06-16  
**维护者**: Moling Team

---

**END**
