```mermaid
gitGraph
   commit id: "init"
   branch develop
   checkout develop
   commit id: "feat: 用户认证基础"
   branch feat/card-weight
   checkout feat/card-weight
   commit id: "feat: 添加权重计算"
   commit id: "feat: 集成滑块组件"
   checkout develop
   merge feat/card-weight type: SQUASH id: "squash 合并功能"

   branch fix/login-redirect
   checkout fix/login-redirect
   commit id: "fix: 修复重定向bug"
   checkout develop
   merge fix/login-redirect type: SQUASH id: "hotfix 合入develop"

   checkout main
   merge develop tag: "v1.2.0" id: "发布版本"
```

## 墨灵 Git 工作流时序图

```
┌─────────┐     ┌──────────┐     ┌───────────┐     ┌────────┐
│ 开发者   │     │ 本地开发  │     │  GitHub    │     │  CI/CD │
│ (你)     │     │ 分支     │     │  Remote    │     │        │
└────┬────┘     └────┬─────┘     └─────┬─────┘     └───┬────┘
     │               │                 │               │
     │ 1. fetch      │                 │               │
     │──────────────→│                 │               │
     │ 2. rebase     │                 │               │
     │──────────────→│                 │               │
     │               │                 │               │
     │ 3. 开发+提交   │                 │               │
     │──────────────→│                 │               │
     │               │                 │               │
     │ 4. push       │                 │               │
     │────────────────────────────────→│               │
     │               │                 │               │
     │ 5. 创建 PR    │                 │               │
     │────────────────────────────────→│               │
     │               │                 │ 6. 触发 CI    │
     │               │                 │──────────────→│
     │               │                 │               │
     │               │                 │ 7. 结果通知   │
     │               │                 │←──────────────│
     │               │                 │               │
     │ 8. Code Review                  │               │
     │←────────────── 批准 ────────────│               │
     │               │                 │               │
     │ 9. Squash Merge → develop       │               │
     │────────────────────────────────→│               │
     │               │                 │               │
     │ 10. 删除分支  │                 │               │
     │────────────────────────────────→│               │
```
