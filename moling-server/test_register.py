"""Test registration logic directly, bypassing HTTP."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.config import get_settings
from app.dao import user_dao
from app.models import User
from app.service.auth_service import AuthService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def test_register():
    settings = get_settings()
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    
    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        svc = AuthService()
        
        # Simulate RegisterReq
        class FakeReq:
            email = "test3@moling.com"
            nickname = "测试用户3"
            password = "Test1234!"
        
        try:
            result = await svc.register(db, FakeReq())
            print(f"SUCCESS: {result}")
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_register())
