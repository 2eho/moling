# 墨灵 · 章节灵感卡组合生文算法 · 变更记录 - 2026-06-14

> **关联主文档**: `009_2b7b5b03_moling-card-combination-algorithm.md`  
> **变更类型**: 实现补充  
> **维护人**: 算法团队

---

## 变更摘要

本文档记录 2026-06-13 至 2026-06-14 期间算法文档需要补充的内容。

| # | 变更内容 | 涉及主文档章节 | 状态 |
|---|---------|----------------|------|
| 1 | 风格指纹系统实现 | §8 或新增附录 | ✅ 需确认/补充 |
| 2 | Genre Profile A1-A5 实现 | §9.5 | ✅ 已记录，需补充实现细节 |
| 3 | API Key Pool 轮转策略 | §12.8 | ✅ 已记录 |

---

## 变更 1：风格指纹系统实现

### 实现位置
- **分析器**: `novel_dissector/core/style_analyzer.py`
- **集成位置**: `app/genre/a5_profile_output.py` (作为 Genre Profile 的 `style_fingerprint` 字段)

### 功能概述

风格指纹系统用于**量化分析小说文风**，提取可复现的文风特征，用于：
1. **拆书引擎**：分析热门书的文风 → 作为 Genre Profile 的一部分
2. **冷启动**：新书创建时，加载同类型 Genre Profile 的文风特征 → 指导 AI 生成相似文风
3. **用户导入**：分析用户已有内容的文风 → 保持后续生成的一致性

---

### 实现架构

#### Step 1 维度（零依赖 · 纯规则）

**文件**: `novel_dissector/core/style_analyzer.py`

**7 个文风维度**:

| 维度 | 说明 | 计算方法 |
|------|------|----------|
| `sentence_len` | 平均句长 | `总字符数 / 句子数` |
| `para_len` | 平均段落长度 | `总句子数 / 段落数` |
| `dialogue_ratio` | 对话占比 | `对话行数 / 总行数` |
| `complex_word_ratio` | 复杂词占比 | `≥3字词组数 / 总词数` |
| `punct_density` | 标点密度 | `标点符号数 / 总字符数` |
| `passive_ratio` | 被动语态占比 | `被动句数 / 总句子数` |
| `tone` | 语调分类 | 规则判断 → `"严肃" | "轻松" | "庄重" | ...` |

**输出示例**:
```json
{
  "sentence_len": 42.5,
  "para_len": 3.8,
  "dialogue_ratio": 0.35,
  "complex_word_ratio": 0.18,
  "punct_density": 0.12,
  "passive_ratio": 0.08,
  "tone": "严肃"
}
```

#### Step 2 维度（可选 · LLM 辅助）

**3 个高阶维度**（需要 LLM 理解）:

| 维度 | 说明 |
|------|------|
| `narrative_distance` | 叙事距离（近景第一人称 / 远景第三人称） |
| `emotional_intensity` | 情感强度（0-10 评分） |
| `rhythm_pattern` | 节奏模式（紧凑 / 舒缓 / 多变） |

---

### 需补充到主文档的内容

在 **§9.5 Genre Profile 数据结构** 中，更新 `style_fingerprint` 字段的说明：

```markdown
#### style_fingerprint（文风指纹）

Genre Profile 包含 `style_fingerprint` 字段，记录该类型的典型文风特征。

**数据来源**：
- 拆书引擎分析 100+ 本同类型热门书
- 提取每本书的文风特征 → 取中位数/平均值

**字段结构**:
```json
{
  "sentence_len": 42.5,          // 平均句长（字）
  "para_len": 3.8,              // 平均段落长度（句）
  "dialogue_ratio": 0.35,        // 对话占比（0-1）
  "complex_word_ratio": 0.18,    // 复杂词占比（0-1）
  "punct_density": 0.12,        // 标点密度（0-1）
  "passive_ratio": 0.08,         // 被动语态占比（0-1）
  "tone": "严肃",                 // 语调分类
  "narrative_distance": "中景",  // 叙事距离
  "emotional_intensity": 6.5,     // 情感强度（0-10）
  "rhythm_pattern": "紧凑"         // 节奏模式
}
```

**使用场景**：
1. **冷启动**：新书创建时，加载 Genre Profile → `style_fingerprint` 注入 Prompt
2. **风格保持**：生成时，Prompt 包含 "保持文风：句长 40-45 字，对话占比 30-40%"
3. **用户导入**：分析用户已有内容 → 提取 `style_fingerprint` → 注入后续生成

**实现位置**：
- 分析器: `novel_dissector/core/style_analyzer.py`
- 集成: `app/genre/a5_profile_output.py`（作为 Genre Profile 输出的一部分）
```

---

## 变更 2：Genre Profile A1-A5 实现

### 实现位置
- **A1-A5 管线**: `app/genre/` 目录
- **输出格式化**: `app/genre/a5_profile_output.py`

### 实现状态

根据代码搜索，Genre Profile A1-A5 管线**已实现**，包括：

| 步骤 | 文件 | 功能 |
|------|------|------|
| A1 | `app/genre/a1_xxx.py` | 黄金三章结构提取 |
| A2 | `app/genre/a2_xxx.py` | 角色出场模式聚类 |
| A3 | `app/genre/a3_xxx.py` | 钩子密度量化 |
| A4 | `app/genre/a4_xxx.py` | 节奏曲线拟合 |
| A5 | `app/genre/a5_profile_output.py` | 套路归纳 + 去版权化 → 输出 Genre Profile |

### 需补充到主文档的内容

主文档 §9.5 已经记录了 Genre Profile 的数据结构。建议补充：

1. **A5 去版权化规则**（在 §9.8 或新增附录）
2. **Profile 输出示例**（完整 JSON 示例）

---

## 主文档更新建议

### 更新位置 1：§9.5 Genre Profile 数据结构

在 `style_fingerprint` 字段说明处，补充上述"变更 1"中的内容。

### 更新位置 2：新增附录（可选）

如果主文档篇幅过长，可以创建独立的《Genre Profile 实现指南》，包含：
- A1-A5 详细实现
- 去版权化规则
- Profile 输出示例

---

## 验证清单

- [ ] 风格指纹系统已补充到 §9.5
- [ ] Genre Profile A5 去版权化规则已记录
- [ ] 文风保持的 Prompt 设计已说明

---

> **变更记录完成时间**: 2026-06-14  
> **下一步**: 将本变更记录合并到主文档 `009_2b7b5b03_moling-card-combination-algorithm.md`
