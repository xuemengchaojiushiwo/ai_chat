from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..utils.embeddings import EmbeddingFactory
import numpy as np
import logging
import json
from sklearn.metrics.pairwise import cosine_similarity
from ..services.vector_store import vector_store

# SQLAlchemy models - 只保留一个 DocumentSegment 导入
from ..models.document import Document, DocumentSegment, DocumentWorkspace

# Pydantic models
from ..models.types import (
    DocumentResponse,
    DocumentSegmentResponse
)

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_factory = EmbeddingFactory()
        self.logger = logging.getLogger(__name__)

    async def search(self, query: str, limit: int = 5, workspace_id: Optional[int] = None) -> List[Dict]:
        """搜索相关文档片段"""
        try:
            # 构建基础查询
            stmt = (
                select(DocumentSegment)
                .join(Document)
            )
            
            if workspace_id:
                # 添加工作空间过滤条件
                self.logger.info(f"Searching in workspace: {workspace_id}")
                stmt = (
                    stmt
                    .join(DocumentWorkspace)
                    .filter(DocumentWorkspace.workspace_id == workspace_id)
                )
                
                # 添加更多日志来帮助调试
                self.logger.info(f"Built query: {str(stmt)}")
            
            # 添加限制条件
            stmt = stmt.limit(limit)
            
            result = await self.db.execute(stmt)
            segments = result.scalars().all()
            
            self.logger.info(f"Found {len(segments)} segments in workspace {workspace_id}")
            
            # 添加更多日志来显示找到的内容
            for segment in segments:
                self.logger.info(f"Found segment: {segment.content[:100]}...")
            
            return [
                {
                    "document_id": segment.document_id,
                    "segment_id": segment.id,
                    "content": segment.content,
                }
                for segment in segments
            ]
        except Exception as e:
            self.logger.error(f"Error in search: {str(e)}")
            self.logger.exception("Full traceback:")
            return []

    async def get_document(self, document_id: int) -> Optional[DocumentResponse]:
        """获取文档信息"""
        result = await self.db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        return DocumentResponse.from_orm(document) if document else None

    async def get_segment(self, segment_id: int) -> Optional[DocumentSegmentResponse]:
        """获取文档片段"""
        result = await self.db.execute(
            select(DocumentSegment).filter(DocumentSegment.id == segment_id)
        )
        segment = result.scalar_one_or_none()
        return DocumentSegmentResponse.from_orm(segment) if segment else None

    async def search_with_embedding(self, query: str, limit: int = 3, workspace_id: Optional[int] = None) -> List[Dict]:
        """搜索相关文档段落"""
        try:
            # 1. 获取查询的向量表示
            self.logger.info(f"Processing query: {query}")
            query_embedding = await self.embedding_factory.get_embeddings(query)
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding)
            query_embedding = query_embedding.flatten().tolist()  # 转换为列表
            self.logger.info(f"Generated query embedding")

            # 2. 构建Chroma查询条件
            where_filter = None
            if workspace_id:
                # 获取工作空间关联的文档ID
                stmt = (
                    select(DocumentWorkspace.document_id)
                    .filter(DocumentWorkspace.workspace_id == workspace_id)
                )
                result = await self.db.execute(stmt)
                document_ids = [str(doc_id) for doc_id, in result.fetchall()]
                
                if document_ids:
                    # 直接使用document_id作为过滤条件
                    where_filter = {"document_id": {"$in": document_ids}}
                    self.logger.info(f"Searching in workspace {workspace_id} with documents: {document_ids}")
                    self.logger.debug(f"Using filter: {where_filter}")

            # 3. 使用Chroma进行向量检索
            try:
                results = await vector_store.query_similar(
                    query_embedding=query_embedding,
                    n_results=limit,
                    where=where_filter
                )
                self.logger.info(f"Chroma search completed")
                
                # 打印原始结果
                if results and results.get("ids") and results["ids"][0]:
                    self.logger.info("Chroma raw results:")
                    for i, (doc_id, distance) in enumerate(zip(results["ids"][0], results["distances"][0])):
                        self.logger.info(f"  Document {doc_id}: distance={distance:.4f}, similarity={1-distance:.4f}")
                else:
                    self.logger.info("No results from Chroma")
                    
            except Exception as e:
                self.logger.error(f"Chroma search error: {str(e)}")
                return []

            # 4. 处理检索结果
            similarities = []
            if results and results.get("ids") and results["ids"][0]:
                for i, (doc_id, distance, metadata) in enumerate(zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0]
                )):
                    # 使用Chroma返回的相似度分数
                    # 余弦距离 = 1 - 余弦相似度
                    # 所以余弦相似度 = 1 - 余弦距离
                    similarity = 1 - distance
                    self.logger.info(f"Processing result {i+1}: distance={distance:.4f}, similarity={similarity:.4f}")
                    
                    # 获取文档段落信息
                    segment_result = await self.db.execute(
                        select(DocumentSegment)
                        .filter(DocumentSegment.chroma_id == doc_id)
                    )
                    segment = segment_result.scalar_one_or_none()
                    
                    if segment:
                        # 获取文档信息
                        document_result = await self.db.execute(
                            select(Document).filter(Document.id == segment.document_id)
                        )
                        document = document_result.scalar_one_or_none()
                        
                        if document:
                            self.logger.info(f"Found matching segment {segment.id} from document {document.name} with similarity {similarity:.4f}")
                            similarities.append({
                                'segment_id': segment.id,
                                'document_id': segment.document_id,
                                'content': segment.content,
                                'similarity': float(similarity),
                                'document_name': document.name,
                                'page_number': segment.page_number,
                                'bbox_x': segment.bbox_x,
                                'bbox_y': segment.bbox_y,
                                'bbox_width': segment.bbox_width,
                                'bbox_height': segment.bbox_height
                            })

            # 5. 按相似度降序排序
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 记录检索结果
            self.logger.info(f"Found {len(similarities)} relevant segments")
            for sim in similarities[:limit]:
                self.logger.info(f"Document: {sim['document_name']}, Similarity: {sim['similarity']:.4f}")
                self.logger.info(f"Content preview: {sim['content'][:100]}...")

            return similarities[:limit]

        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            raise

    def _compute_similarity(self, query_embedding: List[float], doc_embedding: List[float]) -> float:
        """计算余弦相似度"""
        try:
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {str(e)}")
            return 0.0 