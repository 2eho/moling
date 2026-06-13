"""在Windows上强制使用同步数据库操作的补丁."""

import platform
import sys

def patch_sqlalchemy_for_windows():
    """Patch SQLAlchemy to work on Windows with SQLite."""
    if platform.system() != "Windows":
        return
    
    print("[PATCH] Applying Windows SQLite sync patch...")
    
    # 强制使用同步引擎
    import os
    os.environ["MOLING_SYNC_DB"] = "1"
    
    # Patch AsyncSession to use sync session
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session
    
    # 创建一个同步Session工厂
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import get_settings
    
    settings = get_settings()
    db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite:///", 1)
    sync_engine = create_engine(db_url)
    SyncSessionFactory = sessionmaker(bind=sync_engine)
    
    # 保存同步工厂到app状态
    import app.dependencies as deps
    deps._sync_session_factory = SyncSessionFactory
    
    # Patch get_db to use sync session
    async def get_db_sync():
        """Provide a synchronous database session (Windows only)."""
        sync_session = SyncSessionFactory()
        try:
            yield sync_session
            sync_session.commit()
        except Exception as e:
            sync_session.rollback()
            raise
        finally:
            sync_session.close()
    
    # Replace the async get_db with sync version
    deps.get_db = get_db_sync
    
    print("[PATCH] Windows SQLite sync patch applied successfully")

if __name__ == "__main__":
    patch_sqlalchemy_for_windows()
