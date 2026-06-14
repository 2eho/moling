# 墨灵 (Moling) - AI驱动的网络小说创作平台

> 一个基于AI辅助创作的网络小说平台，提供从灵感收集、卡牌抽取、AI生文到四库管理的完整创作流程。

---

## 📸 项目截图

> TODO: 添加Landing页面、工作空间、四库管理的关键截图

---

## ✨ 核心功能

### 1. 🃏 卡牌系统（灵感管理）
- **卡牌抽取**：基于Phase 4算法智能抽取灵感卡牌
- **多种抽卡模式**：single（单张）、dual（双张）、all（全部）、hybrid（混合）
- **权重调整**：用户可调整每张卡牌的权重，影响AI生文风格

### 2. 🤖 AI生文
- **一键生成**：基于当前章节+抽取的卡牌，调用LLM API生成内容
- **任务管理**：实时查询生成进度、取消生成任务
- **多模型支持**：通过LiteLLM Proxy支持多种AI模型（DeepSeek、GPT、Claude等）

### 3. 📚 四库管理（世界观构建）
- **角色库**：管理小说角色信息、性格、关系
- **时间线**：记录关键事件和时间节点
- **伏笔管理**：追踪伏笔的设置和回收状态
- **世界观**：构建完整的世界规则、地理、历史

### 4. 📖 章节管理
- **章节CRUD**：创建、编辑、删除、重新排序章节
- **富文本编辑器**：支持Markdown、实时预览
- **版本管理**：追踪章节修改历史（TODO）

### 5. 📊 项目管理
- **多项目支持**：用户可以创建多个小说项目
- **项目统计**：字数统计、章节数、完成度等
- **模板系统**：基于成熟网文模板快速创建项目（TODO）

---

## 🛠️ 技术栈

### 后端 (FastAPI)
- **框架**：FastAPI 0.115 + Python 3.12
- **数据库**：PostgreSQL + pgvector（生产） / SQLite（开发）
- **ORM**：SQLAlchemy 2.0 (async)
- **缓存/队列**：Redis + Celery (可选)
- **AI集成**：LiteLLM Proxy + DeepSeek API
- **认证**：JWT (access + refresh token)
- **文档**：自动生成OpenAPI规范 (Swagger UI)

### 前端 (Next.js)
- **框架**：Next.js 15 (App Router) + React 19
- **语言**：TypeScript 5.7
- **样式**：CSS Modules + Design Tokens
- **状态管理**：React Context (Auth、Project、Workspace)
- **API调用**：自定义apiClient + SWR/React Query (计划中)
- **测试**：Playwright (E2E) + Vitest (Unit) (待完善)

### DevOps
- **包管理**：pnpm (前端) + pip (后端)
- **代码质量**：ESLint + Prettier (前端) / flake8 + black (后端) (待完善)
- **部署**：Docker + CloudBase (腾讯云) (TODO)

---

## 📂 项目结构

```
MolingProject/
├── moling-server/              # 后端FastAPI服务
│   ├── app/
│   │   ├── main.py           # FastAPI应用入口
│   │   ├── router/           # API路由（Auth、Project、Chapter等）
│   │   ├── service/          # 业务逻辑层
│   │   ├── dao/             # 数据访问层
│   │   ├── models/          # SQLAlchemy模型
│   │   ├── schemas/         # Pydantic验证/序列化
│   │   ├── llm/            # LLM客户端
│   │   ├── dependencies.py   # 依赖注入（DB、Redis、认证）
│   │   ├── errors.py        # 统一错误处理
│   │   └── middleware/      # 中间件（CORS、Rate Limit等）
│   ├── .env                 # 环境变量（勿提交至Git）
│   ├── requirements.txt      # Python依赖
│   └── alembic/            # 数据库迁移脚本（TODO）
│
├── moling-web/                # 前端Next.js应用
│   ├── src/
│   │   ├── app/            # Next.js App Router页面
│   │   │   ├── (auth)/     # 认证布局组
│   │   │   ├── projects/   # 项目管理页面
│   │   │   ├── workspace/  # 写作工作空间
│   │   │   ├── vaults/     # 四库管理页面
│   │   │   └── ...
│   │   ├── components/     # React组件
│   │   ├── hooks/          # 自定义React Hooks
│   │   ├── contexts/       # React Context（状态管理）
│   │   ├── lib/           # 工具函数、API客户端、类型定义
│   │   └── styles/        # 全局样式、Design Tokens
│   ├── public/             # 静态资源
│   ├── package.json        # Node.js依赖
│   └── tsconfig.json      # TypeScript配置
│
├── tests/                     # 集成测试脚本
│   └── api-test-guide.md  # API测试指南（curl命令）
│
├── docs/                     # 项目文档
│   ├── 启动指南.md         # 启动指南
│   ├── API文档.md          # API文档（TODO）
│   └── 部署指南.md         # 部署指南（TODO）
│
└── README.md                 # 本文件
```

---

## 🚀 快速启动

### 前置条件
- Python 3.12+
- Node.js 22+
- SQLite (开发) / PostgreSQL (生产)
- Redis (可选)

### 1. 启动后端 (FastAPI)

```bash
cd C:\Users\Admin\Desktop\MolingProject\moling-server

# 创建虚拟环境（首次运行）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动FastAPI服务（默认端口8000）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**验证启动成功：**
- 访问 http://localhost:8000/docs 查看Swagger API文档
- 访问 http://localhost:8000/api/v1/health 查看健康检查

### 2. 启动前端 (Next.js)

```bash
cd C:\Users\Admin\Desktop\MolingProject\moling-web

# 安装依赖（首次运行）
npm install
# 或使用pnpm: pnpm install

