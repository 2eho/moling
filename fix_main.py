# 临时脚本：修复 main.py，移除重复的健康检查端点

file_path = "c:/Users/Admin/Desktop/MolingProject/moling-server/app/main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要删除的行范围
# 当前文件状态：
# 241-243: 错误的 "# Prometheus Metrics" 注释（原本是 Health Check）
# 245-252: /health 端点
# 255-262: /api/v1/health 端点
# 265-267: 正确的 "# Prometheus Metrics" 注释

# 需要删除 241-264 行（索引 240-263）
# 即：错误的注释 + 两个健康检查端点 + 后面的空行

new_lines = []
skip_start = 240  # 索引从0开始，第241行对应索引240
skip_end = 263      # 第264行对应索引263

for i, line in enumerate(lines):
    if skip_start <= i <= skip_end:
        continue  # 跳过这些行
    new_lines.append(line)

# 写入新文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"修复完成！删除了 {skip_end - skip_start + 1} 行")
print(f"原文件行数: {len(lines)}")
print(f"新文件行数: {len(new_lines)}")
