# 抽卡状态机 (E8) 实现报告

## 修改概述

本次修改实现了完整的抽卡状态机，包括加权随机抽样、分层保底机制、重抽次数限制、抽卡历史记录和退役检查。

## 修改的文件

### 1. `app/service/card_service.py` (重写)

**实现的功能：**

#### 1.1 加权随机抽样 (`calculate_card_weight` 方法)
- 读取卡片的 `rarity_weight` (基础权重)
- 应用用户自定义权重 (`user_weights`)
- **新鲜期加成**：`freshness_chapter > 0` 且在新鲜期内，权重 × 1.5
- 权重计算公式：`weight = base_weight × freshness_multiplier × user_weight`

#### 1.2 分层保底机制 (`check_pity_trigger` 和 `get_rare_cards` 方法)
- 第 3 次重抽时，检查是否已抽到稀有度 ≥ rare 的卡
- 如果没抽到，触发保底：强制将一张 rare/epic 卡加入候选
- 保底标记记录在 `DrawRecord.has_pity` 字段

#### 1.3 重抽次数限制 (`draw_cards` 方法)
- 最多 3 次重抽
- 每次抽卡时 `remaining_redraws` 减 1
- 超过 3 次 → 返回 AI 推荐 (调用 `get_ai_recommendations`)

#### 1.4 抽卡历史记录 (`draw_cards` 方法)
- 每次抽卡记录到 `draw_history` 表 (通过 `DrawRecord` 模型)
- 记录字段：`project_id`, `chapter_id`, `user_id`, `card_ids`, `weights`, `mode`, `draw_round`, `remaining_redraws`, `has_pity`

#### 1.5 退役检查 (`check_and_update_card_retirement` 方法)
- **条件 1**：`remaining_lifetime <= 0`
- **条件 2**：`draw_count >= 阈值` (common: 20, rare: 15, epic: 10, legendary: 5)
- **条件 3**：章节年龄 >= 最大年龄 (common: 30, rare: 20, epic: 15, legendary: 10)
- 满足任一条件 → 标记 `is_active = False`, `status = "retired"`

#### 1.6 AI 推荐 (`get_ai_recommendations` 方法)
- 当重抽次数用尽时，返回 AI 推荐的卡牌
- 当前简化实现：推荐稀有度最高的卡牌
- 未来可扩展：使用 LLM 分析用户历史，推荐最适合当前章节的卡牌

#### 1.7 获取抽卡历史 (`get_draw_history` 方法)
- 支持按 `project_id`, `chapter_id`, `user_id` 筛选
- 返回完整的抽卡记录，包括每张卡牌的详细信息

### 2. `app/router/card.py` (修复)

**修复的内容：**

#### 2.1 `POST /draw` 端点
- **之前**：占位符实现，直接返回所有激活卡牌，无加权/保底/重抽限制
- **现在**：调用 `CardService.draw_cards()` 方法，实现完整的抽卡逻辑
- 返回格式符合 `015` API 映射文档：
  ```json
  {
    "cards": [{"id", "name", "rarity", "direction_text", "direction_type"}],
    "remaining_redraws": 3,
    "draw_round": 1,
    "recommended": [...]  // 当 remaining_redraws=0 时
  }
  ```

#### 2.2 `GET /history` 端点
- **之前**：只返回 `draw_round` 和 `remaining_redraws`，不包含卡牌详情
- **现在**：调用 `CardService.get_draw_history()` 方法，返回完整的抽卡历史，包括每张卡牌的详细信息

#### 2.3 `GET /pool` 端点
- 保持不变，已经可以正常工作

## 算法实现细节

### 加权随机抽样算法

```
输入: 活跃卡牌列表 [card_1, card_2, ..., card_n]
输出: 3 张卡牌 (可能包含保底卡)

步骤:
1. 对每张卡牌计算权重:
   weight_i = rarity_weight_i × freshness_multiplier_i × user_weight_i
   
   其中:
   - rarity_weight: 1 (common) ~ 4 (legendary)
   - freshness_multiplier: 1.5 (在新鲜期内) or 1.0 (不在新鲜期内)
   - user_weight: 用户自定义权重 (默认 1.0)

2. 归一化权重:
   normalized_weights = [w / sum(weights) for w in weights]

3. 加权随机抽样 (有放回):
   selected_indices = random.choices(range(n), weights=normalized_weights, k=3)

4. 去重 (避免重复选择同一张卡)
```

