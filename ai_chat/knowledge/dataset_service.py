import os
from typing import List, Optional, BinaryIO, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from ..models.document import Document as DBDocument, DocumentSegment as DBDocumentSegment
from ..utils.file_processor import process_file
from ..utils.text_splitter import split_text
from ..utils.embeddings import EmbeddingFactory
from ..services.vector_store import vector_store
import asyncio
import chardet
import logging
import json
import numpy as np
from io import BytesIO
import re
import PyPDF2
import io
from datetime import datetime
from ..models.dataset import Dataset as DBDataset
from ..models.types import DocumentSegmentCreate
from ..models.workspace import Workspace as DBWorkspace
import hashlib
import shutil

logger = logging.getLogger(__name__)

class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_factory = EmbeddingFactory()
        self.logger = logging.getLogger(__name__)  # 添加 logger 初始化
        
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

            # 根据文件类型提取文本
            if mime_type == 'application/pdf':
                logger.info("Processing PDF file")
                content = await self._extract_text_from_pdf(file)
                logger.info(f"Extracted text from PDF: {len(content)} characters")
            else:
                # 处理文本文件
                raw_content = file.read()
                # 检测编码
                result = chardet.detect(raw_content)
                encoding = result['encoding'] if result['encoding'] else 'utf-8'
                content = raw_content.decode(encoding)
                logger.info(f"Read text file with encoding {encoding}")

            if not content.strip():
                raise ValueError("Extracted content is empty")

            # 创建文档记录
            document = DBDocument(
                name=unique_filename,
                original_name=filename,
                mime_type=mime_type,
                size=file_size,
                content=content,
                file_path=file_path,
                file_hash=file_hash,
                version=version,
                status="pending",
                dataset_id=dataset_id,
                created_at=datetime.now()
            )
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)
            logger.info(f"Created document record with ID: {document.id}")

            # 分段并生成向量表示
            segments = self._split_text(content)
            logger.info(f"Split text into {len(segments)} segments")
            
            for i, segment_content in enumerate(segments, 1):
                try:
                    logger.info(f"Processing segment {i}/{len(segments)}")
                    # 获取embedding
                    embeddings = await self.embedding_factory.get_embeddings(segment_content)
                    logger.info(f"Raw embedding type: {type(embeddings)}")
                    
                    # 转换embedding为原生Python类型并确保正确的格式
                    embeddings = self._convert_to_native_types(embeddings)
                    # 确保是一维列表
                    if isinstance(embeddings, list) and isinstance(embeddings[0], list) and isinstance(embeddings[0][0], list):
                        embeddings = embeddings[0][0]  # 取出内层列表
                    elif isinstance(embeddings, list) and isinstance(embeddings[0], list):
                        embeddings = embeddings[0]  # 取出内层列表
                    
                    logger.info(f"Converted embedding type: {type(embeddings)}, length: {len(embeddings)}")
                    logger.info(f"Embedding format check - is list: {isinstance(embeddings, list)}")
                    logger.info(f"First few values: {embeddings[:5]}")

                    # 生成唯一的chroma_id
                    chroma_id = f"{document.id}_{i}"

                    # 将embedding存储到Chroma
                    try:
                        await vector_store.add_embeddings(
                            ids=[chroma_id],
                            embeddings=[embeddings],  # 现在应该是正确的格式
                            documents=[segment_content],
                            metadatas=[{
                                "document_id": str(document.id),
                                "segment_id": i,
                                "segment_position": i,
                                "document_name": document.name
                            }]
                        )
                        logger.info(f"Successfully added embedding to Chroma for segment {i}")

                        # 创建文档段落记录
                        segment = DBDocumentSegment(
                            document_id=document.id,
                            content=segment_content,
                            chroma_id=chroma_id,
                            position=i,
                            word_count=len(segment_content.split()),
                            tokens=len(segment_content),
                            status="completed",
                            dataset_id=dataset.id
                        )
                        self.db.add(segment)
                        logger.info(f"Created document segment record for segment {i}")

                    except Exception as e:
                        logger.error(f"Error adding embedding to Chroma for segment {i}: {str(e)}")
                        logger.error(f"Embedding shape: {len(embeddings) if embeddings else 'None'}")
                        logger.error(f"Document ID: {document.id}, Segment position: {i}")
                        logger.error(f"Full error details:", exc_info=True)
                        # 创建失败状态的段落记录
                        segment = DBDocumentSegment(
                            document_id=document.id,
                            content=segment_content,
                            position=i,
                            word_count=len(segment_content.split()),
                            tokens=len(segment_content),
                            status="failed",
                            dataset_id=dataset.id
                        )
                        self.db.add(segment)
                        await self.db.commit()  # 立即提交以避免后续错误影响
                        logger.info(f"Created failed document segment record for segment {i}")

                except Exception as e:
                    logger.error(f"Error processing segment {i}: {str(e)}")
                    logger.error(f"Full error details:", exc_info=True)
                    # 创建失败状态的段落记录
                    segment = DBDocumentSegment(
                        document_id=document.id,
                        content=segment_content,
                        position=i,
                        word_count=len(segment_content.split()),
                        tokens=len(segment_content),
                        status="failed",
                        dataset_id=dataset.id
                    )
                    self.db.add(segment)
                    await self.db.commit()  # 立即提交以避免后续错误影响
                    logger.info(f"Created failed document segment record for segment {i}")

            # 更新文档状态
            document.status = "completed"
            await self.db.commit()
            logger.info(f"Document processing completed. ID: {document.id}")
            
            return document
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            if document:
                document.status = "failed"
                document.error = str(e)
                await self.db.commit()
            raise

    def _split_text(self, text: str, max_length: int = 1000) -> List[str]:
        """将文本分割成段落"""
        logger.info(f"Starting text splitting. Input text length: {len(text)}")
        
        # 按段落分割
        paragraphs = text.split('\n\n')
        logger.info(f"Split into {len(paragraphs)} raw paragraphs")
        
        # 处理每个段落
        segments = []
        current_segment = ""
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 如果当前段落加上已有内容不超过最大长度，则添加到当前片段
            if current_length + len(para) <= max_length:
                current_segment += para + "\n\n"
                current_length += len(para)
            else:
                # 如果当前片段不为空，保存它
                if current_segment:
                    segments.append(current_segment.strip())
                # 开始新的片段
                current_segment = para + "\n\n"
                current_length = len(para)
        
        # 添加最后一个片段
        if current_segment:
            segments.append(current_segment.strip())
        
        logger.info(f"Final segments count: {len(segments)}")
        for i, segment in enumerate(segments):
            logger.info(f"Segment {i+1} length: {len(segment)}")
            
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