"""
Remove non-ASCII characters from Python files with syntax errors.
This is a pragmatic fix to avoid encoding issues.
"""
import os
import re

def remove_non_ascii(content):
    """Remove non-ASCII characters from a string."""
    # Keep ASCII characters (0-127) and common whitespace
    return content.encode('ascii', errors='ignore').decode('ascii')

def fix_file(filepath):
    """Read a file, remove non-ASCII characters, and save."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove non-ASCII characters
        fixed_content = remove_non_ascii(content)
        
        # Save
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"FIXED: {filepath}")
        return True
    except Exception as e:
        print(f"ERROR: {filepath} - {e}")
        return False

def main():
    """Fix all files with syntax errors."""
    error_files = [
        'app\\router\\admin.py',
        'app\\router\\auth.py',
        'app\\router\\card.py',
        'app\\router\\chapter.py',
        'app\\router\\generation.py',
        'app\\router\\notification.py',
        'app\\router\\phase4.py',
        'app\\router\\project.py',
        'app\\router\\setting.py',
        'app\\router\\template.py',
        'app\\router\\vault.py',
        'app\\router\\weave.py',
        'app\\service\\algorithm_service.py',
        'app\\service\\card_service.py',
        'app\\service\\chapter_service.py',
        'app\\service\\generation_service.py',
        'app\\service\\health_service.py',
        'app\\service\\phase4_service.py',
        'app\\service\\phase4_service_fixed.py',
        'app\\service\\project_service.py',
        'app\\service\\prompt_service.py',
        'app\\service\\prompt_service_fixed.py',
        'app\\service\\validation_service.py',
        'app\\service\\vault_service.py',
    ]
    
    fixed = 0
    for filepath in error_files:
        if fix_file(filepath):
            fixed += 1
    
    print(f"\nDone! Fixed: {fixed}/{len(error_files)}")

if __name__ == '__main__':
    main()
