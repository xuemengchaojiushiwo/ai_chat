from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Citation(BaseModel):
    """引用模型"""
    text: str = Field(description="引用的文本内容")
    document_id: int = Field(description="文档ID")
    segment_id: int = Field(description="文档片段ID")
    index: int = Field(default=1, description="引用序号")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "text": "这是一段引用文本",
                "document_id": 1,
                "segment_id": 1,
                "index": 1
            }
        }

class MessageBase(BaseModel):
    """消息基础模型"""
    content: str

class MessageCreate(BaseModel):
    """创建消息的请求模型"""
    message: str
    use_rag: bool = False

class Message(BaseModel):
    """消息响应模型"""
    id: int
    conversation_id: int
    role: str
    content: str
    tokens: Optional[int] = None
    citations: List[Citation] = Field(default_factory=list)
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ConversationBase(BaseModel):
    """对话基础模型"""
    name: str

class ConversationCreate(BaseModel):
    name: str = "新对话"
    workspace_id: Optional[int] = None

class Conversation(BaseModel):
    id: int
    name: str
    created_at: Optional[str] = None
    messages: List[Message] = []

    class Config:
        from_attributes = True

class Document(BaseModel):
    """文档模型"""
    id: int
    dataset_id: int
    name: str
    content: str
    mime_type: str
    status: str
    error: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True 