import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from sqlalchemy import create_engine, text
from ai_chat.config import settings
from ai_chat.database import Base
from ai_chat.models.workspace import Workgroup, Workspace
from ai_chat.models.document import Document, DocumentWorkspace, DocumentSegment
from ai_chat.models.dataset import Dataset, Conversation, Message
import logging

logger = logging.getLogger(__name__)

def init_db():
    """初始化数据库"""
    try:
        # 创建数据库引擎
        root_engine = create_engine(
            settings.DATABASE_URL.replace('/ai_chat', ''),
            echo=True
        )
        
        # 尝试删除并重新创建数据库
        with root_engine.connect() as conn:
            conn.execute(text("DROP DATABASE IF EXISTS ai_chat"))
            conn.execute(text("CREATE DATABASE ai_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            logger.info("Database recreated successfully")
        
        # 重新连接到新创建的数据库
        engine = create_engine(settings.DATABASE_URL, echo=True)
        
        # 创建所有表
        Base.metadata.create_all(engine)
        logger.info("Tables created successfully")
        
        # 创建默认数据
        with engine.connect() as conn:
            # 创建默认工作组
            conn.execute(text("""
                INSERT INTO workgroups (name, description, created_at)
                VALUES ('default', 'Default workgroup', NOW())
            """))
            
            # 创建默认工作空间
            conn.execute(text("""
                INSERT INTO workspaces (name, description, group_id, created_at, updated_at)
                VALUES ('default', 'Default workspace', 1, NOW(), NOW())
            """))
            
            # 创建默认数据集
            conn.execute(text("""
                INSERT INTO datasets (name, description, created_at)
                VALUES ('default', 'Default dataset', NOW())
            """))
            
            conn.commit()
            logger.info("Default data created successfully")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化数据库
    if init_db():
        print("Database initialized successfully!")
    else:
        print("Error initializing database!") 