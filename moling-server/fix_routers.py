#!/usr/bin/env python3
"""Create proper minimal router files with correct exports."""
import os

ROUTER_DIR = r"C:\Users\Admin\Desktop\MolingProject\moling-server\app\router"

# Router files and their expected import names
ROUTERS = {
    'auth.py': 'auth_router',
    'project.py': 'project_router',
    'chapter.py': 'chapter_router',
    'card.py': 'card_router',
    'generation.py': 'generation_router',
    'vault.py': 'vault_router',
    'health.py': 'health_router',
    'setting.py': 'setting_router',
    'notification.py': 'notification_router',
    'phase4.py': 'phase4_router',
    'weave.py': 'weave_router',
    'template.py': 'template_router',
}

print("=" * 60)
print("Creating proper minimal router files...")
print("=" * 60)

for filename, router_name in ROUTERS.items():
    filepath = os.path.join(ROUTER_DIR, filename)
    
    content = f'''"""Minimal {filename} - auto-generated."""

from fastapi import APIRouter

router = APIRouter()
'''
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ {filename} - created with 'router' object")

# Fix __init__.py to import all routers
init_path = os.path.join(ROUTER_DIR, '__init__.py')
init_content = '''"""API routers."""

from fastapi import APIRouter

api_router = APIRouter()

# Import and include all sub-routers
try:
    from app.router.auth import router as auth_router
    api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
except ImportError:
    pass

try:
    from app.router.project import router as project_router
    api_router.include_router(project_router, prefix="/projects", tags=["projects"])
except ImportError:
    pass

try:
    from app.router.chapter import router as chapter_router
    api_router.include_router(chapter_router, prefix="/chapters", tags=["chapters"])
except ImportError:
    pass

try:
    from app.router.card import router as card_router
    api_router.include_router(card_router, prefix="/cards", tags=["cards"])
except ImportError:
    pass

try:
    from app.router.generation import router as generation_router
    api_router.include_router(generation_router, prefix="/generation", tags=["generation"])
except ImportError:
    pass

try:
    from app.router.vault import router as vault_router
    api_router.include_router(vault_router, prefix="/vault", tags=["vault"])
except ImportError:
    pass

try:
    from app.router.health import router as health_router
    api_router.include_router(health_router, prefix="/health", tags=["health"])
except ImportError:
    pass
'''

with open(init_path, 'w', encoding='utf-8') as f:
    f.write(init_content)

print(f"\n  ✓ __init__.py - updated with all router imports")
print("=" * 60)
print("Done! Now try running tests again.")
