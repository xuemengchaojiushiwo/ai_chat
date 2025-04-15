import pytest

from ..knowledge.retriever import Retriever
from ..models.document import Document, DocumentSegment
from ..services.vector_store import ChromaService


@pytest.mark.asyncio
async def test_search_with_embedding(test_session):
    try:
        # 创建测试数据
        document = Document(
            name="测试文档",
            content="这是一个测试文档的内容"
        )
        test_session.add(document)
        await test_session.flush()
        
        # 创建文档段落
        segment = DocumentSegment(
            document_id=document.id,
            content="这是第一个测试段落，用于测试向量检索功能。",
            sequence=1
        )
        test_session.add(segment)
        await test_session.commit()
        
        # 初始化检索器
        retriever = Retriever(test_session)
        
        # 初始化ChromaService并插入测试数据
        chroma = ChromaService()
        embedding = await retriever.embedding_factory.get_embeddings(segment.content)
        chroma.insert(segment.id, embedding, segment.content)
        
        # 测试搜索
        query = "测试向量检索"
        results = await retriever.search_with_embedding(query, limit=3)
        
        # 验证结果
        assert len(results) > 0, "搜索结果不应为空"
        assert results[0]['segment_id'] == segment.id, "应该找到测试段落"
        assert results[0]['similarity'] > 0.5, "相似度应该大于阈值"
        
        print("测试结果:")
        for result in results:
            print(f"段落ID: {result['segment_id']}")
            print(f"相似度: {result['similarity']}")
            print(f"内容: {result['content']}")
            print("---")
        
    finally:
        # 清理测试数据
        await test_session.rollback()
        chroma.reset()

if __name__ == "__main__":
    asyncio.run(test_search_with_embedding()) 