from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, func, and_
from typing import List, Optional
from ..database import get_db
from pydantic import BaseModel
from datetime import datetime
import os
import mimetypes
from pathlib import Path
from ..models.document import Document as DBDocument, DocumentWorkspace, DocumentSegment
from ..models.workspace import Workspace as DBWorkspace
from ..knowledge.dataset_service import DatasetService
from ..models.dataset import Dataset as DBDataset
import logging
from ..models.types import Document as DocumentSchema
import io
import numpy as np
from ..utils.embeddings import EmbeddingFactory, get_embedding
from ..services.vector_store import vector_store

# 配置日志
logger = logging.getLogger(__name__)

# 定义依赖函数
async def get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    return DatasetService(db)

router = APIRouter(
    tags=["documents"]
)

# 支持的文件类型
SUPPORTED_MIME_TYPES = {
    # PDF文件
    'application/pdf': '.pdf',
    
    # Word文件
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    
    # Excel文件
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    
    # 文本文件
    'text/plain': '.txt',
    'text/csv': '.csv',
}

# 数据模型
class DocumentBase(BaseModel):
    name: str
    description: str = None
    file_type: str
    size: int

class DocumentCreate(DocumentBase):
    content: str
    mime_type: str

class DocumentResponse(DocumentBase):
    id: int
    dataset_id: int
    content: Optional[str] = None
    mime_type: str
    status: str
    error: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class ResetResponse(BaseModel):
    status: str
    message: str

def format_size(size_in_bytes: int) -> str:
    """将字节大小转换为人类可读的格式（KB或MB）"""
    if size_in_bytes < 1024 * 1024:  # 小于1MB
        return f"{size_in_bytes / 1024:.1f}KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f}MB"

