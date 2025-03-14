import aiohttp
import numpy as np
from typing import List, Union, Optional
from ..config import settings, SF_API_KEY
import httpx
import logging
import json
import time

logger = logging.getLogger(__name__)

class EmbeddingFactory:
    @staticmethod
    async def get_embeddings(texts: Union[str, List[str]], model: str = None) -> List[np.ndarray]:
        """
        获取文本的embedding向量，支持单条或多条文本
        
        Args:
            texts: 单条文本或文本列表
            model: 模型名称，如果为None则使用配置中的默认模型
        
        Returns:
            embedding向量列表
        """
        if isinstance(texts, str):
            texts = [texts]
            
        if not model:
            model = settings.EMBEDDING_MODEL
            
        headers = {
            "Authorization": f"Bearer {settings.SF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 为 BAAI/bge-m3 模型添加特殊前缀
        if "bge" in model.lower():
            texts = [f"为这段文字生成表示: {text}" for text in texts]
        
        data = {
            "model": model,
            "input": texts,
            "encoding_format": "float"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.SF_EMBEDDING_URL,
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        error_detail = await response.text()
                        logger.error(f"Embedding API error: {error_detail}")
                        raise Exception(f"Embedding API error: {error_detail}")
                        
                    result = await response.json()
                    
                    # 提取所有文本的embedding
                    embeddings = [np.array(item['embedding']) for item in result['data']]
                    
                    # 如果输入是单条文本，返回单个结果
                    return embeddings[0] if isinstance(texts, str) else embeddings
                    
        except Exception as e:
            logger.error(f"Failed to get embeddings: {str(e)}")
            raise

    @staticmethod
    def normalize_embeddings(embeddings: Union[np.ndarray, List[np.ndarray]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        标准化embedding向量
        
        Args:
            embeddings: 单个向量或向量列表
            
        Returns:
            标准化后的向量
        """
        if isinstance(embeddings, list):
            return [EmbeddingFactory.normalize_embeddings(emb) for emb in embeddings]
            
        # L2标准化
        norm = np.linalg.norm(embeddings)
        if norm > 0:
            return embeddings / norm
        return embeddings
        
    @staticmethod
    def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            embedding1: 第一个向量
            embedding2: 第二个向量
            
        Returns:
            相似度分数 (0-1)
        """
        # 确保向量已标准化
        emb1_normalized = EmbeddingFactory.normalize_embeddings(embedding1)
        emb2_normalized = EmbeddingFactory.normalize_embeddings(embedding2)
        
        return float(np.dot(emb1_normalized, emb2_normalized))

async def get_embeddings(text: str, model: str = None, max_retries: int = 3) -> Optional[List[float]]:
    """获取文本的向量表示"""
    if not model:
        model = settings.EMBEDDING_MODEL
        
    # 为 BAAI/bge-m3 模型添加特殊前缀
    if "bge" in model.lower():
        text = f"为这段文字生成表示: {text}"
    
    headers = {
        "Authorization": f"Bearer {settings.SF_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "input": text,
        "encoding_format": "float"
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SF_EMBEDDING_URL,
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["data"][0]["embedding"]
                else:
                    logger.error(f"Error getting embeddings (attempt {attempt + 1}/{max_retries}): {response.status_code} - {response.text}")
                    
                    if response.status_code == 400:
                        # 如果是输入错误，不需要重试
                        return None
                    
                    # 如果是其他错误，等待后重试
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                        continue
                        
        except Exception as e:
            logger.error(f"Exception getting embeddings (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            
    return None

__all__ = ['EmbeddingFactory', 'get_embeddings'] 