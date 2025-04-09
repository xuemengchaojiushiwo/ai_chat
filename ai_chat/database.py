import logging
import os

import chromadb
import pymysql
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

logger = logging.getLogger(__name__)

def create_database():
    """创建数据库如果不存在"""
    try:
        # 解析数据库URL
        db_parts = settings.DATABASE_URL.replace('mysql+pymysql://', '').split('/')
        db_name = db_parts[1].split('?')[0]  # 获取数据库名称
        logger.info(f"Attempting to create database: {db_name}")
        # 创建到MySQL服务器的连接（不指定数据库）
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            charset='utf8mb4'
        )

        try:
            with connection.cursor() as cursor:
                # 检查数据库是否存在
                cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
                result = cursor.fetchone()
                
                if not result:
                    # 创建数据库
                    cursor.execute(f"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info(f"Database {db_name} created successfully")
                else:
                    logger.info(f"Database {db_name} already exists")
                
                connection.commit()
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise

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


# Async database dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 初始化数据库
async def init_db():
    try:
        # 首先创建数据库（如果不存在）
        create_database()
        
        # 创建表
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # 初始化 Chroma collection
        get_or_create_collection()
        logger.info("Chroma collection initialized")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# 删除数据库表
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    # Delete Chroma collection if exists
    try:
        chroma_client.delete_collection(settings.COLLECTION_NAME)
    except:
        pass 