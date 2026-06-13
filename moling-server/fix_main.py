"""修复 main.py 文件，删除重复的代码片段。"""

import re

with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到第一个函数结束的位置（正确的函数）
# 然后删除后面所有重复的代码直到空行

lines = content.split('\n')
output_lines = []
skip = False
i = 0
while i < len(lines):
    line = lines[i]
    
    # 检查是否开始了重复的代码块
    if '#         status_code=500,' in line:
        skip = True
    
    if skip:
        # 跳过直到遇到空行
        if line.strip() == '':
            skip = False
            output_lines.append(line)
    else:
        output_lines.append(line)
    
    i += 1

fixed_content = '\n'.join(output_lines)

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print('File fixed successfully')
