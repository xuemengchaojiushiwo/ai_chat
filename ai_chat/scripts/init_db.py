from ai_chat.database import Base, engine, get_db
from ai_chat.models.workspace import Workgroup, Workspace
from ai_chat.models.document import Document, DocumentWorkspace
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    """初始化数据库"""
    try:
        # 删除所有现有表
        logger.info("Dropping all existing tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        # 创建所有表
        logger.info("Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # 确保 messages 表有 citations 列
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER REFERENCES conversations(id),
                    role VARCHAR(50),
                    content TEXT,
                    tokens INTEGER DEFAULT 0,
                    citations JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        
        # 创建默认知识库
        logger.info("Creating default dataset...")
        service = DatasetService(next(get_db()))
        service.create_dataset("默认知识库", "系统默认知识库")
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db()) 