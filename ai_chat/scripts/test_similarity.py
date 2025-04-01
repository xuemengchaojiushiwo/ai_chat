import sys
import os
import asyncio
import chromadb
from chromadb.config import Settings
import numpy as np
import logging
import aiohttp
import json

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ai_chat.config import settings

async def get_embedding(text: str) -> list:
    """使用 text-embedding-3-small 模型获取文本向量"""
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": settings.EMBEDDING_MODEL,
        "input": [text]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            settings.OPENAI_EMBEDDING_URL,
            headers=headers,
            json=data
        ) as response:
            if response.status != 200:
                raise Exception(f"API error: {await response.text()}")
            result = await response.json()
            return result["data"][0]["embedding"]

async def test_similarity():
    # 测试文本
    original_texts = [
        "安联美元高收益基金主要投资于美元计价的高收益债券",
        "该基金专注于新能源和可持续发展领域的投资",
        "今天天气真不错，阳光明媚",
    ]
    
    query_texts = [
        "你好",  # 完全不相关
        "美元高收益债券基金",  # 高度相关
        "美元投资",  # 部分相关
        "新能源投资基金",  # 与第二句相关
        "今天是个好天气",  # 与第三句相关
        "阳光很好"  # 与第三句部分相关
    ]
    
    # 初始化 Chroma
    logger.info("初始化 Chroma...")
    client = chromadb.Client(Settings(anonymized_telemetry=False))
    collection_name = "test_similarity_openai"
    
    # 如果集合已存在，先删除
    try:
        client.delete_collection(collection_name)
    except:
        pass
    
    # 创建新集合，使用余弦距离
    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    logger.info("创建新的集合，使用余弦距离度量")
    
    # 生成原文的向量表示
    logger.info("\n生成原文的向量表示...")
    original_embeddings = []
    for text in original_texts:
        embedding = await get_embedding(text)
        original_embeddings.append(embedding)
        logger.info(f"文本: {text}")
        logger.info(f"向量维度: {len(embedding)}")
    
    # 添加到 Chroma
    collection.add(
        ids=[f"doc_{i}" for i in range(len(original_texts))],
        embeddings=original_embeddings,
        metadatas=[{"text": text} for text in original_texts],
        documents=original_texts
    )
    
    # 测试查询相似度
    logger.info("\n开始测试查询相似度...")
    for query in query_texts:
        logger.info(f"\n查询文本: {query}")
        query_embedding = await get_embedding(query)
        
        # 查询相似文档
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=len(original_texts),
            include=["metadatas", "distances", "documents"]
        )
        
        # 显示结果
        for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
            # Chroma 返回的是余弦距离，范围是 [0, 2]
            # 相似度 = 1 - (distance / 2)
            similarity = 1 - (distance / 2)
            logger.info(f"原文: {doc}")
            logger.info(f"余弦距离: {distance:.4f}")
            logger.info(f"相似度: {similarity:.4f}")
            logger.info("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_similarity()) 