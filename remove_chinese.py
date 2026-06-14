"""
Batch fix all Python files in the project.
Replace Chinese characters with English equivalents.
This is a temporary fix to make the project runnable.
"""
import os
import re

def replace_chinese_in_string(match):
    """Replace Chinese characters in a string literal."""
    string_content = match.group(1)
    
    # Common Chinese phrases and their English equivalents
    replacements = {
        '用户不存在': 'User not found',
        '邮箱已存在': 'Email already exists',
        '用户名已存在': 'Username already exists',
        '密码错误': 'Invalid password',
        '无效的凭证': 'Invalid credentials',
        '无效的令牌': 'Invalid token',
        '令牌已过期': 'Token expired',
        '权限不足': 'Permission denied',
        '资源不存在': 'Resource not found',
        '墨灵': 'Moling',
        '注册成功': 'Registration successful',
        '登录成功': 'Login successful',
        '已登出': 'Logged out',
        '项目': 'Project',
        '章节': 'Chapter',
        '角色': 'Character',
        '事件': 'Event',
        '伏笔': 'Foreshadowing',
        '卡牌': 'Card',
    }
    
    for cn, en in replacements.items():
        string_content = string_content.replace(cn, en)
    
    return match.group(0).replace(match.group(1), string_content)

def fix_file_remove_chinese(file_path):
    """Fix a Python file by removing/replacing Chinese characters."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Replace Chinese characters in string literals
        # Match single and double quoted strings
        content = re.sub(r'"(.*?)"', replace_chinese_in_string, content)
        content = re.sub(r"'(.*?)'", replace_chinese_in_string, content)
        
        # Replace Chinese in comments
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            try:
                line.encode('ascii')
                cleaned_lines.append(line)
            except UnicodeEncodeError:
                # Line contains non-ASCII, remove or replace
                if '#' in line:
                    # It's a comment, remove the comment
                    code_part = line.split('#')[0].rstrip()
                    if code_part:
                        cleaned_lines.append(code_part)
                else:
                    # Not a comment, try to keep but replace non-ASCII
                    cleaned_line = line.encode('ascii', errors='ignore').decode('ascii')
                    if cleaned_line.strip():
                        cleaned_lines.append(cleaned_line)
        
        content = '\n'.join(cleaned_lines)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        return False, str(e)

def main():
    """Fix all Python files."""
    project_dir = r'C:\moling-server-v2'
    
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk(project_dir):
        # Skip virtual environment
        if '.venv' in root or 'venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    if fix_file_remove_chinese(file_path):
                        print(f"Fixed: {file_path}")
                        fixed_count += 1
                    else:
                        print(f"ERROR: {file_path}")
                        error_count += 1
                except Exception as e:
                    print(f"ERROR: {file_path} - {str(e)}")
                    error_count += 1
    
    print(f"\nTotal fixed: {fixed_count}")
    print(f"Total errors: {error_count}")
    print("\nDone!")

if __name__ == '__main__':
    main()
