import logging
import os
import urllib.parse
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..knowledge.dataset_service import DatasetService
from ..models.dataset import Dataset as DBDataset
from ..models.document import Document as DBDocument, DocumentWorkspace, DocumentSegment
from ..models.types import Document as DocumentSchema
from ..models.workspace import Workspace as DBWorkspace
from ..services.vector_store import vector_store
from ..utils.embeddings import get_embedding

# 配置日志
logger = logging.getLogger(__name__)

# 定义依赖函数
async def get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    return DatasetService(db)

router = APIRouter(
)



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
        # 使用异步会话查询数据库
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
    file_stream = None
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
        
        try:
            # 打开文件流
            file_stream = open(document.file_path, "rb")
            
            # 设置响应头，使用URL编码处理中文文件名
            encoded_filename = urllib.parse.quote(document.name)
            headers = {
                'Content-Disposition': f'attachment; filename="{encoded_filename}"'
            }
            
            # 定义异步清理函数
            async def cleanup():
                if file_stream:
                    file_stream.close()
            
            # 返回文件流
            return StreamingResponse(
                file_stream,
                media_type=document.mime_type,
                headers=headers,
                background=cleanup  # 使用异步清理函数
            )
        except UnicodeEncodeError as e:
            # 确保在发生编码错误时关闭文件流
            if file_stream:
                file_stream.close()
            
            logger.error(f"Encoding error while downloading document: {str(e)}")
            # 如果遇到编码问题，尝试返回文本内容
            if document.content:
                return JSONResponse(
                    content={"text": document.content},
                    status_code=200
                )
            else:
                raise HTTPException(status_code=500, detail="无法处理文件编码")
        
    except Exception as e:
        # 确保在发生任何错误时关闭文件流
        if file_stream:
            file_stream.close()
        
        logger.error(f"Error downloading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取文档内容（纯文本）"""
    try:
        # 获取文档信息
        result = await db.execute(
            select(DBDocument).filter(DBDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 如果文档有存储的文本内容，直接返回
        if document.content:
            return JSONResponse(
                content={"text": document.content},
                status_code=200
            )
            
        # 如果没有存储的文本内容，但有文件路径，尝试读取文件
        elif document.file_path and os.path.exists(document.file_path):
            try:
                # 对于PDF文件，可以尝试提取文本
                if document.mime_type == 'application/pdf':
                    # 这里可以使用PyPDF2或其他PDF解析库提取文本
                    # 此处仅作为示例，实际实现可能需要添加相应的依赖
                    return JSONResponse(
                        content={"text": "PDF文件内容无法直接显示，请下载后查看。"},
                        status_code=200
                    )
                else:
                    # 对于其他文件类型，尝试直接读取
                    with open(document.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return JSONResponse(
                        content={"text": content},
                        status_code=200
                    )
            except Exception as read_error:
                logger.error(f"Error reading file content: {str(read_error)}")
                return JSONResponse(
                    content={"text": "无法读取文件内容，可能是不支持的文件格式。"},
                    status_code=200
                )
        else:
            return JSONResponse(
                content={"text": "该文档没有可用的文本内容。"},
                status_code=200
            )
            
    except Exception as e:
        logger.error(f"Error getting document content: {str(e)}")
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