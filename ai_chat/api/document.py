from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, func
from typing import List, Optional
from ..database import get_db
from pydantic import BaseModel
from datetime import datetime
import os
import mimetypes
from pathlib import Path
from ..models.document import Document as DBDocument, DocumentWorkspace, DocumentSegment
from ..models.workspace import Workspace
from ..knowledge.dataset_service import DatasetService
from ..models.dataset import Dataset as DBDataset
import logging
from ..models.types import Document as DocumentSchema

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

@router.get("/documents/list", response_model=List[DocumentSchema])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """获取文档列表"""
    try:
        service = DatasetService(db)
        documents = await service.get_documents()
        return [
            DocumentSchema(
                id=doc.id,
                dataset_id=doc.dataset_id or 1,
                name=doc.name,
                content=doc.content,
                mime_type=doc.mime_type,
                status=doc.status,
                error=doc.error,
                created_at=doc.created_at.isoformat() if doc.created_at else None
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
            name=document.name,
            content=document.content if hasattr(document, 'content') else None,
            mime_type=document.mime_type,
            status=document.status,
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