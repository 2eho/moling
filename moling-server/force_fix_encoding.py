#!/usr/bin/env python3
"""
Fix encoding by reading files with error handling and re-saving as UTF-8.
Remove or replace non-ASCII characters that cause syntax errors.
"""
import os
import ast

FILES_TO_FIX = [
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

def fix_python_file(filepath):
    """Fix a Python file by reading with lax encoding and rewriting."""
    try:
        # Read the file with error tolerance
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Try to compile to check if it's valid Python
        try:
            ast.parse(content)
            print(f"  ✓ Already valid: {os.path.basename(filepath)}")
            return True
        except SyntaxError as e:
            print(f"  ✗ Syntax error in {os.path.basename(filepath)}: {e}")
            # Try to fix common issues
            # Replace problematic detail= strings
            lines = content.split('\n')
            fixed_lines = []
            for line in lines:
                # Remove or replace non-ASCII characters in this line
                try:
                    line.encode('ascii')
                    fixed_lines.append(line)
                except UnicodeEncodeError:
                    # This line has non-ASCII chars, try to fix
                    # Replace common Chinese error patterns
                    fixed_line = line
                    # Remove emoji and special chars
                    fixed_line = ''.join(c for c in fixed_line if ord(c) < 128 or c in '\n\r\t')
                    if fixed_line != line:
                        print(f"    Fixed line: {line[:50]}... -> {fixed_line[:50]}...")
                    fixed_lines.append(fixed_line)
            
            fixed_content = '\n'.join(fixed_lines)
            
            # Try to compile again
            try:
                ast.parse(fixed_content)
                # Save the fixed content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                print(f"  ✓ Fixed and saved: {os.path.basename(filepath)}")
                return True
            except SyntaxError as e2:
                print(f"  ✗ Still has syntax error: {e2}")
                return False
                
    except Exception as ex:
        print(f"  ✗ Error processing {filepath}: {ex}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing Python file encodings...")
    print("=" * 60)
    
    results = []
    for filepath in FILES_TO_FIX:
        if os.path.exists(filepath):
            print(f"\nChecking: {os.path.basename(filepath)}")
            success = fix_python_file(filepath)
            results.append((filepath, success))
        else:
            print(f"\n✗ File not found: {filepath}")
            results.append((filepath, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for filepath, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {os.path.basename(filepath)}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\nTotal: {success_count}/{len(results)} files fixed")
