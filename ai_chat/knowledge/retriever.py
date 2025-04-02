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
            query_embedding = query_embedding.flatten().tolist()
            self.logger.info(f"Generated query embedding")

            # 2. 构建Chroma查询条件
            where_filter = None
            if workspace_id:
                # 首先检查工作空间中的文档
                stmt = (
                    select(DocumentWorkspace.document_id, Document.name)
                    .join(Document)
                    .filter(DocumentWorkspace.workspace_id == workspace_id)
                )
                result = await self.db.execute(stmt)
                workspace_docs = result.fetchall()
                
                if workspace_docs:
                    document_ids = [str(doc_id) for doc_id, _ in workspace_docs]
                    self.logger.info(f"Found {len(workspace_docs)} documents in workspace {workspace_id}:")
                    for doc_id, doc_name in workspace_docs:
                        self.logger.info(f"  Document {doc_id}: {doc_name}")
                    
                    # 确保文档ID是字符串类型
                    where_filter = {"document_id": {"$in": document_ids}}
                    self.logger.info(f"Using where filter: {where_filter}")
                else:
                    self.logger.warning(f"No documents found in workspace {workspace_id}")
                    return []

            # 3. 使用Chroma进行向量检索
            try:
                # 增加检索数量以提高召回率
                n_results = limit * 10  # 增加检索数量
                self.logger.info(f"Searching with n_results={n_results}, where_filter={where_filter}")
                
                # 对每个文档分别进行查询
                all_results = []
                if workspace_docs:
                    for doc_id, doc_name in workspace_docs:
                        doc_filter = {"document_id": str(doc_id)}
                        self.logger.info(f"Querying document {doc_id} ({doc_name})")
                        
                        doc_results = await vector_store.query_similar(
                            query_embedding=query_embedding,
                            n_results=n_results,
                            where=doc_filter
                        )
                        
                        if doc_results and doc_results.get("ids") and doc_results["ids"][0]:
                            all_results.append(doc_results)
                            self.logger.info(f"Found {len(doc_results['ids'][0])} results for document {doc_id}")
                
                # 合并所有文档的结果
                if all_results:
                    # 合并所有文档的ID、距离和元数据
                    combined_ids = []
                    combined_distances = []
                    combined_metadatas = []
                    
                    for result in all_results:
                        combined_ids.extend(result["ids"][0])
                        combined_distances.extend(result["distances"][0])
                        combined_metadatas.extend(result["metadatas"][0])
                    
                    # 按距离排序
                    sorted_indices = np.argsort(combined_distances)
                    results = {
                        "ids": [combined_ids],
                        "distances": [combined_distances],
                        "metadatas": [combined_metadatas]
                    }
                else:
                    results = {"ids": [[]], "distances": [[]], "metadatas": [[]]}
                
                self.logger.info(f"Chroma search completed")
                
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
                    # 修正相似度计算
                    similarity = 1 - (distance / 2)
                    
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
                            # 计算文本相关性分数
                            text_relevance = self._compute_text_relevance(query, segment.content)
                            
                            # 综合相似度 = 向量相似度 * 0.6 + 文本相关性 * 0.4
                            combined_similarity = similarity * 0.6 + text_relevance * 0.4
                            
                            # 只有当综合相似度超过阈值时才添加结果
                            if combined_similarity >= 0.5:  # 提高相似度阈值
                                self.logger.info(f"Found matching segment {segment.id} from document {document.name} (ID: {document.id}) with combined similarity {combined_similarity:.4f}")
                                self.logger.info(f"Segment content preview: {segment.content[:100]}...")

                                similarities.append({
                                    'segment_id': segment.id,
                                    'document_id': segment.document_id,
                                    'content': segment.content,
                                    'similarity': float(combined_similarity),
                                    'document_name': document.name,
                                    'page_number': segment.page_number,
                                    'bbox_x': segment.bbox_x,
                                    'bbox_y': segment.bbox_y,
                                    'bbox_width': segment.bbox_width,
                                    'bbox_height': segment.bbox_height
                                })

            # 5. 按相似度降序排序
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 限制返回结果数量为2个最相关的段落
            similarities = similarities[:2]
            
            # 记录最终检索结果
            self.logger.info(f"Found {len(similarities)} relevant segments")
            for sim in similarities:
                self.logger.info(f"Final result - Document: {sim['document_name']} (ID: {sim['document_id']}), "
                               f"Similarity: {sim['similarity']:.4f}, Page: {sim['page_number']}")
                self.logger.info(f"Content preview: {sim['content'][:100]}...")

            return similarities

        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            raise

    def _compute_text_relevance(self, query: str, content: str) -> float:
        """计算文本相关性分数，考虑标题和列表的权重"""
        try:
            # 将查询和内容转换为小写
            query = query.lower()
            content = content.lower()
            
            # 计算关键词匹配度
            query_words = set(query.split())
            content_words = set(content.split())
            matching_words = query_words.intersection(content_words)
            
            # 计算匹配分数
            if len(query_words) == 0:
                return 0.0
            
            # 计算基础分数
            base_score = len(matching_words) / len(query_words)
            
            # 考虑完整短语匹配
            phrase_bonus = 0.0
            if query in content:
                phrase_bonus = 0.3  # 降低完整短语匹配的权重
            
            # 检查是否是标题或列表
            is_title = any(line.startswith(('#', '##', '###')) for line in content.split('\n')) or content.isupper()
            is_list = any(line.strip().startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.')) 
                         for line in content.split('\n'))
            
            # 添加标题和列表的权重
            structure_bonus = 0.0
            if is_title:
                structure_bonus += 0.2  # 降低标题权重
            if is_list:
                structure_bonus += 0.2
            
            # 计算关键词密度
            density_score = 0.0
            content_length = len(content.split())
            if content_length > 0:
                keyword_density = len(matching_words) / content_length
                density_score = min(0.2, keyword_density * 2)  # 降低密度分数上限
            
            # 返回综合分数
            final_score = min(1.0, base_score + phrase_bonus + structure_bonus + density_score)

            # 记录详细的评分信息
            self.logger.info(f"Text relevance scores - Base: {base_score:.2f}, Phrase: {phrase_bonus:.2f}, "
                           f"Structure: {structure_bonus:.2f}, Density: {density_score:.2f}, Final: {final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"Error computing text relevance: {str(e)}")
            return 0.0

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