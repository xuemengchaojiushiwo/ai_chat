from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ai_chat.models import Conversation, Message, DBDocument
from ai_chat.database import get_db
from ai_chat.utils import logger

router = APIRouter()

@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取对话详情"""
    try:
        # 获取对话信息
        result = await db.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # 获取对话消息
        messages_result = await db.execute(
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = messages_result.scalars().all()
        
        # 收集所有引用的文档ID
        document_ids = set()
        for message in messages:
            if message.citations:
                for citation in message.citations:
                    if citation.document_id:
                        document_ids.add(citation.document_id)
        
        # 获取文档信息
        documents = []
        if document_ids:
            docs_result = await db.execute(
                select(DBDocument).filter(DBDocument.id.in_(list(document_ids)))
            )
            documents = docs_result.scalars().all()
        
        # 构建文档下载信息
        document_downloads = []
        for doc in documents:
            document_downloads.append({
                "id": doc.id,
                "name": doc.name,
                "mime_type": doc.mime_type,
                "file_path": doc.file_path,
                "size": doc.size if hasattr(doc, 'size') else None,
                "download_url": f"/api/v1/documents/download/{doc.id}"
            })
        
        # 构建响应
        return {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "messages": [message.to_dict() for message in messages],
            "documents": document_downloads  # 添加文档下载信息
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 