import hashlib
import json
import logging
import os
import re
from typing import List, BinaryIO, Any

import numpy as np
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DOCUMENT_PROCESSING
from ..models.dataset import Dataset as DBDataset
from ..models.document import Document as DBDocument, DocumentSegment as DBDocumentSegment
from ..models.workspace import Workspace as DBWorkspace
from ..services.vector_store import vector_store
from ..utils.embeddings import EmbeddingFactory
from ..utils.file_processor import process_file

logger = logging.getLogger(__name__)

class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_factory = EmbeddingFactory()
        self.logger = logging.getLogger(__name__)
        self.max_segment_length = DOCUMENT_PROCESSING["max_segment_length"]
        self.overlap_length = DOCUMENT_PROCESSING["overlap_length"]
        self.min_segment_length = DOCUMENT_PROCESSING["min_segment_length"]
        self.max_segments_per_page = DOCUMENT_PROCESSING["max_segments_per_page"]
        




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
            logger.info(f"开始处理文档: {filename}")
            
            # 获取数据集
            result = await self.db.execute(select(DBDataset).filter(DBDataset.id == dataset_id))
            dataset = result.scalar_one_or_none()
            if not dataset:
                dataset = DBDataset(name="default", description="Default dataset")
                self.db.add(dataset)
                await self.db.commit()
                logger.info("创建默认数据集")

            # 计算文件哈希值
            file_hash = await self._calculate_file_hash(file)
            version = await self._get_next_version(file_hash, filename)
            unique_filename = await self._get_unique_filename(filename, file_hash, version)
            file_path = os.path.join("uploads", unique_filename)

            # 保存文件
            with open(file_path, "wb") as f:
                f.write(file.read())
            file.seek(0)

            # 创建文档记录
            document = DBDocument(
                name=filename,
                file_path=file_path,
                file_hash=file_hash,
                size=file.tell(),
                mime_type=mime_type,
                version=version,
                dataset_id=dataset.id,
                original_name=filename
            )
            self.db.add(document)
            await self.db.commit()
            await self.db.refresh(document)

            # 处理文件并获取文本内容和位置信息
            content, mime_type, text_blocks = process_file(file_path)
            logger.info(f"Processed file content length: {len(content)} characters")
            logger.info(f"Number of text blocks: {len(text_blocks)}")

            if not content.strip():
                raise ValueError("Extracted content is empty")

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

            # 如果没有文本块，将整个内容作为一个块处理
            if not page_blocks:
                logger.info("No text blocks found, processing entire content as one block")
                if mime_type == 'text/plain':
                    # 对于文本文档，我们使用行号作为定位依据
                    lines = content.split('\n')
                    line_blocks = []
                    
                    # 每10行作为一个块，这样可以更好地定位
                    for i in range(0, len(lines), 10):
                        block_lines = lines[i:i+10]
                        line_blocks.append({
                            'text': '\n'.join(block_lines),
                            'page_number': 0,
                            'line_number': i + 1,  # 使用行号作为定位依据
                            'line_count': len(block_lines)  # 使用行数作为高度
                        })
                    
                    page_blocks = {0: line_blocks}
                else:
                    # 对于其他类型的文档，使用默认处理方式
                    page_blocks = {0: [{'text': content, 'page_number': 0, 'position': {'x0': 0, 'y0': 0, 'x1': 0, 'y1': 0}}]}

            for page_num, blocks in page_blocks.items():
                # 按位置排序文本块
                if mime_type == 'text/plain':
                    blocks.sort(key=lambda x: (x.get('line_number', 0), x.get('position', {}).get('x0', 0)))
                else:
                    blocks.sort(key=lambda x: (x.get('position', {}).get('y0', 0), x.get('position', {}).get('x0', 0)))
                
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
                    
                    # 找到段落对应的文本块
                    matching_blocks = []
                    for block in blocks:
                        if block['text'] in segment:
                            matching_blocks.append(block)
                    
                    # 根据文档类型处理定位信息
                    if mime_type == 'text/plain':
                        # 文本文档使用行号定位
                        if matching_blocks:
                            block_info = {
                                'page_number': page_num,
                                'line_number': matching_blocks[0].get('line_number', matching_blocks[0].get('position', {}).get('y0', 0)),
                                'line_count': matching_blocks[0].get('line_count', matching_blocks[0].get('position', {}).get('y1', 1) - matching_blocks[0].get('position', {}).get('y0', 0))
                            }
                        else:
                            # 对于没有匹配块的情况，使用段落在文本中的位置
                            line_number = content.count('\n', 0, content.find(segment)) + 1
                            block_info = {
                                'page_number': page_num,
                                'line_number': line_number,
                                'line_count': segment.count('\n') + 1
                            }
                    else:
                        # PDF文档使用坐标定位
                        if matching_blocks:
                            positions = [block.get('position', {}) for block in matching_blocks]
                            block_info = {
                                'page_number': page_num,
                                'bbox_x': min(pos.get('x0', 0) for pos in positions),
                                'bbox_y': min(pos.get('y0', 0) for pos in positions),
                                'bbox_width': max(pos.get('x1', 0) for pos in positions) - min(pos.get('x0', 0) for pos in positions),
                                'bbox_height': max(pos.get('y1', 0) for pos in positions) - min(pos.get('y0', 0) for pos in positions)
                            }
                        else:
                            block_info = {
                                'page_number': page_num,
                                'bbox_x': 0,
                                'bbox_y': 0,
                                'bbox_width': 0,
                                'bbox_height': 0
                            }
                    
                    # 检查是否是表格单元格
                    is_table = False
                    is_key_value = False
                    row_y = None
                    has_numbers = False
                    has_dates = False
                    table_data = []
                    
                    # 检查文本是否包含表格特征
                    if any(char.isdigit() for char in segment) and any(char in segment for char in ['-', '/']):
                        # 检查是否包含日期格式
                        date_patterns = [r'\d{2}-\d{2}-\d{4}', r'\d{2}/\d{2}/\d{4}']
                        for pattern in date_patterns:
                            if re.search(pattern, segment):
                                is_table = True
                                has_dates = True
                                break
                    
                    # 检查是否是键值对表格
                    lines = segment.split('\n')
                    if len(lines) >= 2:
                        # 检查是否包含冒号分隔的键值对
                        key_value_pairs = [line for line in lines if ':' in line]
                        if len(key_value_pairs) >= 2:
                            is_key_value = True
                            is_table = False  # 键值对表格不作为普通表格处理
                    
                    for block in matching_blocks:
                        if block.get('block_type') == 'table_cell':
                            is_table = True
                            row_y = block.get('metadata', {}).get('row_y')
                            # 提取表格数据
                            if 'text' in block:
                                table_data.append({
                                    'text': block['text'],
                                    'position': block.get('position', {}),
                                    'metadata': block.get('metadata', {})
                                })
                        if block.get('metadata', {}).get('has_numbers', False):
                            has_numbers = True
                        if block.get('metadata', {}).get('has_dates', False):
                            has_dates = True
                    
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
                        bbox_x=block_info.get('bbox_x', 0),
                        bbox_y=block_info.get('bbox_y', block_info.get('line_number', 0)),
                        bbox_width=block_info.get('bbox_width', 0),
                        bbox_height=block_info.get('bbox_height', block_info.get('line_count', 0)),
                        chroma_id=chroma_id,
                        metadata=json.dumps({
                            'is_table': is_table,
                            'is_key_value': is_key_value,
                            'row_y': float(row_y) if row_y is not None else None,
                            'has_numbers': has_numbers,
                            'has_dates': has_dates,
                            'table_data': table_data if table_data else None,
                            'content_type': 'key_value' if is_key_value else ('table' if is_table else 'text')
                        }) if matching_blocks else None
                    )
                    
                    segment_records.append(segment_record)
                    embeddings_batch.append(embedding)
                    ids_batch.append(chroma_id)
                    documents_batch.append(segment)

            # 批量保存文档片段
            self.db.add_all(segment_records)
            await self.db.commit()

            # 准备元数据
            metadatas_batch = []
            for segment_record in segment_records:
                metadata = {
                    "document_id": str(document.id),
                    "segment_id": str(segment_record.id),
                    "page_number": segment_record.page_number
                }
                
                if segment_record.metadata:
                    try:
                        metadata.update(json.loads(segment_record.metadata))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse metadata for segment {segment_record.id}")
                
                # 确保所有元数据值都是基本类型
                for key, value in metadata.items():
                    if value is None:
                        metadata[key] = ""  # 将 None 转换为空字符串
                    elif isinstance(value, (list, dict)):
                        metadata[key] = str(value)  # 将复杂类型转换为字符串
                
                metadatas_batch.append(metadata)

            # 批量添加向量到向量存储
            try:
                await vector_store.add_embeddings(
                    ids=ids_batch,
                    embeddings=embeddings_batch,
                    documents=documents_batch,
                    metadatas=metadatas_batch
                )
                logger.info(f"成功添加 {len(ids_batch)} 个向量到向量存储")
            except Exception as e:
                logger.error(f"添加向量到向量存储时出错: {str(e)}")
                raise

            return document

        except Exception as e:
            logger.error(f"处理文档时出错: {str(e)}")
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
            
            # 检查是否是表格数据
            is_table = False
            if any(char.isdigit() for char in para) and any(char in para for char in ['-', '/']):
                # 检查是否包含日期格式
                date_patterns = [r'\d{2}-\d{2}-\d{4}', r'\d{2}/\d{2}/\d{4}']
                for pattern in date_patterns:
                    if re.search(pattern, para):
                        is_table = True
                        break
            
            # 如果是表格数据，保持完整
            if is_table:
                segments.append(para)
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