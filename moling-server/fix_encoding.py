"""
Fix encoding issues in all Python files.
This script reads all .py files and re-saves them with UTF-8 encoding.
"""
import os
import chardet

def fix_file_encoding(filepath):
    """Try to read a file with detected encoding and re-save as UTF-8."""
    try:
        # Read raw bytes
        with open(filepath, 'rb') as f:
            raw_data = f.read()
        
        # Try to detect encoding
        result = chardet.detect(raw_data)
        detected_encoding = result['encoding']
        
        if detected_encoding is None:
            detected_encoding = 'utf-8'
        
        # Try to decode with detected encoding
        try:
            content = raw_data.decode(detected_encoding)
        except:
            # If that fails, try common encodings
            for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    content = raw_data.decode(enc)
                    break
                except:
                    continue
            else:
                print(f"SKIP: Could not decode {filepath}")
                return False
        
        # Remove non-ASCII characters (Chinese characters) and replace with English
        # Actually, let's just re-save as UTF-8
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"FIXED: {filepath} (detected: {detected_encoding})")
        return True
        
    except Exception as e:
        print(f"ERROR: {filepath} - {e}")
        return False

def main():
    """Walk through all .py files and fix encoding."""
    fixed_count = 0
    error_count = 0
    
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if fix_file_encoding(filepath):
                    fixed_count += 1
                else:
                    error_count += 1
    
    print(f"\nDone! Fixed: {fixed_count}, Errors: {error_count}")

if __name__ == '__main__':
    main()