# 启动Next.js开发服务器（默认端口3000）
npm run dev
```

**验证启动成功：**
- 访问 http://localhost:3000 查看Landing页面
- 尝试注册/登录功能

### 3. 并行启动（推荐）

**Windows (PowerShell)：**
```powershell
# 启动后端
Start-Process -WorkingDirectory "C:\Users\Admin\Desktop\MolingProject\moling-server" -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"

# 启动前端
Start-Process -WorkingDirectory "C:\Users\Admin\Desktop\MolingProject\moling-web" -FilePath "npm" -ArgumentList "run", "dev"
```

**Linux/Mac (bash)：**
```bash
# 后端
cd C:\Users\Admin\Desktop\MolingProject\moling-server && python -m uvicorn app.main:app --reload --port 8000 &

# 前端
cd C:\Users\Admin\Desktop\MolingProject\moling-web && npm run dev &
```

---

## 🧪 测试

### 后端API测试

**使用Swagger UI（推荐）：**
1. 启动后端服务
2. 访问 http://localhost:8000/docs
3. 展开端点，点击"Try it out"，填写参数，点击"Execute"

**使用curl命令：**
1. 参考 `tests/api-test-guide.md` 文件
2. 复制对应的curl命令，在终端中运行
3. 查看响应结果

### 前端E2E测试（待完善）

```bash
cd C:\Users\Admin\Desktop\MolingProject\moling-web

# 安装Playwright浏览器
npx playwright install

# 运行E2E测试
npm run test:e2e
```

---

## 📝 开发指南

### 后端开发规范

**1. 添加新API端点：**
- 在 `app/router/` 下创建新的router文件
- 在 `app/service/` 下创建对应的service文件
- 在 `app/router/__init__.py` 中注册router
- 遵循已有代码的命名规范和风格

**2. 数据库模型变更：**
- 修改 `app/models/` 下的模型文件
- 创建Alembic迁移脚本（生产环境）
- 或删除 `moling.db` 让应用自动重建（开发环境、SQLite）

**3. 错误处理：**
- 使用 `app/errors.py` 中定义的 `AppError` 类
- 使用业务错误码（如 `AUTH_INVALID_CREDENTIALS = 40101`）

### 前端开发规范

**1. 添加新页面：**
- 在 `src/app/` 下创建新的App Router目录
- 创建 `page.tsx` 作为页面入口
- 如需认证保护，使用 `AuthGuard` 组件

**2. API调用：**
- 在 `src/lib/apiClient.ts` 中添加API调用函数
- 创建对应的hook（如 `useXxx.ts`）管理状态
- 在页面组件中使用hook获取数据

**3. 样式管理：**
- 使用CSS Modules（`.module.css`）
- 遵循Design Tokens（`src/styles/design-tokens.css`）
- 勿直接修改全局样式

---

## 📊 项目进度

| 模块 | 进度 | 说明 |
|------|------|------|
| **后端API** | ~90% | 核心模块已完成（Auth、Project、Chapter、Card、Generation、Vault、Subscription、LLM Config），剩余部分测试报告待更新 |
| **前端Next.js** | ~95% | 核心页面已完成（Projects、Workspace、Auth、Vaults、Admin等），API集成完善中 |
| **数据库模型** | 100% | 所有模型已定义（User、Project、Chapter、Card、GenerationTask等） |
| **算法实现** | ~85% | 卡牌组合算法、四库提取、风格指纹已实现，Phase 4异步更新进行中 |
| **API文档** | ~70% | Swagger UI自动生成，核心端点文档已完善 |
| **测试** | ~50% | E2E和Unit测试文件存在，部分测试需重新运行 |
| **部署** | ~30% | Docker配置已完成，CloudBase部署待完善 |

**最后更新：** 2026-06-15 by 郝交付(交付总监)

---

## 📚 核心设计文档

| 文档 | 说明 | 最后更新 |
|------|------|----------|
| `012_a7c27b64_墨灵后端设计文档.md` | 后端API、Service、数据模型设计 | 2026-06-15 |
| `009_2b7b5b03_moling-card-combination-algorithm.md` | 卡牌组合算法、四库管理、风格指纹 | 2026-06-15 |
| `004_79b91a8b_前端设计系统-主文档.md` | 前端页面规格、组件库、Design Tokens | 2026-06-15 |
| `001_b8542cf6_后台管理-设计系统规范.md` | 后台管理页面设计、响应式规范 | 2026-06-15 |
| `PRD_墨灵MVP.md` | 产品需求文档 | - |
| `架构设计_墨灵MVP.md` | 系统架构设计 | - |
| `墨灵项目介绍-专业技术报告.md` | 项目全面介绍与技术报告 | 2026-06-15 |

---

## 👥 开发团队

| 角色 | 名称 | 职责 |
|------|------|------|
| **交付总监** | 郝交付 | 统筹协调、进度跟踪、质量保证 |
| **后端专家** | 贝洛奇 | FastAPI服务端开发、数据库设计、API实现 |
| **前端专家** | 贾思敏 | Next.js前端开发、React组件、API集成 |
| **测试专家** | 严过关 | API测试、E2E测试、代码质量检查 |
| **运维专家** | 卜宕机 | 部署配置、CI/CD、性能优化 |

---

## 📄 许可证

> TODO: 选择合适的开源许可证（如MIT、Apache 2.0）

---

## 📮 联系方式

- **项目Issues**：[GitHub Issues链接]
- **讨论区**：[GitHub Discussions链接]
- **邮件**：[联系邮箱]

---

## 🙏 致谢

- **FastAPI** - 现代化的Python Web框架
- **Next.js** - 强大的React全栈框架
- **LiteLLM** - 统一的LLM API代理
- **Playwright** - 可靠的E2E测试工具

---

**最后更新：** 2026-06-15 by 郝交付(交付总监)
