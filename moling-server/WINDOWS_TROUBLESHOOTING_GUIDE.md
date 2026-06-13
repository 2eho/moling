# Windows上运行墨灵后端的故障排除指南

**创建日期**: 2026-06-14  
**创建人**: perf-tester  
**适用环境**: Windows 11 + Python 3.13.12 + SQLAlchemy + SQLite  

## 问题描述

在Windows上运行墨灵后端时，遇到SQLAlchemy异步操作的兼容性问题：

### 错误1: greenlet DLL加载失败
```
ImportError: DLL load failed while importing _greenlet: 找不到指定的模块。
```

**原因**: greenlet库在Windows上有DLL依赖问题。

**影响**: 无法使用SQLAlchemy的异步功能。

### 错误2: run_in_executor()参数错误
```
BaseEventLoop.run_in_executor() got an unexpected keyword argument 'params'
```

**原因**: SQLAlchemy尝试使用`greenlet_spawn()`来运行同步代码，但是我们的patch传递了`**kwargs`给`run_in_executor()`，而`run_in_executor()`不接受关键字参数。

**影响**: 所有数据库写操作（注册、创建项目等）失败。

### 错误3: greenlet_spawn未调用
```
greenlet_spawn has not been called; can't call await_only() here.
Was IO attempted in an unexpected place?
```

**原因**: SQLAlchemy期望在greenlet上下文中运行数据库操作，但是我们的patch没有正确工作。

**影响**: 所有数据库操作失败。

## 已尝试的修复方案

### 修复1: 创建假的greenlet模块 (app/dependencies.py)
**方法**: 在导入SQLAlchemy之前，创建一个假的greenlet模块并插入到`sys.modules`中。

**代码位置**: `app/dependencies.py` 第22-53行

**状态**: ✅ 部分成功 - 解决了导入错误，但运行时还有问题。

### 修复2: Patch greenlet_spawn (app/dependencies.py)
**方法**: 创建`_patched_greenlet_spawn()`函数，使用`loop.run_in_executor()`来运行同步代码。

**代码位置**: `app/dependencies.py` 第25-28行, 第72-86行

**状态**: ⚠️ 部分成功 - 修复了`run_in_executor()`的参数问题，但是还有`greenlet_spawn has not been called`错误。

### 修复3: 使用同步引擎创建表 (app/main.py)
**方法**: 在启动时，使用同步SQLAlchemy引擎来创建数据库表，避免Windows上的greenlet问题。

**代码位置**: `app/main.py` 第32-40行

**状态**: ✅ 成功 - 数据库表可以正常创建。

## 推荐的解决方案

### 方案1: 使用PostgreSQL (推荐)

**优点**:
- PostgreSQL的异步驱动(asyncpg)在Windows上工作正常
- 更适合生产环境
- 性能更好

**步骤**:
1. 安装PostgreSQL
2. 创建数据库和用户
3. 修改`.env`文件中的`DATABASE_URL`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/moling_db
   ```
4. 重新运行数据库迁移

**影响**: 需要修改配置，但代码不需要大改。

### 方案2: 使用WSL2 (Windows Subsystem for Linux)

**优点**:
- Linux环境下greenlet和SQLAlchemy异步操作工作正常
- 接近生产环境(Linux服务器)
- 性能更好

**步骤**:
1. 安装WSL2 (Ubuntu)
2. 在WSL2中安装Python、PostgreSQL等依赖
3. 在WSL2中运行后端和性能测试

**影响**: 需要配置WSL2，但一劳永逸。

### 方案3: Windows上完全使用同步引擎

**优点**:
- 快速修复，不需要安装新软件
- 适合开发和测试

**缺点**:
- 性能较差（同步 vs 异步）
- 需要大量修改代码（所有DAO和服务）

**步骤**:
1. 修改`app/dependencies.py`，强制使用同步Session
2. 修改所有DAO，使用同步Session
3. 修改所有服务，使用同步DAO
4. 修改所有API端点，移除`async/await`

**影响**: 需要大量修改代码，不推荐。

### 方案4: 等待SQLAlchemy/SQLAlchemy团队的修复

**缺点**: 可能耗时很长，不确定何时能修复。

**不推荐**。

## 性能测试的影响

当前问题严重影响性能测试：

1. **成功率极低** (18-35%)
   - 因为数据库写操作失败
   - 无法准确测试性能

2. **响应时间不准确**
   - 失败的请求可能导致超时
   - P95响应时间虚高 (3492ms)

3. **无法建立性能基线**
   - 因为测试结果不准确
   - 无法跟踪性能趋势

## 建议的工作流程

### 立即行动 (1-2天)
1. **选择解决方案**: 团队决策使用方案1(PostgreSQL)还是方案2(WSL2)
2. **实施解决方案**: 按照上述步骤实施
3. **验证修复**: 运行`debug_performance.py`确认所有API工作正常
4. **重新运行性能测试**: 使用`run_performance_tests.py`

### 短期计划 (1-2周)
1. **建立性能基线**: 使用`performance_automation.py --baseline`
2. **识别性能瓶颈**: 分析性能测试结果
3. **优化关键端点**: 添加缓存、优化查询等

### 长期计划 (1个月+)
1. **建立CI/CD性能测试**: 每次提交自动运行性能测试
2. **性能监控**: 使用APM工具(Prometheus + Grafana)
3. **定期性能测试**: 每周/每月运行性能测试，跟踪趋势

## 有用的脚本

### 1. 排查工具 (`debug_performance.py`)
```bash
python debug_performance.py
```
**功能**: 检查后端健康状态，测试注册、登录、项目API

### 2. 运行性能测试 (`run_performance_tests.py`)
```bash
python run_performance_tests.py
```
**功能**: 自动检查后端，运行所有性能测试，生成报告

### 3. 性能测试自动化 (`performance_automation.py`)
```bash
# 创建基线
python performance_automation.py --baseline

# 与基线比较
python performance_automation.py --compare baseline.json
```
**功能**: 自动化性能测试，检测性能回退

### 4. 修复Unicode编码 (`fix_unicode.py`)
```bash
python fix_unicode.py
```
**功能**: 修复性能测试脚本中的Unicode编码问题(Windows)

## 常见问题解答

### Q1: 为什么不直接修复greenlet问题？
**A**: greenlet是C扩展库，在Windows上的DLL依赖问题很复杂。我们已经尝试了多种方法，但都无法完全解决。建议使用PostgreSQL或WSL2。

### Q2: 使用同步引擎会影响多少性能？
**A**: 取决于具体场景。对于IO密集型操作(如数据库查询)，异步可以显著提高性能(2-10倍)。对于CPU密集型操作，影响不大。

### Q3: 如何在WSL2中运行性能测试？
**A**: 
1. 在Windows上启动后端(使用WSL2)
2. 在Windows上运行性能测试脚本(因为Locust/requests需要访问Windows浏览器或其他资源)
3. 或者，完全在WSL2中运行(后端 + 性能测试)

### Q4: 性能测试的目标是什么？
**A**: 
- 认证API: RPS > 50
- 响应时间: P95 < 200ms
- 失败率: < 1%

当前性能远低于目标，需要大量优化。

## 联系信息

如果有问题或需要帮助，请联系：
- **perf-tester** (性能测试工程师): 负责性能测试和优化建议
- **integration-tester** (集成测试工程师): 负责后端服务启动和集成测试
- **team-lead** (团队负责人): 负责团队协调和决策

---

**文档版本**: 1.0  
**最后更新**: 2026-06-14  
**状态**: 待审核
