from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = "sqlite+aiosqlite:///ai_chat.db"

# 创建数据库引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True
)

# 创建会话工厂
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 创建基类
Base = declarative_base()

# 获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 初始化数据库
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 删除数据库表
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) 