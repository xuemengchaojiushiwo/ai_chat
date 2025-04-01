import asyncio
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import chromadb
from chromadb.config import Settings as ChromaSettings

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database import Base, get_or_create_collection
from models.document import DocumentSegment

# SQLite database configuration
SQLITE_URL = "sqlite:///app.db"
sqlite_engine = create_engine(SQLITE_URL)
SQLiteSession = sessionmaker(bind=sqlite_engine)

# MySQL database configuration
mysql_engine = create_engine(settings.DATABASE_URL)
MySQLSession = sessionmaker(bind=mysql_engine)

async def migrate_data():
    print("开始数据迁移...")
    
    # 初始化Chroma客户端
    chroma_client = chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIRECTORY,
        settings=ChromaSettings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # 获取或创建collection
    collection = get_or_create_collection()
    
    # 从SQLite读取数据
    sqlite_session = SQLiteSession()
    try:
        # 获取所有文档片段
        segments = sqlite_session.query(DocumentSegment).all()
        print(f"从SQLite中读取到{len(segments)}条文档片段")
        
        # 准备Chroma数据
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for segment in segments:
            if segment.embedding:  # 只迁移有embedding的数据
                ids.append(str(segment.id))
                embeddings.append(segment.embedding)
                metadatas.append({
                    "document_id": str(segment.document_id),
                    "segment_index": segment.index,
                    "total_segments": segment.total_segments
                })
                documents.append(segment.content)
        
        # 批量添加到Chroma
        if ids:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            print(f"成功将{len(ids)}条embedding数据迁移到Chroma")
        
        # 创建MySQL表
        Base.metadata.create_all(mysql_engine)
        
        # 迁移数据到MySQL
        mysql_session = MySQLSession()
        try:
            # 将embedding字段设为None，因为已经迁移到Chroma了
            for segment in segments:
                segment.embedding = None
                mysql_session.merge(segment)
            
            mysql_session.commit()
            print("成功将文档片段数据迁移到MySQL")
            
        except Exception as e:
            mysql_session.rollback()
            print(f"MySQL数据迁移失败: {str(e)}")
            raise
        finally:
            mysql_session.close()
            
    except Exception as e:
        print(f"数据迁移失败: {str(e)}")
        raise
    finally:
        sqlite_session.close()
    
    print("数据迁移完成!")

if __name__ == "__main__":
    asyncio.run(migrate_data()) 