#!/usr/bin/env python3
"""Fix specific garbled strings in project_service.py"""
import os

filepath = r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\project_service.py"

# Read the file in binary mode, then decode with error handling
with open(filepath, 'rb') as f:
    raw_content = f.read()

# Try to decode as UTF-8 with error replacement
content = raw_content.decode('utf-8', errors='replace')

# Replace garbled Chinese strings with English
# The garbled strings appear as mojibake of Chinese characters
replacements = [
    # ("椤圭洰涓嶅瓨鍦?", "Project not found"),
    # ("鏃犳潈璁块棶璇ラ」鐩?", "Access denied"),
    # Actually, let me just find all detail= strings and replace them
]

# Strategy: Find lines with detail="..." and replace non-ASCII content
lines = content.split('\n')
fixed_lines = []
for line in lines:
    if 'detail=' in line and '"' in line:
        # Extract the detail message
        # Format: detail="message",
        try:
            start = line.index('detail="') + len('detail="')
            end = line.index('"', start)
            message = line[start:end]
            
            # Check if message contains non-ASCII
            try:
                message.encode('ascii')
                # All ASCII, keep it
                fixed_lines.append(line)
            except UnicodeEncodeError:
                # Has non-ASCII, replace with generic message
                new_line = line[:start] + "Request failed" + line[end:]
                print(f"Fixed: {line[:60]}... -> {new_line[:60]}...")
                fixed_lines.append(new_line)
        except ValueError:
            # Can't parse, keep original
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

fixed_content = '\n'.join(fixed_lines)

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"Fixed: {filepath}")
print(f"Lines processed: {len(lines)}")
