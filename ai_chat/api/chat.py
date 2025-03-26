from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..database import get_db
from ..models.conversation import DBConversation
from ..models.message import DBMessage, Message
from ..models.workspace import DBWorkspace
from ..services.chat import chat_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class ConversationBase(BaseModel):
    title: str
    workspace_id: int

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    created_at: Optional[datetime] = None
    messages: List[Message] = []

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

async def generate_title(user_message: str, ai_response: str) -> str:
    """生成对话标题"""
    try:
        # 构建提示词
        prompt = f"""请根据以下对话生成一个简短、有意义的标题（不超过20个字）：

用户：{user_message}
AI：{ai_response}

要求：
1. 标题要简洁明了，不超过20个字
2. 标题要能概括对话的主要内容
3. 不要使用标点符号
4. 不要使用"对话"、"聊天"等词
5. 直接返回标题，不要其他内容

标题："""

        # 调用AI服务生成标题
        title = await chat_service.get_chat_response(prompt)
        
        # 清理标题
        title = title.strip()
        if len(title) > 20:
            title = title[:20]
            
        return title
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}")
        # 如果生成标题失败，使用用户消息的前20个字符
        return user_message[:20] if user_message else "新对话"

@router.post("/conversations/create", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    try:
        # 检查工作空间是否存在
        workspace = await db.execute(
            select(DBWorkspace).filter(DBWorkspace.id == conversation.workspace_id)
        )
        if not workspace.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Workspace not found")

        # 获取AI回复
        logger.info(f"Getting AI response for: {conversation.title}")
        ai_response = await chat_service.get_chat_response(conversation.title)
        logger.info(f"Got AI response: {ai_response[:50]}...")

        # 生成对话标题
        logger.info("Generating conversation title...")
        title = await generate_title(conversation.title, ai_response)
        logger.info(f"Generated title: {title}")

        # 创建对话
        db_conversation = DBConversation(
            title=title,
            workspace_id=conversation.workspace_id
        )
        db.add(db_conversation)
        await db.commit()
        await db.refresh(db_conversation)
        logger.info(f"Created conversation with ID: {db_conversation.id}")

        # 添加用户消息
        user_message = DBMessage(
            conversation_id=db_conversation.id,
            role="user",
            content=conversation.title
        )
        db.add(user_message)
        await db.commit()
        logger.info(f"Added user message with ID: {user_message.id}")

        # 添加AI回复消息
        ai_message = DBMessage(
            conversation_id=db_conversation.id,
            role="assistant",
            content=ai_response
        )
        db.add(ai_message)
        await db.commit()
        logger.info(f"Added AI message with ID: {ai_message.id}")

        # 获取所有消息
        messages = await db.execute(
            select(DBMessage)
            .filter(DBMessage.conversation_id == db_conversation.id)
            .order_by(DBMessage.created_at)
        )
        message_list = messages.scalars().all()
        logger.info(f"Found {len(message_list)} messages")

        # 构建响应
        response = ConversationResponse(
            id=db_conversation.id,
            title=db_conversation.title,
            workspace_id=db_conversation.workspace_id,
            created_at=db_conversation.created_at,
            messages=message_list
        )

        return response
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 