"""测试 async_session_factory 是否正常工作。"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.dependencies import async_session_factory, AsyncSession

async def test_session():
    print(f"async_session_factory: {async_session_factory}")
    print(f"AsyncSession: {AsyncSession}")
    
    try:
        async with async_session_factory() as session:
            print(f"Session created: {session}")
            print(f"Session type: {type(session)}")
    except Exception as e:
        print(f"Error creating session: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_session())
