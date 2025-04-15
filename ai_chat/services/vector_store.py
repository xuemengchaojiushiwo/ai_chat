import logging
import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings
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
        
        # 尝试获取现有collection，如果不存在则创建新的
        try:
            self.collection = self.client.get_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=None
            )
            vector_logger.info(f"Got existing collection: {settings.COLLECTION_NAME}")
        except Exception as e:
            vector_logger.info(f"Creating new collection: {str(e)}")
            self.collection = self.client.create_collection(
                name=settings.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}  # 使用余弦距离
            )
            vector_logger.info(f"Created new collection with cosine distance: {settings.COLLECTION_NAME}")
    
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
            # 提取document_id
            document_id = None
            
            # 从过滤条件中提取document_id - 支持多种格式
            if where:
                # 1. 直接格式: {"document_id": "37"}
                if 'document_id' in where and isinstance(where['document_id'], str):
                    document_id = where['document_id']
                    vector_logger.info(f"Using document_id filter: {document_id}")
                
                # 2. 列表格式: {"document_id": {"$in": ["37"]}}
                elif 'document_id' in where and isinstance(where['document_id'], dict) and '$in' in where['document_id']:
                    # 只取第一个文档ID进行处理
                    if where['document_id']['$in'] and len(where['document_id']['$in']) > 0:
                        document_id = where['document_id']['$in'][0]
                        vector_logger.info(f"Using document_id from $in list: {document_id}")
                
                # 3. ID列表格式
                elif 'id' in where and isinstance(where['id'], dict) and '$in' in where['id']:
                    # 尝试解析出文档ID
                    for segment_id in where['id']['$in']:
                        if segment_id.startswith('doc_'):
                            parts = segment_id.split('_')
                            if len(parts) > 1 and parts[1].isdigit():
                                document_id = parts[1]
                                vector_logger.info(f"Extracted document_id {document_id} from segment IDs")
                                break
            
            results = None
            
            # 如果有document_id，直接使用document_id过滤
            if document_id:
                vector_logger.info(f"Querying with document_id: {document_id}")
                # 统一使用字符串格式的document_id
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results * 2, 20),
                    where={"document_id": str(document_id)},
                    include=["metadatas", "distances", "documents"]
                )
            else:
                # 无document_id过滤，使用原始过滤条件
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results * 2, 20),
                    where=where,
                    include=["metadatas", "distances", "documents"]
                )
            
            # 记录原始距离值
            if results['distances'] and results['distances'][0]:
                vector_logger.info(f"Raw distances from Chroma: {results['distances'][0]}")
            
            filtered_results = {
                'ids': [],
                'distances': [],
                'metadatas': [],
                'documents': []
            }
            
            if results['metadatas'] and len(results['metadatas'][0]) > 0:
                filtered_indices = []
                for i, (metadata, distance) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
                    # Chroma使用cosine distance，范围是[0, 2]
                    # cosine_similarity = 1 - (cosine_distance / 2)
                    similarity = 1 - (distance / 2)
                    vector_logger.info(f"Distance: {distance}, Calculated similarity: {similarity}")
                    
                    # 只保留相似度大于阈值的结果
                    if similarity >= settings.SIMILARITY_THRESHOLD:
                        filtered_indices.append(i)
                        
                # 如果有符合条件的结果，构建过滤后的结果字典
                if filtered_indices:
                    filtered_results['ids'] = [[results['ids'][0][i] for i in filtered_indices]]
                    filtered_results['distances'] = [[results['distances'][0][i] for i in filtered_indices]]
                    filtered_results['metadatas'] = [[results['metadatas'][0][i] for i in filtered_indices]]
                    if results.get('documents'):
                        filtered_results['documents'] = [[results['documents'][0][i] for i in filtered_indices]]
                
                vector_logger.info(f"Found {len(filtered_indices)} results above threshold {settings.SIMILARITY_THRESHOLD}")
            
            return filtered_results
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
                metadata={"hnsw:space": "cosine"}  # 使用余弦距离
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