from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import chromadb
from chromadb.config import Settings as ChromaSettings
from .config import settings
import os

# Create async engine for MySQL with connection pool settings
async_engine = create_async_engine(
    settings.DATABASE_URL.replace('mysql+pymysql', 'mysql+aiomysql'),
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10
)

# Create sync engine for initialization with connection pool settings
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10
)

# Configure session makers
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Add event listeners for better error handling
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    connection_record.info['pid'] = os.getpid()

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    pid = os.getpid()
    if connection_record.info['pid'] != pid:
        connection_record.connection = connection_proxy.connection = None
        raise Exception(
            "Connection record belongs to pid %s, "
            "attempting to check out in pid %s" %
            (connection_record.info['pid'], pid)
        )

# Initialize Chroma client
chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIRECTORY,
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# Create or get collection
def get_or_create_collection():
    return chroma_client.get_or_create_collection(
        name=settings.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

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
    # Create tables using sync engine
    Base.metadata.create_all(bind=engine)
    
    # Initialize Chroma collection
    get_or_create_collection()
    
    return True

# 删除数据库表
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Delete Chroma collection if exists
    try:
        chroma_client.delete_collection(settings.COLLECTION_NAME)
    except:
        pass 