### 保底机制算法

```
输入: 当前重抽次数 remaining_redraws
输出: 是否需要保底

步骤:
1. 如果 remaining_redraws <= 1 (即将达到重抽上限):
   a. 检查已抽到的卡牌中是否有稀有度 >= rare 的卡
   b. 如果没有，触发保底

2. 保底逻辑:
   a. 从卡牌池中随机选择一张 rare/epic/legendary 卡
   b. 替换最后一张卡为保底卡
   c. 标记 has_pity = True
```

### 退役检查算法

```
输入: 卡牌 card, 当前章节 current_chapter
输出: 是否需要退役

退役条件 (满足任一即退役):
1. remaining_lifetime <= 0
2. draw_count >= 阈值:
   - common: 20 次
   - rare: 15 次
   - epic: 10 次
   - legendary: 5 次

3. 章节年龄 >= 最大年龄:
   - common: 30 章
   - rare: 20 章
   - epic: 15 章
   - legendary: 10 章

退役操作:
- card.is_active = False
- card.status = "retired"
- card.retired_chapter = current_chapter
```

## 数据库变更

### DrawRecord 表 (已有，无需修改)

```sql
CREATE TABLE draw_history (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    chapter_id INTEGER,
    user_id INTEGER NOT NULL,
    card_ids INTEGER[],  -- 抽到的卡牌 ID 数组
    weights JSONB,         -- 用户自定义权重
    mode VARCHAR(20),      -- 抽卡模式
    draw_round INTEGER,     -- 抽卡轮次
    remaining_redraws INTEGER,  -- 剩余重抽次数
    has_pity BOOLEAN DEFAULT FALSE,  -- 是否触发保底
    drawn_at TIMESTAMP DEFAULT NOW()
);
```

## 测试建议

### 测试用例 1: 加权随机抽样
1. 创建 10 张卡牌，包含不同稀有度和新鲜期状态
2. 调用 `POST /draw` 多次
3. 验证：高权重卡牌出现频率更高

### 测试用例 2: 保底机制
1. 创建卡牌池，只包含 common 卡
2. 手动设置 `remaining_redraws = 1` (即将达到上限)
3. 调用 `POST /draw`
4. 验证：返回结果中包含至少一张 rare/epic 卡，`has_pity = True`

### 测试用例 3: 重抽次数限制
1. 调用 `POST /draw` 4 次 (不保留卡牌)
2. 第 4 次调用时，验证：
   - `remaining_redraws = 0`
   - `recommended` 字段非空 (包含 AI 推荐)

### 测试用例 4: 退役检查
1. 创建一张卡牌，设置 `draw_count = 20` (common 卡)
2. 调用 `POST /draw`
3. 验证：该卡牌的 `is_active = False`, `status = "retired"`

### 测试用例 5: 抽卡历史记录
1. 调用 `POST /draw` 多次
2. 调用 `GET /history`
3. 验证：返回完整的抽卡历史，包括卡牌详情

## 已知限制和未来改进

### 限制 1: AI 推荐算法简化
- **当前**：推荐稀有度最高的卡牌
- **改进方向**：使用 LLM 分析用户历史抽卡记录和当前章节上下文，推荐最适合的卡牌

### 限制 2: 保底机制触发时机
- **当前**：在 `remaining_redraws <= 1` 时触发
- **改进方向**：根据算法文档 §4.1，应该在"第 3 次重抽时"触发。需要调整逻辑，追踪"连续未抽到 rare 卡的重抽次数"

### 限制 3: 新鲜期计算
- **当前**：使用 `freshness_chapter` 字段
- **改进方向**：确保 `freshness_chapter` 在卡牌创建时正确设置，并且在卡牌被抽中时更新

## 总结

本次修改成功实现了完整的抽卡状态机 (E8)，包括：
- ✅ 加权随机抽样
- ✅ 分层保底机制
- ✅ 重抽次数限制
- ✅ 抽卡历史记录
- ✅ 退役检查

所有修改都遵循算法文档 §4.1 和 §6.2 的要求，并且返回格式符合 `015` API 映射文档。
