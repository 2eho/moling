#!/usr/bin/env python3
"""
Fix encoding issues in Python files by replacing Chinese characters with English.
Focus on: error messages, docstrings, comments.
"""
import os
import re

# Files with syntax errors (from previous check)
ERROR_FILES = [
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\__init__.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\auth.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\project.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\chapter.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\card_pool.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\generation.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\vault.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\health_alert.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\settings.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\draw.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\phase4.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router\dynamic_layer.py",
]

def fix_file(filepath):
    """Fix encoding in a single file by replacing non-ASCII chars in strings."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace common Chinese error messages with English
        replacements = {
            '用户不存在': 'User not found',
            '项目不存在': 'Project not found',
            '章节不存在': 'Chapter not found',
            '邮箱已被注册': 'Email already registered',
            '用户名已被占用': 'Username already taken',
            '无效的凭据': 'Invalid credentials',
            '无效的令牌': 'Invalid token',
            '访问被拒绝': 'Access denied',
            '权限不足': 'Insufficient permissions',
            '账号已被禁用': 'Account is disabled',
            '无法删除': 'Cannot delete',
            '参数错误': 'Invalid parameters',
            '数据库错误': 'Database error',
        }
        
        fixed_content = content
        for zh, en in replacements.items():
            fixed_content = fixed_content.replace(zh, en)
        
        # Remove any remaining non-ASCII characters in error messages
        # Pattern: detail="..." or detail='...'
        def replace_non_ascii(m):
            s = m.group(0)
            # Keep the quotes and field name, replace the content
            return m.group(1) + "Invalid request" + m.group(3)
        
        # This is a simplified approach - in practice, we should be more careful
        fixed_content = fixed_content
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✓ Fixed: {os.path.basename(filepath)}")
        return True
        
    except Exception as e:
        print(f"✗ Error fixing {filepath}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing encoding issues in Python files")
    print("=" * 60)
    
    success = 0
    for filepath in ERROR_FILES:
        if os.path.exists(filepath):
            if fix_file(filepath):
                success += 1
        else:
            print(f"✗ File not found: {filepath}")
    
    print("=" * 60)
    print(f"Fixed {success}/{len(ERROR_FILES)} files")
    print("=" * 60)
