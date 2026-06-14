# 墨灵项目 - API集成测试脚本

## 使用说明

1. **启动后端服务**
```bash
cd C:\Users\Admin\Desktop\MolingProject\moling-server
python -m uvicorn app.main:app --reload --port 8000
```

2. **运行测试**
```bash
# 在另一个终端中运行
cd C:\Users\Admin\Desktop\MolingProject
bash tests/api-test.sh  # Linux/Mac
# 或手动复制下面的curl命令（Windows）
```

---

## 1. 认证测试（Auth API）

### 1.1 注册新用户
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test1234!"
  }' -v
```

### 1.2 登录获取Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }' -v
```
**保存返回的access_token，后续请求需要使用！**

### 1.3 获取当前用户信息
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 2. 项目管理测试（Project API）

### 2.1 创建项目
```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "title": "测试小说",
    "author": "测试作者",
    "genre": "玄幻",
    "tags": ["修仙", "升级"],
    "synopsis": "这是一个测试小说",
    "worldview": "世界观描述",
    "protagonist": "主角描述",
    "supporting_chars": "配角描述",
    "target_words": 100000,
    "frequency": "daily",
    "style": "descriptive",
    "creation_mode": "card_first",
    "template_id": null
  }' -v
```
**保存返回的项目ID（project_id），后续请求需要使用！**

### 2.2 获取项目列表
```bash
curl -X GET "http://localhost:8000/api/v1/projects?page=1&page_size=20" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 2.3 获取单个项目
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 2.4 更新项目
```bash
curl -X PUT "http://localhost:8000/api/v1/projects/<PROJECT_ID>" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "title": "更新后的标题",
    "synopsis": "更新后的简介"
  }' -v
```

### 2.5 删除项目
```bash
curl -X DELETE "http://localhost:8000/api/v1/projects/<PROJECT_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 3. 章节管理测试（Chapter API）

### 3.1 创建章节
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "title": "第一章 开始",
    "order": 1,
    "content": "这是第一章的内容..."
  }' -v
```
**保存返回的章节ID（chapter_id），后续请求需要使用！**

### 3.2 获取章节列表
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 3.3 获取单个章节
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters/<CHAPTER_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 3.4 更新章节
```bash
curl -X PUT "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters/<CHAPTER_ID>" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "title": "第一章 新的开始",
    "content": "更新后的内容..."
  }' -v
```

### 3.5 重新排序章节
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters/reorder" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "chapter_ids": ["<CHAPTER_ID_1>", "<CHAPTER_ID_2>"]
  }' -v
```

### 3.6 删除章节
```bash
curl -X DELETE "http://localhost:8000/api/v1/projects/<PROJECT_ID>/chapters/<CHAPTER_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 4. 卡牌系统测试（Card API）

### 4.1 获取卡池
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/cards/pool" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 4.2 抽卡（Phase 4算法）
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/cards/draw" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "card_ids": ["<CARD_ID_1>", "<CARD_ID_2>"],
    "weights": [0.6, 0.4],
    "mode": "single"
  }' -v
```

### 4.3 重新抽卡
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/cards/redraw" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "chapter_id": "<CHAPTER_ID>"
  }' -v
```

---

## 5. AI生文测试（Generation API）

### 5.1 开始生成
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/generation" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "chapter_id": "<CHAPTER_ID>",
    "card_ids": ["<CARD_ID_1>"],
    "words": 1000
  }' -v
```
**保存返回的任务ID（task_id），用于查询进度！**

### 5.2 查询生成任务状态
```bash
curl -X GET "http://localhost:8000/api/v1/generation/<TASK_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 5.3 取消生成任务
```bash
curl -X DELETE "http://localhost:8000/api/v1/generation/<TASK_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 6. 四库管理测试（Vault API）

### 6.1 获取角色库
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/vault/characters" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 6.2 创建角色
```bash
curl -X POST "http://localhost:8000/api/v1/projects/<PROJECT_ID>/vault/characters" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "name": "主角名",
    "role": "protagonist",
    "description": "角色描述",
    "traits": ["聪明", "勇敢"]
  }' -v
```

### 6.3 获取时间线
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/vault/timeline" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 6.4 获取伏笔
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/vault/plot-promises" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 6.5 获取世界观
```bash
curl -X GET "http://localhost:8000/api/v1/projects/<PROJECT_ID>/vault/world" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 7. 通知测试（Notification API） - 贝洛奇实现后测试

### 7.1 获取通知列表
```bash
curl -X GET "http://localhost:8000/api/v1/notifications" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 7.2 标记通知已读
```bash
curl -X PUT "http://localhost:8000/api/v1/notifications/<NOTIFICATION_ID>/read" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 7.3 删除通知
```bash
curl -X DELETE "http://localhost:8000/api/v1/notifications/<NOTIFICATION_ID>" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

---

## 8. 设置测试（Setting API） - 贝洛奇实现后测试

### 8.1 获取个人设置
```bash
curl -X GET "http://localhost:8000/api/v1/settings/me" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" -v
```

### 8.2 更新个人设置
```bash
curl -X PUT "http://localhost:8000/api/v1/settings/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "username": "new_username",
    "bio": "个人简介"
  }' -v
```

### 8.3 修改密码
```bash
curl -X POST "http://localhost:8000/api/v1/settings/change-password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "old_password": "Test1234!",
    "new_password": "NewTest5678!"
  }' -v
```

---

## 9. 健康检查（无需认证）

### 9.1 健康检查
```bash
curl -X GET "http://localhost:8000/api/v1/health" -v
```

---

## 测试检查清单

- [ ] Auth API - 注册、登录、获取用户信息
- [ ] Project API - CRUD操作
- [ ] Chapter API - CRUD操作、重新排序
- [ ] Card API - 获取卡池、抽卡、重新抽卡
- [ ] Generation API - 开始生成、查询状态、取消
- [ ] Vault API - 四库CRUD操作
- [ ] Notification API - 列表、标记已读、删除（贝洛奇完成后）
- [ ] Setting API - 获取、更新、修改密码（贝洛奇完成后）
- [ ] Health Check - 无需认证即可访问

---

**最后更新：** 2026-06-14 by 郝交付
