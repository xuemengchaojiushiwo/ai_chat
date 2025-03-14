from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..utils.embeddings import EmbeddingFactory
import numpy as np
import logging
import json
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

# SQLAlchemy models - 只保留一个 DocumentSegment 导入
from ..models.document import Document, DocumentSegment, DocumentWorkspace

# Pydantic models
from ..models.types import (
    DocumentResponse,
    DocumentSegmentResponse
)

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, db: Session):
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

    async def search_with_embedding(self, query: str, limit: int = 3) -> List[Dict]:
        """搜索相关文档段落"""
        try:
            # 1. 获取查询的向量表示
            self.logger.info(f"Processing query: {query}")
            query_embedding = await self.embedding_factory.get_embeddings(query)
            if not isinstance(query_embedding, np.ndarray):
                query_embedding = np.array(query_embedding)
            query_embedding = query_embedding.flatten()
            self.logger.info(f"Query embedding shape: {query_embedding.shape}")

            # 2. 获取所有文档片段
            stmt = select(DocumentSegment).join(Document)
            result = await self.db.execute(stmt)
            segments = result.scalars().all()
            self.logger.info(f"Found {len(segments)} total segments")

            # 3. 计算相似度并排序
            similarities = []
            for segment in segments:
                try:
                    if not segment.embedding:
                        self.logger.warning(f"Segment {segment.id} has no embedding")
                        continue
                    
                    # 将字符串转换为numpy数组
                    segment_embedding = np.array(json.loads(segment.embedding))
                    if not isinstance(segment_embedding, np.ndarray):
                        segment_embedding = np.array(segment_embedding)
                    segment_embedding = segment_embedding.flatten()

                    # 确保向量维度匹配
                    if query_embedding.shape != segment_embedding.shape:
                        self.logger.warning(f"Shape mismatch: query {query_embedding.shape} vs segment {segment_embedding.shape}")
                        continue

                    # 计算余弦相似度
                    similarity = cosine_similarity(
                        query_embedding.reshape(1, -1),
                        segment_embedding.reshape(1, -1)
                    )[0][0]

                    # 获取文档信息
                    document = await self.db.get(Document, segment.document_id)
                    if not document:
                        self.logger.warning(f"Document not found for segment {segment.id}")
                        continue

                    self.logger.info(f"Segment {segment.id} from {document.name}: similarity = {similarity:.4f}")
                    self.logger.info(f"Content preview: {segment.content[:100]}...")

                    similarities.append({
                        'segment_id': segment.id,
                        'document_id': segment.document_id,
                        'content': segment.content,
                        'similarity': float(similarity),
                        'document_name': document.name
                    })

                except Exception as e:
                    self.logger.error(f"Error processing segment {segment.id}: {str(e)}")
                    continue

            # 4. 按相似度降序排序并返回前N个结果
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 记录最终选择的结果
            self.logger.info("Selected segments:")
            for sim in similarities[:limit]:
                self.logger.info(f"Document: {sim['document_name']}, Similarity: {sim['similarity']:.4f}")
                self.logger.info(f"Content: {sim['content'][:100]}...")

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