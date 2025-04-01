import sys
import os
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.document import DocumentSegment
from ..services.vector_store import vector_store
from ..utils.embeddings import get_embedding
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def rebuild_vectors():
    """重建所有文档段落的向量"""
    db = SessionLocal()
    try:
        # 获取所有文档段
        segments = db.query(DocumentSegment).all()
        logger.info(f"Found {len(segments)} segments to process")
        
        # 清空现有的向量存储
        try:
            vector_store.collection.delete(ids=[str(segment.id) for segment in segments])
            logger.info("Cleared existing vectors")
        except Exception as e:
            logger.warning(f"Error clearing vectors: {e}")
        
        # 批量处理文档段
        batch_size = 10  # 每批处理10个文档
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            try:
                # 准备批量数据
                ids = [str(segment.id) for segment in batch]
                texts = [segment.content for segment in batch]
                metadatas = [{"segment_id": segment.id, "document_id": str(segment.document_id)} for segment in batch]
                
                # 批量生成向量
                embeddings = await get_embedding(texts)
                
                # 添加到向量存储
                await vector_store.add_embeddings(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                logger.info(f"Processed batch of {len(batch)} segments")
                
                # 打印一些段落内容用于验证
                for text in texts:
                    logger.info(f"Processed text: {text[:100]}...")
                
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                continue
        
        logger.info("Vector rebuilding completed")
        
    except Exception as e:
        logger.error(f"Error rebuilding vectors: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(rebuild_vectors()) 