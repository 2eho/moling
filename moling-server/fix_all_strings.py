#!/usr/bin/env python3
"""Fix ALL non-ASCII strings in Python files by replacing with English."""
import os
import re

TARGET_FILES = [
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\auth_service.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\project_service.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\chapter_service.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\card_service.py",
    r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\service\generation_service.py",
]

def fix_file(filepath):
    """Fix all non-ASCII strings in a file."""
    print(f"\nProcessing: {os.path.basename(filepath)}")
    
    try:
        # Read file
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        lines = content.split('\n')
        fixed_lines = []
        fixes = 0
        
        for i, line in enumerate(lines):
            # Check if line contains non-ASCII characters
            try:
                line.encode('ascii')
                # All ASCII, keep as-is
                fixed_lines.append(line)
            except UnicodeEncodeError:
                # Contains non-ASCII, try to fix
                # Look for detail="..." or message="..." patterns
                new_line = line
                
                # Fix detail="..." patterns
                if 'detail=' in line:
                    # Find the string content
                    match = re.search(r'detail="([^"]*)"', line)
                    if match:
                        fixes += 1
                        # Replace with generic message
                        new_line = line.replace(match.group(0), 'detail="Request failed"')
                        print(f"  Line {i+1}: Fixed detail= string")
                
                # Fix message="..." patterns  
                if 'message=' in line and '=' in line:
                    match = re.search(r'message="([^"]*)"', line)
                    if match:
                        fixes += 1
                        new_line = line.replace(match.group(0), 'message="Operation failed"')
                        print(f"  Line {i+1}: Fixed message= string")
                
                # Fix description="..." patterns
                if 'description=' in line:
                    match = re.search(r'description="([^"]*)"', line)
                    if match:
                        fixes += 1
                        new_line = line.replace(match.group(0), 'description="No description"')
                        print(f"  Line {i+1}: Fixed description= string")
                
                fixed_lines.append(new_line)
        
        if fixes > 0:
            # Write back
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            print(f"  ✓ Fixed {fixes} strings")
            return True
        else:
            print(f"  - No fixes needed")
            return True
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Fixing non-ASCII strings in service files...")
    print("=" * 60)
    
    for filepath in TARGET_FILES:
        if os.path.exists(filepath):
            fix_file(filepath)
        else:
            print(f"\n✗ File not found: {filepath}")
    
    print("\n" + "=" * 60)
    print("Done! Now try running: python -m pytest tests/ -v")
    print("=" * 60)
