import chromadb
from chromadb.config import Settings as ChromaSettings
from ..config import settings
import numpy as np
import os
import logging
from typing import List, Dict, Any, Optional
from ..database import get_or_create_collection
from ..utils.logger import vector_logger

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        vector_logger.info("Initializing VectorStore")
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIRECTORY,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection = get_or_create_collection()
        vector_logger.info(f"VectorStore initialized with collection: {settings.COLLECTION_NAME}")
    
    async def add_embeddings(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        添加文档embedding到向量存储
        """
        vector_logger.info(f"Adding {len(ids)} embeddings to collection")
        try:
            # 添加前记录当前集合状态
            try:
                current_count = len(self.collection.get()['ids'])
                vector_logger.info(f"Current documents in collection before adding: {current_count}")
            except Exception as e:
                vector_logger.info(f"Collection might be empty: {str(e)}")

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            vector_logger.info(f"Successfully added {len(ids)} embeddings")
            for i, doc_id in enumerate(ids):
                vector_logger.info(f"Added document {doc_id} with metadata: {metadatas[i] if metadatas else None}")

            # 添加后确认
            try:
                new_count = len(self.collection.get()['ids'])
                vector_logger.info(f"Total documents in collection after adding: {new_count}")
            except Exception as e:
                vector_logger.error(f"Error checking collection after adding: {str(e)}")

        except Exception as e:
            vector_logger.error(f"Error adding embeddings: {str(e)}")
            raise
    
    async def query_similar(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        查询最相似的文档
        """
        vector_logger.info(f"Querying similar documents with n_results={n_results}")
        if where:
            vector_logger.info(f"Using filter: {where}")
        
        try:
            # 先检查集合中的所有数据
            all_data = self.collection.get()
            vector_logger.info(f"Total documents in collection: {len(all_data['ids'])}")
            vector_logger.info(f"Sample metadata in collection: {all_data['metadatas'][:5] if all_data['metadatas'] else []}")
            
            # 执行查询
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["metadatas", "distances", "documents"]
            )
            vector_logger.info(f"Found {len(results['ids'][0]) if results['ids'] else 0} similar documents")
            if results['ids'] and results['ids'][0]:
                vector_logger.info(f"First result metadata: {results['metadatas'][0][0] if results['metadatas'] else None}")
            vector_logger.debug(f"Query results: {results}")
            return results
        except Exception as e:
            vector_logger.error(f"Error querying similar documents: {str(e)}")
            raise
    
    async def delete_embeddings(self, ids: List[str]) -> None:
        """
        删除指定ID的embedding
        """
        vector_logger.info(f"Deleting {len(ids)} embeddings")
        try:
            self.collection.delete(ids=ids)
            vector_logger.info(f"Successfully deleted embeddings with ids: {ids}")
        except Exception as e:
            vector_logger.error(f"Error deleting embeddings: {str(e)}")
            raise
    
    async def update_embedding(
        self,
        id: str,
        embedding: List[float],
        document: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新指定ID的embedding
        """
        vector_logger.info(f"Updating embedding for id: {id}")
        try:
            # Chroma不直接支持更新，所以我们先删除再添加
            self.collection.delete(ids=[id])
            self.collection.add(
                ids=[id],
                embeddings=[embedding],
                documents=[document],
                metadatas=[metadata] if metadata else None
            )
            vector_logger.info(f"Successfully updated embedding for id: {id}")
            vector_logger.debug(f"Updated with metadata: {metadata}")
        except Exception as e:
            vector_logger.error(f"Error updating embedding: {str(e)}")
            raise
    
    async def get_embeddings(self, ids: List[str]) -> Dict[str, Any]:
        """
        获取指定ID的embedding
        """
        vector_logger.info(f"Getting embeddings for ids: {ids}")
        try:
            results = self.collection.get(ids=ids)
            vector_logger.info(f"Successfully retrieved {len(results['ids'])} embeddings")
            return results
        except Exception as e:
            vector_logger.error(f"Error getting embeddings: {str(e)}")
            raise

# 创建全局实例
vector_store = VectorStore()

class ChromaService:
    def __init__(self):
        self.collection_name = settings.CHROMA_COLLECTION
        # 确保存储目录存在
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        logger.info(f"Using Chroma persist directory: {settings.CHROMA_PERSIST_DIR}")
        
        # 使用持久化存储的Client
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        logger.info("Initialized Chroma client")
        self._init_collection()

    def _init_collection(self):
        """初始化collection"""
        try:
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"Got existing collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "l2"}
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def insert(self, segment_id: int, embedding: list, content: str = None):
        """插入向量"""
        try:
            logger.info(f"Inserting vector for segment {segment_id}")
            logger.debug(f"Embedding shape: {len(embedding)}")
            if content:
                logger.debug(f"Content length: {len(content)}")
            
            # 确保 embedding 是 Python 列表
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            
            self.collection.add(
                ids=[str(segment_id)],
                embeddings=[embedding],
                metadatas=[{"segment_id": segment_id}],
                documents=[content] if content else None
            )
            logger.info(f"Successfully inserted vector for segment {segment_id}")
            return True
        except Exception as e:
            logger.error(f"Error inserting vector for segment {segment_id}: {e}")
            return False

    def search(self, query_embedding: list, limit: int = 5, threshold: float = 0.5):
        """搜索相似向量"""
        try:
            logger.info(f"Searching vectors with limit {limit} and threshold {threshold}")
            # 确保 query_embedding 是 Python 列表
            if hasattr(query_embedding, 'tolist'):
                query_embedding = query_embedding.tolist()
            # 确保 query_embedding 是单个向量，而不是向量的列表
            if isinstance(query_embedding, list) and len(query_embedding) == 1:
                query_embedding = query_embedding[0]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=['metadatas', 'distances']
            )
            
            hits = []
            if results['metadatas']:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    # Chroma返回的是L2距离，需要转换为相似度分数
                    similarity = 1 / (1 + distance)  # 简单的距离到相似度的转换
                    if similarity >= threshold:
                        hits.append({
                            "segment_id": metadata['segment_id'],
                            "score": similarity
                        })
            logger.info(f"Found {len(hits)} hits above threshold")
            return hits
        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            return []

    def delete(self, segment_id: int):
        """删除向量"""
        try:
            logger.info(f"Deleting vector for segment {segment_id}")
            self.collection.delete(ids=[str(segment_id)])
            logger.info(f"Successfully deleted vector for segment {segment_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting vector for segment {segment_id}: {e}")
            return False

    def reset(self):
        """重置集合（删除所有数据）"""
        try:
            logger.info(f"Resetting collection {self.collection_name}")
            self.client.delete_collection(self.collection_name)
            self._init_collection()
            logger.info("Successfully reset collection")
            return True
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return False

    def __del__(self):
        """清理资源"""
        pass  # PersistentClient会自动处理持久化 