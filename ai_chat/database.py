from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = "sqlite:///app.db"

# Create async engine
async_engine = create_async_engine('sqlite+aiosqlite:///app.db', echo=True)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Create sync engine for initialization
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# Import all models
from .models.workspace import Workgroup, Workspace
from .models.document import Document, DocumentWorkspace, DocumentSegment
from .models.dataset import Dataset, Conversation, Message

# Async database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Sync database dependency
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 初始化数据库
async def init_db():
    # Create tables using sync engine to avoid async issues
    Base.metadata.create_all(bind=engine)
    
    # Return success
    return True

# 删除数据库表
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) 