import logging

import numpy as np

from ..services.vector_store import ChromaService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_vector_store():
    """测试向量存储功能"""
    try:
        # 初始化ChromaService
        chroma = ChromaService()
        logger.info("ChromaService initialized")
        
        # 创建测试数据
        test_id = 999
        test_embedding = np.random.rand(1536).tolist()  # 创建一个1536维的随机向量
        test_content = "这是一个测试文档段落，用于验证向量存储功能。"
        
        # 插入向量
        success = chroma.insert(test_id, test_embedding, test_content)
        assert success, "向量插入失败"
        logger.info("Vector inserted successfully")
        
        # 搜索向量
        results = chroma.search(test_embedding, limit=1)
        assert len(results) > 0, "搜索结果为空"
        assert results[0]['segment_id'] == test_id, "搜索结果不匹配"
        logger.info("Vector search successful")
        
        # 清理测试数据
        success = chroma.delete(test_id)
        assert success, "向量删除失败"
        logger.info("Vector deleted successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_reset_collection():
    """测试重置 Chroma 集合"""
    try:
        chroma_service = ChromaService()
        logger.info("Resetting Chroma collection...")
        success = chroma_service.reset()
        assert success, "Failed to reset collection"
        logger.info("Successfully reset Chroma collection")
    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

if __name__ == "__main__":
    test_vector_store()
    test_reset_collection() 