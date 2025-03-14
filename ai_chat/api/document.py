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
    pass

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    status: str
    workspace_ids: List[int] = []
    
    class Config:
        from_attributes = True

class DocumentStatus(BaseModel):
    """文档状态响应模型"""
    status: str
    created_at: datetime
    error: Optional[str] = None
    segments: Optional[int] = None
    segments_with_embeddings: Optional[int] = None

def validate_file_type(content_type: str) -> bool:
    """验证文件类型是否支持"""
    return content_type in SUPPORTED_MIME_TYPES

def get_file_extension(content_type: str) -> str:
    """获取文件扩展名"""
    return SUPPORTED_MIME_TYPES.get(content_type, '')

# 文档管理接口
@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    workspace_id: Optional[int] = None,
    file_type: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取文档列表，支持多种过滤条件"""
    query = select(DBDocument)
    
    if workspace_id:
        query = query.join(DocumentWorkspace).filter(DocumentWorkspace.workspace_id == workspace_id)
    
    if file_type:
        query = query.filter(DBDocument.file_type == file_type)
    
    if status:
        query = query.filter(DBDocument.status == status)
    
    if search:
        query = query.filter(
            or_(
                DBDocument.name.ilike(f"%{search}%"),
                DBDocument.description.ilike(f"%{search}%")
            )
        )
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # 获取每个文档关联的工作空间ID
    for doc in documents:
        workspace_result = await db.execute(
            select(DocumentWorkspace.workspace_id)
            .filter(DocumentWorkspace.document_id == doc.id)
        )
        doc.workspace_ids = [r[0] for r in workspace_result]
    
    return documents

@router.post("/documents", response_model=DocumentSchema)
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

@router.delete("/documents/{document_id}")
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

# 文档关联工作空间
@router.post("/documents/{document_id}/workspaces")
async def link_document_workspace(
    document_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db)
):
    """关联文档到工作空间"""
    # 检查文档是否存在
    doc_result = await db.execute(
        select(DBDocument).filter(DBDocument.id == document_id)
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 检查工作空间是否存在
    workspace_result = await db.execute(
        select(Workspace).filter(Workspace.id == workspace_id)
    )
    if not workspace_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # 检查关联是否已存在
    existing = await db.execute(
        select(DocumentWorkspace).filter(
            DocumentWorkspace.document_id == document_id,
            DocumentWorkspace.workspace_id == workspace_id
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already linked"}
    
    # 创建关联
    link = DocumentWorkspace(
        document_id=document_id,
        workspace_id=workspace_id
    )
    db.add(link)
    await db.commit()
    
    return {"status": "success"}

@router.delete("/documents/{document_id}/workspaces/{workspace_id}")
async def unlink_document_workspace(
    document_id: int,
    workspace_id: int,
    db: AsyncSession = Depends(get_db)
):
    """解除文档与工作空间的关联"""
    result = await db.execute(
        delete(DocumentWorkspace).where(
            DocumentWorkspace.document_id == document_id,
            DocumentWorkspace.workspace_id == workspace_id
        )
    )
    
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Document-workspace link not found")
    
    return {"status": "success"}

@router.get("/documents/{document_id}/status", response_model=DocumentStatus)
async def get_document_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """获取文档处理状态"""
    try:
        # 首先检查文档是否存在
        result = await db.execute(
            select(DBDocument).filter(DBDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
            
        # 获取文档状态
        status = {
            "status": document.status,
            "created_at": document.created_at,
            "error": document.error if hasattr(document, 'error') else None
        }
        
        # 如果文档已处理完成，获取段落信息
        if document.status == "processed":
            segments_result = await db.execute(
                select(func.count()).select_from(DocumentSegment)
                .filter(DocumentSegment.document_id == document_id)
            )
            total_segments = segments_result.scalar()
            
            segments_with_embeddings = await db.execute(
                select(func.count()).select_from(DocumentSegment)
                .filter(
                    DocumentSegment.document_id == document_id,
                    DocumentSegment.embedding.isnot(None)
                )
            )
            embedded_segments = segments_with_embeddings.scalar()
            
            status.update({
                "segments": total_segments,
                "segments_with_embeddings": embedded_segments
            })
            
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 