import logging

import pytest
import pytest_asyncio
from sqlalchemy import select

from ..models.document import Document, DocumentSegment
from ..services.vector_store import vector_store
from ..utils.embeddings import EmbeddingFactory

# 设置日志级别为DEBUG以查看详细信息
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 使用 pytest_asyncio 而不是 pytest.mark.asyncio
@pytest_asyncio.fixture
async def setup_test():
    """准备测试环境"""
    logger.info("设置测试环境")
    yield
    logger.info("清理测试环境")

@pytest.mark.asyncio
async def test_document_segments(setup_test, db_session, document_id):
    """测试查询文档段落内容"""
    try:
        if document_id is not None:
            # 查询指定文档
            result = await db_session.execute(
                select(Document).filter(Document.id == document_id)
            )
            documents = [result.scalar_one_or_none()]
            if not documents[0]:
                logger.error(f"未找到ID为 {document_id} 的文档")
                return
        else:
            # 查询所有文档
            result = await db_session.execute(
                select(Document)
            )
            documents = result.scalars().all()
        
        logger.info(f"\nFound {len(documents)} documents:")
        for doc in documents:
            logger.info(f"\nDocument ID: {doc.id}")
            logger.info(f"Name: {doc.name}")
            
            # 查询该文档的所有段落
            result = await db_session.execute(
                select(DocumentSegment)
                .filter(DocumentSegment.document_id == doc.id)
                .order_by(DocumentSegment.position)
            )
            segments = result.scalars().all()
            
            logger.info(f"Found {len(segments)} segments:")
            for i, segment in enumerate(segments, 1):
                logger.info(f"\nSegment {i}:")
                logger.info(f"ID: {segment.id}")
                logger.info(f"Position: {segment.position}")
                logger.info(f"Page: {segment.page_number}")
                logger.info(f"Content: {segment.content[:200]}...")
    except Exception as e:
        logger.error(f"查询文档时发生错误: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_similarity_search(setup_test, db_session, document_id):
    """测试相似度搜索"""
    try:
        # 测试查询
        test_queries = [
            "十大主要投资关键词",
            "资产配置和风险管理",
            "长期投资策略",
            "投资组合管理"
        ]
        
        # 创建embedding工厂
        embedding_factory = EmbeddingFactory()
        
        # 如果指定了文档ID，构建where条件
        where_filter = None
        if document_id is not None:
            # 获取文档的所有段落ID
            result = await db_session.execute(
                select(DocumentSegment.chroma_id)
                .filter(DocumentSegment.document_id == document_id)
            )
            segment_ids = [str(row[0]) for row in result.fetchall()]
            if segment_ids:
                where_filter = {"$or": [{"id": id} for id in segment_ids]}
            else:
                logger.error(f"未找到文档 {document_id} 的任何段落")
                return
        
        for query in test_queries:
            logger.info(f"\n测试查询: {query}")
            
            # 生成查询的embedding
            query_embedding = await embedding_factory.get_embeddings(query)
            
            # 使用Chroma进行相似度搜索
            results = await vector_store.query_similar(
                query_embedding=query_embedding,
                n_results=5,
                where=where_filter
            )
            
            if results and results.get("ids") and results["ids"][0]:
                logger.info(f"找到 {len(results['ids'][0])} 个相关段落:")
                
                for i, (doc_id, distance) in enumerate(zip(
                    results["ids"][0],
                    results["distances"][0]
                )):
                    similarity = 1 - distance
                    logger.info(f"\n结果 {i+1}:")
                    logger.info(f"Chroma ID: {doc_id}")
                    logger.info(f"相似度: {similarity:.4f}")
                    
                    # 查询对应的文档段落
                    result = await db_session.execute(
                        select(DocumentSegment)
                        .filter(DocumentSegment.chroma_id == doc_id)
                    )
                    segment = result.scalar_one_or_none()
                    
                    if segment:
                        logger.info(f"段落ID: {segment.id}")
                        logger.info(f"文档ID: {segment.document_id}")
                        logger.info(f"位置: {segment.position}")
                        logger.info(f"页码: {segment.page_number}")
                        logger.info(f"内容预览: {segment.content[:200]}...")
                    else:
                        logger.warning(f"未找到对应的段落记录: {doc_id}")
            else:
                logger.warning(f"未找到与查询 '{query}' 相关的段落")
    except Exception as e:
        logger.error(f"相似度搜索时发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    
    # 获取命令行参数中的文档ID
    doc_id = None
    if len(sys.argv) > 1:
        try:
            doc_id = int(sys.argv[1])
            logger.info(f"将在文档 {doc_id} 中进行搜索")
        except ValueError:
            logger.error("文档ID必须是一个整数")
            sys.exit(1)
    
    # 运行测试
    pytest.main([__file__, "-v", "--log-cli-level=DEBUG", f"--doc-id={doc_id}" if doc_id else ""]) 