import hashlib
import io
import json
import logging
import os
from typing import List, Optional, BinaryIO, Any

import PyPDF2
import numpy as np
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.dataset import Dataset as DBDataset
from ..models.document import Document as DBDocument, DocumentSegment as DBDocumentSegment
from ..models.workspace import Workspace as DBWorkspace
from ..services.vector_store import vector_store
from ..utils.embeddings import EmbeddingFactory
from ..utils.file_processor import process_file
from ..utils.text_splitter import split_text
from ..config import DOCUMENT_PROCESSING

logger = logging.getLogger(__name__)

class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_factory = EmbeddingFactory()
        self.logger = logging.getLogger(__name__)  # 添加 logger 初始化
        self.max_segment_length = DOCUMENT_PROCESSING["max_segment_length"]
        self.overlap_length = DOCUMENT_PROCESSING["overlap_length"]
        self.min_segment_length = DOCUMENT_PROCESSING["min_segment_length"]
        self.max_segments_per_page = DOCUMENT_PROCESSING["max_segments_per_page"]
        
    async def get_datasets(self) -> List[DBDataset]:
        """获取所有知识库列表"""
        result = await self.db.execute(select(DBDataset))
        return result.scalars().all()
        
    async def create_dataset(self, name: str, description: Optional[str] = None) -> DBDataset:
        """创建新的知识库"""
        dataset = DBDataset(
            name=name,
            description=description
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get_documents(self) -> List[DBDocument]:
        """获取所有文档"""
        result = await self.db.execute(select(DBDocument))
        return result.scalars().all()

    async def get_document(self, document_id: int) -> Optional[DBDocument]:
        """获取单个文档"""
        result = await self.db.execute(
            select(DBDocument).filter(DBDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def _extract_text_from_pdf(self, file: BinaryIO) -> str:
        """从PDF文件中提取文本"""
        try:
            # 读取PDF文件
            pdf_content = file.read()
            logger.info(f"Read PDF file content: {len(pdf_content)} bytes")
            
            pdf_file = io.BytesIO(pdf_content)
            
            # 使用PyPDF2读取PDF
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            logger.info(f"PDF has {len(pdf_reader.pages)} pages")
            
            # 提取所有页面的文本
            text_content = []
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                logger.info(f"Page {i+1} extracted text length: {len(page_text)}")
                text_content.append(page_text)
            
            final_text = "\n".join(text_content)
            logger.info(f"Total extracted text length: {len(final_text)}")
            return final_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise

    def _convert_to_native_types(self, obj):
        """递归转换numpy类型为Python原生类型"""
        if isinstance(obj, np.ndarray):
            return self._convert_to_native_types(obj.tolist())
        elif isinstance(obj, list):
            return [self._convert_to_native_types(item) for item in obj]
        elif isinstance(obj, np.number):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        return obj

    async def _calculate_file_hash(self, file: BinaryIO) -> str:
        """计算文件的 SHA256 哈希值"""
        sha256_hash = hashlib.sha256()
        # 保存当前文件指针位置
        current_position = file.tell()
        # 重置文件指针到开头
        file.seek(0)
        
        # 分块读取文件并更新哈希值
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)
            
        # 恢复文件指针位置
        file.seek(current_position)
        return sha256_hash.hexdigest()

    async def _get_next_version(self, file_hash: str, original_name: str) -> int:
        """获取文件的下一个版本号"""
        # 使用子查询获取最大版本号
        result = await self.db.execute(
            select(func.max(DBDocument.version))
            .filter(
                DBDocument.file_hash == file_hash,
                DBDocument.original_name == original_name
            )
        )
        max_version = result.scalar() or 0
        return max_version + 1

    async def _get_unique_filename(self, original_name: str, file_hash: str, version: int) -> str:
        """生成唯一的文件名"""
        name, ext = os.path.splitext(original_name)
        return f"{name}_v{version}_{file_hash[:8]}{ext}"

    async def process_document(
        self,
        file: Any,
        filename: str,
        mime_type: str,
        dataset_id: int
    ) -> DBDocument:
        """处理上传的文档"""
        try:
            logger.info(f"Starting to process document: {filename} with mime type: {mime_type}")
            
            # 获取默认数据集
            result = await self.db.execute(select(DBDataset).filter(DBDataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            if not dataset:
                dataset = DBDataset(name="default", description="Default dataset")
                self.db.add(dataset)
                await self.db.commit()
                logger.info("Created default dataset")

            # 获取文件大小
            file.seek(0, 2)  # 移动到文件末尾
            file_size = file.tell()  # 获取文件大小
            file.seek(0)  # 重置文件指针到开头
            logger.info(f"File size: {file_size} bytes")

            # 计算文件哈希值
            file_hash = await self._calculate_file_hash(file)
            logger.info(f"File hash: {file_hash}")

            # 获取下一个版本号
            version = await self._get_next_version(file_hash, filename)
            logger.info(f"Next version: {version}")
            
            # 生成唯一的文件名
            unique_filename = await self._get_unique_filename(filename, file_hash, version)
            file_path = os.path.join("uploads", unique_filename)

            # 保存文件到文件系统
            with open(file_path, "wb") as f:
                f.write(file.read())
            logger.info(f"Saved new file to: {file_path}")
            
            file.seek(0)  # 重置文件指针

            # 处理文件并获取文本内容和位置信息
            content, mime_type, text_blocks = process_file(file_path)
            logger.info(f"Processed file content length: {len(content)} characters")
            logger.info(f"Number of text blocks: {len(text_blocks)}")

            if not content.strip():
                raise ValueError("Extracted content is empty")

            # 创建文档记录
            document = DBDocument(
                name=filename,
                file_path=file_path,
                file_hash=file_hash,
                size=file_size,
                mime_type=mime_type,
                version=version,
                dataset_id=dataset.id,
                original_name=filename
            )
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
            logger.info(f"Created document record with ID: {document.id}")

            # 按页面组织文本块
            page_blocks = {}
            for block in text_blocks:
                page_num = block['page_number']
                if page_num not in page_blocks:
                    page_blocks[page_num] = []
                page_blocks[page_num].append(block)
            
            # 为每个页面分别处理文本块
            segment_records = []
            embeddings_batch = []
            ids_batch = []
            documents_batch = []
            
            for page_num, blocks in page_blocks.items():
                # 按位置排序文本块
                blocks.sort(key=lambda x: (x['bbox_y'], x['bbox_x']))
                
                # 合并同一页面的文本
                page_text = "\n".join(block['text'] for block in blocks)
                
                # 分割页面文本
                page_segments = self._split_text(page_text)
                
                # 处理每个段落
                for i, segment in enumerate(page_segments):
                    if not segment.strip():
                        continue
                        
                    # 生成embedding
                    embedding = await self.embedding_factory.get_embeddings(segment)
                    
                    # 确保 embedding 是一维列表
                    if isinstance(embedding, np.ndarray):
                        embedding = embedding.tolist()
                    elif isinstance(embedding, list) and len(embedding) == 1:
                        # 如果是嵌套列表，获取内部向量
                        if isinstance(embedding[0], (list, np.ndarray)):
                            embedding = embedding[0]
                            if isinstance(embedding, np.ndarray):
                                embedding = embedding.tolist()
                    
                    logger.info(f"Embedding type: {type(embedding)}, shape/length: {len(embedding) if isinstance(embedding, list) else 'unknown'}")
                    
                    # 找到段落对应的文本块
                    matching_blocks = []
                    for block in blocks:
                        if block['text'] in segment:
                            matching_blocks.append(block)
                    
                    # 如果找到匹配的块，计算合并后的边界框
                    if matching_blocks:
                        block_info = {
                            'page_number': page_num,  # 使用当前页码
                            'bbox_x': min(block['bbox_x'] for block in matching_blocks),
                            'bbox_y': min(block['bbox_y'] for block in matching_blocks),
                            'bbox_width': max(block['bbox_x'] + block['bbox_width'] for block in matching_blocks) - min(block['bbox_x'] for block in matching_blocks),
                            'bbox_height': max(block['bbox_y'] + block['bbox_height'] for block in matching_blocks) - min(block['bbox_y'] for block in matching_blocks)
                        }
                    else:
                        block_info = {'page_number': page_num}  # 至少保存页码信息
                    
                    # 生成唯一的 chroma_id
                    chroma_id = f"doc_{document.id}_seg_{len(segment_records)}"
                    
                    # 创建文档片段记录
                    segment_record = DBDocumentSegment(
                        document_id=document.id,
                        content=segment,
                        position=len(segment_records),
                        word_count=len(segment.split()),
                        tokens=len(segment),
                        page_number=block_info['page_number'],
                        bbox_x=block_info.get('bbox_x'),
                        bbox_y=block_info.get('bbox_y'),
                        bbox_width=block_info.get('bbox_width'),
                        bbox_height=block_info.get('bbox_height'),
                        chroma_id=chroma_id
                    )
                    
                    segment_records.append(segment_record)
                    embeddings_batch.append(embedding)
                    ids_batch.append(chroma_id)
                    documents_batch.append(segment)

            logger.info(f"Created {len(segment_records)} segment records")
            logger.info(f"Embeddings batch type check:")
            for i, emb in enumerate(embeddings_batch):
                logger.info(f"  Embedding {i}: type={type(emb)}, length={len(emb) if isinstance(emb, (list, np.ndarray)) else 'unknown'}")
            
            # 批量保存文档片段
            self.db.add_all(segment_records)
            await self.db.commit()
            
            # 更新元数据批处理数据
            metadatas_batch = [
                {
                    "document_id": str(document.id),
                    "segment_id": str(segment_record.id),
                    "page_number": segment_record.page_number
                }
                for segment_record in segment_records
            ]

            # 批量添加向量到 Chroma
            try:
                # 确保所有 embeddings 都是列表格式
                embeddings_batch = [
                    emb.tolist() if isinstance(emb, np.ndarray) else emb
                    for emb in embeddings_batch
                ]
                
                await vector_store.add_embeddings(
                    ids=ids_batch,
                    embeddings=embeddings_batch,
                    documents=documents_batch,
                    metadatas=metadatas_batch
                )
                logger.info(f"Added {len(ids_batch)} embeddings to vector store")
            except Exception as e:
                logger.error(f"Error adding embeddings to vector store: {str(e)}")
                logger.error(f"Embeddings types: {[type(emb) for emb in embeddings_batch]}")
                logger.error(f"First embedding example: {embeddings_batch[0][:10] if embeddings_batch else 'No embeddings'}")
                raise

            return document

        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def _split_text(self, text: str) -> List[str]:
        """将文本分割成段落，使用滑动窗口方式"""
        logger.info(f"Starting text splitting. Input text length: {len(text)}")
        
        # 首先按段落分割
        paragraphs = text.split('\n\n')
        logger.info(f"Split into {len(paragraphs)} raw paragraphs")
        
        # 处理每个段落
        segments = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果段落长度小于最大长度，直接添加
            if len(para) <= self.max_segment_length:
                segments.append(para)
                continue
            
            # 使用滑动窗口方式分割长段落
            start = 0
            while start < len(para):
                # 计算当前窗口的结束位置
                end = start + self.max_segment_length
                
                # 如果不是最后一个窗口，尝试在句子边界分割
                if end < len(para):
                    # 在最大长度范围内找到最后一个句号
                    last_period = para.rfind('。', start, end)
                    if last_period > start + self.min_segment_length:
                        end = last_period + 1
                
                # 提取当前段落
                current_segment = para[start:end].strip()
                if current_segment:
                    segments.append(current_segment)
                
                # 移动到下一个窗口，考虑重叠
                start = end - self.overlap_length
        
        logger.info(f"Final segments count: {len(segments)}")
        for i, segment in enumerate(segments):
            logger.info(f"Segment {i+1} length: {len(segment)}")
            logger.info(f"Segment {i+1} preview: {segment[:100]}...")
            
        return segments

    def _get_mime_type(self, filename: str) -> str:
        """获取文件的MIME类型"""
        if filename.endswith('.txt'):
            return 'text/plain'
        elif filename.endswith('.pdf'):
            return 'application/pdf'
        else:
            return 'application/octet-stream'

    async def delete_document(self, document_id: int) -> bool:
        """删除文档及其相关数据"""
        try:
            # 检查文档是否存在
            result = await self.db.execute(
                select(DBDocument).filter(DBDocument.id == document_id)  # 使用 DBDocument
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return False
            
            # 删除文档
            await self.db.execute(
                delete(DBDocument).where(DBDocument.id == document_id)  # 使用 DBDocument
            )
            
            await self.db.commit()
            self.logger.info(f"Successfully deleted document {document_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error deleting document and embeddings: {str(e)}")
            raise

    async def get_document_status(self, document_id: int) -> dict:
        """获取文档处理状态和详细信息"""
        try:
            # 获取文档信息
            result = await self.db.execute(
                select(DBDocument).filter(DBDocument.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return {
                    "status": "not_found",
                    "error": "Document not found",
                    "segments": 0,
                    "segments_with_embeddings": 0
                }

            # 获取文档段落信息
            result = await self.db.execute(
                select(DBDocumentSegment).filter(DBDocumentSegment.document_id == document_id)
            )
            segments = result.scalars().all()
            
            # 统计向量生成情况
            total_segments = len(segments)
            segments_with_embeddings = len([s for s in segments if s.embedding])
            
            return {
                "status": document.status,
                "error": document.error,
                "name": document.name,
                "mime_type": document.mime_type,
                "segments": total_segments,
                "segments_with_embeddings": segments_with_embeddings,
                "created_at": document.created_at.isoformat() if document.created_at else None
            }

        except Exception as e:
            logger.error(f"Error getting document status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "segments": 0,
                "segments_with_embeddings": 0
            }

    async def check_embeddings(self, document_id: int) -> dict:
        """检查文档的向量生成情况"""
        try:
            # 获取所有段落
            result = await self.db.execute(
                select(DBDocumentSegment).filter(DBDocumentSegment.document_id == document_id)
            )
            segments = result.scalars().all()
            
            # 检查每个段落的向量
            segments_status = []
            for segment in segments:
                has_embedding = bool(segment.embedding)
                embedding_length = 0
                if has_embedding:
                    try:
                        embedding_data = json.loads(segment.embedding)
                        embedding_length = len(embedding_data)
                    except:
                        has_embedding = False
                
                segments_status.append({
                    "segment_id": segment.id,
                    "content_preview": segment.content[:100] + "..." if len(segment.content) > 100 else segment.content,
                    "has_embedding": has_embedding,
                    "embedding_length": embedding_length
                })
            
            return {
                "total_segments": len(segments),
                "segments_with_embeddings": len([s for s in segments_status if s["has_embedding"]]),
                "segments_details": segments_status
            }
            
        except Exception as e:
            logger.error(f"Error checking embeddings: {str(e)}")
            return {
                "error": str(e),
                "total_segments": 0,
                "segments_with_embeddings": 0,
                "segments_details": []
            }

    async def get_dataset(self, dataset_id: int) -> DBDataset:
        """获取数据集"""
        result = await self.db.execute(
            select(DBDataset).filter(DBDataset.id == dataset_id)
        )
        return result.scalar_one_or_none()

    async def get_workspace(self, workspace_id: int) -> DBWorkspace:
        """获取工作空间"""
        result = await self.db.execute(
            select(DBWorkspace).filter(DBWorkspace.id == workspace_id)
        )
        return result.scalar_one_or_none() 