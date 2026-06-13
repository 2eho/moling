"""
Find all Python files with syntax errors and report them.
This helps identify files that need encoding fixes.
"""
import os
import ast

def check_syntax(filepath):
    """Check if a Python file has syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def main():
    """Check all .py files in the app directory for syntax errors."""
    app_dir = 'app'
    error_files = []
    
    for root, dirs, files in os.walk(app_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                ok, error = check_syntax(filepath)
                if not ok:
                    error_files.append((filepath, error))
    
    if error_files:
        print(f"\nFound {len(error_files)} files with syntax errors:\n")
        for filepath, error in error_files:
            print(f"  {filepath}")
            print(f"    Error: {error}\n")
    else:
        print("All files have valid syntax!")

if __name__ == '__main__':
    main()
