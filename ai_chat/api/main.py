from fastapi import FastAPI, APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from ai_chat.database import get_db, engine, init_db, SessionLocal
from ai_chat.chat.conversation_service import ConversationService
from ai_chat.knowledge.dataset_service import DatasetService
from sqlalchemy import select
import logging
from ai_chat.models.types import Dataset as DatasetSchema, Conversation as ConversationModel, Message as MessageModel
from ai_chat.models.dataset import Dataset as DBDataset, Conversation as DBConversation
from ai_chat.api.schemas import (
    Conversation, Message, ConversationCreate, 
    MessageCreate, Document
)
from datetime import datetime
from pydantic import BaseModel
from ai_chat.api.workspace import router as workspace_router
from ai_chat.api.document import router as document_router
from .routes.templates import router as template_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chat API")

# 创建路由器
router = APIRouter()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 DatasetService 依赖
async def get_dataset_service(db: AsyncSession = Depends(get_db)) -> DatasetService:
    return DatasetService(db)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    try:
        # 初始化数据库
        await init_db()
        logger.info("Database initialized successfully")

        # 使用同步会话进行初始化
        db = SessionLocal()
        try:
            # 检查并创建默认工作组
            from ai_chat.models.workspace import Workgroup
            default_workgroup = db.query(Workgroup).filter(Workgroup.name == "default").first()
            
            if not default_workgroup:
                default_workgroup = Workgroup(
                    name="default",
                    description="Default workgroup",
                    created_at=datetime.utcnow()
                )
                db.add(default_workgroup)
                db.commit()
                logger.info("Created default workgroup")
            else:
                logger.info("Default workgroup exists")

            # 检查并创建默认工作空间
            from ai_chat.models.workspace import Workspace
            default_workspace = db.query(Workspace).filter(Workspace.name == "default").first()
            
            if not default_workspace:
                default_workspace = Workspace(
                    name="default",
                    description="Default workspace",
                    group_id=default_workgroup.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(default_workspace)
                db.commit()
                logger.info("Created default workspace")
            else:
                logger.info("Default workspace exists")

            # 检查并创建默认数据集
            default_dataset = db.query(DBDataset).filter(DBDataset.name == "default").first()
            
            if not default_dataset:
                default_dataset = DBDataset(
                    name="default",
                    description="Default dataset",
                    created_at=datetime.utcnow()
                )
                db.add(default_dataset)
                db.commit()
                logger.info("Created default dataset")
            else:
                logger.info("Default dataset exists")

            logger.info("Application startup complete")
            
        except Exception as e:
            logger.error(f"Error during startup: {e}")
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("Application shutting down")

@app.get("/")
async def root():
    """API 根路由"""
    return {"status": "ok", "message": "AI Chat API is running"}

@router.get("/conversations/list", response_model=List[Conversation])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """获取所有对话列表"""
    try:
        service = ConversationService(db)
        conversations = await service.get_conversations()
        return [
            {
                "id": conv.id,
                "name": conv.title,
                "workspace_id": conv.workspace_id,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "messages": []
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/create", response_model=Conversation)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新对话"""
    try:
        service = ConversationService(db)
        conversation = await service.create_conversation(data.name, data.workspace_id)
        return {
            "id": conversation.id,
            "name": conversation.title,
            "workspace_id": conversation.workspace_id,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "messages": []
        }
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/send-message", response_model=Message)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """发送消息并获取回复"""
    try:
        service = ConversationService(db)
        message = await service.send_message(conversation_id, data.message, data.use_rag)
        
        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "citations": message.citations if hasattr(message, 'citations') else [],
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/messages/{conversation_id}", response_model=List[Message])
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取对话的所有消息"""
    try:
        service = ConversationService(db)
        messages = await service.get_messages(conversation_id)
        return [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "citations": msg.citations if msg.citations is not None else [],
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/delete")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除对话"""
    try:
        service = ConversationService(db)
        success = await service.delete_conversation(conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



class GenerateTitleRequest(BaseModel):
    message: str

class GenerateTitleResponse(BaseModel):
    title: str

@router.post("/generate_title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest, db: AsyncSession = Depends(get_db)):
    """根据用户的第一条消息生成对话标题"""
    try:
        service = ConversationService(db)
        # 构建提示词
        prompt = f"""请为以下对话生成一个简短的标题（不超过15个字）。标题应该概括用户的主要问题或意图。
用户的问题是：{request.message}
请直接返回标题，不要包含任何其他内容。"""
        
        # 调用大模型生成标题
        message = await service.send_message(0, prompt, use_rag=False)
        title = message.content.strip().strip('"').strip()
        
        if not title:
            # 如果生成失败，使用消息的前15个字符
            title = request.message[:15] + '...' if len(request.message) > 15 else request.message
            
        return {"title": title}
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate title: {str(e)}")

# 注册路由
app.include_router(workspace_router, prefix="/api/v1", tags=["工作空间管理"])
app.include_router(document_router, prefix="/api/v1", tags=["文档管理"])
app.include_router(router, prefix="/api/v1/chat", tags=["对话管理"])
app.include_router(template_router) 