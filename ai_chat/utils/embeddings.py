import aiohttp
import numpy as np
from typing import List, Union, Optional
from ..config import settings, SF_API_KEY
import httpx
import logging
import json
import time

logger = logging.getLogger(__name__)

async def get_embedding(texts: Union[str, List[str]]) -> List[List[float]]:
    """使用 text-embedding-3-small 模型获取文本向量"""
    # 确保输入是列表格式
    if isinstance(texts, str):
        texts = [texts]
    
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 批量处理，每批最多20个文本
    batch_size = 20
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        data = {
            "model": settings.EMBEDDING_MODEL,
            "input": batch_texts
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.OPENAI_EMBEDDING_URL,
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        raise Exception(f"API error: {await response.text()}")
                    result = await response.json()
                    batch_embeddings = [item["embedding"] for item in result["data"]]
                    all_embeddings.extend(batch_embeddings)
        except Exception as e:
            logger.error(f"Error in batch {i//batch_size}: {str(e)}")
            raise
    
    return all_embeddings

class EmbeddingFactory:
    def __init__(self):
        self.model = settings.EMBEDDING_MODEL
        logger.info(f"Initialized EmbeddingFactory with model: {self.model}")
    
    async def get_embeddings(self, text: Union[str, List[str]]) -> List[List[float]]:
        """获取文本的向量表示"""
        return await get_embedding(text)

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

    @staticmethod
    async def get_embeddings_batch(texts: List[str], model: str = None, batch_size: int = 20) -> List[np.ndarray]:
        """
        批量获取文本的embedding向量
        
        Args:
            texts: 文本列表
            model: 模型名称，如果为None则使用配置中的默认模型
            batch_size: 每批处理的文本数量
            
        Returns:
            embedding向量列表
        """
        if not model:
            model = settings.EMBEDDING_MODEL
            
        # 为 BAAI/bge-m3 模型添加特殊前缀
        if "bge" in model.lower():
            processed_texts = []
            for text in texts:
                if len(text) < 20:  # 如果是短文本，可能是查询
                    processed_text = f"查询：{text}"
                else:  # 如果是长文本，可能是文档
                    processed_text = f"段落：{text}"
                processed_texts.append(processed_text)
            texts = processed_texts
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                # 直接使用 get_embedding 函数
                embeddings = await get_embedding(batch_texts)
                # 确保每个 embedding 是一维列表
                for emb in embeddings:
                    if isinstance(emb, np.ndarray):
                        all_embeddings.append(emb.tolist())
                    elif isinstance(emb, list):
                        if len(emb) == 1 and isinstance(emb[0], (list, np.ndarray)):
                            inner_emb = emb[0]
                            if isinstance(inner_emb, np.ndarray):
                                all_embeddings.append(inner_emb.tolist())
                            else:
                                all_embeddings.append(inner_emb)
                        else:
                            all_embeddings.append(emb)
                    else:
                        all_embeddings.append(emb)
                logger.info(f"Generated embeddings for batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {str(e)}")
                raise
        
        return all_embeddings

async def get_embeddings(text: str, model: str = None, max_retries: int = 3) -> Optional[List[float]]:
    """获取文本的向量表示"""
    if not model:
        model = settings.EMBEDDING_MODEL
        
    # 为 BAAI/bge-m3 模型添加特殊前缀
    if "bge" in model.lower():
        if len(text) < 20:  # 如果是短文本，可能是查询
            text = f"查询：{text}"
        else:  # 如果是长文本，可能是文档
            text = f"段落：{text}"
    
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