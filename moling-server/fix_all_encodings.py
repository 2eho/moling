"""
Batch fix encoding issues in Python files.
Reads files that might be in GBK encoding and re-saves them as UTF-8.
"""
import os
import sys

def fix_encoding(filepath):
    """Try to read file with GBK, fallback to other encodings, then save as UTF-8."""
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'cp1252']
    
    for encoding in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Successfully read, now save as UTF-8
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"OK: {filepath} (read as {encoding}, saved as UTF-8)")
            return True
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"ERROR: {filepath} - {e}")
            return False
    
    print(f"SKIP: {filepath} (could not decode with any encoding)")
    return False

def main():
    """Fix all .py files in the app directory."""
    app_dir = 'app'
    
    if not os.path.exists(app_dir):
        print(f"Error: {app_dir} directory not found")
        return
    
    fixed = 0
    failed = 0
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_encoding(filepath):
                    fixed += 1
                else:
                    failed += 1
    
    print(f"\nDone! Fixed: {fixed}, Failed: {failed}")

if __name__ == '__main__':
    main()
