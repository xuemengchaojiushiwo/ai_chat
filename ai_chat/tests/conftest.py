import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ..api.main import app
from ..database import Base, get_db

# 使用内存数据库进行测试
TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_SQLALCHEMY_DATABASE_URL,
        echo=True,
        future=True,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """创建测试会话"""
    TestingSessionLocal = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def test_client(test_session):
    """创建测试客户端"""
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def pytest_addoption(parser):
    parser.addoption("--doc-id", action="store", default=None, type=int,
                    help="指定要查询的文档ID")

@pytest.fixture
def document_id(request):
    return request.config.getoption("--doc-id")

@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话，使用实际的数据库"""
    from ..database import get_db
    
    # 正确获取会话对象
    async for session in get_db():
        try:
            yield session
        finally:
            await session.close() 