@router.get("/documents/list", response_model=List[DocumentSchema])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    show_all_versions: bool = Query(True, description="是否显示所有版本")
):
    """获取文档列表"""
    try:
        service = DatasetService(db)
        
        # 构建查询
        query = select(DBDocument)
        
        # 如果不显示所有版本，只显示每个文件的最新版本
        if not show_all_versions:
            subquery = (
                select(
                    DBDocument.file_hash,
                    DBDocument.original_name,
                    func.max(DBDocument.version).label('max_version')
                )
                .group_by(DBDocument.file_hash, DBDocument.original_name)
                .subquery()
            )
            
            query = (
                select(DBDocument)
                .join(
                    subquery,
                    and_(
                        DBDocument.file_hash == subquery.c.file_hash,
                        DBDocument.original_name == subquery.c.original_name,
                        DBDocument.version == subquery.c.max_version
                    )
                )
            )
        
        # 执行查询
        result = await db.execute(query)
        documents = result.scalars().all()
        
        # 获取每个文档关联的工作空间
        document_workspaces = {}
        for doc in documents:
            # 查询文档关联的工作空间
            workspace_result = await db.execute(
                select(DBWorkspace)
                .join(DocumentWorkspace, DocumentWorkspace.workspace_id == DBWorkspace.id)
                .filter(DocumentWorkspace.document_id == doc.id)
            )
            workspaces = workspace_result.scalars().all()
            document_workspaces[doc.id] = [
                {
                    "id": ws.id,
                    "name": ws.name,
                    "description": ws.description
                }
                for ws in workspaces
            ]
        
        return [
            DocumentSchema(
                id=doc.id,
                dataset_id=doc.dataset_id or 1,
                name=doc.original_name or doc.name or f"未命名文档_{doc.id}",  # 使用原始文件名，如果为空则使用name字段或默认名称
                content=doc.content,
                mime_type=doc.mime_type,
                status=doc.status,
                size=format_size(doc.size) if doc.size else "0KB",
                version=doc.version,  # 添加版本信息
                file_hash=doc.file_hash[:8] if doc.file_hash else None,  # 添加文件哈希前8位
                error=doc.error,
                created_at=doc.created_at.isoformat() if doc.created_at else None,
                creator = "admin",
                workspaces=document_workspaces.get(doc.id, [])  # 添加关联的工作空间列表
            )
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload", response_model=DocumentSchema)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """上传文档"""
    try:
        # 获取默认数据集
        result = await db.execute(
            select(DBDataset).filter(DBDataset.name == "default")
        )
        default_dataset = result.scalar_one_or_none()
        if not default_dataset:
            raise HTTPException(status_code=404, detail="Default dataset not found")

        # 获取文件类型
        mime_type = file.content_type or dataset_service._get_mime_type(file.filename)
        
        # 处理文档
        document = await dataset_service.process_document(
            file=file.file,
            filename=file.filename,
            mime_type=mime_type,
            dataset_id=default_dataset.id
        )
        
        return DocumentSchema(
            id=document.id,
            dataset_id=document.dataset_id,
            name=document.original_name,  # 使用原始文件名
            content=document.content if hasattr(document, 'content') else None,
            mime_type=document.mime_type,
            status=document.status,
            size=format_size(document.size) if document.size else "0KB",
            version=document.version,  # 添加版本号
            file_hash=document.file_hash[:8] if document.file_hash else None,  # 添加文件哈希
            error=document.error if hasattr(document, 'error') else None,
            created_at=document.created_at.isoformat() if document.created_at else None
        )
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/delete")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """删除文档"""
    try:
        success = await dataset_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/status/{document_id}")
async def get_document_status(document_id: int, db: AsyncSession = Depends(get_db)):
    """获取文档处理状态"""
    try:
        service = DatasetService(db)
        status = await service.get_document_status(document_id)
        # 确保 created_at 是字符串格式
        if status.get('created_at') and isinstance(status['created_at'], datetime):
            status['created_at'] = status['created_at'].isoformat()
        return status
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/embeddings/{document_id}")
async def check_document_embeddings(document_id: int, db: AsyncSession = Depends(get_db)):
    """检查文档的向量生成情况"""
    try:
        service = DatasetService(db)
        status = await service.check_embeddings(document_id)
        return status
    except Exception as e:
        logger.error(f"Error checking embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/download/{document_id}")
async def download_document(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """下载文档"""
    try:
        # 获取文档信息
        result = await db.execute(
            select(DBDocument).filter(DBDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 检查文件是否存在
        if not document.file_path or not os.path.exists(document.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # 打开文件流
        file_stream = open(document.file_path, "rb")
        
        # 设置响应头
        headers = {
            'Content-Disposition': f'attachment; filename="{document.name}"'
        }
        
        # 返回文件流
        return StreamingResponse(
            file_stream,
            media_type=document.mime_type,
            headers=headers,
            background=lambda: file_stream.close()  # 确保文件流在响应完成后关闭
        )
        
    except Exception as e:
        logger.error(f"Error downloading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/rebuild_vectors")
async def rebuild_vectors(db: AsyncSession = Depends(get_db)):
    """重建所有文档的向量表示"""
    try:
        # 获取所有文档段
        result = await db.execute(select(DocumentSegment))
        segments = result.scalars().all()
        logger.info(f"Found {len(segments)} segments to process")
        
        # 清空现有的向量存储
        try:
            vector_store.collection.delete(ids=[str(segment.id) for segment in segments])
            logger.info("Cleared existing vectors")
        except Exception as e:
            logger.warning(f"Error clearing vectors: {e}")
        
        # 批量处理文档段
        batch_size = 10  # 每批处理10个文档
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            try:
                # 准备批量数据
                ids = [str(segment.id) for segment in batch]
                texts = [segment.content for segment in batch]
                metadatas = [{"segment_id": segment.id} for segment in batch]
                
                # 批量生成向量
                embeddings = await get_embedding(texts)
                
                # 添加到向量存储
                await vector_store.add_embeddings(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                logger.info(f"Processed batch of {len(batch)} segments")
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                continue
        
        return {
            "status": "success",
            "message": f"Successfully rebuilt vectors for {len(segments)} segments",
            "processed_count": len(segments)
        }
    except Exception as e:
        logger.error(f"Error rebuilding vectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset", response_model=ResetResponse)
async def reset_vector_store():
    """重置向量存储，清空所有数据并重新初始化"""
    try:
        # 调用 vector_store 的重置方法
        await vector_store.delete_embeddings(
            ids=vector_store.collection.get()["ids"]
        )
        return {
            "status": "success",
            "message": "Vector store has been reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting vector store: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset vector store: {str(e)}"
        ) 