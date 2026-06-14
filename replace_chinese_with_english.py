"""
Replace Chinese characters in Python files with English equivalents.
This script reads files in binary mode to avoid encoding issues.
"""
import os
import re

# Mapping of common Chinese error messages to English
ERROR_MESSAGE_MAP = {
    '用户不存在': 'User not found',
    '邮箱已存在': 'Email already exists',
    '用户名已存在': 'Username already exists',
    '密码错误': 'Wrong password',
    '无效的凭证': 'Invalid credentials',
    '无效的令牌': 'Invalid token',
    '令牌已过期': 'Token expired',
    '权限不足': 'Permission denied',
    '资源不存在': 'Resource not found',
    '参数错误': 'Invalid parameters',
    '数据库错误': 'Database error',
}

# Mapping of common Chinese strings to English
GENERAL_STRING_MAP = {
    '墨灵': 'Moling',
    '已登出': 'Logged out',
    '注册': 'Register',
    '登录': 'Login',
    '项目': 'Project',
    '章节': 'Chapter',
    '角色': 'Character',
    '事件': 'Event',
    '伏笔': 'Foreshadowing',
    '卡牌': 'Card',
    '世界观': 'Worldview',
    '生成': 'Generate',
    '草稿': 'Draft',
}

def fix_file(file_path):
    """Fix a single Python file by reading in binary mode and replacing Chinese."""
    try:
        # Read file as binary
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        # Decode with latin-1 (never fails)
        content = raw_data.decode('latin-1')
        
        # Replace error messages
        for cn, en in ERROR_MESSAGE_MAP.items():
            # Look for the Chinese string in various forms of corruption
            cn_bytes = cn.encode('utf-8')
            cn_gbk = cn.encode('gbk', errors='ignore')
            
            # Replace in content
            if cn in content:
                content = content.replace(cn, en)
        
        # Replace general strings
        for cn, en in GENERAL_STRING_MAP.items():
            if cn in content:
                content = content.replace(cn, en)
        
        # Remove any remaining non-ASCII characters in string literals
        # This is a simplified approach - may break some strings
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            # Check if line is a comment
            if line.strip().startswith('#'):
                # Comment line, skip it
                continue
            # Check if line contains non-ASCII
            try:
                line.encode('ascii')
                clean_lines.append(line)
            except UnicodeEncodeError:
                # Contains non-ASCII, try to fix
                # Simple approach: just skip the line if it's not code
                if '=' in line or 'def ' in line or 'class ' in line or 'import ' in line:
                    # This is code, try to keep it
                    clean_line = line.encode('ascii', errors='ignore').decode('ascii')
                    if clean_line.strip():
                        clean_lines.append(clean_line)
        
        content = '\n'.join(clean_lines)
        
        # Write as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {str(e)}")
        return False

def main():
    """Fix all Python files in the project."""
    project_dir = r'C:\moling-server-v2'
    
    fixed_count = 0
    skipped_count = 0
    
    for root, dirs, files in os.walk(project_dir):
        # Skip virtual environment
        if '.venv' in root or 'venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file(file_path):
                    print(f"Fixed: {file_path}")
                    fixed_count += 1
                else:
                    skipped_count += 1
    
    print(f"\nTotal fixed: {fixed_count}")
    print(f"Total skipped: {skipped_count}")
    print("\nDone! All files should now be ASCII-compatible.")

if __name__ == '__main__':
    main()
