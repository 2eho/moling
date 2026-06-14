"""
Fix Python file encoding issues.
Read files in binary mode, detect encoding, convert to UTF-8.
"""
import os
import sys

def detect_encoding_of_file(file_path):
    """Try to detect the encoding of a file."""
    # Try UTF-8 first
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()
        return 'utf-8'
    except:
        pass
    
    # Try GBK
    try:
        with open(file_path, 'r', encoding='gbk') as f:
            f.read()
        return 'gbk'
    except:
        pass
    
    # Try GB2312
    try:
        with open(file_path, 'r', encoding='gb2312') as f:
            f.read()
        return 'gb2312'
    except:
        pass
    
    # Default to latin-1 (never fails)
    return 'latin-1'

def fix_file_preserve_chinese(file_path):
    """Fix file encoding while preserving Chinese characters."""
    try:
        # Detect encoding
        encoding = detect_encoding_of_file(file_path)
        
        # Read with detected encoding
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        
        # Write as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, encoding
    except Exception as e:
        return False, str(e)

def main():
    """Fix all Python files in the project."""
    project_dir = r'C:\moling-server-v2'
    
    if not os.path.exists(project_dir):
        print(f"ERROR: Directory not found: {project_dir}")
        return
    
    fixed_count = 0
    error_count = 0
    skipped_count = 0
    
    for root, dirs, files in os.walk(project_dir):
        # Skip virtual environment
        if '.venv' in root or 'venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    success, info = fix_file_preserve_chinese(file_path)
                    if success:
                        if info != 'utf-8':
                            print(f"Fixed: {file_path} (from {info})")
                            fixed_count += 1
                        else:
                            skipped_count += 1
                    else:
                        print(f"ERROR: {file_path} - {info}")
                        error_count += 1
                except Exception as e:
                    print(f"ERROR: {file_path} - {str(e)}")
                    error_count += 1
    
    print(f"\nTotal files processed: {fixed_count + skipped_count + error_count}")
    print(f"Fixed (converted to UTF-8): {fixed_count}")
    print(f"Skipped (already UTF-8): {skipped_count}")
    print(f"Errors: {error_count}")
    print("\nDone!")

if __name__ == '__main__':
    main()
