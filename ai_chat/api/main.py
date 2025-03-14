from fastapi import FastAPI, APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from ai_chat.database import get_db, engine, init_db
from ai_chat.chat.conversation_service import ConversationService
from ai_chat.knowledge.dataset_service import DatasetService
from sqlalchemy import select
import logging
from ..models.types import Dataset as DatasetSchema, Conversation as ConversationModel, Message as MessageModel
from ..models.dataset import Dataset as DBDataset, Conversation as DBConversation  # 导入 SQLAlchemy 模型和数据库模型
from .schemas import (
    Conversation, Message, ConversationCreate, 
    MessageCreate, Document
)
from datetime import datetime
from pydantic import BaseModel
from ai_chat.api.workspace import router as workspace_router
from ai_chat.api.document import router as document_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chat API")

# 创建路由器
router = APIRouter(prefix="/chat")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 允许的前端地址
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
        await init_db()
        logger.info("Database initialized successfully")

        # 检查数据库连接
        async with engine.connect() as conn:
            await conn.execute(select(1))
            logger.info("Database connection successful")

            # 检查是否存在默认数据集
            async with AsyncSession(engine) as session:
                result = await session.execute(
                    select(DBDataset).filter(DBDataset.name == "default")
                )
                default_dataset = result.scalar_one_or_none()
                
                if not default_dataset:
                    # 创建默认数据集
                    default_dataset = DBDataset(
                        name="default", 
                        description="Default dataset"
                    )
                    session.add(default_dataset)
                    await session.commit()
                    logger.info("Created default dataset")
                else:
                    logger.info("Default dataset exists")

        logger.info("Application startup complete")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    logger.info("Application shutting down")

@router.get("/")
async def root():
    return {"message": "AI Chat API"}

@router.get("/conversations", response_model=List[Conversation])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """获取所有对话列表"""
    try:
        service = ConversationService(db)
        conversations = await service.get_conversations()
        return [
            {
                "id": conv.id,
                "name": conv.title,  # 从 title 映射到 name
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "messages": []
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations", response_model=Conversation)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    """创建新对话"""
    try:
        service = ConversationService(db)
        name = str(data.name) if data.name else "新对话"
        
        # 确保记录工作空间ID
        logger.info(f"Creating conversation with workspace_id: {data.workspace_id}")
        
        conversation = await service.create_conversation(
            name=name,
            workspace_id=data.workspace_id
        )
        
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

@router.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """获取对话消息历史"""
    try:
        conversation_service = ConversationService(db)
        messages = await conversation_service.get_messages(conversation_id)
        return [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "role": msg.role,
                "content": msg.content,
                "citations": msg.citations if hasattr(msg, 'citations') else [],
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversations/{conversation_id}/messages", response_model=Message)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """发送消息并获取回复"""
    try:
        service = ConversationService(db)
        message = await service.send_message(conversation_id, data.message, data.use_rag)
        
        # 手动构建响应对象，而不是调用 to_dict()
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

@router.get("/documents", response_model=List[Document])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """获取文档列表"""
    try:
        service = DatasetService(db)
        documents = await service.get_documents()
        return [
            Document(
                id=doc.id,
                dataset_id=doc.dataset_id or 1,  # 使用默认数据集ID
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

@router.post("/documents", response_model=Document)
async def upload_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    dataset_service: DatasetService = Depends(get_dataset_service)
):
    """上传文档"""
    try:
        # 获取文件类型
        mime_type = dataset_service._get_mime_type(file.filename)
        
        # 处理文档
        document = await dataset_service.process_document(
            file=file.file,
            filename=file.filename,
            mime_type=mime_type
        )
        
        return Document(
            id=document.id,
            dataset_id=document.dataset_id or 1,
            name=document.name,
            content=document.content,
            mime_type=document.mime_type,
            status=document.status,
            error=document.error,
            created_at=document.created_at.isoformat() if document.created_at else None
        )
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """删除文档"""
    try:
        service = DatasetService(db)
        success = await service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/status")
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

@router.get("/documents/{document_id}/embeddings")
async def check_document_embeddings(document_id: int, db: AsyncSession = Depends(get_db)):
    """检查文档的向量生成情况"""
    try:
        service = DatasetService(db)
        status = await service.check_embeddings(document_id)
        return status
    except Exception as e:
        logger.error(f"Error checking embeddings: {str(e)}")
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
app.include_router(workspace_router, prefix="/api")
app.include_router(document_router, prefix="/api")

# 将路由器包含到应用中
app.include_router(router) 